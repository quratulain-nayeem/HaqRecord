import sys
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from voice_listening import listening_configuration,inject_listening_prompt,LISTENING_MARKER,RESOLUTION_MARKER

prompt='Original worker instructions.\nInternal voice_token: {voice_token}.\n\n'+RESOLUTION_MARKER+'\nExisting resolution instructions.'
agent={'agent_prompts':{'task_1':{'system_prompt':prompt}},'tasks':[{'task_config':{'hangup_after_LLMCall':True,'call_terminate':300,'hangup_after_silence':45,'call_cancellation_prompt':'End after read-back'},
    'tools_config':{'transcriber':{'provider':'sarvam','model':'saaras:v4','language':'hi','encoding':'linear16'},
        'llm_agent':{'model':'unchanged-model'},'synthesizer':{'voice':'unchanged-voice'},'api_tools':{'private':'unchanged'},
        'multilingual_config':{'language_switch_trigger':'caller_requested','languages':{
            'en':{'transcriber':{'provider':'deepgram','model':'nova-3','language':'en'},'system_prompt':prompt,'synthesizer':{'voice':'unchanged-English-voice'}},
            'hi':{'transcriber':{'provider':'sarvam','model':'saaras:v4','language':'hi'},'system_prompt':prompt}}}}}],
        'composition_by_language':{'hi':[{'type':'variable','scope':'execution','name':'voice_token'},{'type':'text','text':prompt}]}}
before=deepcopy(agent);fixed=listening_configuration(agent)
assert agent==before
assert listening_configuration(fixed)==fixed
t=fixed['tasks'][0];config=t['tools_config']
assert t['task_config']['hangup_after_LLMCall'] is False
assert t['task_config']['call_cancellation_prompt'] is None
assert t['task_config']['hangup_after_silence']==t['task_config']['call_terminate']==0
assert t['task_config']['incremental_delay']==2500 and t['task_config']['number_of_words_for_interruption']==1
for language,p in config['multilingual_config']['languages'].items():
    assert p['transcriber']['provider']=='sarvam' and p['transcriber']['model']=='saaras:v4'
    assert p['transcriber']['language']==language and p['transcriber']['endpointing']==2500
    assert p['system_prompt'].count(LISTENING_MARKER)==1 and 'Internal voice_token: {voice_token}' in p['system_prompt']
    assert p['system_prompt'].endswith('Existing resolution instructions.')
for key in ('llm_agent','synthesizer','api_tools'):assert config[key]==before['tasks'][0]['tools_config'][key]
assert fixed['composition_by_language']['hi'][0]==before['composition_by_language']['hi'][0]
print('PASS: both language slots use Sarvam, deliberate turn pause and user barge-in; no auto hangup; idempotent prompt injection preserves tools, voice, model and call variables.')

# Exercise both API representations, including an unrelated provider tool.
import json
for encoded in (False,True):
    sample=deepcopy(agent)
    api={'tools':[{'name':'capture_worker_account','pre_call_message':None,'parameters':{'private':'schema'}},
                  {'type':'function','function':{'name':'calculate_reported_balance','pre_call_message':{'en':'Please wait'}}},
                  {'name':'switch_language','pre_call_message':'provider-owned'}],
         'tools_params':{'capture_worker_account':{'url':'https://example.test/bolna/tools/capture-account','api_token':'private-test-token','pre_call_message':None},
                         'calculate_reported_balance':{'url':'https://example.test/bolna/tools/calculate','param':{'value':'unchanged'}}}}
    original=deepcopy(api)
    if encoded:api['tools']=json.dumps(api['tools'])
    sample['tasks'][0]['tools_config']['api_tools']=api
    corrected=listening_configuration(sample)
    assert listening_configuration(corrected)==corrected
    result=corrected['tasks'][0]['tools_config']['api_tools']
    definitions=json.loads(result['tools']) if encoded else result['tools']
    for index,name in enumerate(('capture_worker_account','calculate_reported_balance')):
        definition=definitions[index].get('function',definitions[index])
        assert definition['pre_call_message']=={'hi':'','en':''}
        assert result['tools_params'][name]['pre_call_message']=={'hi':'','en':''}
        expected=deepcopy(original['tools_params'][name]);expected['pre_call_message']={'hi':'','en':''}
        assert result['tools_params'][name]==expected
    assert definitions[0]['parameters']==original['tools'][0]['parameters']
    assert definitions[2]==original['tools'][2]
    hindi=corrected['tasks'][0]['tools_config']['multilingual_config']['languages']['hi']
    assert hindi['handoff_message']=='जी, अब हिंदी में बात करेंगे।'
    assert 'Devanagari' in hindi['system_prompt'] and 'at most ONE question' in hindi['system_prompt']
print('PASS: silent Hindi/English callback maps survive serialization; credentials, schemas and unrelated tools preserved; Hindi speech policy synchronized.')
