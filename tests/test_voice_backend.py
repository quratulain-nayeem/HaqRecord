import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from contextlib import closing
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE']='false'
import httpx
from fastapi.testclient import TestClient
import auth
import database
import voice_backend as vb
from main import app
from bridge_app import app as bridge_app

with tempfile.TemporaryDirectory(prefix='haqrecord-voice-backend-test-') as temporary:
    database.DB_PATH=Path(temporary)/'cases.db';auth.AUTH_DB=Path(temporary)/'auth.db'
    database.initialise_database();auth.initialize_auth();vb.initialize()
    config={'HAQRECORD_VOICE_PUBLIC_URL':'https://example.test','HAQRECORD_VOICE_TOOL_SECRET':'isolated-service-secret'}
    headers={'Authorization':'Bearer isolated-service-secret'}
    a=TestClient(app);b=TestClient(app);bridge=TestClient(bridge_app)
    def reset_mint_limit():
        with closing(auth.connect()) as db,db:db.execute('DELETE FROM voice_mints')
    try:
        with patch('voice_backend.voice.check_agent',return_value={'ready':True,'status':'verified'}),patch('voice_backend.voice.callback_available',return_value=True),patch('voice_backend.dotenv_values',return_value=config),patch('voice_backend.voice.settings',return_value={'BOLNA_API_KEY':'test-key','BOLNA_AGENT_ID':'test-agent'}),patch('voice_backend.httpx.post',return_value=httpx.Response(200,json={'run_id':'fictional-test-run','session_id':'ephemeral-session'})) as mint:
            assert a.post('/voice/intake/session',json={'consent_to_voice_processing':False}).status_code==422
            with patch('voice_backend.voice.callback_available',return_value=False):
                assert a.post('/voice/intake/session',json={'consent_to_voice_processing':True}).status_code==503
                assert mint.call_count==0
            started=a.post('/voice/intake/session',json={'consent_to_voice_processing':True,'mode':'new','language':'hi'})
            assert started.status_code==200,started.text
            voice_token=mint.call_args.kwargs['json']['user_data']['voice_token']
            assert 'pin' not in str(mint.call_args.kwargs['json'])
            state=a.get('/voice/intake/state').json();csrf=state['csrf_token']
            with patch('research.dotenv_values',return_value={}):
                sources=bridge.post('/bolna/tools/resources',json={'voice_token':voice_token,'city':'bengaluru','issue':'unpaid_wages','language':'hi','fresh_lookup':True},headers=headers)
                assert sources.status_code==200,sources.text
                assert sources.json()['status']=='research_not_configured'
                assert a.get('/voice/intake/state').json()['resources']['city']=='bengaluru'
                assert bridge.post('/bolna/tools/resources',json={'voice_token':voice_token,'city':'bengaluru'}).status_code==401
            figures={'voice_token':voice_token,'pay_basis':'weekly','units_worked':4,'rate_per_unit':'1000','payments_received':'1000','adjustments_clear':True}
            assert bridge.post('/bolna/tools/calculate',json=figures).status_code==401
            calc=bridge.post('/bolna/tools/calculate',json=figures,headers=headers)
            assert calc.status_code==200 and calc.json()['calculation']['balance']=='3000.00'
            unclear=bridge.post('/bolna/tools/calculate',json={**figures,'adjustments_clear':False},headers=headers)
            assert unclear.json()['status']=='needs_clarification' and 'calculation' not in unclear.json()
            intake={**figures,'preferred_name':'Fictional Voice Worker','original_statement':'Four weeks at one thousand per week; received one thousand.',
                'language':'hi','employer_name':'','workplace_location':'','consent_to_store':True,'worker_confirmed':True}
            assert bridge.post('/bolna/tools/prepare-case',json={**intake,'worker_confirmed':False},headers=headers).status_code==422
            staged=bridge.post('/bolna/tools/prepare-case',json=intake,headers=headers)
            assert staged.status_code==200 and staged.json()['status']=='awaiting_browser_approval'
            duplicate=bridge.post('/bolna/tools/prepare-case',json=intake,headers=headers)
            assert duplicate.json()['draft_id']==staged.json()['draft_id']
            with closing(sqlite3.connect(database.DB_PATH)) as db:
                assert db.execute('SELECT COUNT(*) FROM cases').fetchone()[0]==0
            draft_id=staged.json()['draft_id']
            commit={'draft_id':draft_id,'approved':True,'pin':'938471'}
            assert bridge.post('/voice/intake/confirm',json=commit).status_code==404
            assert b.post('/voice/intake/confirm',json=commit,headers={'X-CSRF-Token':csrf}).status_code==401
            assert a.post('/voice/intake/confirm',json=commit).status_code==403
            assert a.post('/voice/intake/confirm',json={**commit,'draft_id':str(uuid4())},headers={'X-CSRF-Token':csrf}).status_code==409
            saved=a.post('/voice/intake/confirm',json=commit,headers={'X-CSRF-Token':csrf})
            assert saved.status_code==200,saved.text
            case_id=saved.json()['case']['case_id'];worker_csrf=saved.json()['session']['csrf_token']
            assert saved.json()['case']['calculation']['balance']=='3000.00'
            assert '938471' not in saved.text
            retry=a.post('/voice/intake/confirm',json=commit,headers={'X-CSRF-Token':csrf})
            assert retry.status_code==200 and retry.json()['case']['case_id']==case_id
            assert a.get('/worker/my-case').json()['case_id']==case_id
            print('PASS: voice calculation and draft staging; only private browser approval + PIN creates the case.')

            read=bridge.post('/bolna/tools/current-case',json={'voice_token':voice_token},headers=headers)
            assert read.json()['case']['case_id']==case_id
            payment={'voice_token':voice_token,'amount':'1000','received_on':'','method':'cash',
                'original_statement':'I received another thousand for this case.','worker_confirmed':True,'case_id':'HR-ATTACKER-CHOICE'}
            proposal=bridge.post('/bolna/tools/prepare-payment',json=payment,headers=headers)
            assert proposal.status_code==200,proposal.text
            assert a.get('/worker/my-case').json()['calculation']['balance']=='3000.00'
            payment_commit={'draft_id':proposal.json()['draft_id'],'approved':True}
            result=a.post('/voice/intake/confirm',json=payment_commit,headers={'X-CSRF-Token':csrf})
            assert result.status_code==200,result.text
            assert result.json()['case']['case_id']==case_id and result.json()['case']['calculation']['balance']=='2000.00'
            again=a.post('/voice/intake/confirm',json=payment_commit,headers={'X-CSRF-Token':csrf})
            assert again.status_code==200 and len(again.json()['case']['follow_up_payments'])==1
            repeat=bridge.post('/bolna/tools/prepare-payment',json=payment,headers=headers)
            assert repeat.json()['status']=='saved'
            print('PASS: confirmed follow-up changes 3000 to 2000; retries do not double-count or choose another case.')

            reset_mint_limit()
            started_b=b.post('/voice/intake/session',json={'consent_to_voice_processing':True,'mode':'new','language':'en'})
            assert started_b.status_code==200,started_b.text
            token_b=mint.call_args.kwargs['json']['user_data']['voice_token']
            assert bridge.post('/bolna/tools/current-case',json={'voice_token':token_b,'case_id':case_id},headers=headers).json()['status']=='no_case_open'
            assert b.get('/voice/intake/state').json()['case_id'] is None
            assert bridge.get('/cases/'+case_id).status_code==404
            assert bridge.get('/worker/my-case').status_code==404
            assert bridge.get('/docs').status_code==404
            print('PASS: another voice session cannot select the saved case; public bridge exposes no dashboard or case APIs.')

            assert a.post('/worker/logout',headers={'X-CSRF-Token':worker_csrf}).status_code==200
            assert bridge.post('/bolna/tools/current-case',json={'voice_token':voice_token},headers=headers).status_code==401
            assert a.get('/voice/intake/state').status_code==401
            print('PASS: worker logout revokes access to case data through the existing voice capability.')
    finally:
        a.close();b.close();bridge.close()
print('All connected voice/backend tests passed using fictional records in temporary databases.')
