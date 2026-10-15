#!/usr/bin/env python3
"""Local configuration report. Never reads or prints secret values."""
import json,re,shutil
from pathlib import Path
r=Path(__file__).resolve().parents[1]
checks={}
for name in ('git','python3'): checks[name]=bool(shutil.which(name))
for name in ('Assets','Packages/manifest.json','ProjectSettings/ProjectVersion.txt','unity-kit.json'):
    checks[name]=(r/name).exists()
p=r/'ProjectSettings/ProjectVersion.txt'
if p.exists():
    match=re.search(r'm_EditorVersion: (\S+)',p.read_text());print('Pinned Unity:',match[1] if match else 'INVALID')
print(json.dumps(checks,indent=2))
print('Unity is not needed locally. Configure license/signing secrets in GitHub UI; see docs/SETUP.md.')
raise SystemExit(0 if all(checks.values()) else 1)
