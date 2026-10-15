#!/usr/bin/env python3
"""Explicit-path commit/push: workers own branches; Captain owns main. No CI or merges."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROLES = ('captain', 'head', 'agent-a', 'agent-b', 'agent-c')

def valid_branch(role, branch):
    if role in ('captain', 'head'):  # head is a legacy CLI alias only
        return branch == 'main' or branch.startswith('integration/')
    return bool(re.fullmatch(r'work/' + re.escape(role) + r'/[A-Za-z0-9][A-Za-z0-9._/-]*', branch))

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-m', required=True)
    parser.add_argument('--files', nargs='+', required=True)
    parser.add_argument('--push', action='store_true')
    parser.add_argument('--role', choices=ROLES, required=True)
    args = parser.parse_args()
    def git(*x):
        return subprocess.check_output(['git', *x], cwd=root).decode().strip()
    branch = git('branch', '--show-current')
    if not valid_branch(args.role, branch):
        raise SystemExit('Wrong branch: workers use work/<agent-a|agent-b|agent-c>/<task>; only Captain uses main/integration.')
    subprocess.run(['git', 'check-ref-format', '--branch', branch], cwd=root, check=True, stdout=subprocess.DEVNULL)
    if not re.match(r'^(feat|fix|chore|docs|test|refactor)(\([\w-]+\))?!?: .+', args.m):
        raise SystemExit('Use a conventional commit message')
    if git('diff', '--cached', '--name-only'):
        raise SystemExit('Index is not empty; review existing staged changes first')
    subprocess.run([sys.executable, str(root / 'tool/preflight.py')], cwd=root, check=True)
    subprocess.run(['git', 'add', '--', *args.files], cwd=root, check=True)
    subprocess.run(['git', 'diff', '--cached', '--check'], cwd=root, check=True)
    subprocess.run(['git', 'commit', '-m', args.m], cwd=root, check=True)
    if args.push:
        # Normal fast-forward push only; reject races without force/rebase/retry.
        subprocess.run(['git', 'push', '-u', 'origin', 'HEAD:refs/heads/' + branch], cwd=root, check=True)
        local = git('rev-parse', 'HEAD')
        remote = git('ls-remote', 'origin', 'refs/heads/' + branch).split()[0]
        if local != remote:
            raise SystemExit('SHA mismatch; stop and inspect, no automatic force/retry')
        print('Verified branch:', branch, 'SHA:', local)
    print('Captain reviews branch/SHA before merging main. CI NOT dispatched. No merge performed.')

if __name__ == '__main__':
    main()
