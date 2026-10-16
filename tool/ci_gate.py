#!/usr/bin/env python3
"""Fail fast before downloading Unity. Environment-only inputs avoid shell injection."""
import json,os,re,sys
from pathlib import Path

def validate(env,config):
    stage=env.get('KIT_STAGE','preflight');errors=[]
    if stage not in {'preflight','targeted','full','build','apk','internal'}: return ['Unknown stage']
    if stage=='preflight': return errors
    for key in ('UNITY_LICENSE','UNITY_EMAIL','UNITY_PASSWORD'):
        if not env.get(key): errors.append(f'Missing GitHub secret: {key}')
    if stage=='targeted' and not re.fullmatch(r'[A-Za-z0-9_.;,]+',env.get('KIT_FILTER','')):
        errors.append('Targeted stage requires exact class/method filter (letters/digits/underscore/dot/semicolon/comma only)')
    if stage in {'build','internal','apk'}:
        for key in ('ANDROID_KEYSTORE_BASE64','KEYSTORE_PASSWORD','KEY_ALIAS','KEY_PASSWORD'):
            if not env.get(key): errors.append(f'Missing GitHub secret: {key}')
        code=env.get('KIT_VERSION_CODE','')
        if stage=='apk' and code=='': code='1'  # a sideloaded phone build needs no Play versionCode
        if not code.isdigit() or not 1<=int(code)<=2100000000: errors.append('Explicit valid versionCode required; must exceed all prior Play uploads')
        api=env.get('KIT_TARGET_API','')
        if not api.isdigit() or not 35<=int(api)<=99: errors.append('Explicit supported target API >=35 required; verify current Play policy')
        if config.get('packageName','').startswith('com.example.'):
            errors.append('Replace placeholder packageName before building')
    if stage=='internal':
        if not env.get('PLAY_SERVICE_ACCOUNT_JSON'): errors.append('Missing GitHub secret: PLAY_SERVICE_ACCOUNT_JSON')
        if env.get('KIT_CONFIRM')!='UPLOAD INTERNAL': errors.append('Confirmation must be exactly UPLOAD INTERNAL')
        if env.get('GITHUB_REF')!='refs/heads/main': errors.append('Internal upload is main-only')
    return errors

if __name__=='__main__':
    r=Path(__file__).resolve().parents[1];config=json.loads((r/'unity-kit.json').read_text())
    errors=validate(os.environ,config)
    for error in errors: print('ERROR:',error)
    if errors: sys.exit(1)
    out=os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out,'a') as f:
            f.write('package='+config['packageName']+'\n')
            f.write('version='+config['versionName']+'\n')
    print('Configuration gate passed. No credentials printed. Unity not yet run.')
