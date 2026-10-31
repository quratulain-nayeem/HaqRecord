"""Validate callback connections; conversational tuning is advisory."""
import hashlib
import secrets
import time
from pathlib import Path
import httpx
from voice_listening import ENDPOINTING_MS, RESPONSE_DELAY_MS, LISTENING_MARKER, RESOLUTION_MARKER

ROOT=Path(__file__).resolve().parent
_cache={}
TOOLS={'calculate_reported_balance':'calculate','prepare_case':'prepare-case',
       'read_current_case':'current-case','prepare_payment':'prepare-payment','find_official_resources':'resources','capture_worker_account':'capture-account',
       'reconstruct_wage_dispute':'reconstruct-dispute','prepare_no_payment_followup':'prepare-no-payment-followup','prepare_case_reminder':'prepare-reminder','explain_case_next_step':'next-step'}
TOOLS.update({'get_resolution_summary':'resolution-summary','propose_case_action':'propose-resolution'})
TOOLS['guide_case_section']='guide-section'
OPTIONAL_TOOLS={'capture_worker_account','reconstruct_wage_dispute','prepare_no_payment_followup','prepare_case_reminder','explain_case_next_step','get_resolution_summary','propose_case_action'}
OPTIONAL_TOOLS.add('guide_case_section')
BLOCKING_ISSUES={'callback_tools','callback_authentication','invalid_configuration','speech_recognition','premature_hangup'}

def mismatches(agent,prompt,public,tool_secret=None):
    try:
        task=agent['tasks'][0];config=task['tools_config'];multi=config.get('multilingual_config') or {}
        failures=[]
        def prompt_matches(actual):
            positions=sorted(prompt.index(marker) for marker in (RESOLUTION_MARKER,LISTENING_MARKER) if marker in prompt)
            if positions:
                sections=[prompt[start:end].strip() for start,end in zip(positions,positions[1:]+[len(prompt)])]
                return actual.startswith(prompt[:positions[0]].rstrip()) and all(section in actual for section in sections)
            return actual.startswith(prompt)
        if not prompt_matches((((agent.get('agent_prompts') or {}).get('task_1') or {}).get('system_prompt') or '')):failures.append('prompt')
        if any(not prompt_matches(p.get('system_prompt') or '') for p in multi.get('languages',{}).values()):failures.append('language_prompts')
        if multi.get('language_switch_trigger')!='caller_requested':failures.append('language_switching')
        # Bolna normalizes redundant language fields away after Studio saves.
        # Validate the effective profile, merging the base with actual overrides.
        # A missing inherited value is not configuration drift.
        base=config.get('transcriber') or {}
        profiles=[base]
        for language,entry in multi.get('languages',{}).items():
            overrides={k:v for k,v in (entry.get('transcriber') or {}).items() if v is not None}
            profiles.append({**base,**overrides,'language':overrides.get('language',language)})
        if any(p.get('provider')!='sarvam' or p.get('model')!='saaras:v4' for p in profiles):failures.append('speech_recognition')
        if any(p.get('language') not in ('hi','en') or p.get('endpointing')!=ENDPOINTING_MS for p in profiles):failures.append('listening')
        if any(task['task_config'].get(k)!=v for k,v in {'incremental_delay':RESPONSE_DELAY_MS,'number_of_words_for_interruption':1,'optimize_latency':False}.items()):failures.append('turn_timing')
        policy=task['task_config']
        if policy.get('hangup_after_LLMCall') or (policy.get('hangup_after_silence') or 0)>0 or (policy.get('call_terminate') or 0)>0:failures.append('premature_hangup')
        tools=config['api_tools']
        for name,path in TOOLS.items():
            if name not in tools['tools_params'] and name in OPTIONAL_TOOLS:
                issue='early_account_capture' if name=='capture_worker_account' else 'workspace_tools'
                if issue not in failures:failures.append(issue)
                continue
            if tools['tools_params'].get(name,{}).get('url')!=public.rstrip('/')+'/bolna/tools/'+path:failures.append('callback_tools');break
            if tool_secret:
                params=tools['tools_params'][name]
                supplied=([params['api_token']] if params.get('api_token') else [])+[value for key,value in (params.get('headers') or {}).items() if key.lower()=='authorization']
                if not supplied or any(not secrets.compare_digest(str(value),'Bearer '+tool_secret) for value in supplied):
                    failures.append('callback_authentication');break
        definitions=tools['tools'];definitions=__import__('json').loads(definitions) if isinstance(definitions,str) else definitions
        calculation=next((t.get('function',t) for t in definitions if t.get('function',t).get('name')=='calculate_reported_balance'),{})
        if 'original_statement' not in calculation.get('parameters',{}).get('properties',{}):failures.append('preview_fields')
        return failures
    except (KeyError,IndexError,TypeError,ValueError,AttributeError):return ['invalid_configuration']

def check_agent(settings,public,force=False,tool_secret=None):
    key,agent_id=settings.get('BOLNA_API_KEY'),settings.get('BOLNA_AGENT_ID')
    if not key or not agent_id or not public:return {'ready':False,'status':'not_configured'}
    try:prompt=(ROOT/'SARA_BACKEND_PROMPT.md').read_text(encoding='utf-8')
    except OSError:return {'ready':False,'status':'configuration_unavailable'}
    signature=hashlib.sha256((key+agent_id+public+prompt+(tool_secret or '')).encode()).hexdigest()
    if not force and _cache.get('signature')==signature and time.monotonic()-_cache.get('at',0)<30:return dict(_cache['result'])
    try:
        response=httpx.get('https://api.bolna.ai/v2/agent/'+agent_id,headers={'Authorization':'Bearer '+key},timeout=8)
        response.raise_for_status();agent=response.json();issues=mismatches(agent,prompt,public,tool_secret)
        blockers=[issue for issue in issues if issue in BLOCKING_ISSUES]
        warnings=[issue for issue in issues if issue not in BLOCKING_ISSUES]
        result={'ready':not blockers,
            'status':'configuration_changed' if blockers else 'configuration_warning' if warnings else 'verified',
            'warnings':warnings,'section_voice_ready':section_ready(agent,public) and not blockers}
    except (httpx.HTTPError,ValueError):result={'ready':False,'status':'configuration_unavailable'}
    _cache.update(signature=signature,at=time.monotonic(),result=result)
    return dict(result)


def section_ready(agent,public):
    try:
        config=agent['tasks'][0]['tools_config'];api=config['api_tools']
        definitions=api['tools'];definitions=__import__('json').loads(definitions) if isinstance(definitions,str) else definitions
        present=any(d.get('function',d).get('name')=='guide_case_section' for d in definitions)
        prompts=[agent['agent_prompts']['task_1']['system_prompt']]+[p['system_prompt'] for p in config['multilingual_config']['languages'].values()]
        return bool(present and api['tools_params']['guide_case_section']['url']==public.rstrip('/')+'/bolna/tools/guide-section'
            and agent['agent_welcome_message']=='{haqrecord_opening}' and all('{section_guidance}' in p for p in prompts))
    except (KeyError,TypeError,ValueError):return False
