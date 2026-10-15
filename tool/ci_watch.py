#!/usr/bin/env python3
"""Read ONE human-dispatched run. No dispatch, waiting, retry or download of secret artifacts."""
import argparse,os,urllib.request,json,sys
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--run',type=int,required=True);p.add_argument('--failed-log',action='store_true');a=p.parse_args()
if a.run<=0: p.error('run must be a real run ID from GitHub')
t=os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
if not t: sys.exit('Set GH_TOKEN securely in the process environment; never paste it into chat.')
def get(path,raw=False):
    req=urllib.request.Request('https://api.github.com'+path,headers={'Authorization':'Bearer '+t,'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=30) as resp:
        return resp.read().decode(errors='replace') if raw else json.load(resp)
r=get(f'/repos/{a.repo}/actions/runs/{a.run}')
print(json.dumps({k:r.get(k) for k in ('id','head_sha','status','conclusion','html_url')},indent=2))
if a.failed_log:
    jobs=get(f'/repos/{a.repo}/actions/runs/{a.run}/jobs?per_page=100')['jobs']
    for j in jobs:
        if j['conclusion'] in ('failure','timed_out'):
            print('FAILED JOB:',j['name']);print(get(f'/repos/{a.repo}/actions/jobs/{j["id"]}/logs',True))
