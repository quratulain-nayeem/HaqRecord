import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE']='false'

import httpx
from fastapi.testclient import TestClient
import auth
import database
import voice
from main import app

with tempfile.TemporaryDirectory(prefix='haqrecord-worker-test-') as temporary:
    database.DB_PATH=Path(temporary)/'cases.db'
    auth.AUTH_DB=Path(temporary)/'auth.db'
    database.initialise_database();auth.initialize_auth()
    password=secrets.token_urlsafe(24)
    auth.provision_account('voice-tester',password)
    staff=TestClient(app);a=TestClient(app);b=TestClient(app)
    try:
        weekly={'pay_basis':'weekly','units_worked':4,'rate_per_unit':'1000.00','payments_received':'1000.00'}
        assert a.post('/calculate',json=weekly).json()['balance']=='3000.00'
        daily={'days_worked':8,'daily_rate':800,'payments_received':2500}
        assert a.post('/calculate',json=daily).json()['balance']=='3900.00'
        assert a.post('/calculate',json={**weekly,'pay_basis':'monthly'}).json()['balance']=='3000.00'
        assert a.post('/calculate',json={**daily,'units_worked':7}).status_code==422
        assert a.post('/calculate',json={**weekly,'rate_per_unit':'1000.001'}).status_code==422
        print('PASS: daily compatibility, weekly 3000 calculation and invalid arrangements rejected.')

        case_payload={**weekly,'preferred_name':'Fictional Worker A','original_statement':'Four weeks at 1000; received 1000.',
                      'pin':'938471','operation_id':str(uuid4()),'consent_to_store':True,'worker_confirmed':True}
        assert a.post('/worker/cases',json=case_payload,headers={'Origin':'https://evil.example'}).status_code==403
        assert a.post('/worker/cases',json={**case_payload,'consent_to_store':False}).status_code==422
        saved=a.post('/worker/cases',json=case_payload)
        assert saved.status_code==201,saved.text
        data=saved.json();case_a=data['case']['case_id'];csrf_a=data['session']['csrf_token']
        old_token=a.cookies.get('haqrecord_worker')
        retried=a.post('/worker/cases',json=case_payload)
        assert retried.status_code==201 and retried.json()['case']['case_id']==case_a
        csrf_a=retried.json()['session']['csrf_token']
        with closing(sqlite3.connect(database.DB_PATH)) as db:
            assert db.execute('SELECT COUNT(*) FROM cases').fetchone()[0]==1
            pin_hash=db.execute('SELECT pin_hash FROM worker_access').fetchone()[0]
            assert pin_hash.startswith('$argon2id$') and pin_hash!=case_payload['pin']
            original_snapshot=db.execute('SELECT record_json FROM cases WHERE case_id=?',(case_a,)).fetchone()[0]
        assert '938471' not in a.get('/worker/my-case').text
        other=b.post('/worker/cases',json={**case_payload,'preferred_name':'Fictional Worker B',
                                         'pin':'840295','operation_id':str(uuid4())})
        assert other.status_code==201
        case_b=other.json()['case']['case_id']
        assert a.get('/worker/my-case').json()['case_id']==case_a
        assert b.get('/worker/my-case').json()['case_id']==case_b
        assert a.get('/cases/'+case_b).status_code==401
        assert b.get('/cases/'+case_a).status_code==401
        assert a.get('/caseworker',follow_redirects=False).status_code==303
        print('PASS: PIN hashes, retry-safe case creation and separate worker access on a shared device.')

        payment={'operation_id':str(uuid4()),'amount':1000,'received_on':'2026-10-25','method':'cash',
                 'original_statement':'I received another 1000 for this case.','worker_confirmed':True}
        assert a.post('/worker/payments',json=payment).status_code==403
        update=a.post('/worker/payments',json=payment,headers={'X-CSRF-Token':csrf_a})
        assert update.status_code==201,update.text
        assert update.json()['case']['calculation']['balance']=='2000.00'
        retry=a.post('/worker/payments',json=payment,headers={'X-CSRF-Token':csrf_a})
        assert retry.status_code==201
        assert retry.json()['payment']['payment_id']==update.json()['payment']['payment_id']
        assert len(retry.json()['case']['follow_up_payments'])==1
        conflict=a.post('/worker/payments',json={**payment,'amount':1500},headers={'X-CSRF-Token':csrf_a})
        assert conflict.status_code==409
        duplicate=a.post('/worker/payments',json={**payment,'operation_id':str(uuid4()),'received_on':None},headers={'X-CSRF-Token':csrf_a})
        assert duplicate.status_code==409 and duplicate.json()['detail']['code']=='possible_duplicate'
        with closing(sqlite3.connect(database.DB_PATH)) as db:
            assert db.execute('SELECT record_json FROM cases WHERE case_id=?',(case_a,)).fetchone()[0]==original_snapshot
        assert b.get('/worker/my-case').json()['calculation']['balance']=='3000.00'
        print('PASS: 3000 -> 2000, retries do not deduct twice, ambiguous duplicates flagged, original record unchanged.')

        concurrent={**payment,'operation_id':str(uuid4()),'amount':'2.50','method':'transfer'}
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:database.append_payment(case_a,concurrent),range(2)))
        assert results[0]['payment_id']==results[1]['payment_id']
        assert a.get('/worker/my-case').json()['calculation']['balance']=='1997.50'
        assert len(a.get('/worker/my-case').json()['follow_up_payments'])==2
        print('PASS: concurrent payment retries are serialized and recorded only once.')

        assert a.post('/worker/logout',headers={'X-CSRF-Token':csrf_a}).status_code==200
        assert a.get('/worker/my-case').status_code==401
        assert a.post('/worker/login',json={'case_id':case_a,'pin':'000000'}).status_code==401
        reopened=a.post('/worker/login',json={'case_id':case_a,'pin':'938471'})
        assert reopened.status_code==200
        assert a.get('/worker/my-case').json()['case_id']==case_a
        for _ in range(5):
            assert b.post('/worker/login',json={'case_id':case_a,'pin':'000000'}).status_code==401
        assert b.post('/worker/login',json={'case_id':case_a,'pin':'938471'}).status_code==429
        print('PASS: workers return by reference + PIN; logout and PIN attempt limits work.')

        assert staff.post('/auth/login',json={'username':'voice-tester','password':password}).status_code==200
        staff_csrf=staff.get('/auth/session').json()['csrf_token']
        headers={'X-CSRF-Token':staff_csrf}
        request={'consent_to_voice_processing':True,'language':'hi'}
        assert a.post('/voice/session',json=request).status_code==401
        with patch('voice.settings',return_value={}):
            assert not staff.get('/voice/status').json()['ready']
            assert staff.post('/voice/session',json=request,headers=headers).status_code==503
        with patch('voice.settings',return_value={'BOLNA_API_KEY':'server-only-test-key','BOLNA_AGENT_ID':'test-agent'}):
            assert staff.post('/voice/session',json={**request,'consent_to_voice_processing':False},headers=headers).status_code==422
            assert staff.post('/voice/session',json=request).status_code==403
            with patch('voice.httpx.post',return_value=httpx.Response(200,json={'session_id':'ephemeral-test-session'})) as mint:
                response=staff.post('/voice/session',json=request,headers=headers)
                assert response.status_code==200,response.text
                assert response.json()=={'session_id':'ephemeral-test-session'}
                assert 'server-only-test-key' not in response.text
                assert mint.call_args.kwargs['json']['agent_id']=='test-agent'
                assert staff.post('/voice/session',json=request,headers=headers).status_code==200
        print('PASS: voice session credentials stay server-side; consent, login and CSRF enforced; immediate voice retries allowed.')
        print('NOTE: provider responses were mocked. A real two-way Bolna/Sarvam call is still required.')
    finally:
        staff.close();a.close();b.close()

print('All worker/voice tests passed using temporary databases.')
