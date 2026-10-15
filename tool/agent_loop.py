#!/usr/bin/env python3
"""Integrator-only commit/push. Explicit files; no git-add-all, CI dispatch, or retries."""
import argparse,re,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('-m',required=True);p.add_argument('--files',nargs='+',required=True);p.add_argument('--push',action='store_true');p.add_argument('--role',choices=['head'],required=True);a=p.parse_args()
def git(*x): return subprocess.check_output(['git',*x],cwd=r).decode().strip()
if git('branch','--show-current')!='main': sys.exit('Integrator must be on main')
if not re.match(r'^(feat|fix|chore|docs|test|refactor)(\([\w-]+\))?: .+',a.m): sys.exit('Use a conventional commit message')
if git('diff','--cached','--name-only'): sys.exit('Index is not empty; review existing staged changes first')
subprocess.run([sys.executable,str(r/'tool/preflight.py')],cwd=r,check=True)
subprocess.run(['git','add','--',*a.files],cwd=r,check=True)
subprocess.run(['git','diff','--cached','--check'],cwd=r,check=True)
subprocess.run(['git','commit','-m',a.m],cwd=r,check=True)
if a.push:
    subprocess.run(['git','push','origin','main'],cwd=r,check=True)
    local=git('rev-parse','HEAD');remote=git('ls-remote','origin','refs/heads/main').split()[0]
    if local!=remote: sys.exit('SHA mismatch; stop and inspect, no automatic force/retry')
    print('Verified local == remote:',local)
print('batch ready — Actions → Unity Android → Run workflow. CI NOT dispatched.')
