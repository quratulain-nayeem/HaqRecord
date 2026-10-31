"""Repair only mismatched authentication on known HaqRecord callback URLs."""
import argparse
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import secrets

import httpx
from dotenv import dotenv_values
from voice_agent_guard import TOOLS

ROOT=Path(__file__).resolve().parent


def repair_configuration(agent,public,secret):
    fixed=deepcopy(agent);changed=[]
    for task in fixed['tasks']:
        for name,params in task['tools_config']['api_tools']['tools_params'].items():
            if name not in TOOLS:continue
            if params.get('url')!=public.rstrip('/')+'/bolna/tools/'+TOOLS[name]:raise ValueError('A known callback URL differs from the verified local address. No credential was published.')
            expected='Bearer '+secret
            mismatch=not secrets.compare_digest(str(params.get('api_token') or ''),expected)
            for key,value in (params.get('headers') or {}).items():
                if key.lower()=='authorization' and not secrets.compare_digest(str(value),expected):
                    params['headers'][key]=expected;mismatch=True
            if mismatch:params['api_token']=expected;changed.append(name)
    return fixed,changed


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    env=dotenv_values(ROOT/'.env');public=env.get('HAQRECORD_VOICE_PUBLIC_URL');secret=env.get('HAQRECORD_VOICE_TOOL_SECRET')
    if not public or not secret:raise SystemExit('Callback URL and authentication must be configured first.')
    with httpx.Client(headers={'Authorization':'Bearer '+env['BOLNA_API_KEY']},timeout=25) as client:
        endpoint='https://api.bolna.ai/v2/agent/'+env['BOLNA_AGENT_ID']
        response=client.get(endpoint);response.raise_for_status();before=response.json()
        expected,changed=repair_configuration(before,public,secret)
        print('Callbacks requiring authentication repair:',', '.join(changed) or 'none')
        if not args.apply or not changed:return
        backup=ROOT/'.tools'/('agent-before-callback-auth-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
        backup.write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
        allowed=('agent_name','agent_welcome_message','webhook_url','agent_type','tasks','ingest_source_config','calling_guardrails','call_summary_enabled')
        payload={'agent_config':{key:expected[key] for key in allowed if key in expected},'agent_prompts':expected['agent_prompts']}
        if 'composition_by_language' in expected:payload['composition_by_language']=expected['composition_by_language']
        response=client.put(endpoint,json=payload);print('Repair HTTP:',response.status_code);response.raise_for_status()
        response=client.get(endpoint);response.raise_for_status();actual=response.json()
        for key in (*allowed,'agent_prompts','composition_by_language'):
            if actual.get(key)!=expected.get(key):raise SystemExit('Provider verification incomplete. Snapshot retained; no success assumed.')
        print('Verified: callback authentication repaired; all other agent settings and cases preserved. Secret values withheld.')


if __name__=='__main__':main()
