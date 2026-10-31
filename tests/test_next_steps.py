"""Useful post-save help, URL-free speech and persistence of a spoken city."""
import json,os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE']='false'
import httpx
from fastapi.testclient import TestClient
import auth,database,voice_backend as vb
from main import app
from bridge_app import app as bridge_app

with tempfile.TemporaryDirectory(prefix='haq-next-step-') as folder:
    database.DB_PATH=Path(folder)/'cases.db';auth.AUTH_DB=Path(folder)/'auth.db'
    database.initialise_database();auth.initialize_auth();vb.initialize()
    a=TestClient(app);other=TestClient(app);bridge=TestClient(bridge_app)
    saved=a.post('/worker/cases',json={'preferred_name':'Raju','original_statement':'Fictional account: four weeks at 2500, received 2000.',
        'pay_basis':'weekly','units_worked':4,'rate_per_unit':'2500','payments_received':'2000',
        'pin':'684295','operation_id':str(uuid4()),'consent_to_store':True,'worker_confirmed':True})
    assert saved.status_code==201,saved.text
    csrf=saved.json()['session']['csrf_token']
    assert a.get('/worker/workspace/next-step?language=en').json()['kind']=='confirm_city'
    assert other.get('/worker/workspace/help-summary').status_code==401
    config={'HAQRECORD_VOICE_PUBLIC_URL':'https://example.test','HAQRECORD_VOICE_TOOL_SECRET':'isolated-secret'}
    with patch('voice_backend.dotenv_values',return_value=config),patch('voice_backend.voice.settings',return_value={'BOLNA_API_KEY':'fake','BOLNA_AGENT_ID':'fake'}),patch('voice_backend.voice.callback_available',return_value=True),patch('voice_backend.voice.check_agent',return_value={'ready':True,'status':'verified'}),patch('voice_backend.httpx.post',return_value=httpx.Response(200,json={'run_id':'fictional-help-call'})) as mint:
        session=a.post('/voice/intake/session',json={'mode':'existing','language':'hi','consent_to_voice_processing':True},headers={'X-CSRF-Token':csrf})
        assert session.status_code==200,session.text
        token=mint.call_args.kwargs['json']['user_data']['voice_token'];headers={'Authorization':'Bearer isolated-secret'}
        request={'voice_token':token,'city':'hyderabad','language':'hi','issue':'unpaid_wages','fresh_lookup':False}
        response=bridge.post('/bolna/tools/resources',json=request,headers=headers)
        assert response.status_code==200,response.text
        result=response.json()
        assert 'तेलंगाना' in result['spoken_response'] and result['links_on_screen']
        assert 'http' not in json.dumps(result).lower() and 'www.' not in json.dumps(result).lower()
        assert not result['jurisdiction_verified'] and not result['complaint_submitted']
        state=a.get('/voice/intake/state').json()
        assert state['resources']['directory'][0]['url'].startswith('https://')
        assert state['resources']['action_card']['phone']=='040-27611437'
        loaded=a.get('/worker/my-case').json()
        assert loaded['workspace']['pilot_city']=='hyderabad'
        assert not loaded['intake']['workplace_location']
        annotations=len(loaded['workspace']['facts'])
        bridge.post('/bolna/tools/resources',json=request,headers=headers)
        assert len(a.get('/worker/my-case').json()['workspace']['facts'])==annotations
        next_step=bridge.post('/bolna/tools/next-step',json={'voice_token':token,'language':'hi'},headers=headers)
        assert next_step.status_code==200,next_step.text
        assert 'http' not in json.dumps(next_step.json()).lower()
        assert 'सार' in next_step.json()['spoken_response']
        card=a.get('/voice/intake/state').json()['next_step']
        assert card['kind']=='seek_support' and card['resource_card']['url'].startswith('https://')
        read=bridge.post('/bolna/tools/next-step',json={'voice_token':token,'language':'hi','read_summary':True},headers=headers).json()
        assert '8000.00' in read['spoken_response'] and '10000.00' in read['spoken_response']
        assert 'http' not in json.dumps(read).lower()
        assert mint.call_count==1  # Only the mocked voice session; resource directory makes no external lookup.
    help_text=a.get('/worker/workspace/help-summary?language=en')
    assert help_text.status_code==200
    assert '8000.00' in help_text.text and 'No government complaint submitted' in help_text.text
    assert '684295' not in help_text.text
    card=a.get('/worker/workspace/next-step?language=en').json()
    assert card['kind']=='seek_support' and card['resource_card']['bring']
    assert '4 weeks' in card['summary']
    from next_steps import case_next_step
    complete=a.get('/worker/my-case').json();complete['calculation']['balance']='0.00'
    assert case_next_step(complete,'en')['kind']=='balance_settled'
    assert case_next_step(complete,'en')['resource_card'] is None
    print('PASS: resource names and plain speech reach Sara; links and contact details stay on screen; spoken city is retained without rewriting intake; assistance summary is private and factual.')
