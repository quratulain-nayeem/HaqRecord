import os
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE']='false'
from fastapi.testclient import TestClient
from pydantic import ValidationError
import auth,database,resolution,resolution_voice
from main import app
from case_models import CaseCreate,WageCalculation
from case_service import calculate_wages
from dispute_models import DisputeReconstruction

uid=lambda:str(uuid4())
assert calculate_wages(WageCalculation(pay_basis='hourly',units_worked='3.5',rate_per_unit='100',payments_received='0'))['balance']=='350.00'
assert calculate_wages(WageCalculation(pay_basis='piece',units_worked=12,rate_per_unit='2.50',payments_received='10'))['balance']=='20.00'
try:
    CaseCreate(pay_basis='monthly',units_worked=1,rate_per_unit=1000,payments_received=0,preferred_name='Fictional',original_statement='Monthly salary and weekly wages were both agreed.',worker_confirmed=True,consent_to_store=True)
    raise AssertionError('Mixed units must be clarified')
except ValidationError:pass

with tempfile.TemporaryDirectory(prefix='haqrecord-foundations-') as folder:
    database.DB_PATH=Path(folder)/'cases.db';auth.AUTH_DB=Path(folder)/'auth.db'
    database.initialise_database();auth.initialize_auth()
    client=TestClient(app)
    created=client.post('/worker/diary-books',json={'operation_id':uid(),'preferred_name':'Fictional diarist','pin':'928371','language':'hi','consent_to_store':True})
    assert created.status_code==201,created.text
    saved=created.json();headers={'X-CSRF-Token':saved['session']['csrf_token']}
    def state():return client.get('/worker/resolution/state').json()
    def mutation(**data):return {'operation_id':uid(),'expected_revision':state()['revision'],'confirmed':True,**data}
    def post(path,data):
        response=client.post('/worker/resolution/'+path,json=data,headers=headers)
        assert response.status_code==200,response.text
        return response.json()
    assert state()['next_action']=='record_work' and state()['case']['record_type']=='work_diary'
    entry=post('diary',mutation(work_date='2026-10-31',workplace='Fictional Site',quantity='1',rate_unit='daily',rate='700',payment_received='100',statement='One day, 700 agreed; 100 received.'))['events'][-1]['event_id']
    assert state()['case']['calculation']['balance']=='0.00'
    included=mutation(entry_id=entry,balance_version=state()['balance_version'],new_work_confirmed=True,payment_is_additional=True,reason='Explicitly include this work, not counted before.')
    result=post('include-diary',included)
    assert result['case']['calculation']['balance']=='600.00'
    assert post('include-diary',included)['case']['calculation']['balance']=='600.00'
    assert client.post('/worker/resolution/include-diary',json=mutation(**{k:v for k,v in included.items() if k not in ('operation_id','expected_revision','confirmed')}),headers=headers).status_code==409
    print('PASS: private standalone diary, explicit inclusion with one receipt reference, and duplicate-allocation protection.')

    periods=post('work-periods',mutation(balance_version=state()['balance_version'],pay_basis='daily',periods=[
        {'quantity':'1','rate':'700','description':'First confirmed day','worker_confirmed':True},
        {'quantity':'1.5','rate':'800','description':'Later confirmed partial period at a changed rate','worker_confirmed':True}],reason='Confirmed rate change and partial day.'))
    assert periods['case']['calculation']['total_earned']=='1900.00'
    assert periods['case']['calculation']['balance']=='1800.00'
    assert len(periods['case']['calculation']['work_periods'])==2
    # Messy fixture: reimbursement remains allocated elsewhere, promise not received.
    reconstruction=DisputeReconstruction(pay_basis='weekly',units_worked=4,rate_per_unit='1500',payments=[
        {'payment_id':'wages','amount':'1500','status':'received','allocation':'this_case','worker_confirmed':True,'statement':'Wages from the 2000 received'},
        {'payment_id':'travel','amount':'500','status':'received','allocation':'reimbursement','worker_confirmed':True,'statement':'Confirmed separate travel reimbursement, not wages'},
        {'payment_id':'promise','amount':'1000','status':'promised','allocation':'this_case','worker_confirmed':True,'statement':'Not yet received'}])
    result=calculate_wages(WageCalculation(pay_basis='weekly',units_worked=4,rate_per_unit='1500',payments_received='1500',reconstruction=reconstruction))
    assert (result['total_earned'],result['payments_received'],result['balance'])==('6000.00','1500.00','4500.00')
    print('PASS: hourly/piece units, confirmed partial periods and different rates, mixed-unit clarification, and 6000/1500/4500 reimbursement fixture.')

    body={'operation_id':uid(),'amount':'300','original_statement':'Actual payment for the account.','worker_confirmed':True,'distinct_payment_confirmed':True}
    payment=client.post('/worker/payments',json=body,headers=headers);assert payment.status_code==201,payment.text
    pid=payment.json()['payment']['payment_id']
    correction=mutation(payment_id=pid,expected_amount='300',corrected_amount='200',balance_version=state()['balance_version'],reason='Confirmed actual amount was 200, not 300.')
    corrected=post('correct-payment',correction)
    assert corrected['case']['calculation']['balance']=='1600.00'
    assert post('correct-payment',correction)['case']['calculation']['balance']=='1600.00'
    assert len(corrected['case']['follow_up_payments'])==2
    print('PASS: actual payment correction is append-only, atomic, exact and safe to retry.')

    # Voice proposals never commit facts on a model assertion of confirmation.
    context={'case_id':saved['case']['case_id'],'context_id':uid()}
    with patch('resolution_voice.voice_backend.tool_context',return_value=context):
        proposal=resolution_voice.propose(resolution_voice.Proposal(voice_token='fictional-token-value-long-enough',action='record_promise',fields_json='{"amount":"100","statement":"Fictional promise"}'))
    assert proposal['saved'] is False and state()['pending_voice_proposals']
    before=state()['case']['calculation']['balance']
    post('confirm-voice-proposal',mutation(proposal_id=proposal['proposal_id']))
    assert not state()['pending_voice_proposals'] and state()['case']['calculation']['balance']==before
    with patch('resolution_voice.voice_backend.tool_context',return_value=context):
        proposal=resolution_voice.propose(resolution_voice.Proposal(voice_token='fictional-token-value-long-enough',action='record_promise',fields_json='{"amount":"200","statement":"Discard this"}'))
    post('dismiss-voice-proposal',mutation(proposal_id=proposal['proposal_id']))
    assert not state()['pending_voice_proposals']
    assert client.post('/worker/resolution/confirm-voice-proposal',json=mutation(proposal_id=proposal['proposal_id']),headers=headers).status_code==409
    print('PASS: voice can only stage a case-bound proposal; browser confirmation required; discarded proposal cannot silently become a confirmed fact.')
    assert client.post('/worker/resolution/delete',json={'case_reference':'another-record','delete_case_and_originals':True},headers=headers).status_code==422
    deleted=client.post('/worker/resolution/delete',json={'case_reference':saved['case']['case_id'],'delete_case_and_originals':True},headers=headers)
    assert deleted.status_code==200 and deleted.json()['deleted']
    assert client.get('/worker/my-case').status_code==401
    import sqlite3
    with sqlite3.connect(database.DB_PATH) as db:
        for table in ('cases','resolution_events','case_revisions','payment_events','reply_sources','worker_access'):
            assert db.execute('SELECT count(*) FROM '+table).fetchone()[0]==0
    db.close()
    print('PASS: deletion requires the attached reference and removes the active record, originals, payments, revisions and history; shared-browser access is revoked.')

print('Foundation checks passed using isolated fictional databases.')
