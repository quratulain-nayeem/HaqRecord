"""Real callback auth + ambiguity + private approval, with fictional temp data."""
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE']='false'
import httpx
from fastapi.testclient import TestClient
import auth,database,voice_backend
from main import app
from bridge_app import app as bridge_app
from repair_voice_tool_auth import repair_configuration

public='https://example.test';secret='fictional-callback-secret'
config={'HAQRECORD_VOICE_PUBLIC_URL':public,'HAQRECORD_VOICE_TOOL_SECRET':secret}
agent={'tasks':[{'tools_config':{'api_tools':{'tools_params':{
    'prepare_case':{'url':public+'/bolna/tools/prepare-case','api_token':'Bearer stale-fixture'},
    'calculate_reported_balance':{'url':public+'/bolna/tools/calculate','api_token':'Bearer '+secret}}},'llm_agent':{'model':'preserve'},'synthesizer':{'voice':'preserve'}}}]}
original=deepcopy(agent);fixed,changed=repair_configuration(agent,public,secret)
assert changed==['prepare_case'] and agent==original
assert repair_configuration(fixed,public,secret)[1]==[]
assert fixed['tasks'][0]['tools_config']['llm_agent']==original['tasks'][0]['tools_config']['llm_agent']
bad=deepcopy(agent);bad['tasks'][0]['tools_config']['api_tools']['tools_params']['prepare_case']['url']='https://other.example/collect'
try:repair_configuration(bad,public,secret);raise AssertionError('Unverified callback URL accepted')
except ValueError:pass

with tempfile.TemporaryDirectory(prefix='haqrecord-save-path-') as folder:
    database.DB_PATH=Path(folder)/'cases.db';auth.AUTH_DB=Path(folder)/'auth.db'
    database.initialise_database();auth.initialize_auth();voice_backend.initialize()
    client=TestClient(app);bridge=TestClient(bridge_app)
    with patch('voice_backend.dotenv_values',return_value=config),patch('voice_backend.voice.settings',return_value={'BOLNA_API_KEY':'fixture','BOLNA_AGENT_ID':'fixture'}),patch('voice_backend.voice.check_agent',return_value={'ready':True,'status':'verified'}),patch('voice_backend.voice.callback_available',return_value=True),patch('voice_backend.httpx.post',return_value=httpx.Response(200,json={'run_id':'fictional-save-run'})) as mint:
        response=client.post('/voice/intake/session',json={'consent_to_voice_processing':True,'language':'hi'});assert response.status_code==200,response.text
        token=mint.call_args.kwargs['json']['user_data']['voice_token'];headers={'Authorization':'Bearer '+secret}
        notes={'voice_token':token,'language':'hi','pay_basis':'weekly','units_worked':4,'rate_per_unit':'1500','payments_received':'0',
            'preferred_name':'Fictional Worker','original_statement':'A month of work, promised 1500 each week, no wages received.',
            'unresolved_questions':'How many weeks exactly did you work in that month?'}
        captured=bridge.post('/bolna/tools/capture-account',json=notes,headers=headers);assert captured.status_code==200
        assert captured.json()['next_action']=='ask_work_quantity'
        current=client.get('/voice/intake/state').json();assert current['notes']['units_worked'] is None
        payload={k:v for k,v in notes.items() if k!='unresolved_questions'}
        payload.update(adjustments_clear=True,worker_confirmed=True,consent_to_store=True)
        rejected=bridge.post('/bolna/tools/prepare-case',json=payload,headers={'Authorization':'Bearer stale-fixture'})
        assert rejected.status_code==401 and rejected.json()['detail']=='Invalid voice tool credential'
        assert bridge.post('/bolna/tools/calculate',json=payload,headers=headers).json()['status']=='needs_clarification'
        assert bridge.post('/bolna/tools/prepare-case',json=payload,headers=headers).json()['status']=='needs_clarification'
        # A new explicit worker answer resolves the quantity; no month conversion.
        clarified={**notes,'units_worked':5,'original_statement':'Worker explicitly clarified five completed weeks at 1500 per week; received zero.','unresolved_questions':''}
        assert bridge.post('/bolna/tools/capture-account',json=clarified,headers=headers).json()['next_action']=='calculate_reported_balance'
        payload.update(units_worked=5,original_statement=clarified['original_statement'])
        prepared=bridge.post('/bolna/tools/prepare-case',json=payload,headers=headers);assert prepared.status_code==200,prepared.text
        assert prepared.json()['status']=='awaiting_browser_approval'
        state=client.get('/voice/intake/state').json();assert state['case_id'] is None
        approved=client.post('/voice/intake/confirm',json={'draft_id':state['draft_id'],'approved':True,'pin':'928371'},headers={'X-CSRF-Token':state['csrf_token']})
        assert approved.status_code==200,approved.text
        assert approved.json()['case']['calculation']['balance']=='7500.00'
        repeated=client.post('/voice/intake/confirm',json={'draft_id':state['draft_id'],'approved':True,'pin':'928371'},headers={'X-CSRF-Token':state['csrf_token']})
        assert repeated.status_code==200 and repeated.json()['case']['case_id']==approved.json()['case']['case_id']
print('PASS: stale callback auth rejected; targeted credential repair preserves unrelated settings; unresolved candidate cannot calculate/save; clarified quantity stages a draft; only private browser PIN approval saves, once. Fictional temporary records only.')
