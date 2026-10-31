"""Case-bound one-field guidance, resume/restart and read-only scope checks."""
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE']='false'
import httpx
from fastapi.testclient import TestClient
import auth,database,voice_backend as vb
from main import app
from bridge_app import app as bridge_app

with tempfile.TemporaryDirectory(prefix='haq-section-voice-') as folder:
    database.DB_PATH=Path(folder)/'cases.db';auth.AUTH_DB=Path(folder)/'auth.db'
    database.initialise_database();auth.initialize_auth();vb.initialize()
    browser=TestClient(app);stranger=TestClient(app);bridge=TestClient(bridge_app)
    saved=browser.post('/worker/cases',json={'operation_id':str(uuid4()),'pin':'928371','preferred_name':'Fictional worker',
        'original_statement':'Fictional account: five days at 1000; 1000 received.','language':'en','pay_basis':'daily','units_worked':5,
        'rate_per_unit':'1000','payments_received':'1000','workplace_location':'Hyderabad','consent_to_store':True,
        'worker_confirmed':True,'adjustments_checked':True}).json()
    csrf={'X-CSRF-Token':saved['session']['csrf_token']}
    secret='fictional-section-secret';headers={'Authorization':'Bearer '+secret}
    config={'HAQRECORD_VOICE_PUBLIC_URL':'https://example.test','HAQRECORD_VOICE_TOOL_SECRET':secret}
    baseline=browser.get('/worker/my-case').json()
    with patch('voice_backend.dotenv_values',return_value=config),patch('voice_backend.voice.settings',return_value={'BOLNA_API_KEY':'fixture','BOLNA_AGENT_ID':'fixture'}),patch('voice_backend.voice.check_agent',return_value={'ready':True,'status':'verified','section_voice_ready':True}),patch('voice_backend.voice.callback_available',return_value=True),patch('voice_backend.httpx.post',return_value=httpx.Response(200,json={'run_id':'fictional-section-run'})) as mint:
        def start(section,values=None,restart=False,language='hi'):
            response=browser.post('/voice/intake/session',headers=csrf,json={'consent_to_voice_processing':True,'mode':'existing',
                'language':language,'section':section,'section_values':values or {},'restart_section':restart})
            assert response.status_code==200,response.text
            data=mint.call_args.kwargs['json']['user_data']
            assert 'SCOPED SECTION MODE' in data['section_guidance']
            return data['voice_token'],response.headers['X-Voice-CSRF'],data
        def guide(token,action='read',field='',value=None):
            result=bridge.post('/bolna/tools/guide-section',headers=headers,json={'voice_token':token,'action':action,'field':field,'value_json':json.dumps(value)})
            assert result.status_code==200,result.text
            return result.json()
        values={'workspace-basis':'daily','workspace-units':'5','workspace-rate':'1000','workspace-rate-source':'worker_account',
            'workspace-units-source':'worker_account','workspace-reason':'','workspace-open-questions':'','_payments':[]}
        assert stranger.post('/voice/intake/session',json={'consent_to_voice_processing':True,'mode':'existing','section':'agreement'}).status_code in (401,403)
        token,vcsrf,data=start('agreement',values)
        assert data['language']=='Hindi' and 'मज़दूरी' in data['haqrecord_opening']
        assert guide(token)['current_field']=='workspace-basis'
        assert not guide(token,'answer','workspace-rate',900)['accepted']
        assert not guide(token,'answer','workspace-basis','invented')['accepted']
        state=guide(token,'answer','workspace-basis','weekly');assert state['current_field']=='workspace-units'
        assert not guide(token,'answer','workspace-units','a month')['accepted']
        state=guide(token,'answer','workspace-units',4);assert state['current_field']=='workspace-rate'
        # No full-case reads or business writes are possible with a scoped capability.
        assert bridge.post('/bolna/tools/current-case',headers=headers,json={'voice_token':token}).status_code==403
        assert bridge.post('/bolna/tools/propose-resolution',headers=headers,json={'voice_token':token,'action':'schedule_reminder','fields_json':'{}'}).status_code==403
        assert bridge.post('/bolna/tools/guide-section',json={'voice_token':token,'action':'read'}).status_code==401
        assert stranger.get('/voice/intake/section-state').status_code==401
        assert browser.post('/voice/intake/end').status_code==403
        assert browser.post('/voice/intake/end',headers={'X-CSRF-Token':vcsrf}).status_code==200
        assert bridge.post('/bolna/tools/guide-section',headers=headers,json={'voice_token':token}).status_code==401
        token,vcsrf,_=start('agreement',values)
        assert guide(token)['current_field']=='workspace-rate'
        assert guide(token,'answer','workspace-rate',1500)['values']['workspace-rate']=='1500'
        assert not guide(token,'answer','workspace-rate-source','another-case-source')['accepted']
        token,vcsrf,_=start('agreement',values,restart=True,language='en')
        state=guide(token);assert state['current_field']=='workspace-basis' and state['values']['workspace-rate']=='1000'
        assert state['next_question'].startswith('Was pay agreed')
        row=guide(token,'add_payment')['values']['_payments'][0]
        assert row['amount']=='' and row['worker_confirmed'] is False
        print('PASS: one question at a time; invalid/cross-section answers blocked; scoped capabilities cannot read full cases or stage business actions; pause revokes; resume and restart are distinct.')

        token,vcsrf,_=start('evidence')
        assert not guide(token,'answer','workspace-file','invented-file.png')['accepted']
        assert browser.post('/voice/intake/section-file',json={'filename':'chosen.txt'}).status_code==403
        response=browser.post('/voice/intake/section-file',headers={'X-CSRF-Token':vcsrf},json={'filename':'chosen.txt'})
        assert response.status_code==200
        state=guide(token,'answer','workspace-file','chosen.txt');assert state['current_field']=='workspace-file-description'
        state=guide(token,'answer','workspace-file-description','A fictional message')
        assert not guide(token,'answer','workspace-fictional','yes')['accepted']
        assert guide(token,'answer','workspace-fictional',True)['current_field']=='workspace-store'
        assert not guide(token,'confirm','workspace-store')['accepted']
        assert guide(token,'answer','workspace-store',False)['current_field']=='workspace-fact-source'
        token,_,_=start('evidence',restart=True)
        assert guide(token,'skip','workspace-file')['current_field']=='workspace-fact-source'
        # Resume works after visiting another block; file contents were never uploaded.
        token,_,_=start('agreement',values)
        assert len(guide(token)['values']['_payments'])==1
        token,_,_=start('evidence')
        assert guide(token)['current_field']=='workspace-fact-source'
        print('PASS: file selection requires the browser; skip moves past upload-only fields; explicit booleans required; voice never uploads or invents a file; drafts resume across sections.')

        for section in ('facts','history'):
            token,_,_=start(section)
            state=guide(token);assert state['read_only'] and not state['fields'] and state['next_question'] is None
            assert not guide(token,'answer','workspace-rate',999)['accepted']
            assert 'records' in state and state['values']=={}
        token,_,_=start('followup',{'workspace-outcome':'received','workspace-reminder-id':''})
        assert guide(token,'skip','workspace-due')['current_field']=='workspace-reminder-id'
        assert guide(token,'answer','workspace-reminder-id','')['current_field']=='workspace-outcome'
        assert guide(token,'answer','workspace-outcome','none')['current_field']=='workspace-follow-statement'
        after=browser.get('/worker/my-case').json()
        assert after==baseline
        assert browser.get('/worker/resolution/state').json()['pending_voice_proposals']==[]
        bad=browser.post('/voice/intake/session',headers=csrf,json={'consent_to_voice_processing':True,'mode':'existing','section':'evidence',
            'restart_section':True,'section_values':{'workspace-rate':'999'}})
        assert bad.status_code==422
        print('PASS: facts/history remain read-only; no-payment branch skips received-money questions; all guidance leaves the case, payments, reminders and approved records unchanged.')
