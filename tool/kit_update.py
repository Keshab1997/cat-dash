#!/usr/bin/env python3
"""Review-first updater. Check is read-only; apply requires an exact reviewed commit.
Only toolkit instructions/tools/workflows update. No game files, deletes or auto-push.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

REMOTE = 'https://github.com/Keshab1997/unity-agent-kit.git'
SOURCE = 'Keshab1997/unity-agent-kit'
START = '<!-- unity-agent-kit:start -->'
END = '<!-- unity-agent-kit:end -->'
PROTECTED = {'unity-kit.json', 'docs/GAME_BRIEF.md', 'docs/ASSETS.md', 'docs/HANDOFF.md'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def eligible(name):
    path = PurePosixPath(name)
    return (bool(path.parts) and not path.is_absolute() and '..' not in path.parts and '\\' not in name
            and name not in PROTECTED and (name in {'AGENTS.md', '.gitignore'}
            or path.parts[0] in {'tool', 'agents', 'docs'}
            or name.startswith('.github/workflows/')))

def safe_path(root, name):
    if not eligible(name):
        raise ValueError('Forbidden toolkit path: ' + name)
    path = root / name
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Symlink path rejected: ' + name)
    if path.exists() and not path.is_file():
        raise ValueError('Not a regular file: ' + name)
    return path

def block(text):
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError('Malformed managed AGENTS block')
    a = text.index(START)
    b = text.index(END) + len(END)
    if b <= a:
        raise ValueError('Malformed managed AGENTS block order')
    return a, b, text[a:b]

def plan(root, incoming, baseline, receipt, allow_workflows=False):
    """Pure planning: no writes. Baseline is read from the locked source commit."""
    changes, conflicts, approvals, notes = {}, [], [], []
    hashes = dict(receipt.get('files', {}))
    for name, data in sorted(incoming.items()):
        if not eligible(name):
            notes.append('PROTECTED ' + name)
            continue
        path = safe_path(root, name)
        current = path.read_bytes() if path.exists() else None
        old = baseline.get(name)
        # Already manually synced, or unchanged upstream: preserve local customization.
        if current == data or (old == data and current is not None):
            hashes[name] = sha(data)
            continue
        output = data
        if current is not None:
            if name == 'AGENTS.md':
                if old is None:
                    conflicts.append(name)
                    continue
                a, b, actual = block(current.decode())
                _, _, previous = block(old.decode())
                _, _, new = block(data.decode())
                if actual not in {previous, new}:
                    conflicts.append(name)
                    continue
                output = (current.decode()[:a] + new + current.decode()[b:]).encode()
            elif name == '.gitignore':
                lines = current.decode().splitlines()
                additions = [line for line in data.decode().splitlines() if line and line not in lines]
                output = current + (b'\n' if current and not current.endswith(b'\n') else b'')
                output += ('\n'.join(additions) + ('\n' if additions else '')).encode()
            elif old is None or current != old:
                conflicts.append(name)
                continue
        if current != output:
            changes[name] = output
            if name.startswith('.github/workflows/') and not allow_workflows:
                approvals.append(name)
        hashes[name] = sha(data)
    # Never delete removed source files. Keep their old baselines for transparency.
    for name in baseline.keys() - incoming.keys():
        if eligible(name):
            notes.append('RETAIN REMOVED UPSTREAM ' + name)
    return changes, conflicts, approvals, notes, hashes

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE, timeout=60).decode().strip()

def source_files(repo, revision):
    result = {}
    names = git(repo, 'ls-tree', '-r', '--name-only', revision, '--', 'template/').splitlines()
    for path in names:
        name = path.removeprefix('template/')
        if not eligible(name):
            continue
        mode = git(repo, 'ls-tree', revision, '--', path).split()[0]
        if mode != '100644' and mode != '100755':
            raise ValueError('Non-regular source entry: ' + name)
        result[name] = subprocess.check_output(['git', '-C', str(repo), 'show', revision + ':' + path], timeout=30)
    return result

def apply_transaction(root, changes, lock_data, preflight=True):
    """Rollback changed contents on handled write/preflight failure (not crash-proof)."""
    payload = dict(changes)
    payload['unity-kit.lock.json'] = lock_data
    old = {}
    for name in payload:
        path = root / name
        if name != 'unity-kit.lock.json':
            safe_path(root, name)
        if path.is_symlink():
            raise ValueError('Symlink rejected: ' + name)
        old[name] = path.read_bytes() if path.exists() else None
    try:
        for name, data in payload.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
            try:
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        if preflight:
            subprocess.run([sys.executable, str(root / 'tool/preflight.py')], cwd=root, check=True, timeout=30)
    except Exception:
        for name, data in old.items():
            path = root / name
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        raise ValueError('Apply failed; changed file contents restored. Review working tree before retry.') from None

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    parser.add_argument('--ref', help='Exact reviewed 40-character commit; check defaults to current main')
    parser.add_argument('--approve-workflows', action='store_true', help='Owner explicitly approved these workflow changes')
    args = parser.parse_args()
    if args.apply and not args.ref:
        parser.error('--apply requires --ref <reviewed full commit SHA>')
    if args.ref and not re.fullmatch('[a-f0-9]{40}', args.ref):
        parser.error('--ref must be a full lowercase 40-character commit SHA')
    root = Path(__file__).resolve().parents[1]
    lock = root / 'unity-kit.lock.json'
    if lock.is_symlink():
        raise ValueError('Lockfile symlink rejected')
    receipt = json.loads(lock.read_text())
    base = receipt.get('revision', '')
    if receipt.get('source') != SOURCE or not re.fullmatch('[a-f0-9]{40}', base):
        raise ValueError('Unsupported source/receipt revision; resolve manually')
    if args.apply and git(root, 'status', '--porcelain'):
        raise ValueError('Apply requires a clean committed working tree; do not discard local work')
    with tempfile.TemporaryDirectory(prefix='unity-kit-update-') as directory:
        repo = Path(directory) / 'kit'
        subprocess.run(['git', 'clone', '--quiet', '--no-checkout', REMOTE, str(repo)], check=True, timeout=120)
        target = args.ref or git(repo, 'rev-parse', 'origin/main')
        if git(repo, 'rev-parse', target + '^{commit}') != target:
            raise ValueError('Target commit mismatch')
        incoming = source_files(repo, target)
        baseline = source_files(repo, base)
        changes, conflicts, approvals, notes, hashes = plan(root, incoming, baseline, receipt, args.approve_workflows)
        print('Installed:', base, '\nCandidate:', target)
        for name in changes:
            print('UPDATE', name)
        for name in conflicts:
            print('CONFLICT — manual merge required:', name)
        for name in approvals:
            print('APPROVAL REQUIRED — workflow:', name)
        for note in notes:
            print(note)
        print('Protected: game assets/code/settings/identity and project-authored brief/register/handoff. No deletes.')
        if args.check:
            print('Check only. No project writes, preflight, commit/push, CI or secrets/settings change.')
            return 1 if conflicts or approvals else 0
        if conflicts or approvals:
            print('Nothing applied. Resolve conflicts or obtain explicit workflow approval first.')
            return 1
        updated = dict(receipt, revision=target, files=hashes, protected_seed_files_not_updated=True)
        apply_transaction(root, changes, (json.dumps(updated, indent=2) + '\n').encode())
        print('Applied + preflight passed. Review diff and commit manually. No push/CI/upload performed.')
        return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError):
        print('Updater stopped safely: invalid/conflicting paths, source/receipt, network/git, dirty tree or apply failure. Review state; no automatic retry.')
        raise SystemExit(1)
