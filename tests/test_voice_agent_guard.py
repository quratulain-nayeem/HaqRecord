import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
import voice_agent_guard as guard
prompt=(guard.ROOT/'SARA_BACKEND_PROMPT.md').read_text(encoding='utf-8')
public='https://example.test'
profile={'provider':'sarvam','model':'saaras:v4','language':'hi','endpointing':2500}
agent={'agent_prompts':{'task_1':{'system_prompt':prompt}},'tasks':[{'task_config':{'incremental_delay':2500,'number_of_words_for_interruption':1,'optimize_latency':False},'tools_config':{'transcriber':profile,'multilingual_config':{'language_switch_trigger':'caller_requested','languages':{'hi':{'transcriber':dict(profile),'system_prompt':prompt},'en':{'transcriber':{**profile,'language':'en'},'system_prompt':prompt}}},'api_tools':{'tools_params':{n:{'url':public+'/bolna/tools/'+path} for n,path in guard.TOOLS.items()},'tools':[{'name':'calculate_reported_balance','parameters':{'properties':{'original_statement':{'type':'string'}}}}]}}}]}
settings={'BOLNA_API_KEY':'isolated-key','BOLNA_AGENT_ID':'isolated-agent'}
def check(payload):
 response=httpx.Response(200,json=payload,request=httpx.Request('GET','https://api.bolna.ai/test'))
 with patch('voice_agent_guard.httpx.get',return_value=response):return guard.check_agent(settings,public,force=True)
assert check(agent)=={'ready':True,'status':'verified','warnings':[],'section_voice_ready':False}
scoped=deepcopy(agent);scoped['agent_welcome_message']='{haqrecord_opening}'
scoped['tasks'][0]['tools_config']['api_tools']['tools'].append({'name':'guide_case_section'})
assert check(scoped)['section_voice_ready']
broken_scope=deepcopy(scoped)
broken_scope['tasks'][0]['tools_config']['multilingual_config']['languages']['hi']['system_prompt']='No section variable here'
assert not check(broken_scope)['section_voice_ready']
with_variables=deepcopy(agent)
marker='Resolution workflow extension (preserve existing voice, language and intake rules)'
if marker in prompt:
    base,extension=prompt.split(marker,1)
    with_variables['agent_prompts']['task_1']['system_prompt']=base.rstrip()+'\nInternal voice_token: {voice_token}.\n'+marker+extension
    assert check(with_variables)['status']=='verified'
inherited=deepcopy(agent)
for entry in inherited['tasks'][0]['tools_config']['multilingual_config']['languages'].values():entry['transcriber'].pop('endpointing',None)
assert check(inherited)['status']=='verified'
older=deepcopy(agent);config=older['tasks'][0]['tools_config']
older['agent_prompts']['task_1']['system_prompt']='Different prompt'
config['multilingual_config']['languages']['hi']['system_prompt']='Different language prompt'
config['transcriber']['endpointing']=1500
older['tasks'][0]['task_config']['incremental_delay']=1200
config['api_tools']['tools_params'].pop('capture_worker_account')
result=check(older)
assert result['ready'] and result['status']=='configuration_warning'
assert {'prompt','language_prompts','listening','turn_timing','early_account_capture'}.issubset(set(result['warnings']))
for missing in ('prepare_case','calculate_reported_balance'):
 bad=deepcopy(agent);bad['tasks'][0]['tools_config']['api_tools']['tools_params'].pop(missing)
 assert not check(bad)['ready']
for name in ('prepare_case','capture_worker_account'):
 bad=deepcopy(older if name=='prepare_case' else agent)
 bad['tasks'][0]['tools_config']['api_tools']['tools_params'][name]['url']='https://other.example/tool'
 assert not check(bad)['ready']
with patch('voice_agent_guard.httpx.get',return_value=httpx.Response(503,request=httpx.Request('GET','https://api.bolna.ai/test'))):
 assert guard.check_agent(settings,public,force=True)['status']=='configuration_unavailable'
with patch('voice_agent_guard.httpx.get',return_value=httpx.Response(200,json=older,request=httpx.Request('GET','https://api.bolna.ai/test'))) as get:
 assert guard.check_agent(settings,public,force=True)['ready']
 assert guard.check_agent(settings,public)['ready'] and get.call_count==1
for field,value in (('hangup_after_LLMCall',True),('call_terminate',300),('hangup_after_silence',45)):
 bad=deepcopy(agent);bad['tasks'][0]['task_config'][field]=value
 assert not check(bad)['ready']
bad=deepcopy(agent);bad['tasks'][0]['tools_config']['multilingual_config']['languages']['en']['transcriber'].update(provider='deepgram',model='nova-3')
assert not check(bad)['ready']
print('PASS: English-only ASR regression and automatic hangup are blocked; prompt/timing-only tuning stays advisory; callback checks, inherited settings and caching remain valid.')
authenticated=deepcopy(agent)
for entry in authenticated['tasks'][0]['tools_config']['api_tools']['tools_params'].values():entry['api_token']='Bearer fixture-callback-secret'
assert 'callback_authentication' not in guard.mismatches(authenticated,prompt,public,'fixture-callback-secret')
authenticated['tasks'][0]['tools_config']['api_tools']['tools_params']['prepare_case']['api_token']='Bearer wrong-fixture-value'
assert 'callback_authentication' in guard.mismatches(authenticated,prompt,public,'fixture-callback-secret')
response=httpx.Response(200,json=authenticated,request=httpx.Request('GET','https://api.bolna.ai/test'))
with patch('voice_agent_guard.httpx.get',return_value=response):
 assert not guard.check_agent(settings,public,force=True,tool_secret='fixture-callback-secret')['ready']
print('PASS: prepare-case credential mismatch blocks session issuance; no credential value is returned in readiness diagnostics.')
