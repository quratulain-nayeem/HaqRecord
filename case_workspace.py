"""Browser-only case evidence, corrections, packets and in-app reminders."""
import base64
import binascii
import io
import json
import sqlite3
import zipfile
from decimal import Decimal
from contextlib import closing
from datetime import datetime
from html import escape
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

import database
import worker
from case_service import read_case_record
from case_service import calculate_wages
from case_models import WageCalculation
from case_workspace_service import apply_revision, fingerprint, now, save_evidence
from dispute_models import DisputeReconstruction

router = APIRouter(prefix='/worker/workspace', tags=['Case workspace'])


@router.get('/next-step')
def next_step(language:Literal['hi','en']='hi',session=Depends(worker.require_worker)):
    from next_steps import case_next_step
    return case_next_step(read_case_record(session['case_id']),language)


@router.get('/help-summary')
def help_summary(language:Literal['hi','en']='hi',session=Depends(worker.require_worker)):
    from next_steps import case_next_step
    record=read_case_record(session['case_id']);step=case_next_step(record,language)
    lines=['HAQRECORD — FACTUAL ACCOUNT FOR SEEKING ASSISTANCE',record['case_id'],
           'Worker-reported information, not a legal finding. No government complaint submitted.',
           '',record['intake']['preferred_name'],step['summary'],'',
           'Original account:',record['intake']['original_statement'],'','Unresolved points:',
           *record['unresolved_questions']]
    if step['resource_card']:
        card=step['resource_card'];lines+=['','What to say:',card['what_to_say'],'',card['display_name'],card['action'],
             'Published general contact: '+card['phone'],card['address'],'Source: '+card['url'],
             'Source checked: '+card['checked_on'],card['notice']]
    return Response('\n'.join(lines),media_type='text/plain; charset=utf-8',
                    headers={'Content-Disposition':f'attachment; filename="{record["case_id"]}-help-summary.txt"'})


class Revision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    operation_id: UUID
    expected_version: int = Field(ge=0)
    reconstruction: DisputeReconstruction
    reason: str = Field(min_length=1, max_length=2000, pattern=r'\S')
    worker_confirmed: Literal[True]


@router.post('/reconstruction')
def revise(data: Revision, session=Depends(worker.require_worker)):
    apply_revision(session['case_id'],data.reconstruction,data.expected_version,data.operation_id,data.reason)
    return read_case_record(session['case_id'])


@router.post('/preview')
def preview(data: DisputeReconstruction, session=Depends(worker.require_worker)):
    record=read_case_record(session['case_id'])
    calculation=calculate_wages(WageCalculation(pay_basis=data.pay_basis,units_worked=data.units_worked,
        rate_per_unit=data.rate_per_unit,payments_received=data.allocated_total(),reconstruction=data),
        sum((Decimal(p['amount']) for p in record['follow_up_payments']),Decimal('0')))
    return {'calculation':calculation,'version':record['workspace']['version'],'saved':False}


class Evidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    operation_id: UUID
    filename: str = Field(min_length=1,max_length=200)
    mime: Literal['image/png','image/jpeg','application/pdf','text/plain']
    content_base64: str = Field(max_length=7*1024*1024)
    description: str = Field(min_length=1,max_length=2000,pattern=r'\S')
    fictional: bool = False
    consent_to_store: Literal[True]


@router.post('/evidence', status_code=201)
async def upload(request: Request, session=Depends(worker.require_worker)):
    worker.check_json_origin(request)
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>7*1024*1024:raise HTTPException(413,'Maximum upload size is 5 MB.')
    try:data=Evidence.model_validate_json(body)
    except ValidationError:raise HTTPException(422,'Provide the file, description, storage consent and a supported file type.')
    try:content=base64.b64decode(data.content_base64,validate=True)
    except (ValueError,binascii.Error):raise HTTPException(422,'Invalid file encoding')
    if not content or len(content)>5*1024*1024:raise HTTPException(413,'Choose a non-empty file up to 5 MB.')
    valid = ((data.mime=='image/png' and content.startswith(b'\x89PNG\r\n\x1a\n'))
             or (data.mime=='image/jpeg' and content.startswith(b'\xff\xd8\xff'))
             or (data.mime=='application/pdf' and content.startswith(b'%PDF-')))
    if data.mime=='text/plain':
        try:content.decode('utf-8');valid=b'\x00' not in content
        except UnicodeDecodeError:valid=False
    if not valid:raise HTTPException(422,'File contents do not match the selected type. Use PNG, JPEG, PDF or UTF-8 text.')
    source=save_evidence(session['case_id'],data.operation_id,data.filename,data.mime,content,data.description,data.fictional)
    return {'source_id':source,'case':read_case_record(session['case_id']),
            'notice':'Stored as supporting material. Contents and job allocation are not independently verified.'}


@router.get('/evidence/{source_id}')
def download_source(source_id: str, session=Depends(worker.require_worker)):
    with closing(sqlite3.connect(database.DB_PATH)) as db:
        row=db.execute('SELECT filename,mime,content FROM case_evidence WHERE case_id=? AND source_id=?',(session['case_id'],source_id)).fetchone()
    if not row:raise HTTPException(404,'Source not found')
    return Response(row[2],media_type=row[1],headers={'Content-Disposition':f'attachment; filename="{row[0]}"','X-Content-Type-Options':'nosniff'})


class Annotation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    operation_id: UUID
    source_id: str = Field(max_length=100)
    fact: Literal['rate_per_unit','units_worked','payment_amount','workplace_location','employer_name','other']
    value: str = Field(min_length=1,max_length=2000,pattern=r'\S')
    unresolved: str = Field(default='',max_length=2000)
    worker_confirmed: bool = False


@router.post('/fact-source')
def annotate(data: Annotation, session=Depends(worker.require_worker)):
    payload=data.model_dump(mode='json',exclude={'operation_id'});payload['status']='supplied_material_interpretation_not_independently_verified'
    if not data.worker_confirmed and not data.unresolved:
        payload['unresolved']=('Confirm the payment amount and which job this supporting record concerns.' if data.fact=='payment_amount'
                               else 'Ask the worker to confirm this interpretation of the supplied source.')
    with closing(sqlite3.connect(database.DB_PATH,timeout=15)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if data.source_id!='worker_account' and not db.execute('SELECT 1 FROM case_evidence WHERE case_id=? AND source_id=?',(session['case_id'],data.source_id)).fetchone():
            raise HTTPException(422,'The supplied source does not belong to this case.')
        old=db.execute('SELECT request_hash FROM case_fact_sources WHERE case_id=? AND operation_id=?',(session['case_id'],str(data.operation_id))).fetchone()
        if old and old[0]!=fingerprint(payload):raise HTTPException(409,'This source-link operation was already used.')
        if not old:db.execute('INSERT INTO case_fact_sources VALUES (?,?,?,?,?)',
                              (session['case_id'],str(data.operation_id),fingerprint(payload),json.dumps(payload,ensure_ascii=False),now()))
    return read_case_record(session['case_id'])


class Reminder(BaseModel):
    model_config = ConfigDict(extra='forbid')
    operation_id: UUID
    due_at: datetime
    action: str = Field(min_length=1,max_length=1000,pattern=r'\S')
    consent: Literal[True]

    @field_validator('due_at')
    @classmethod
    def require_timezone(cls,value):
        if value.tzinfo is None or value.utcoffset() is None:raise ValueError('Include a timezone.')
        return value


@router.post('/reminders')
def remind(data: Reminder, session=Depends(worker.require_worker)):
    payload=data.model_dump(mode='json',exclude={'operation_id'});digest=fingerprint(payload)
    with closing(sqlite3.connect(database.DB_PATH,timeout=15)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT request_hash FROM case_reminders WHERE case_id=? AND operation_id=?',(session['case_id'],str(data.operation_id))).fetchone()
        if old and old[0]!=digest:raise HTTPException(409,'This reminder reference was already used.')
        if not old:db.execute('INSERT INTO case_reminders VALUES (?,?,?,?,?,?,?,?,?)',
            (str(uuid4()),session['case_id'],str(data.operation_id),digest,data.due_at.isoformat(),data.action,'pending',now(),None))
    return read_case_record(session['case_id'])


class NoPaymentFollowup(BaseModel):
    operation_id: UUID
    reminder_id: UUID | None = None
    statement: str = Field(min_length=1,max_length=2000,pattern=r'\S')
    worker_confirmed: Literal[True]


@router.post('/no-payment-followup')
def no_payment(data: NoPaymentFollowup,session=Depends(worker.require_worker)):
    payload=data.model_dump(mode='json');digest=fingerprint(payload)
    with closing(sqlite3.connect(database.DB_PATH,timeout=15)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT request_hash FROM case_followup_notes WHERE case_id=? AND operation_id=?',(session['case_id'],str(data.operation_id))).fetchone()
        if old:
            if old[0]!=digest:raise HTTPException(409,'This follow-up reference was already used.')
        else:
            if data.reminder_id:
                changed=db.execute("UPDATE case_reminders SET state='completed',completed_by=? WHERE case_id=? AND reminder_id=? AND state='pending'",
                                   (str(data.operation_id),session['case_id'],str(data.reminder_id))).rowcount
                if changed!=1:raise HTTPException(409,'The reminder is unavailable or already completed.')
            db.execute('INSERT INTO case_followup_notes VALUES (?,?,?,?,?,?)',
                (session['case_id'],str(data.operation_id),digest,data.statement,str(data.reminder_id) if data.reminder_id else None,now()))
    return read_case_record(session['case_id'])


@router.get('/packet')
def packet(session=Depends(worker.require_worker)):
    record=read_case_record(session['case_id']);w=record['workspace'];c=record['calculation']
    esc=lambda x:escape(str(x))
    def table(headers,rows):
        return '<table><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'
    html='<!doctype html><html lang="en"><meta charset="utf-8"><title>HaqRecord case packet</title><style>body{font:16px Arial;max-width:1000px;margin:30px auto;line-height:1.5}table{border-collapse:collapse;width:100%;margin:15px 0}td,th{border:1px solid #aaa;text-align:left;padding:8px;vertical-align:top}p{white-space:pre-wrap}@media print{body{margin:0}tr{break-inside:avoid}}</style>'
    html+='<h1>HaqRecord case packet</h1><p>'+esc(record['case_id'])+'</p><p>Worker-reported account. No government complaint submitted or official status checked. Supplied files and interpretations are not independently verified.</p>'
    html+='<h2>Original account</h2><p>'+esc(record['intake']['original_statement'])+'</p><h2>Current calculation</h2>'
    html+=table(['Reported earnings','Wages received for this work','Received money needing clarification','Promised, not received','Remaining before unclear payments'],[[c['total_earned'],c['payments_received'],c.get('unallocated_received','0.00'),c.get('promised_amount','0.00'),c['balance']]])
    html+='<p>'+esc(c['note'])+'</p><h2>Facts and sources</h2>'
    html+=table(['Fact','Value','Source references','Unresolved'],[[f['fact'],f['value'],', '.join(f.get('source_ids') or [f.get('source_id','worker_account')]),f.get('unresolved','')] for f in w['facts']])
    html+='<h2>Payment reconstruction</h2>'+table(['ID','Amount','Received or promised','Allocation','Worker confirmed','Sources'],[[p['payment_id'],p['amount'],p['status'],p['allocation'],p['worker_confirmed'],', '.join(p['source_ids'] or ['worker_account'])] for p in c.get('payment_items',[])])
    html+='<h2>Unresolved points</h2><ul>'+''.join('<li>'+esc(q)+'</li>' for q in record['unresolved_questions'])+'</ul>'
    html+='<h2>Timeline</h2>'+table(['Time (with offset)','Event','Account'],[[e['at'],e['kind'],e['description']] for e in w['timeline']])
    html+='<h2>Supporting material</h2>'+table(['Source ID','Filename','Description','SHA-256','Fictional demo material'],[[s['source_id'],s['filename'],s['description'],s['sha256'],s['fictional']] for s in w['sources']])
    html+='<h2>Follow-up reminders (in-app only)</h2>'+table(['Time (with offset)','Action','Status'],[[r['due_at'],r['action'],r['state']] for r in w['reminders']])
    html+='<h2>Next useful question</h2><p>'+esc(w['next_question'])+'</p><p>Reminders are shown when this case is opened. Outbound calls and external submissions are not connected.</p></html>'
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        from resolution import packet as resolution_packet
        archive.writestr('resolution-report.html',resolution_packet(session).body)
        archive.writestr('case-packet.html',html)
        archive.writestr('case-record.json',json.dumps(record,ensure_ascii=False,indent=2))
        from next_steps import case_next_step
        help_step=case_next_step(record,'en')
        help_text=help_step['summary']+'\n\nNo government complaint submitted. Worker-reported account, not a legal finding.'
        if help_step['resource_card']:
            card=help_step['resource_card'];help_text+='\n\n'+card['display_name']+'\n'+card['what_to_say']+'\n'+card['notice']+'\nSource: '+card['url']
        archive.writestr('help-summary.txt',help_text)
        with closing(sqlite3.connect(database.DB_PATH)) as db:
            for source,filename,content in db.execute('SELECT source_id,filename,content FROM case_evidence WHERE case_id=?',(session['case_id'],)):
                archive.writestr('supporting-material/'+source+'-'+filename,content)
            from case_workspace_service import safe_filename
            for source,filename,content in db.execute('SELECT source_id,filename,content FROM reply_sources WHERE case_id=?',(session['case_id'],)):
                archive.writestr('reply-originals/'+source+'-'+safe_filename(filename),content)
    return Response(buffer.getvalue(),media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{record["case_id"]}-packet.zip"'})
