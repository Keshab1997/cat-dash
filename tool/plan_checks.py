#!/usr/bin/env python3
"""Advisory risk plan; no test execution and no auto-dispatch."""
import argparse,json,subprocess
from pathlib import Path

def plan(files):
    files=[x for x in files if x]
    risky=any(x.startswith(('Packages/','ProjectSettings/','Assets/Editor/')) or
              x.endswith(('.unity','.prefab','.asmdef','.shader','.mat')) or
              any(s in x.lower() for s in ('shared/','physics/','camera/')) for x in files)
    if not files or all(x.endswith(('.md','.txt')) or x.startswith('docs/') for x in files): stage='preflight'
    elif risky: stage='full'
    elif any(x.endswith('.cs') for x in files): stage='targeted'
    else: stage='review'
    return {'recommended':stage,'changed':files,'advisory':True,
            'next':'Head reviews scope. For targeted supply exact test filter. Never launch CI automatically.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    names=subprocess.check_output(['git','diff','--name-only',a.base,'--'],cwd=root).decode().splitlines()
    names+=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=root).decode().splitlines()
    print(json.dumps(plan(sorted(set(names))),indent=2))
