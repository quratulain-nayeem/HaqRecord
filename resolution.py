"""Case-bound resolution actions. Browser approval is required for every mutation."""
import base64
import binascii
import hashlib
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, quote
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from dotenv import dotenv_values

import auth
import database
import worker
from memory_budget import memory_heavy,single_source_job
import resolution_store as store
from case_service import read_case_record
from case_workspace_service import fingerprint
from reply_sources import extract, interpret, provider_interpret, settings as extraction_settings, validate_file

router=APIRouter(prefix='/worker/resolution',tags=['Case resolution'])
public_router=APIRouter(tags=['Recipient response'])
# The India pilot uses IST (UTC+05:30), with no daylight-saving transition.
INDIA=timezone(timedelta(hours=5,minutes=30),name='Asia/Kolkata')


class Model(BaseModel):
    model_config=ConfigDict(extra='forbid')


class Mutation(Model):
    operation_id: UUID
    expected_revision: int = Field(ge=0)
    confirmed: Literal[True]


def record(case_id):
    result=read_case_record(case_id)
    if not result:raise HTTPException(404,'Case unavailable')
    return result


def balance_version(case):
    return fingerprint({'calculation':case['calculation'],'payments':case['follow_up_payments'],
                        'version':case['workspace']['version']})


def append(case_id,data,kind,payload):
    with store.transaction() as db:
        return store.append(db,case_id,data.operation_id,data.expected_revision,kind,payload,
                            data.model_dump(mode='json'))


def next_action(case,events,sources,today=None):
    today=today or datetime.now(INDIA).date()
    if case.get('record_type')=='work_diary' and not case['workspace']['reconstruction']:return 'record_work'
    reviewed={e['payload']['source_id'] for e in events if e['kind']=='reply_reviewed'}
    promises=[e for e in events if e['kind']=='promise_recorded']
    safety=[e for e in events if e['kind']=='contact_preference']
    if safety and not safety[-1]['payload']['contact_safe']:return 'next_step'
    if safety and safety[-1]['payload'].get('wants_next_step'):return 'next_step'
    if any(s['source_id'] not in reviewed for s in sources):return 'explain_reply'
    if any(e['kind']=='recipient_response' and not any(r['kind']=='recipient_response_reviewed' and r['payload']['response_id']==e['event_id'] for r in events) for e in events):return 'explain_reply'
    if case['calculation'].get('provisional'):return 'clarify_account'
    if Decimal(case['calculation']['balance'])<=0:return 'review_case_status'
    for promise in reversed(promises):
        p=promise['payload'];paid=sum((Decimal(x['amount']) for x in case['follow_up_payments'] if x.get('promise_id')==promise['event_id']),Decimal(0))
        answers=[e for e in events if e['kind']=='promise_checked' and e['payload']['promise_id']==promise['event_id']]
        if paid>=Decimal(p['amount']):continue
        if p.get('due_on') and date.fromisoformat(p['due_on'])<today:
            if not answers:return 'ask_if_paid'
            if not answers[-1]['payload']['money_arrived']:return 'next_step'
            return 'record_payment'
        return 'offer_reminder' if p.get('due_on') else 'confirm_promise_date'
    if any(e['kind']=='worker_reports_sent' for e in events):return 'next_step'
    return 'prepare_request'


def public_base():
    values=dotenv_values(Path(__file__).with_name('.env'))
    raw=(values.get('HAQRECORD_PUBLIC_APP_URL') or os.getenv('HAQRECORD_PUBLIC_APP_URL','')).rstrip('/')
    url=urlsplit(raw)
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('','/'):
        return None
    import ipaddress
    if url.hostname.lower() in ('localhost','testserver') or url.hostname.lower().endswith(('.local','.localhost')):return None
    try:
        if not ipaddress.ip_address(url.hostname).is_global:return None
    except ValueError:pass
    return raw


class DiaryBook(Model):
    operation_id: UUID
    preferred_name: str=Field(default='Worker',min_length=1,max_length=100)
    pin: str=Field(pattern=r'^[0-9]{6,12}$')
    language: Literal['hi','en']='hi'
    consent_to_store: Literal[True]


class DeleteCase(Model):
    case_reference: str=Field(min_length=1,max_length=100)
    delete_case_and_originals: Literal[True]


@router.post('/delete')
def delete_case(data:DeleteCase,session=Depends(worker.require_worker)):
    if data.case_reference!=session['case_id']:raise HTTPException(422,'Type this case reference to confirm deletion.')
    # Delete history and originals together; append-only history is not a retention
    # exception. Copies outside this active database are disclosed separately.
    with store.transaction() as db:
        db.execute('PRAGMA secure_delete=ON')
        for table in ('response_links','resolution_events','reply_sources','case_fact_sources','case_evidence','case_reminders',
                      'case_followup_notes','case_revisions','payment_events','voice_confirmations','voice_contexts','worker_sessions','worker_access'):
            if db.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',('table',table)).fetchone():
                db.execute('DELETE FROM '+table+' WHERE case_id=?',(session['case_id'],))
        db.execute('DELETE FROM cases WHERE case_id=?',(session['case_id'],))
    return {'deleted':True,'notice':'Removed from the active case database, including originals, diary and history. Previously downloaded files, operator backups, and provider-retained data require separate removal; physical erasure is not guaranteed.'}


@public_router.post('/worker/diary-books',status_code=201)
def diary_book(data:DiaryBook,request:Request,response:Response):
    worker.check_json_origin(request)
    worker.rate_limit(['create-diary:'+(request.client.host if request.client else 'unknown')])
    public=data.model_dump(mode='json',exclude={'pin','operation_id'})
    digest=fingerprint(public)
    pin_hash=auth.PASSWORDS.hash(data.pin)
    with store.transaction() as db:
        old=db.execute('SELECT case_id,pin_hash,request_hash FROM worker_access WHERE operation_id=?',(str(data.operation_id),)).fetchone()
        if old:
            if old['request_hash']!=digest or not auth.PASSWORDS.verify(data.pin,old['pin_hash']):raise HTTPException(409,'This creation reference was already used.')
            case_id=old['case_id']
        else:
            case_id='HR-'+uuid4().hex.upper()
            calculation={'currency':'INR','pay_basis':'daily','units_worked':0,'rate_per_unit':'0.00','total_earned':'0.00','payments_received':'0.00','balance':'0.00','note':'No wage dispute created. Work diary entries remain separate.'}
            value={'case_id':case_id,'created_at':store.now(),'record_type':'work_diary','status':'work_diary',
                'complaint_status':'not_prepared','source':'reported_by_worker','intake':{'preferred_name':data.preferred_name,
                'original_statement':'Private work diary, not a wage dispute.','language':data.language,'pay_basis':'daily','units_worked':0,
                'rate_per_unit':'0.00','payments_received':'0.00','workplace_location':None,'employer_name':None},
                'calculation':calculation,'unresolved_questions':[]}
            db.execute('INSERT INTO cases VALUES(?,?,?)',(case_id,value['created_at'],json.dumps(value,ensure_ascii=False)))
            db.execute('INSERT INTO worker_access VALUES(?,?,?,?)',(case_id,pin_hash,str(data.operation_id),digest))
    session=worker.start_session(case_id,request,response)
    return {'session':session,'case':record(case_id),'message':'Private diary saved. Keep the reference and PIN. No dispute or complaint created.'}


@router.get('/state')
def state(session=Depends(worker.require_worker)):
    case=record(session['case_id'])
    with store.transaction() as db:
        history=store.events(db,session['case_id'])
        sources=[dict(r) for r in db.execute('SELECT source_id,filename,mime,origin,message_date,fictional,status,result,created_at FROM reply_sources WHERE case_id=? ORDER BY created_at', (session['case_id'],))]
        for source in sources:source['result']=json.loads(source['result'])
        links=[dict(r) for r in db.execute('SELECT request_id,expires_at,revoked,created_at FROM response_links WHERE case_id=?',(session['case_id'],))]
    submissions=[e for e in history if e['kind'] in ('submission_reported','acknowledgement_confirmed','status_recorded') and not e['payload'].get('fictional')]
    submission_state={'submission_reported':'worker_reports_submitted','acknowledgement_confirmed':'acknowledgement_details_confirmed','status_recorded':'source_labelled_status'}[submissions[-1]['kind']] if submissions else 'draft_prepared' if any(e['kind']=='filing_prepared' for e in history) else 'not_prepared'
    diary=[e for e in history if e['kind']=='diary_recorded']
    corrected={e['payload'].get('corrects_entry') for e in diary}
    week_start=datetime.now(INDIA).date()-timedelta(days=6)
    weekly=[e for e in diary if e['event_id'] not in corrected and date.fromisoformat(e['payload']['work_date'])>=week_start]
    weekly_diary={'earnings':str(sum((Decimal(e['payload']['reported_earnings']) for e in weekly),Decimal(0))),
                  'received':str(sum((Decimal(e['payload']['payment_received']) for e in weekly),Decimal(0))),
                  'from':week_start.isoformat(),'through':datetime.now(INDIA).date().isoformat()}
    committed={e['operation_id'] for e in history if e['kind']!='voice_proposal'}
    dismissed={e['payload']['proposal_id'] for e in history if e['kind']=='voice_proposal_dismissed'}
    pending=[e for e in history if e['kind']=='voice_proposal' and e['event_id'] not in dismissed and str(uuid5(NAMESPACE_URL,'confirm-resolution:'+e['event_id'])) not in committed]
    payments=case['follow_up_payments']
    correctable=[{**p,'effective_amount':str(Decimal(p['amount'])+sum((Decimal(c['amount']) for c in payments if c.get('corrects_payment_id')==p['payment_id']),Decimal(0)))} for p in payments if not p.get('corrects_payment_id')]
    return {'revision':len(history),'balance_version':balance_version(case),'events':history,'sources':sources,'links':links,'weekly_diary':weekly_diary,'pending_voice_proposals':pending,
            'next_action':next_action(case,history,sources),'submission_state':submission_state,'demo':os.getenv('HAQRECORD_DEMO')=='true',
            'complaint_verified':False,'external_reminders_configured':False,
            'response_links_available':bool(public_base()) and os.getenv('HAQRECORD_DEMO')!='true',
            'extraction':{'text':True,'pdf_text':True,'image':bool(extraction_settings()['SARVAM_API_KEY']),
                          'wav':bool(extraction_settings()['SARVAM_API_KEY'])},
            'limits':{'bytes':5*1024*1024,'pdf_pages':20,'audio_seconds':29},
            'case':case,'correctable_payments':correctable}


class Upload(Model):
    operation_id: UUID
    filename: str = Field(min_length=1,max_length=150,pattern=r'^[^\r\n"\\/]+$')
    mime: Literal['text/plain','image/png','image/jpeg','application/pdf','audio/wav']
    content_base64: str = Field(max_length=7*1024*1024)
    origin: Literal['employer_message','official_correspondence','worker_recollection']
    message_date: date | None = None
    language: Literal['hi','en']='hi'
    fictional: bool=False
    consent_to_store: Literal[True]


@memory_heavy
def extract_source(mime,content,language):
    task={'mime':mime,'content_base64':base64.b64encode(content).decode(),'language':language}
    completed=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('extract_reply_worker.py'))],
        input=json.dumps(task).encode('utf-8'),capture_output=True,timeout=50,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,check=True)
    return json.loads(completed.stdout.decode('utf-8'))


@single_source_job
def process_source(source_id,language):
    # BackgroundTasks runs this in a bounded synchronous worker thread. Original
    # remains available if a provider fails; failure never changes case finances.
    with store.transaction() as db:
        row=db.execute('SELECT mime,content,status FROM reply_sources WHERE source_id=?',(source_id,)).fetchone()
        if not row or row['status']!='processing':return
        mime,content=row['mime'],row['content']
    started=time.monotonic()
    try:
        # Release the memory gate BEFORE writing to SQLite: retrying case saves
        # can verify their PIN inside a transaction, and must not deadlock with
        # an extraction trying to write its result.
        processed=extract_source(mime,content,language);result=processed['result'];status=processed['status']
    except Exception:
        # Provider responses and source contents are deliberately absent from logs.
        result={'notice':'Extraction failed. The original is stored; retry or paste a readable transcript.'}
        status='failed'
    result['processing_seconds']=round(time.monotonic()-started,3)
    with store.transaction() as db:
        db.execute('UPDATE reply_sources SET status=?,result=? WHERE source_id=? AND status=?',
                   (status,json.dumps(result,ensure_ascii=False),source_id,'processing'))


@router.post('/sources',status_code=202)
async def upload(request:Request,background:BackgroundTasks,session=Depends(worker.require_worker)):
    worker.check_json_origin(request)
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>7*1024*1024:raise HTTPException(413,'Maximum file size is 5 MB.')
    try:
        data=Upload.model_validate_json(body)
        content=base64.b64decode(data.content_base64,validate=True)
        validate_file(data.mime,content)
    except Exception:raise HTTPException(422,'Use valid UTF-8 text, PNG/JPEG up to 16 megapixels, unencrypted PDF up to 20 pages, or PCM WAV up to 29 seconds. Maximum 5 MB.')
    digest=fingerprint(data.model_dump(mode='json'))
    with store.transaction() as db:
        old=db.execute('SELECT source_id,request_hash,status FROM reply_sources WHERE case_id=? AND operation_id=?',(session['case_id'],str(data.operation_id))).fetchone()
        if old:
            if old['request_hash']!=digest:raise HTTPException(409,'This upload operation was used for another source.')
            return {'source_id':old['source_id'],'status':old['status']}
        usage=db.execute('SELECT count(*),coalesce(sum(length(content)),0) FROM reply_sources WHERE case_id=?',(session['case_id'],)).fetchone()
        if usage[0]>=100 or usage[1]+len(content)>100*1024*1024:raise HTTPException(413,'Case source storage limit reached. Ask the operator about retention before adding more files.')
        cutoff=(datetime.now(timezone.utc)-timedelta(minutes=15)).isoformat()
        recent=db.execute('SELECT count(*) FROM reply_sources WHERE case_id=? AND created_at>=?',(session['case_id'],cutoff)).fetchone()[0]
        if recent>=20:raise HTTPException(429,'Please wait before uploading more sources.')
        source_id=str(uuid4())
        db.execute('INSERT INTO reply_sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (source_id,session['case_id'],str(data.operation_id),digest,data.filename,data.mime,content,data.origin,
             data.message_date.isoformat() if data.message_date else None,int(data.fictional),'processing','{}',store.now()))
    background.add_task(process_source,source_id,data.language)
    return {'source_id':source_id,'status':'processing'}


@router.get('/sources/{source_id}/original')
def original(source_id:UUID,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        row=db.execute('SELECT filename,mime,content FROM reply_sources WHERE source_id=? AND case_id=?',(str(source_id),session['case_id'])).fetchone()
    if not row:raise HTTPException(404,'Source unavailable')
    return Response(row['content'],media_type=row['mime'],headers={'Content-Disposition':"attachment; filename=source; filename*=UTF-8''"+quote(row['filename'],safe=''),'X-Content-Type-Options':'nosniff'})


class SourceRetry(Model):
    language: Literal['hi','en']='hi'


@router.post('/sources/{source_id}/retry')
def retry_source(source_id:UUID,data:SourceRetry,background:BackgroundTasks,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        row=db.execute('SELECT status FROM reply_sources WHERE source_id=? AND case_id=?',(str(source_id),session['case_id'])).fetchone()
        if not row:raise HTTPException(404,'Source unavailable')
        if row['status']=='processing':raise HTTPException(409,'This source is still processing.')
        db.execute("UPDATE reply_sources SET status='processing' WHERE source_id=?",(str(source_id),))
    background.add_task(process_source,str(source_id),data.language)
    return {'status':'processing'}


class ReplyReview(Mutation):
    source_id: UUID
    advance_already_included: Literal['yes','no','unclear','not_applicable']
    clarification: str = Field(min_length=1,max_length=3000)


@router.post('/review-reply')
def review_reply(data:ReplyReview,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        source=db.execute('SELECT status FROM reply_sources WHERE source_id=? AND case_id=?',(str(data.source_id),session['case_id'])).fetchone()
        if not source:raise HTTPException(404,'Source unavailable')
        if source['status']=='processing':raise HTTPException(409,'Wait for processing before reviewing.')
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,'reply_reviewed',
            {**data.model_dump(mode='json',exclude={'operation_id','expected_revision','confirmed'}),'balance_changed':False,'confirmed_at':store.now()},data.model_dump(mode='json'))
    return state(session)


class Promise(Mutation):
    source_id: UUID | None=None
    amount: Decimal = Field(gt=0,max_digits=12,decimal_places=2)
    due_on: date | None=None
    date_confirmed: bool=False
    date_text: str = Field(default='',max_length=150)
    remaining_date_unspecified: bool=True
    statement: str = Field(min_length=1,max_length=2000)

    @model_validator(mode='after')
    def confirmed_date(self):
        if self.due_on and not self.date_confirmed:raise ValueError('Confirm the exact promise date.')
        return self


@router.post('/promises')
def promise(data:Promise,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        if data.source_id and not db.execute('SELECT 1 FROM reply_sources WHERE source_id=? AND case_id=?',(str(data.source_id),session['case_id'])).fetchone():raise HTTPException(404,'Source unavailable')
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,'promise_recorded',
            data.model_dump(mode='json',exclude={'operation_id','expected_revision','confirmed'}),data.model_dump(mode='json'))
    return state(session)


class PromiseCheck(Mutation):
    promise_id: UUID
    money_arrived: bool
    answer_date: date


@router.post('/promise-check')
def check_promise(data:PromiseCheck,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        store.get_event(db,session['case_id'],str(data.promise_id),'promise_recorded')
        if data.answer_date>datetime.now(INDIA).date():raise HTTPException(422,'The answer date cannot be in the future.')
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,'promise_checked',data.model_dump(mode='json'),data.model_dump(mode='json'))
    return state(session)


class Contact(Mutation):
    contact_safe: bool
    wants_next_step: bool=False


@router.post('/contact-preference')
def contact(data:Contact,session=Depends(worker.require_worker)):
    append(session['case_id'],data,'contact_preference',data.model_dump(mode='json'))
    return state(session)


class RequestDraft(Mutation):
    balance_version: str = Field(min_length=64,max_length=64)
    language: Literal['hi','en']='hi'
    work_period: str = Field(default='',max_length=500)
    correction: str = Field(default='',max_length=2000)


def request_text(case,data):
    c=case['calculation'];i=case['intake'];hi=data.language=='hi'
    unit={'daily':('दिन','day'),'weekly':('हफ़्ते','week'),'monthly':('महीने','month'),'hourly':('घंटे','hour'),'piece':('इकाई','piece')}[c['pay_basis']][0 if hi else 1]
    money=lambda key:format(Decimal(c[key]),'f').rstrip('0').rstrip('.') if '.' in format(Decimal(c[key]),'f') else format(Decimal(c[key]),'f')
    if hi:
        text=f"नमस्ते। मेरे पुष्टि किए विवरण के अनुसार मैंने {c['units_worked']} {unit}, ₹{money('rate_per_unit')} प्रति {unit} की दर से काम किया। "
        if data.work_period:text+='काम की अवधि: '+data.work_period+'। '
        text+=f"बताई गई कमाई ₹{money('total_earned')}, मिले मज़दूरी के पैसे ₹{money('payments_received')} और बाकी ₹{money('balance')} हैं। कृपया जवाब दें और बाकी भुगतान की तारीख बताएं।"
        if c.get('provisional'):text+=' कुछ रकम या विवरण स्पष्ट करना बाकी है; यह शेष रकम अंतिम नहीं है।'
        text+=' यह मेरे बताए विवरण पर आधारित साधारण भुगतान अनुरोध है।'
    else:
        text=f"Hello. Based on my confirmed account, I worked {c['units_worked']} {unit}(s) at INR {money('rate_per_unit')} per {unit}. "
        if data.work_period:text+='Work period: '+data.work_period+'. '
        text+=f"Reported earnings: INR {money('total_earned')}. Wages received: INR {money('payments_received')}. Remaining wages: INR {money('balance')}. Please reply and propose a payment date for the remaining wages."
        if c.get('provisional'):text+=' Some amounts or allocations remain unresolved; this balance is provisional.'
        text+=' This is a factual payment request based on my account.'
    if data.correction:text+='\n'+data.correction
    if c.get('work_periods'):
        lines=[f"{p['description']}: {p['quantity']} {unit} × ₹{p['rate']}" for p in c['work_periods']]
        heading='पुष्टि की अलग दरों के काम की अवधि:' if hi else 'Confirmed work periods with separate rates:'
        # Do not present the first rate as a single rate for every period.
        start=text.find('बताई गई कमाई' if hi else 'Reported earnings:')
        text=heading+'\n'+'\n'.join(lines)+'\n'+text[start:]
    return text


@router.post('/requests')
def draft_request(data:RequestDraft,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        case=record(session['case_id'])
        if case.get('record_type')=='work_diary' and not case['workspace']['reconstruction']:raise HTTPException(409,'Include confirmed work in a wage account before preparing a payment request.')
        if data.balance_version!=balance_version(case):raise HTTPException(409,'The balance changed. Review it before preparing this request.')
        event=store.append(db,session['case_id'],data.operation_id,data.expected_revision,'request_drafted',{'text':request_text(case,data),'balance_version':data.balance_version,
            'language':data.language,'worker_name':case['intake']['preferred_name'],'work_period':data.work_period,
            'notice':'Draft only. Not a legal notice or a complaint. No message has been sent.'},data.model_dump(mode='json'))
    return {'event':event,'state':state(session)}


class RequestAction(Mutation):
    request_id: UUID
    exact_text: str = Field(min_length=1,max_length=8000)
    action: Literal['approve','sharing_opened','worker_reports_sent']


def approved_request(db,case_id,request_id):
    draft=store.get_event(db,case_id,request_id,'request_drafted')
    history=store.events(db,case_id)
    if not any(e['kind']=='request_approved' and e['payload']['request_id']==request_id for e in history):raise HTTPException(409,'Approve this exact request first.')
    return draft


@router.post('/request-action')
def request_action(data:RequestAction,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        case=record(session['case_id'])
        draft=store.get_event(db,session['case_id'],str(data.request_id),'request_drafted')
        if data.exact_text!=draft['payload']['text']:raise HTTPException(409,'Edits need a new draft and approval.')
        if draft['payload']['balance_version']!=balance_version(case):raise HTTPException(409,'The account changed; prepare and approve a fresh request.')
        if data.action!='approve':approved_request(db,session['case_id'],str(data.request_id))
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,
            'request_approved' if data.action=='approve' else data.action,{'request_id':str(data.request_id),'text':data.exact_text},data.model_dump(mode='json'))
    return state(session)


class LinkCreate(Mutation):
    request_id: UUID
    disclosure_confirmed: Literal[True]
    expires_in_days: int=Field(default=7,ge=1,le=30)


@router.post('/response-links')
def create_link(data:LinkCreate,session=Depends(worker.require_worker)):
    base=public_base()
    if not base or os.getenv('HAQRECORD_DEMO')=='true':raise HTTPException(503,'A secure public application URL is not configured. Local demonstration only; no usable recipient link is available.')
    with store.transaction() as db:
        case=record(session['case_id'])
        draft=approved_request(db,session['case_id'],str(data.request_id))
        if draft['payload']['balance_version']!=balance_version(case):raise HTTPException(409,'The account changed. Approve an updated request.')
        if store.prior(db,session['case_id'],data.operation_id,fingerprint(data.model_dump(mode='json'))):
            raise HTTPException(409,'This link creation already succeeded. Revoke it before creating another; secret tokens are not stored.')
        token=secrets.token_urlsafe(32);expires=time.time()+data.expires_in_days*86400
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,'response_link_created',
            {'request_id':str(data.request_id),'expires_at':expires,'disclosed':'Approved request text and preferred name only'},data.model_dump(mode='json'))
        db.execute('INSERT INTO response_links VALUES(?,?,?,?,?,?)',(auth.digest(token),session['case_id'],str(data.request_id),expires,0,store.now()))
    # Fragment avoids putting the capability in access logs and link previews.
    return {'url':base+'/respond#'+token,'expires_at':expires,'state':state(session)}


class LinkRevoke(Mutation):
    request_id: UUID


@router.post('/revoke-links')
def revoke(data:LinkRevoke,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        store.get_event(db,session['case_id'],str(data.request_id),'request_drafted')
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,'response_links_revoked',{'request_id':str(data.request_id)},data.model_dump(mode='json'))
        db.execute('UPDATE response_links SET revoked=1 WHERE case_id=? AND request_id=?',(session['case_id'],str(data.request_id)))
    return state(session)


def link_context(db,token):
    link=db.execute('SELECT * FROM response_links WHERE token_hash=? AND expires_at>? AND revoked=0',(auth.digest(token),time.time())).fetchone()
    if not link:raise HTTPException(404,'Response link expired or unavailable.')
    return link


class RecipientToken(Model):
    token: str = Field(min_length=30,max_length=100)


@public_router.get('/respond')
def recipient_page():
    return FileResponse(Path(__file__).with_name('web')/'respond.html',headers={'X-Robots-Tag':'noindex, nofollow','Cache-Control':'no-store','Referrer-Policy':'no-referrer',
        'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})


@public_router.post('/recipient/view')
def recipient_view(data:RecipientToken,request:Request):
    worker.check_json_origin(request)
    worker.rate_limit(['recipient-view:'+(request.client.host if request.client else 'unknown')],limit=50)
    with store.transaction() as db:
        link=link_context(db,data.token)
        draft=approved_request(db,link['case_id'],link['request_id'])
    return {'request_id':link['request_id'],'text':draft['payload']['text'],'preferred_name':draft['payload']['worker_name'],
            'notice':'A response to HaqRecord, not a government filing or binding settlement. Do not send bank credentials, Aadhaar, or payments.',
            'csrf':auth.digest('recipient-csrf:'+data.token)}


class RecipientReply(RecipientToken):
    operation_id: UUID
    csrf: str=Field(min_length=64,max_length=64)
    response: Literal['agree_propose_date','claimed_payment','disagree']
    amount: Decimal | None=Field(default=None,gt=0,max_digits=12,decimal_places=2)
    payment_date: date | None=None
    explanation: str=Field(min_length=1,max_length=2000)
    consent: Literal[True]


@public_router.post('/recipient/respond')
def recipient_reply(data:RecipientReply,request:Request):
    worker.check_json_origin(request)
    if not secrets.compare_digest(data.csrf,auth.digest('recipient-csrf:'+data.token)):raise HTTPException(403,'Refresh the response page.')
    worker.rate_limit(['recipient-submit:'+(request.client.host if request.client else 'unknown'),'recipient-token:'+auth.digest(data.token)],limit=10)
    with store.transaction() as db:
        link=link_context(db,data.token)
        approved_request(db,link['case_id'],link['request_id'])
        payload={**data.model_dump(mode='json',exclude={'token','csrf','operation_id','consent'}),'request_id':link['request_id'],
                 'identity_status':'Response from link recipient; identity not verified','ledger_changed':False}
        store.append(db,link['case_id'],data.operation_id,store.revision(db,link['case_id']),'recipient_response',payload)
    return {'status':'Response recorded. The worker must review it. No wage record was changed.'}


class RecipientReview(Mutation):
    response_id: UUID
    statement: str=Field(min_length=1,max_length=2000)


@router.post('/review-recipient')
def review_recipient(data:RecipientReview,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        store.get_event(db,session['case_id'],str(data.response_id),'recipient_response')
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,'recipient_response_reviewed',data.model_dump(mode='json'),data.model_dump(mode='json'))
    return state(session)


@router.get('/routes')
def routes(session=Depends(worker.require_worker)):
    return json.loads(Path(__file__).with_name('support_routes.json').read_text(encoding='utf-8'))


class Filing(Mutation):
    city: Literal['hyderabad','bengaluru']
    employment_type: str=Field(min_length=1,max_length=300)
    employer_address: str=Field(default='',max_length=1000)
    work_period: str=Field(default='',max_length=500)
    desired_action: str=Field(min_length=1,max_length=2000)


@router.post('/filing')
def filing(data:Filing,session=Depends(worker.require_worker)):
    case=record(session['case_id'])
    payload={'route_id':'preparation_only_v1','official_submission':False,'eligibility_verified':False,
             'fields':{'worker_name':case['intake']['preferred_name'],'employer':case['intake'].get('employer_name') or '',
                       'employer_address':data.employer_address,'work_period':data.work_period,'employment_type':data.employment_type,
                       'city':data.city,'account':case['intake']['original_statement'],'reported_remaining':case['calculation']['balance'],
                       'desired_action':data.desired_action},
             'missing':[name for name,value in {'employer_address':data.employer_address,'work_period':data.work_period,'employer':case['intake'].get('employer_name')}.items() if not value],
             'checklist':['Reviewed account of work and wage agreement','Payment history and unresolved amounts','Messages or supporting documents, if available'],
             'notice':'Preparation only. Current jurisdiction and live form not verified. Confirm the correct office and requirements. This is not a submitted complaint.'}
    append(session['case_id'],data,'filing_prepared',payload)
    return state(session)


class Submission(Mutation):
    office: str=Field(min_length=1,max_length=300)
    submitted_on: date
    reference: str=Field(default='',max_length=200)
    statement: str=Field(min_length=1,max_length=2000)


@router.post('/submission')
def submission(data:Submission,session=Depends(worker.require_worker)):
    append(session['case_id'],data,'submission_reported',{**data.model_dump(mode='json'),
        'source':'worker_report','authority_verified':False})
    return state(session)


class Acknowledgement(Mutation):
    source_id: UUID
    office: str=Field(min_length=1,max_length=300)
    reference: str=Field(min_length=1,max_length=200)
    document_date: date
    appointment_at: datetime | None=None
    requested_documents: list[str]=Field(default_factory=list,max_length=20)
    next_action: str=Field(min_length=1,max_length=2000)
    excerpt: str=Field(min_length=1,max_length=3000)

    @model_validator(mode='after')
    def validate_time(self):
        if self.appointment_at and self.appointment_at.utcoffset() is None:raise ValueError('Include timezone for appointment.')
        if any(len(s)>500 for s in self.requested_documents):raise ValueError('Document description too long.')
        return self


@router.post('/acknowledgement')
def acknowledgement(data:Acknowledgement,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        source=db.execute('SELECT origin,status,result,fictional FROM reply_sources WHERE source_id=? AND case_id=?',(str(data.source_id),session['case_id'])).fetchone()
        if not source:raise HTTPException(404,'Source unavailable')
        if source['origin']!='official_correspondence' or source['status'] not in ('ready_for_review','needs_clarification'):raise HTTPException(422,'Use a readable official-correspondence source.')
        text='\n'.join(p['text'] for p in json.loads(source['result']).get('pages',[]))
        if data.excerpt not in text or data.reference not in text or data.office not in text:
            raise HTTPException(422,'The office, reference and supporting excerpt must be visible in extracted text. Add a clearer transcript if needed.')
        visible_date=lambda value:any(value.strftime(fmt) in text for fmt in ('%Y-%m-%d','%d/%m/%Y','%d-%m-%Y','%d.%m.%Y','%d %B %Y','%d %b %Y'))
        if not visible_date(data.document_date):raise HTTPException(422,'The confirmed document date must be visible. Clarify unclear dates or add a checked transcript.')
        if data.appointment_at and (not visible_date(data.appointment_at.date()) or data.appointment_at.strftime('%H:%M') not in text):
            raise HTTPException(422,'The appointment date and time must be visible. Do not infer an unreadable appointment.')
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,'acknowledgement_confirmed',
            {**data.model_dump(mode='json'),'source':'uploaded_document_worker_confirmed','fictional':bool(source['fictional']),
             'authority_verified':False,'notice':'Sample only; not a real submission.' if source['fictional'] else 'Document details confirmed by worker; authenticity and acceptance not independently verified.'},data.model_dump(mode='json'))
    return state(session)


@router.get('/packet')
def packet(session=Depends(worker.require_worker)):
    from html import escape
    s=state(session);c=s['case'];rupees=lambda value:format(Decimal(value),',.2f').rstrip('0').rstrip('.')
    html=['<!doctype html><html lang="'+c['intake']['language']+'"><meta charset="utf-8"><title>HaqRecord preparation packet</title>',
        '<style>body{font:17px system-ui,sans-serif;line-height:1.65;max-width:760px;margin:24px auto;padding:16px;overflow-wrap:anywhere}pre{white-space:pre-wrap;font:inherit}article{break-inside:avoid;border-top:1px solid #777;padding-top:12px}</style>',
        '<h1>HaqRecord — तैयारी / Preparation</h1><p>Worker-reported account. No government submission or authenticity verification performed by this app.</p>',
        '<p>'+escape(c['case_id'])+'</p><p>'+escape(c['intake']['original_statement'])+'</p>',
        '<p>Reported earnings / बताई कमाई: ₹'+rupees(c['calculation']['total_earned'])+'; Wages received / मिली मज़दूरी: ₹'+rupees(c['calculation']['payments_received'])+'; Remaining / बाकी: ₹'+rupees(c['calculation']['balance'])+'</p>']
    for event in s['events']:
        if event['kind']=='voice_proposal':continue
        labels={'text':'Approved or draft text / तैयार टेक्स्ट','statement':'Reported account / बताई बात','clarification':'Clarification / सफाई',
            'amount':'Amount (rupees) / रकम','due_on':'Promised date / वादा की तारीख','date_text':'Original date words / मूल शब्द',
            'office':'Receiving office / प्राप्त कार्यालय','reference':'Official reference (not HaqRecord ID) / सरकारी संदर्भ',
            'document_date':'Document date / दस्तावेज़ तारीख','submitted_on':'Reported submission date / बताई जमा तारीख',
            'requested_documents':'Requested documents / मांगे दस्तावेज़','next_action':'Next action / अगला कदम','reason':'Reason / कारण',
            'notice':'Source limitation / स्रोत की सीमा','advance_already_included':'Advance already counted / एडवांस पहले से शामिल',
            'due_at':'In-app reminder time / वेबसाइट की याद का समय','action':'Reminder / याद','corrected_amount':'Corrected amount / सही रकम'}
        content=[]
        for key,title in labels.items():
            if key not in event['payload']:continue
            value=event['payload'][key]
            if isinstance(value,list):value='; '.join(map(str,value))
            content+=['<p><strong>'+escape(title)+':</strong> '+escape(str(value or 'Not specified / तय नहीं'))+'</p>']
        fields=event['payload'].get('fields',{})
        if isinstance(fields,dict):
            for key,value in fields.items():content+=['<p><strong>'+escape(key.replace('_',' '))+':</strong> '+escape(str(value or 'Missing / जानकारी बाकी'))+'</p>']
        heading={'reply_reviewed':'Reply clarification / जवाब की सफाई','promise_recorded':'Payment promise, not received / वादा, मिला पैसा नहीं',
            'request_drafted':'Payment request draft / भुगतान अनुरोध मसौदा','request_approved':'Exact text approved / यही टेक्स्ट मंज़ूर',
            'sharing_opened':'Sharing opened; delivery unknown / साझा विकल्प खुला; पहुंचना अज्ञात','worker_reports_sent':'Worker reports sent / मज़दूर ने भेजने की बात कही',
            'filing_prepared':'Preparation only, not submitted / सिर्फ तैयारी; जमा नहीं हुआ','acknowledgement_confirmed':'Uploaded acknowledgement details / अपलोड पावती की जानकारी',
            'diary_recorded':'Worker’s work diary / मज़दूर की काम डायरी','payment_corrected':'Payment correction / भुगतान सुधार'}.get(event['kind'],event['kind'].replace('_',' '))
        local_time=datetime.fromisoformat(event['created_at']).astimezone(INDIA).strftime('%d %b %Y, %H:%M IST')
        html+=['<article><h2>'+escape(heading)+'</h2><p>'+escape(local_time)+'</p>'+''.join(content)+'</article>']
    html+=['<h2>Source originals / मूल सामग्री</h2><p>Supplied material and recollections are not authenticated. Original files are included in the ZIP packet.</p>']
    for source in s['sources']:
        html+=['<article><h3>'+escape(source['filename'])+'</h3><p>'+escape(source['origin'])+(' · FICTIONAL SAMPLE / काल्पनिक नमूना' if source['fictional'] else '')+'</p>']
        for page in source['result'].get('pages',[]):html+=['<p>Page / पेज '+str(page['page'])+'</p><pre>'+escape(page['text'])+'</pre>']
        html+=['</article>']
    html+=['</html>']
    return Response(''.join(html),media_type='text/html; charset=utf-8',headers={'Content-Disposition':'attachment; filename="haqrecord-preparation.html"',
        'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; sandbox"})


class StopReminder(Mutation):
    reminder_id: UUID


class ScheduleReminder(Mutation):
    due_at: datetime
    action: str=Field(min_length=1,max_length=1000)
    consent: Literal[True]

    @model_validator(mode='after')
    def timezone_required(self):
        if self.due_at.utcoffset() is None:raise ValueError('Confirm an exact time in Asia/Kolkata.')
        return self


@router.post('/schedule-reminder')
def schedule_reminder(data:ScheduleReminder,session=Depends(worker.require_worker)):
    payload=data.model_dump(mode='json');reminder={'due_at':data.due_at.isoformat(),'action':data.action,'consent':True}
    with store.transaction() as db:
        old=store.prior(db,session['case_id'],data.operation_id,fingerprint(payload))
        if not old:
            store.append(db,session['case_id'],data.operation_id,data.expected_revision,'reminder_scheduled',reminder,payload)
            db.execute('INSERT INTO case_reminders VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid4()),session['case_id'],str(data.operation_id),fingerprint(reminder),data.due_at.isoformat(),data.action,'pending',store.now(),None))
    return state(session)


class Recollection(Mutation):
    statement: str=Field(min_length=1,max_length=10000)
    language: Literal['hi','en']='hi'
    message_date: date | None=None


@router.post('/recollection')
def recollection(data:Recollection,session=Depends(worker.require_worker)):
    payload=data.model_dump(mode='json')
    with store.transaction() as db:
        old=store.prior(db,session['case_id'],data.operation_id,fingerprint(payload))
        if not old:
            source_id=str(uuid4());result={'pages':[{'page':1,'text':data.statement}],'method':'worker_recollection',**interpret([{'page':1,'text':data.statement}],data.language)}
            store.append(db,session['case_id'],data.operation_id,data.expected_revision,'recollection_confirmed',{'source_id':source_id,'statement':data.statement,'notice':'Worker recollection, not the original sender message.'},payload)
            db.execute('INSERT INTO reply_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(source_id,session['case_id'],str(data.operation_id),fingerprint(payload),'worker-recollection.txt','text/plain',data.statement.encode('utf-8'),'worker_recollection',data.message_date.isoformat() if data.message_date else None,int(os.getenv('HAQRECORD_DEMO')=='true'),'ready_for_review',json.dumps(result,ensure_ascii=False),store.now()))
    return state(session)


class PaymentCorrection(Mutation):
    payment_id: str=Field(min_length=1,max_length=100)
    expected_amount: Decimal=Field(ge=0,max_digits=12,decimal_places=2)
    corrected_amount: Decimal=Field(ge=0,max_digits=12,decimal_places=2)
    balance_version: str=Field(min_length=64,max_length=64)
    reason: str=Field(min_length=1,max_length=2000)


@router.post('/correct-payment')
def correct_payment(data:PaymentCorrection,session=Depends(worker.require_worker)):
    payload=data.model_dump(mode='json')
    with store.transaction() as db:
        old=store.prior(db,session['case_id'],data.operation_id,fingerprint(payload))
        if not old:
            case=record(session['case_id'])
            if data.balance_version!=balance_version(case):raise HTTPException(409,'The balance changed. Review this correction again.')
            original=next((p for p in case['follow_up_payments'] if p['payment_id']==data.payment_id and not p.get('corrects_payment_id')),None)
            if not original:raise HTTPException(404,'Choose an actual payment in this case.')
            effective=Decimal(original['amount'])+sum((Decimal(p['amount']) for p in case['follow_up_payments'] if p.get('corrects_payment_id')==data.payment_id),Decimal(0))
            if effective!=data.expected_amount:raise HTTPException(409,'This payment was already corrected. Review its current amount.')
            delta=data.corrected_amount-effective
            if delta==0:raise HTTPException(422,'The corrected amount is unchanged.')
            previous=Decimal(case['calculation']['balance'])
            event={'payment_id':'COR-'+uuid4().hex.upper(),'operation_id':str(data.operation_id),'recorded_at':store.now(),
                'source':'worker_confirmed_correction','amount':str(delta),'received_on':original.get('received_on'),
                'method':original.get('method','unknown'),'original_statement':data.reason,'worker_confirmed':True,
                'distinct_payment_confirmed':True,'corrects_payment_id':data.payment_id,'corrected_amount':str(data.corrected_amount),
                'promise_id':original.get('promise_id'),'source_id':original.get('source_id'),
                'previous_balance':str(previous),'updated_balance':str(previous-delta),
                'explanation':'Correction of an existing reported payment; original preserved. '+data.reason}
            store.append(db,session['case_id'],data.operation_id,data.expected_revision,'payment_corrected',
                {'payment_id':data.payment_id,'previous_amount':str(effective),'corrected_amount':str(data.corrected_amount),'reason':data.reason},payload)
            db.execute('INSERT INTO payment_events(case_id,event_json,operation_id,request_hash) VALUES(?,?,?,?)',
                (session['case_id'],json.dumps(event,ensure_ascii=False),str(data.operation_id),fingerprint(event)))
    return state(session)


class WorkPeriods(Mutation):
    balance_version: str=Field(min_length=64,max_length=64)
    pay_basis: Literal['hourly','daily','weekly','monthly','piece']
    periods: list[dict]=Field(min_length=1,max_length=30)
    reason: str=Field(min_length=1,max_length=2000)


@router.post('/work-periods')
def work_periods(data:WorkPeriods,session=Depends(worker.require_worker)):
    from dispute_models import DisputeReconstruction,WorkPeriod
    from case_workspace_service import validate_sources
    from pydantic import ValidationError
    try:periods=[WorkPeriod.model_validate(p) for p in data.periods]
    except ValidationError:raise HTTPException(422,'Confirm each work period, quantity, explicit rate and source.')
    payload=data.model_dump(mode='json')
    with store.transaction() as db:
        old=store.prior(db,session['case_id'],data.operation_id,fingerprint(payload))
        if not old:
            case=record(session['case_id'])
            if data.balance_version!=balance_version(case):raise HTTPException(409,'The wage account changed. Review work periods again.')
            base=case['workspace']['reconstruction'] or {'payments':[],'unresolved_questions':[],'fact_sources':{}}
            if not case['workspace']['reconstruction'] and Decimal(case['intake']['payments_received']):
                base['payments']=[{'payment_id':'initial-received','amount':case['intake']['payments_received'],'status':'received','allocation':'this_case','worker_confirmed':True,'statement':'Original confirmed wage receipts','source_ids':['worker_account']}]
            try:
                snapshot=DisputeReconstruction(pay_basis=data.pay_basis,units_worked=sum((p.quantity for p in periods),Decimal(0)),
                    rate_per_unit=periods[0].rate,work_periods=periods,payments=base['payments'],
                    unresolved_questions=base.get('unresolved_questions',[]),fact_sources=base.get('fact_sources',{}))
            except ValidationError:raise HTTPException(422,'Confirm quantities in the same explicit unit, with exact amounts. Do not convert weeks and months.')
            validate_sources(db,session['case_id'],snapshot)
            version=case['workspace']['version']
            revision={'snapshot':snapshot.model_dump(mode='json'),'expected_version':version,'reason':data.reason}
            store.append(db,session['case_id'],data.operation_id,data.expected_revision,'work_periods_confirmed',
                {'pay_basis':data.pay_basis,'periods':[p.model_dump(mode='json') for p in periods],'reason':data.reason},payload)
            db.execute('INSERT INTO case_revisions VALUES(?,?,?,?,?,?,?)',(session['case_id'],version+1,str(data.operation_id),fingerprint(revision),
                json.dumps(snapshot.model_dump(mode='json'),ensure_ascii=False),data.reason,store.now()))
    return state(session)


@router.post('/stop-reminder')
def stop_reminder(data:StopReminder,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        row=db.execute('SELECT state FROM case_reminders WHERE reminder_id=? AND case_id=?',(str(data.reminder_id),session['case_id'])).fetchone()
        if not row:raise HTTPException(404,'Reminder unavailable')
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,'reminder_stopped',{'reminder_id':str(data.reminder_id)},data.model_dump(mode='json'))
        db.execute("UPDATE case_reminders SET state='stopped' WHERE reminder_id=? AND case_id=?",(str(data.reminder_id),session['case_id']))
    return state(session)


class Diary(Mutation):
    work_date: date
    workplace: str=Field(min_length=1,max_length=300)
    employer: str=Field(default='',max_length=200)
    quantity: Decimal=Field(gt=0,max_digits=10,decimal_places=3)
    rate_unit: Literal['hourly','daily','weekly','monthly','piece']
    rate: Decimal=Field(gt=0,max_digits=12,decimal_places=2)
    payment_received: Decimal=Field(default=Decimal(0),ge=0,max_digits=12,decimal_places=2)
    statement: str=Field(min_length=1,max_length=2000)
    corrects_entry: UUID | None=None
    source_id: UUID | None=None

    @model_validator(mode='after')
    def exact_total(self):
        if self.quantity*self.rate != (self.quantity*self.rate).quantize(Decimal('.01')):raise ValueError('Confirm a total with no fractional paise.')
        return self


@router.post('/diary')
def diary(data:Diary,session=Depends(worker.require_worker)):
    with store.transaction() as db:
        if data.work_date>datetime.now(INDIA).date():raise HTTPException(422,'Use the date work was actually done.')
        if data.corrects_entry:
            store.get_event(db,session['case_id'],str(data.corrects_entry),'diary_recorded')
            if any(e['kind']=='diary_allocated' and e['payload']['entry_id']==str(data.corrects_entry) for e in store.events(db,session['case_id'])):
                raise HTTPException(409,'Correct allocated work through the case correction flow first.')
        if data.source_id and not db.execute('SELECT 1 FROM reply_sources WHERE case_id=? AND source_id=?',(session['case_id'],str(data.source_id))).fetchone():raise HTTPException(404,'Source unavailable')
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,'diary_recorded',
            {**data.model_dump(mode='json'),'reported_earnings':str((data.quantity*data.rate).quantize(Decimal('.01'))),
             'included_in_case':False,'notice':'Worker’s own record, not proof of attendance or agreement.'},data.model_dump(mode='json'))
    return state(session)


class DiaryAllocation(Mutation):
    entry_id: UUID
    already_included_in_case: Literal[True]
    payment_id: str | None=Field(default=None,max_length=100)
    statement: str=Field(min_length=1,max_length=2000)


class DiaryInclude(Mutation):
    entry_id: UUID
    balance_version: str=Field(min_length=64,max_length=64)
    new_work_confirmed: Literal[True]
    payment_is_additional: bool=False
    reason: str=Field(min_length=1,max_length=2000)


@router.post('/include-diary')
def include_diary(data:DiaryInclude,session=Depends(worker.require_worker)):
    from dispute_models import DisputeReconstruction,WorkPeriod
    from case_workspace_service import validate_sources
    payload=data.model_dump(mode='json')
    with store.transaction() as db:
        old=store.prior(db,session['case_id'],data.operation_id,fingerprint(payload))
        if not old:
            case=record(session['case_id']);history=store.events(db,session['case_id'])
            if data.balance_version!=balance_version(case):raise HTTPException(409,'The wage account changed. Review the diary allocation again.')
            entry=store.get_event(db,session['case_id'],str(data.entry_id),'diary_recorded');p=entry['payload']
            if any(e['kind']=='diary_allocated' and e['payload']['entry_id']==str(data.entry_id) for e in history):raise HTTPException(409,'This entry is already allocated; no amount was added.')
            if any(e['kind']=='diary_recorded' and e['payload'].get('corrects_entry')==str(data.entry_id) for e in history):raise HTTPException(409,'Use the corrected work entry.')
            if Decimal(p['payment_received']) and not data.payment_is_additional:raise HTTPException(409,'Confirm whether these receipts are separate from all payments already counted. To reference an existing payment, link without adding amounts.')
            c=case['calculation'];r=case['workspace']['reconstruction'];periods=list((r or {}).get('work_periods') or [])
            if Decimal(c['total_earned']):
                if c['pay_basis']!=p['rate_unit']:raise HTTPException(422,'The rate units differ. Keep this entry separate until the units are clarified; no automatic conversion is allowed.')
                if not periods:periods=[WorkPeriod(quantity=c['units_worked'],rate=c['rate_per_unit'],description='Previously confirmed work',worker_confirmed=True).model_dump(mode='json')]
            periods.append(WorkPeriod(quantity=p['quantity'],rate=p['rate'],description=p['work_date']+' · '+p['workplace']+' · '+p['statement'],source_ids=['diary:'+str(data.entry_id)],worker_confirmed=True).model_dump(mode='json'))
            payments=list((r or {}).get('payments',[]))
            if not r and Decimal(case['intake']['payments_received']):payments.append({'payment_id':'initial-received','amount':case['intake']['payments_received'],'status':'received','allocation':'this_case','worker_confirmed':True,'statement':'Original confirmed wage receipts','source_ids':['worker_account']})
            if Decimal(p['payment_received']):payments.append({'payment_id':'diary-'+str(data.entry_id),'amount':p['payment_received'],'status':'received','allocation':'this_case','worker_confirmed':True,'statement':'Confirmed receipts from diary entry','source_ids':['diary:'+str(data.entry_id)]})
            snapshot=DisputeReconstruction(pay_basis=p['rate_unit'],units_worked=sum((Decimal(x['quantity']) for x in periods),Decimal(0)),
                rate_per_unit=periods[0]['rate'],work_periods=periods,payments=payments,
                unresolved_questions=(r or {}).get('unresolved_questions',[]),fact_sources=(r or {}).get('fact_sources',{}))
            validate_sources(db,session['case_id'],snapshot)
            store.append(db,session['case_id'],data.operation_id,data.expected_revision,'diary_included',{'entry_id':str(data.entry_id),'reason':data.reason},payload)
            store.append(db,session['case_id'],uuid5(NAMESPACE_URL,'allocate:'+str(data.operation_id)),data.expected_revision+1,'diary_allocated',{'entry_id':str(data.entry_id),'included_in_case':True,'payment_reference':('diary-'+str(data.entry_id)) if Decimal(p['payment_received']) else None})
            version=case['workspace']['version'];body={'snapshot':snapshot.model_dump(mode='json'),'expected_version':version,'reason':data.reason}
            db.execute('INSERT INTO case_revisions VALUES(?,?,?,?,?,?,?)',(session['case_id'],version+1,str(data.operation_id),fingerprint(body),json.dumps(snapshot.model_dump(mode='json'),ensure_ascii=False),data.reason,store.now()))
    return state(session)


@router.post('/diary-allocation')
def allocate_diary(data:DiaryAllocation,session=Depends(worker.require_worker)):
    case=record(session['case_id'])
    with store.transaction() as db:
        entry=store.get_event(db,session['case_id'],str(data.entry_id),'diary_recorded')
        history=store.events(db,session['case_id'])
        if any(e['kind']=='diary_recorded' and e['payload'].get('corrects_entry')==str(data.entry_id) for e in history):raise HTTPException(409,'Use the corrected diary entry.')
        if data.payment_id and data.payment_id not in {p['payment_id'] for p in case['follow_up_payments']}:
            raise HTTPException(422,'Choose a payment already recorded for this case.')
        if any(e['kind']=='diary_allocated' and e['payload']['entry_id']==str(data.entry_id) and e['operation_id']!=str(data.operation_id) for e in history):raise HTTPException(409,'This diary entry is already linked.')
        store.append(db,session['case_id'],data.operation_id,data.expected_revision,'diary_allocated',data.model_dump(mode='json'),data.model_dump(mode='json'))
    return state(session)
