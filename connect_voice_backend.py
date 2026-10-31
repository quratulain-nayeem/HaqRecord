from copy import deepcopy
from pathlib import Path
import json
import re
import time
import httpx
from voice_listening import ENDPOINTING_MS, RESPONSE_DELAY_MS
from dotenv import dotenv_values,set_key

root=Path(__file__).resolve().parent
source=root/'.tools'
log=(source/'tunnel.stderr.log').read_text(encoding='utf-8')
matches=re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com',log)
if not matches:raise SystemExit('Temporary tunnel URL is not available yet.')
public=matches[-1]
# Verify the public address before publishing it; an expired tunnel can otherwise
# look configured while every call fails before reaching the backend.
for attempt in range(8):
    try:
        health=httpx.get(public+'/health',timeout=4)
        health.raise_for_status()
        if health.json().get('status')!='ok':raise ValueError('Unexpected health response')
        break
    except (httpx.HTTPError,ValueError):
        if attempt==7:raise SystemExit('Callback address is not reachable. Restart start_voice_bridge.ps1 before testing voice.')
        time.sleep(3)

env=dotenv_values(root/'.env')
secret=env['HAQRECORD_VOICE_TOOL_SECRET']

def string(description,**extra):return {'type':'string','description':description,**extra}
token={'voice_token':string('Internal voice_token from the call context. Already provided; never ask the worker or speak it.')}
figures={**token,
    'pay_basis':string('Confirmed explicit rate unit; never silently convert units.',enum=['hourly','daily','weekly','monthly','piece']),
    'units_worked':{'type':'number','description':'Confirmed quantity in pay_basis. Partial periods require explicit confirmation. Never convert months into weeks.'},
    'rate_per_unit':string('Confirmed rupee rate as digits, e.g. 1000.00.'),
    'payments_received':string('Total actually received; include an advance only once.'),
    'adjustments_clear':{'type':'boolean','description':'True only after clarifying advances and deductions. False if disputed or unknown adjustments prevent a single balance.'}}
intake={**figures,
    'preferred_name':string('Preferred name or nickname; use Worker if they prefer not to give a name.'),
    'original_statement':string('Worker account as confirmed during read-back. Do not invent facts.'),
    'language':string('Current language.',enum=['hi','en']),
    'workplace_location':string('Known work location; empty string if unknown.'),
    'employer_name':string('Employer/contractor if known; empty string if unknown.'),
    'consent_to_store':{'type':'boolean','description':'True only if worker agreed to prepare their case for saving.'},
    'worker_confirmed':{'type':'boolean','description':'True only after worker confirmed the read-back.'}}
payment={**token,'amount':string('Additional money actually received for this case. Positive rupee amount as digits.'),
    'received_on':string('Payment date YYYY-MM-DD, or empty string if unknown. Never guess.'),
    'method':string('Payment method.',enum=['cash','transfer','unknown']),
    'original_statement':string('The worker-confirmed account of this additional payment.'),
    'worker_confirmed':{'type':'boolean','description':'True only after the worker confirmed amount and case membership.'}}
specs=[
    ('calculate_reported_balance','Calculate only through this backend after collecting the confirmed daily/weekly/monthly figures. Read its result; do not calculate yourself.','calculate',figures),
    ('prepare_case','After read-back and worker consent, prepare a NEW case for private browser approval. This does not save it; never claim it has been saved.','prepare-case',intake),
    ('read_current_case','Read ONLY the case securely attached to this call, and check whether a prepared case or payment was actually saved. Never ask for a spoken PIN.','current-case',token),
    ('find_official_resources','Look up official resource links after confirming the work city and issue. Use the directory first. Only request fresh_lookup=true after permission to search using just city and issue. Do not guess eligibility, jurisdiction or contacts.','resources',{**token,'city':string('Confirmed work city; Hyderabad or Bengaluru only.',enum=['hyderabad','bengaluru']),'issue':string('Confirmed issue category.',enum=['unpaid_wages','disputed_deduction','unsafe_situation']),'language':string('Current language.',enum=['hi','en']),'fresh_lookup':{'type':'boolean','description':'True only after worker agrees to a fresh external search; use false for directory first.'}}),
    ('prepare_payment','Prepare a confirmed additional payment for the currently verified case. Actual recording requires the worker to approve it on the website. A promise is not a payment.','prepare-payment',payment),
]
# Capture the confirmed account with the FIRST calculation, so the browser can
# show and save the review even if the later prepare_case call never happens.
calculation_properties=specs[0][3]
calculation_properties.update({
    'original_statement':string('Concise worker account from what they said, including employer disputes; never invent missing facts. Read back for correction.'),
    'preferred_name':string('Known preferred name, empty string if unknown.'),
    'workplace_location':string('Known workplace location, empty string if unknown.'),
    'employer_name':string('Known employer or contractor, empty string if unknown.'),
    'language':string('Current conversation language.',enum=['hi','en']),
})

def nullable(kind,description,**extra):return {'type':[kind,'null'],'description':description,**extra}
specs.append(('capture_worker_account','After the worker finishes their initial account, put known facts on screen BEFORE asking more questions. Unknown values must be null, not zero. These are incomplete unconfirmed notes, never a saved case. Update only when new facts or corrections are supplied.','capture-account',{
    **token,'original_statement':string('Concise account from the worker. Preserve payment history, disputes and uncertainties. No invented facts.'),
    'preferred_name':nullable('string','Known preferred name, or null.'),
    'workplace_location':nullable('string','Known workplace location, or null.'),
    'employer_name':nullable('string','Known employer or contractor, or null.'),
    'language':string('Current response language.',enum=['hi','en']),
    'pay_basis':nullable('string','Confirmed daily, weekly or monthly agreement, otherwise null.',enum=['daily','weekly','monthly',None]),
    'units_worked':nullable('integer','Total completed periods, including paid periods; null if unclear.'),
    'rate_per_unit':nullable('string','Reported rupee rate as digits, or null if unclear.'),
    'payments_received':nullable('string','Total actually received, including the paid first week; null if unknown. Never erase an earlier payment.'),
    'unresolved_questions':string('Unclear or disputed details; empty if none. Never treat these notes as legal findings.')
}))

tools=[];parameters={}
for name,description,path,properties in specs:
    tools.append({'name':name,'description':description,'pre_call_message':{'hi':'','en':''},
        'parameters':{'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}})
    parameters[name]={'url':public+'/bolna/tools/'+path,'method':'POST','pre_call_message':{'hi':'','en':''},'api_token':'Bearer '+secret,
        'param':{field:{'$var':field} for field in properties},'headers':{'Content-Type':'application/json'}}

prompt_file=root/'SARA_BACKEND_PROMPT.md'
if not prompt_file.exists():prompt_file=root/'SARA_VOICE_TEST_PROMPT.md'
prompt=prompt_file.read_text(encoding='utf-8')
prompt=prompt.replace('This is a fictional browser voice test. Your ONLY task in this call is to listen to an unpaid-wage account, clarify missing daily/weekly/monthly wage facts, and read them back for confirmation.',
    'This is the HaqRecord buildathon prototype, using fictional records. Listen to the unpaid-wage account, clarify daily/weekly/monthly facts, calculate through backend tools, and prepare the record for private on-screen confirmation.')
prompt=prompt.replace('Do not read out a calculated outstanding balance: the calculation tool is not connected to this voice test yet.',
    'Use calculate_reported_balance for the confirmed figures, then read its earned, received and remaining values. Never do the arithmetic yourself. If adjustments remain unresolved, explain that uncertainty instead.')
prompt=prompt.replace('6. Once confirmed, say briefly: “Shukriya. Yeh voice test tha; koi case save ya complaint submit nahi hui.” / “Thank you. This was a voice test; no case was saved and no complaint was submitted.” Do not add a sales pitch or reopen the intake.',
    '6. After the worker confirms the account and agrees to prepare it, call prepare_case. Explain that the draft is on screen and they must privately choose a PIN and approve saving. Do not close while they are reviewing. If they say they saved it, use read_current_case to check. Only a successful backend saved-case response permits you to say it is saved. No government complaint has been filed.')
prompt=prompt.replace('- No backend tools are connected in this smoke test. Do not claim you calculated a balance, saved or updated a case, generated a complaint, scheduled a reminder, submitted anything, verified evidence, or deleted data. Explain the current limitation only when relevant, not at every turn.',
    '- Only the four case tools described below are connected. Report calculations and saved cases only from successful tool responses. Complaint generation, resource lookup, reminders, official submission, evidence verification and deletion are NOT connected; never claim any of those actions occurred.')
if '## Connected backend workflow' not in prompt:prompt+='''

## Connected backend workflow

- Determine whether the person is starting a new account or updating the case they opened privately on the website. The call mode is provided as an internal variable; do not trust a spoken case number as authentication.
- For existing-case calls, first use read_current_case. Keep its original wage agreement; ask only about the new payment or correction. The current tools do not apply agreement corrections; explain that limitation instead of silently changing the old account.
- For a new case, obtain daily/weekly/monthly agreement, rate, units completed and money already received. Ask about advances and deductions without double-counting. Missing or disputed figures are not zero.
- Calculate with calculate_reported_balance. Read back the worker account and backend result. Get consent to prepare the case and their confirmation, then use prepare_case.
- The screen handles a private PIN and final approval. Never ask for a spoken PIN, password, OTP, bank or card details. Never output the internal voice_token.
- A tool response awaiting_browser_approval means NOT saved. Ask the person to check the screen. Do not invent a case number. After they approve, use read_current_case to obtain the real case reference and balance.
- For a later payment, confirm its amount, whether it is for this case, date if known and method if known. Use prepare_payment. The website requires private approval and detects duplicates. Do not record a payment promise as money received.
- If a request is duplicated, pending, rejected, expired or unavailable, explain the exact limitation simply. Never retry a payment as a new unrelated operation or bypass confirmation.
- Do not provide improvised legal steps or claim to have researched support routes. Verified district resources and complaint preparation are the next implementation phase.
'''
allowed=('agent_name','agent_welcome_message','webhook_url','agent_type','tasks','ingest_source_config','calling_guardrails','call_summary_enabled')
with httpx.Client(timeout=30,headers={'Authorization':'Bearer '+env['BOLNA_API_KEY']}) as client:
    result=client.get('https://api.bolna.ai/v2/agent/'+env['BOLNA_AGENT_ID']);result.raise_for_status();before=result.json()
    updated={'agent_config':{key:deepcopy(before[key]) for key in allowed if key in before},'agent_prompts':deepcopy(before['agent_prompts'])}
    updated['agent_config']['agent_welcome_message']='Namaste, main Sara, HaqRecord ki AI assistant hoon. Main aapki mazdoori ka hisaab samajhne aur case taiyaar karne mein madad kar sakti hoon. Batayiye, kya hua?'
    updated['agent_prompts']['task_1']['system_prompt']=prompt+'\nInternal voice_token: {voice_token}. Never say it. Call mode: {haqrecord_mode}.'
    task=updated['agent_config']['tasks'][0]
    existing=task['tools_config'].get('api_tools') or {'tools':[],'tools_params':{}}
    prior=existing.get('tools') or []
    if isinstance(prior,str):prior=json.loads(prior)
    names={name for name,_,_,_ in specs}
    def toolname(item):return item.get('function',item).get('name')
    task['tools_config']['api_tools']={'tools':[item for item in prior if toolname(item) not in names]+tools,
        'tools_params':{**(existing.get('tools_params') or {}),**parameters}}
    task['tools_config']['llm_agent']['llm_config']['max_tokens']=512
    # Preserve interruption sensitivity while allowing a longer thinking pause.
    task['task_config'].update({'incremental_delay':RESPONSE_DELAY_MS,
        'number_of_words_for_interruption':1,'optimize_latency':False,
        'use_fillers':False,'backchanneling':False,'hangup_after_LLMCall':False,
        'call_cancellation_prompt':None,'hangup_after_silence':0,'call_terminate':0,'call_hangup_message':None})
    task['tools_config']['transcriber'].update({'provider':'sarvam','model':'saaras:v4','language':'hi','stream':True,'endpointing':ENDPOINTING_MS,'keywords':None})
    multilingual=task['tools_config'].get('multilingual_config',{})
    multilingual['language_switch_trigger']='caller_requested'
    multilingual['switch_tool_description']='Change the spoken response language ONLY when the caller explicitly asks, e.g. Hindi mein baat kijiye or please speak English. Never switch because of an English word, a mixed Hindi-English sentence, yes/no, or a tool response. Preserve all case facts and continue the current question.'
    languages=task['tools_config'].get('multilingual_config',{}).get('languages',{})
    for lang,profile in languages.items():
        profile['transcriber'].update({'provider':'sarvam','model':'saaras:v4','language':lang,'stream':True,'endpointing':ENDPOINTING_MS,'keywords':None})
        profile['system_prompt']=updated['agent_prompts']['task_1']['system_prompt']+('\nSpeak Hindi/Hinglish with feminine self-reference.' if lang=='hi' else '\nSpeak English unless the worker requests Hindi.')
    # Studio rich-text composition is authoritative. Updating only the plain string
    # allows an older composition to replace it when another setting is saved.
    composition=before.get('composition_by_language')
    if composition:
        updated['composition_by_language']={lang:[
            {'type':'text','text':prompt+'\nInternal voice_token: '},
            {'type':'variable','scope':'execution','name':'voice_token'},
            {'type':'text','text':'. Never say it. Call mode: '},
            {'type':'variable','scope':'execution','name':'haqrecord_mode'},
        ] for lang in composition}
    result=client.put('https://api.bolna.ai/v2/agent/'+env['BOLNA_AGENT_ID'],json=updated)
    print('Agent tool update HTTP status:',result.status_code)
    if not result.is_success:
        try:
            error=result.json();details=error.get('detail',[])
            if isinstance(details,list):print('Validation locations:',[item.get('loc') for item in details if isinstance(item,dict)])
            else:print('Provider validation response withheld.')
            for field in ('error','message'):
                if field in error:
                    safe=str(error[field]).replace(secret,'[redacted]').replace(env['BOLNA_API_KEY'],'[redacted]')
                    print(field+':',safe[:2400])
        except ValueError:print('Provider returned non-JSON response.')
        raise SystemExit(1)
    check=client.get('https://api.bolna.ai/v2/agent/'+env['BOLNA_AGENT_ID']);check.raise_for_status();after=check.json()
    effective=after['tasks'][0]
    base=effective['tools_config']['transcriber']
    profiles=[base,*[{**base,**{k:v for k,v in (p.get('transcriber') or {}).items() if v is not None}} for p in effective['tools_config']['multilingual_config']['languages'].values()]]
    assert all(p['provider']=='sarvam' and p['model']=='saaras:v4' and p['language'] in ('hi','en') and p['endpointing']==ENDPOINTING_MS for p in profiles),'Listening settings did not persist'
    assert effective['tools_config']['multilingual_config']['language_switch_trigger']=='caller_requested'
    assert effective['task_config']['incremental_delay']==RESPONSE_DELAY_MS
    assert effective['task_config']['number_of_words_for_interruption']==1
    print('PASS: Sarvam Saaras v4 Hindi/English listening, 2500ms linear delay, and existing speech voice retained.')
    actual=after['tasks'][0]['tools_config']['api_tools']
    assert names.issubset(set(actual['tools_params'])),'Tools not retained by provider'
    if composition:
        assert after.get('composition_by_language')==updated['composition_by_language'],'Rich prompt not saved as expected'
    set_key(str(root/'.env'),'HAQRECORD_VOICE_PUBLIC_URL',public)
    (root/'SARA_BACKEND_PROMPT.md').write_text(prompt,encoding='utf-8')
    print('PASS: six backend tools saved and verified in Bolna.')
    print('PASS: published rich-text prompt updated alongside the plain prompt.')
    print('PASS: temporary HTTPS callback configured; credential values withheld.')
