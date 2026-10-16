#!/usr/bin/env python3
"""Cheap tracked+untracked source checks. Never invokes Unity/network. No secret values printed."""
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_SUFFIXES = {'.jks', '.keystore', '.ulf', '.alf', '.p12', '.pem'}
BANNED_DIRS = {'library', 'temp', 'obj', 'logs', 'usersettings', 'build', 'builds', 'secrets'}
SECRET_PATTERNS = [re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),
                   re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
                   re.compile(r'"type"\s*:\s*"service_account"'),
                   re.compile(r'\b(?:storePassword|keyPassword|storekey|keyAlias)\s*[=:]\s*[\'"][^\'"]+[\'"]')]

def inspect(root, files):
    errors=[]
    guids={}
    known=set(files)
    for name in files:
        p=root/name
        if not p.is_file(): continue
        parts=Path(name).parts
        if '.git' in parts: continue
        if any(x.lower() in BANNED_DIRS for x in parts[:-1]):
            errors.append(f'{name}: generated/secret directory must not enter git')
        if p.suffix.lower() in SECRET_SUFFIXES or p.name in {'key.properties','google-services.json','gh_token.txt','gh_refresh_token.txt'}:
            errors.append(f'{name}: forbidden credential/license file')
        if p.stat().st_size>10*1024*1024:
            if not (root/'.gitattributes').exists(): errors.append(f'{name}: large file; define/review LFS policy')
            continue
        try: text=p.read_text(encoding='utf-8')
        except (UnicodeError, OSError): continue
        if re.search(r'^(?:<{7} |={7}$|>{7} )',text,re.M): errors.append(f'{name}: merge conflict marker')
        if any(pattern.search(text) for pattern in SECRET_PATTERNS): errors.append(f'{name}: possible secret (value suppressed)')
        if p.suffix=='.py':
            try: ast.parse(text,filename=name)
            except SyntaxError as e: errors.append(f'{name}:{e.lineno}: Python syntax error')
        if p.suffix in {'.json','.asmdef'}:
            try: json.loads(text)
            except ValueError: errors.append(f'{name}: invalid JSON')
        if name.startswith('Assets/'):
            if p.suffix=='.meta':
                asset=root/name[:-5]
                if not asset.exists(): errors.append(f'{name}: orphan meta')
                m=re.search(r'^guid: ([a-f0-9]{32})$',text,re.M)
                if not m: errors.append(f'{name}: missing/invalid GUID')
                elif m[1] in guids: errors.append(f'{name}: duplicate GUID with {guids[m[1]]}')
                else: guids[m[1]]=name
            elif name+'.meta' not in known: errors.append(f'{name}: missing tracked .meta')
            parent=p.parent
            while parent!=root/'Assets' and parent.is_relative_to(root/'Assets'):
                rel=parent.relative_to(root).as_posix()+'.meta'
                if rel not in known: errors.append(f'{rel}: missing folder .meta')
                parent=parent.parent
    config=root/'unity-kit.json'
    if config.exists():
        try:
            c=json.loads(config.read_text())
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*){2,}',c['packageName']): errors.append('unity-kit.json: invalid packageName')
            if c.get('projectPath')!='.': errors.append('unity-kit.json: this kit currently supports Unity at repo root only')
            if not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?',c.get('versionName','')): errors.append('unity-kit.json: versionName must be semver')
        except (KeyError,ValueError): errors.append('unity-kit.json: invalid configuration')
    return sorted(set(errors))

def main():
    cmd=['git','ls-files','-z','--cached','--others','--exclude-standard']
    files=subprocess.check_output(cmd,cwd=ROOT).decode().split('\0')
    errors=inspect(ROOT,[p for p in files if p])
    for e in errors: print('ERROR:',e)
    print(f'Preflight: {len(errors)} error(s). Static checks only; Unity not run.')
    return bool(errors)
if __name__=='__main__': raise SystemExit(main())
