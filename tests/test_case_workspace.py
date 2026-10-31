"""Two-session messy-case demonstration and private evidence boundaries."""
import base64
import copy
import io
import json
import os
import sqlite3
import sys
import tempfile
import zipfile
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

def uid():return str(uuid4())

with tempfile.TemporaryDirectory(prefix='haq-workspace-') as folder:
    database.DB_PATH=Path(folder)/'cases.db';auth.AUTH_DB=Path(folder)/'auth.db'
    database.initialise_database();auth.initialize_auth();vb.initialize()
    a=TestClient(app);b=TestClient(app);bridge=TestClient(bridge_app)
    reconstruction={'pay_basis':'daily','units_worked':18,'rate_per_unit':'700.00','payments':[
        {'payment_id':'transfer-1','amount':'4000.00','status':'received','allocation':'this_case','worker_confirmed':True,'statement':'Received transfer for this job.'},
        {'payment_id':'cash-1','amount':'1000.00','status':'received','allocation':'unresolved','worker_confirmed':False,'method':'cash','statement':'May be for a previous job.'},
        {'payment_id':'promise-1','amount':'4000.00','status':'promised','allocation':'this_case','worker_confirmed':False,'statement':'Employer promised money; not received.'},
    ]}
    body={'pay_basis':'daily','units_worked':18,'rate_per_unit':'700.00','payments_received':'4000.00','reconstruction':reconstruction,
          'preferred_name':'Fictional Worker','workplace_location':'Hyderabad','original_statement':'Fictional messy wage dispute.',
          'pin':'684295','operation_id':uid(),'consent_to_store':True,'worker_confirmed':True}
    bad=a.post('/worker/cases',json={**body,'payments_received':'9000.00'})
    assert bad.status_code==422
    saved=a.post('/worker/cases',json=body);assert saved.status_code==201,saved.text
    case=saved.json()['case'];case_id=case['case_id'];csrf=saved.json()['session']['csrf_token'];headers={'X-CSRF-Token':csrf}
    c=case['calculation']
    assert (c['total_earned'],c['payments_received'],c['unallocated_received'],c['promised_amount'],c['balance'])==('12600.00','4000.00','1000.00','4000.00','8600.00')
    assert c['provisional'] and '1000.00' in case['workspace']['next_question']
    assert c['balance_if_unallocated_applies']=='7600.00'
    print('PASS: ambiguous cash and promises stay separate; provisional 8600, conditional 7600.')

    upload={'operation_id':uid(),'filename':'../../fictional.png','mime':'image/png',
            'content_base64':base64.b64encode(b'\x89PNG\r\n\x1a\nfictional-fixture').decode(),
            'description':'Fictional transfer screenshot <script>alert(1)</script>','fictional':True,'consent_to_store':True}
    assert a.post('/worker/workspace/evidence',json=upload).status_code==403
    assert b.post('/worker/workspace/evidence',json=upload,headers=headers).status_code==401
    result=a.post('/worker/workspace/evidence',json=upload,headers=headers);assert result.status_code==201,result.text
    source=result.json()['source_id']
    assert a.post('/worker/workspace/evidence',json=upload,headers=headers).json()['source_id']==source
    assert a.post('/worker/workspace/evidence',json={**upload,'description':'different'},headers=headers).status_code==409
    assert b.get('/worker/workspace/evidence/'+source).status_code==401
    assert a.get('/worker/workspace/evidence/'+source).content.startswith(b'\x89PNG')
    assert a.post('/worker/workspace/evidence',json={**upload,'operation_id':uid(),'mime':'application/pdf'},headers=headers).status_code==422
    note={'operation_id':uid(),'source_id':source,'fact':'payment_amount','value':'4000 transfer shown',
          'unresolved':'Confirm which job the screenshot concerns.','worker_confirmed':False}
    linked=a.post('/worker/workspace/fact-source',json=note,headers=headers);assert linked.status_code==200,linked.text
    assert 'not_independently_verified' in linked.json()['workspace']['facts'][-1]['status']
    assert linked.json()['calculation']['balance']=='8600.00'

    revised=copy.deepcopy(reconstruction)
    revised['payments'][0]['source_ids']=[source]
    revised['payments'][1].update(allocation='this_case',worker_confirmed=True)
    preview=a.post('/worker/workspace/preview',json=revised,headers=headers);assert preview.status_code==200,preview.text
    assert preview.json()['calculation']['balance']=='7600.00'
    request={'operation_id':uid(),'expected_version':0,'reconstruction':revised,'reason':'Worker confirmed the cash was for this job.','worker_confirmed':True}
    revised_case=a.post('/worker/workspace/reconstruction',json=request,headers=headers);assert revised_case.status_code==200,revised_case.text
    assert revised_case.json()['calculation']['balance']=='7600.00'
    assert revised_case.json()['intake']['reconstruction']['payments'][1]['allocation']=='unresolved'
    assert a.post('/worker/workspace/reconstruction',json=request,headers=headers).json()['workspace']['version']==1
    assert a.post('/worker/workspace/reconstruction',json={**request,'operation_id':uid()},headers=headers).status_code==409
    invalid=copy.deepcopy(revised);invalid['payments'][0]['source_ids']=['SRC-FOREIGN']
    assert a.post('/worker/workspace/reconstruction',json={**request,'expected_version':1,'operation_id':uid(),'reconstruction':invalid},headers=headers).status_code==422
    print('PASS: evidence is private, links remain interpretations, corrections are versioned and original account survives.')

    reminder={'operation_id':uid(),'due_at':'2026-10-26T09:00:00+05:30','action':'Check whether the promised wages arrived.','consent':True}
    reminded=a.post('/worker/workspace/reminders',json=reminder,headers=headers);assert reminded.status_code==200,reminded.text
    rid=reminded.json()['workspace']['reminders'][0]['reminder_id']
    assert a.post('/worker/workspace/reminders',json=reminder,headers=headers).json()['workspace']['reminders'][0]['reminder_id']==rid
    assert a.post('/worker/workspace/reminders',json={**reminder,'operation_id':uid(),'due_at':'2026-10-26T09:00:00'},headers=headers).status_code==422
    assert a.post('/worker/logout',headers=headers).status_code==200
    reopened=a.post('/worker/login',json={'case_id':case_id,'pin':'684295'});assert reopened.status_code==200
    csrf=reopened.json()['csrf_token'];headers={'X-CSRF-Token':csrf}
    configs={'HAQRECORD_VOICE_PUBLIC_URL':'https://example.test','HAQRECORD_VOICE_TOOL_SECRET':'isolated-tool-secret'}
    with patch('voice_backend.dotenv_values',return_value=configs),patch('voice_backend.voice.settings',return_value={'BOLNA_API_KEY':'test','BOLNA_AGENT_ID':'test'}),patch('voice_backend.voice.callback_available',return_value=True),patch('voice_backend.voice.check_agent',return_value={'ready':True,'status':'verified'}),patch('voice_backend.httpx.post',return_value=httpx.Response(200,json={'run_id':'fictional-followup'})) as mint:
        started=a.post('/voice/intake/session',json={'consent_to_voice_processing':True,'mode':'existing','language':'hi'},headers=headers);assert started.status_code==200,started.text
        token=mint.call_args.kwargs['json']['user_data']['voice_token'];tool_headers={'Authorization':'Bearer isolated-tool-secret'}
        loaded=bridge.post('/bolna/tools/current-case',json={'voice_token':token},headers=tool_headers).json()
        assert loaded['case']['case_id']==case_id and loaded['case']['workspace']['reminders'][0]['reminder_id']==rid
        proposed=bridge.post('/bolna/tools/prepare-payment',json={'voice_token':token,'amount':'2000','reminder_id':rid,'method':'transfer',
            'original_statement':'Another 2000 received for this case.','worker_confirmed':True},headers=tool_headers)
        assert proposed.status_code==200,proposed.text
        voice_csrf=a.get('/voice/intake/state').json()['csrf_token']
        commit={'draft_id':proposed.json()['draft_id'],'approved':True}
        paid=a.post('/voice/intake/confirm',json=commit,headers={'X-CSRF-Token':voice_csrf});assert paid.status_code==200,paid.text
        assert paid.json()['case']['calculation']['balance']=='5600.00'
        assert paid.json()['case']['workspace']['reminders'][0]['state']=='completed'
        retry=a.post('/voice/intake/confirm',json=commit,headers={'X-CSRF-Token':voice_csrf})
        assert retry.json()['case']['calculation']['balance']=='5600.00' and len(retry.json()['case']['follow_up_payments'])==1
        correction=copy.deepcopy(revised);correction['units_worked']=19
        proposal=bridge.post('/bolna/tools/reconstruct-dispute',json={'voice_token':token,'reconstruction':correction,
            'original_statement':'Worker corrected completed days to nineteen.','expected_version':1,'worker_confirmed':True},headers=tool_headers)
        assert proposal.status_code==200,proposal.text
        assert a.get('/worker/my-case').json()['calculation']['balance']=='5600.00'
        corrected=a.post('/voice/intake/confirm',json={'draft_id':proposal.json()['draft_id'],'approved':True},headers={'X-CSRF-Token':voice_csrf})
        assert corrected.status_code==200,corrected.text
        assert corrected.json()['case']['calculation']['balance']=='6300.00'
        proposal=bridge.post('/bolna/tools/prepare-reminder',json={'voice_token':token,'due_at':'2026-10-27T10:00:00+05:30',
            'action':'Check whether more wages arrived.','consent':True},headers=tool_headers)
        assert proposal.status_code==200,proposal.text
        reminded=a.post('/voice/intake/confirm',json={'draft_id':proposal.json()['draft_id'],'approved':True},headers={'X-CSRF-Token':voice_csrf})
        assert reminded.status_code==200,reminded.text
        pending=next(r for r in reminded.json()['case']['workspace']['reminders'] if r['state']=='pending')
        proposal=bridge.post('/bolna/tools/prepare-no-payment-followup',json={'voice_token':token,'reminder_id':pending['reminder_id'],
            'statement':'No further money arrived.','worker_confirmed':True},headers=tool_headers)
        assert proposal.status_code==200,proposal.text
        no_money=a.post('/voice/intake/confirm',json={'draft_id':proposal.json()['draft_id'],'approved':True},headers={'X-CSRF-Token':voice_csrf})
        assert no_money.status_code==200,no_money.text
        assert no_money.json()['case']['calculation']['balance']=='6300.00'
        # The first voice conversation can create a provisional reconstruction too.
        guest=TestClient(app)
        assert guest.post('/voice/intake/session',json={'consent_to_voice_processing':True,'language':'hi'}).status_code==200
        guest_token=mint.call_args.kwargs['json']['user_data']['voice_token']
        result=bridge.post('/bolna/tools/reconstruct-dispute',json={'voice_token':guest_token,'reconstruction':reconstruction,
            'original_statement':'Fictional first conversation with unclear cash.','workplace_location':'Bengaluru'},headers=tool_headers)
        assert result.status_code==200,result.text
        assert result.json()['calculation']['balance']=='8600.00'
        state=guest.get('/voice/intake/state').json();guest_headers={'X-CSRF-Token':state['csrf_token']}
        proposed=guest.post('/voice/intake/prepare-preview',json={'preview_id':state['preview']['preview_id'],
            'original_statement':'Fictional first conversation with unclear cash.','preferred_name':'Fictional second worker',
            'workplace_location':'Bengaluru','approved':True},headers=guest_headers)
        assert proposed.status_code==200,proposed.text
        created=guest.post('/voice/intake/confirm',json={'draft_id':proposed.json()['draft_id'],'approved':True,'pin':'684295'},headers=guest_headers)
        assert created.status_code==200,created.text
        assert created.json()['case']['calculation']['unallocated_received']=='1000.00'
        assert created.json()['case']['workspace']['pilot_city']=='bengaluru'
        assert guest.get('/worker/workspace/evidence/'+source).status_code==404
        guest_worker_headers={'X-CSRF-Token':created.json()['session']['csrf_token']}
        assert guest.post('/worker/workspace/fact-source',json=note,headers=guest_worker_headers).status_code==422
    print('PASS: second voice session changes the same case once, completes its reminder atomically, and applies a reviewed correction.')

    response=a.get('/worker/workspace/packet');assert response.status_code==200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        html=archive.read('case-packet.html').decode()
        assert '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;' in html and 'not independently verified' in html
        snapshot=json.loads(archive.read('case-record.json'))
        assert snapshot['calculation']['balance']=='6300.00'
        assert all('..' not in p and not p.startswith('/') for p in archive.namelist())
        assert len([n for n in archive.namelist() if n.startswith('supporting-material/')])==1
        assert '684295' not in json.dumps(snapshot)
        assert 'government complaint submitted' in html
    assert b.get('/worker/workspace/packet').status_code==401
    reminder2=a.post('/worker/workspace/reminders',json={**reminder,'operation_id':uid()},headers=headers).json()['workspace']['reminders'][-1]['reminder_id']
    # Select the pending reminder explicitly: equal due dates need no stable order.
    reminder2=next(r['reminder_id'] for r in a.get('/worker/my-case').json()['workspace']['reminders'] if r['state']=='pending')
    note={'operation_id':uid(),'reminder_id':reminder2,'statement':'No additional money received.','worker_confirmed':True}
    follow=a.post('/worker/workspace/no-payment-followup',json=note,headers=headers);assert follow.status_code==200,follow.text
    assert follow.json()['calculation']['balance']=='6300.00'
    assert a.post('/worker/workspace/no-payment-followup',json=note,headers=headers).status_code==200
    assert follow.json()['complaint_status']=='not_prepared'
    assert not follow.json()['workspace']['outbound_calls_enabled']
    print('PASS: packet contains printable report, current record and original sources; no-payment follow-up leaves the balance and submission status unchanged.')
