"""Review/apply only the transcript-supported recognition and hangup repair."""
import argparse
import json
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values
from voice_listening import listening_configuration,inject_listening_prompt
from register_resolution_tools import difference_paths

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    env=dotenv_values(ROOT/'.env')
    with httpx.Client(headers={'Authorization':'Bearer '+env['BOLNA_API_KEY']},timeout=25) as client:
        endpoint='https://api.bolna.ai/v2/agent/'+env['BOLNA_AGENT_ID']
        response=client.get(endpoint);response.raise_for_status();before=response.json();expected=listening_configuration(before)
        print('Prepared: Sarvam v4 for Hindi AND English; 2500ms turn delay; user interruption retained; automatic LLM/silence/duration hangup disabled.')
        if not args.apply:print('Read-only review. No agent setting changed.');return
        backup=ROOT/'.tools'/('agent-before-listening-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
        backup.write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
        allowed=('agent_name','agent_welcome_message','webhook_url','agent_type','tasks','ingest_source_config','calling_guardrails','call_summary_enabled')
        payload={'agent_config':{k:expected[k] for k in allowed if k in expected},'agent_prompts':expected['agent_prompts']}
        if 'composition_by_language' in expected:payload['composition_by_language']=expected['composition_by_language']
        response=client.put(endpoint,json=payload);print('Update HTTP:',response.status_code);response.raise_for_status()
        response=client.get(endpoint);response.raise_for_status();actual=response.json()
        for key in (*allowed,'agent_prompts','composition_by_language'):
            if actual.get(key)!=expected.get(key):
                print('Unexpected normalized field paths:',difference_paths(expected.get(key),actual.get(key),key))
                raise SystemExit('Verification incomplete; snapshot retained. No successful repair claimed.')
        local=ROOT/'SARA_BACKEND_PROMPT.md';local.write_text(inject_listening_prompt(local.read_text(encoding='utf-8')),encoding='utf-8')
        print('Verified published repair. Hindi speech policy and silent callback announcements applied; synthesizers, LLM, tool schemas, callback URLs, credentials, facts and cases preserved.')


if __name__=='__main__':main()
