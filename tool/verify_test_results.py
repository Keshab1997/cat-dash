#!/usr/bin/env python3
"""Reject missing XML, empty filters, failed/inconclusive tests; skipped-only is not success."""
import argparse,sys,xml.etree.ElementTree as ET
from pathlib import Path

def verify(directory,need_both=False):
    files=list(Path(directory).rglob('*.xml'));results=[];errors=[]
    for file in files:
        try: root=ET.parse(file).getroot()
        except ET.ParseError: continue
        if root.tag not in {'test-run','test-results'}: continue
        cases=root.findall('.//test-case');passed=sum(c.get('result','').lower() in {'passed','success'} for c in cases)
        bad=[c for c in cases if c.get('result','').lower() not in {'passed','success','skipped','ignored'}]
        if not passed or bad or root.get('result','').lower() in {'failed','failure'}:
            errors.append(f'{file.name}: no passing tests or failed/inconclusive results')
        results.append((file,root))
    if not results: errors.append('No Unity NUnit results found; test execution is unverified')
    if need_both:
        modes=set()
        for file,root in results:
            text=(str(file)+' '+ET.tostring(root,encoding='unicode')).lower()
            for mode in ('editmode','playmode'):
                if mode in text: modes.add(mode)
        if modes!={'editmode','playmode'}: errors.append('Full stage requires evidence of BOTH EditMode and PlayMode')
    return errors
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--both',action='store_true');a=p.parse_args()
    errors=verify(a.directory,a.both)
    for e in errors: print('ERROR:',e)
    print('Unity result gate:', 'FAIL' if errors else 'PASS (not device QA)')
    sys.exit(bool(errors))
