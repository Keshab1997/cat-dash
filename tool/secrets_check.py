#!/usr/bin/env python3
"""Safe presence/format/local-signing checks. Optional Google OAuth + read-only Play request.
Never prints credentials, tokens, command output, file paths or server response bodies.
"""
import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NAMES=('UNITY_LICENSE','UNITY_EMAIL','UNITY_PASSWORD','ANDROID_KEYSTORE_BASE64',
       'KEYSTORE_PASSWORD','KEY_ALIAS','KEY_PASSWORD','PLAY_SERVICE_ACCOUNT_JSON')
SIGNING=('ANDROID_KEYSTORE_BASE64','KEYSTORE_PASSWORD','KEY_ALIAS','KEY_PASSWORD')

def formats(env):
    rows=[]
    for name in NAMES:
        value=env.get(name,'');present=bool(value.strip());ok=None;detail='Not configured'
        if present:
            ok=True;detail='Present only; runtime not verified'
            if name=='UNITY_LICENSE':
                try:
                    root=ET.fromstring(value)
                    ok=any(e.tag.lower().split('}')[-1]=='license' for e in root.iter())
                except ET.ParseError: ok=False
                detail='License XML structure only; Unity activation NOT verified' if ok else 'Invalid or unexpected license XML'
            elif name=='UNITY_EMAIL':
                ok=bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value))
                detail='Email shape only; login NOT verified' if ok else 'Invalid email shape'
            elif name=='ANDROID_KEYSTORE_BASE64':
                try: ok=bool(base64.b64decode(''.join(value.split()),validate=True))
                except (ValueError,TypeError):ok=False
                detail='Base64 decodes; signing test below' if ok else 'Invalid or empty Base64'
            elif name=='PLAY_SERVICE_ACCOUNT_JSON':
                try:
                    d=json.loads(value)
                    ok=isinstance(d,dict) and d.get('type')=='service_account' and bool(re.fullmatch(r'[^\s@]+@[^\s@]+',d.get('client_email',''))) and 'BEGIN PRIVATE KEY' in d.get('private_key','')
                except (ValueError,TypeError):ok=False
                detail='Service-account JSON shape only; authentication NOT verified' if ok else 'Invalid service-account JSON structure'
        rows.append((name,present,ok,detail))
    return rows

def run(cmd,env=None,input=None):
    return subprocess.run(cmd,input=input,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False)

def signing_check(env):
    if not all(env.get(n,'').strip() for n in SIGNING):return False,'Signing test skipped: required secrets missing'
    if not shutil.which('jarsigner'):return None,'Signing test not run: JDK jarsigner unavailable'
    try:
        data=base64.b64decode(''.join(env['ANDROID_KEYSTORE_BASE64'].split()),validate=True)
        with tempfile.TemporaryDirectory(prefix='unity-secret-check-') as directory:
            key=Path(directory)/'upload.keystore';key.write_bytes(data);key.chmod(0o600)
            jar=Path(directory)/'probe.jar'
            with zipfile.ZipFile(jar,'w') as archive:
                archive.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\n\n')
                archive.writestr('probe.txt','local credential check only; not an app build')
            safe_env=dict(os.environ);safe_env.update({n:env[n] for n in ('KEYSTORE_PASSWORD','KEY_PASSWORD')})
            # Avoid interactive stdin and never put passwords on command line.
            result=run(['jarsigner','-keystore',str(key),'-storepass:env','KEYSTORE_PASSWORD',
                        '-keypass:env','KEY_PASSWORD',str(jar),env['KEY_ALIAS']],env=safe_env,input=b'')
            if result.returncode:return False,'Local JAR signing failed: inspect keystore/passwords/alias (details suppressed)'
            verified=run(['jarsigner','-verify',str(jar)],input=b'')
            if verified.returncode:return False,'Local signed probe could not be verified'
        return True,'Local JAR signed and verified; does NOT confirm the Play upload-key match'
    except Exception:return False,'Local signing validation failed (sensitive diagnostics suppressed)'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def request(url,body=None,token=None):
    headers={'Content-Type':'application/x-www-form-urlencoded'} if body else {}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(url,data=body,headers=headers)
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=20) as response:return json.load(response)

def live_play_check(env,package):
    """Explicit opt-in only. Fixed Google endpoints; no upload/edit/release API calls."""
    try:
        account=json.loads(env.get('PLAY_SERVICE_ACCOUNT_JSON',''))
        if not isinstance(account,dict) or account.get('type')!='service_account':return [(False,'Google OAuth: invalid service-account JSON')]
        now=int(time.time())
        def b64(data):return base64.urlsafe_b64encode(data).rstrip(b'=')
        head=b64(json.dumps({'alg':'RS256','typ':'JWT'}).encode())
        claims=b64(json.dumps({'iss':account['client_email'],'scope':'https://www.googleapis.com/auth/androidpublisher',
                    'aud':'https://oauth2.googleapis.com/token','iat':now,'exp':now+300}).encode())
        signing=head+b'.'+claims
        with tempfile.TemporaryDirectory(prefix='unity-oauth-check-') as directory:
            key=Path(directory)/'key.pem';key.write_text(account['private_key']);key.chmod(0o600)
            signed=run(['openssl','dgst','-sha256','-sign',str(key)],input=signing)
        if signed.returncode:return [(False,'Google OAuth: private key cannot sign')]
        assertion=(signing+b'.'+b64(signed.stdout)).decode()
        body=urllib.parse.urlencode({'grant_type':'urn:ietf:params:oauth:grant-type:jwt-bearer','assertion':assertion}).encode()
        try:auth=request('https://oauth2.googleapis.com/token',body=body)
        except urllib.error.HTTPError as error:return [(False,f'Google OAuth: rejected (HTTP {error.code}); response suppressed')]
        token=auth.get('access_token')
        if not token:return [(False,'Google OAuth: no access token returned')]
        rows=[(True,'Google OAuth authenticated; key accepted, app permissions not yet verified')]
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*){2,}',package):
            return rows+[(False,'Play app read check: invalid package ID')]
        url='https://androidpublisher.googleapis.com/androidpublisher/v3/applications/'+urllib.parse.quote(package,safe='')+'/inappproducts?maxResults=1'
        try:request(url,token=token)
        except urllib.error.HTTPError as error:
            return rows+[(False,f'Play app product-list read check: HTTP {error.code}; check API/app access; NOT an upload test')]
        return rows+[(True,'Play app product-list read access succeeded; release/upload permission NOT verified')]
    except Exception:return [(False,'Live check failed: configuration/network/key issue; sensitive diagnostics suppressed')]

def report(env,summary=None):
    rows=formats(env)
    lines=['# Secrets Check','', 'Presence is NOT proof of working credentials. No values are shown.', '',
           '| Secret name | Present | Basic validation |','|---|---|---|']
    failed=False
    for name,present,ok,detail in rows:
        failed|=not present or ok is False
        lines.append(f'| `{name}` | {"✅" if present else "❌"} | {"✅" if ok else "❌"} {detail} |')
    status,detail=signing_check(env);failed|=status is False
    lines+=['','## Local signing check',f'{"✅" if status else "⚪" if status is None else "❌"} {detail}']
    if env.get('CHECK_PLAY_LIVE')=='true':
        try:package=json.loads(Path('unity-kit.json').read_text()).get('packageName','')
        except Exception:package=''
        for ok,detail in live_play_check(env,package):
            failed|=not ok;lines+=['',f'{"✅" if ok else "❌"} {detail}']
    else:lines+=['','⚪ Google OAuth / Play read check NOT RUN (optional checkbox was off).']
    lines+=['','## Still unverified','- Unity login/license activation: run the existing Unity Android tests manually.',
            '- PKCS12 can reuse the store password and ignore a separate key password; KEY_PASSWORD is not independently proven in that case.',
            '- Play upload key match, release permissions and actual AAB acceptance: NOT tested here.',
            '- Missing signing/Play secrets may be intentional before build/upload; report them honestly.',
            '- No Unity download/build, application upload, edit/release creation or secret/settings change.']
    text='\n'.join(lines)+'\n'
    print(text)
    if summary:
        with open(summary,'a') as stream:stream.write(text)
    return 1 if failed else 0

if __name__=='__main__':
    try:code=report(os.environ,os.environ.get('GITHUB_STEP_SUMMARY'))
    except Exception:
        print('Secrets Check could not complete; sensitive diagnostics suppressed.');code=1
    raise SystemExit(code)
