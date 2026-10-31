"""Case-bound Bolna callbacks and browser approvals. No PIN enters a voice tool."""
import hashlib
import json
import os
import secrets
import sqlite3
import time
from decimal import Decimal
from contextlib import closing
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import httpx
from dotenv import dotenv_values
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

import auth
import database
import voice
import worker
from case_models import CaseCreate, PaymentCreate, WageCalculation
from case_service import calculate_wages, read_case_record
from dispute_models import DisputeReconstruction
from wage_basis import monthly_rate_conflicts
import section_voice

browser_router=APIRouter(prefix='/voice/intake',tags=['Voice case intake'])
tool_router=APIRouter(prefix='/bolna/tools',tags=['Case-bound voice tools'])
COOKIE='haqrecord_demo_voice' if os.getenv('HAQRECORD_DEMO')=='true' else 'haqrecord_voice'


def connect():
    return sqlite3.connect(database.DB_PATH,timeout=15)


def initialize():
    with closing(connect()) as db,db:
        db.execute('''CREATE TABLE IF NOT EXISTS voice_contexts (
            context_id TEXT PRIMARY KEY, browser_hash TEXT NOT NULL UNIQUE,
            tool_hash TEXT NOT NULL UNIQUE, csrf TEXT NOT NULL, mode TEXT NOT NULL,
            case_id TEXT, expires_at REAL NOT NULL, state TEXT NOT NULL,
            draft_id TEXT, draft_kind TEXT, draft_json TEXT, run_id TEXT,
            result_json TEXT, draft_hash TEXT, worker_hash TEXT
        )''')
        if 'resources_json' not in {row[1] for row in db.execute('PRAGMA table_info(voice_contexts)')}:
            db.execute('ALTER TABLE voice_contexts ADD COLUMN resources_json TEXT')
        if 'preview_json' not in {row[1] for row in db.execute('PRAGMA table_info(voice_contexts)')}:
            db.execute('ALTER TABLE voice_contexts ADD COLUMN preview_json TEXT')
        if 'notes_json' not in {row[1] for row in db.execute('PRAGMA table_info(voice_contexts)')}:
            db.execute('ALTER TABLE voice_contexts ADD COLUMN notes_json TEXT')
        if 'next_step_json' not in {row[1] for row in db.execute('PRAGMA table_info(voice_contexts)')}:
            db.execute('ALTER TABLE voice_contexts ADD COLUMN next_step_json TEXT')
        if 'section_json' not in {row[1] for row in db.execute('PRAGMA table_info(voice_contexts)')}:
            db.execute('ALTER TABLE voice_contexts ADD COLUMN section_json TEXT')
        db.execute('''CREATE TABLE IF NOT EXISTS voice_confirmations (
            draft_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, run_id TEXT,
            kind TEXT NOT NULL, confirmed_at REAL NOT NULL
        )''')


def context_by(column,value):
    assert column in ('browser_hash','tool_hash','context_id')
    with closing(connect()) as db:
        db.row_factory=sqlite3.Row
        row=db.execute(f'SELECT * FROM voice_contexts WHERE {column}=? AND expires_at>?',
                       (value,time.time())).fetchone()
    return dict(row) if row else None


def require_context(request:Request):
    token=request.cookies.get(COOKIE,'')
    context=context_by('browser_hash',auth.digest(token)) if token and len(token)<=256 else None
    if context is None:raise HTTPException(401,'Start a new voice session on this browser')
    if context['case_id']:
        if not active_worker(context):
            raise HTTPException(401,'Open the same worker case again before accessing this voice session')
    if request.method not in ('GET','HEAD','OPTIONS'):
        auth.check_origin(request)
        if not secrets.compare_digest(request.headers.get('x-csrf-token',''),context['csrf']):
            raise HTTPException(403,'Refresh the voice page before making changes')
    return context


def require_tool(request:Request):
    values=dotenv_values(Path(__file__).resolve().parent/'.env')
    expected=values.get('HAQRECORD_VOICE_TOOL_SECRET') or os.getenv('HAQRECORD_VOICE_TOOL_SECRET','')
    supplied=request.headers.get('authorization','')
    if not expected or not secrets.compare_digest(auth.digest(supplied),auth.digest('Bearer '+expected)):
        raise HTTPException(401,'Invalid voice tool credential')


class ToolToken(BaseModel):
    voice_token:str=Field(min_length=20,max_length=256,description='Internal voice_token supplied in this call context. Copy it exactly. Never ask the worker for it, speak it, invent it or use the backend Bearer token instead.')


def tool_context(data,allow_section=False):
    context=context_by('tool_hash',auth.digest(data.voice_token))
    if not context:raise HTTPException(401,'Voice session expired or unavailable')
    if context['case_id'] and not active_worker(context):
        raise HTTPException(401,'The worker case session ended. Start a fresh verified call.')
    if context.get('section_json') and not allow_section:
        raise HTTPException(403,'This call is limited to its selected form section. Use guide_case_section; other case tools are unavailable.')
    return context


def active_worker(context):
    with closing(connect()) as db:
        return bool(db.execute('SELECT 1 FROM worker_sessions WHERE token_hash=? AND case_id=? AND expires_at>?',
            (context['worker_hash'],context['case_id'],time.time())).fetchone())


class StartIntake(BaseModel):
    consent_to_voice_processing:Literal[True]
    mode:Literal['new','existing']='new'
    language:Literal['hi','en']='hi'
    section:Literal['agreement','evidence','facts','followup','history']|None=None
    section_values:dict=Field(default_factory=dict,max_length=100)
    restart_section:bool=False


@browser_router.post('/session')
def start_intake(data:StartIntake,request:Request,response:Response):
    worker.check_json_origin(request)
    config=voice.settings()
    extra=dotenv_values(Path(__file__).resolve().parent/'.env')
    if not config.get('BOLNA_API_KEY') or not config.get('BOLNA_AGENT_ID'):
        raise HTTPException(503,'Bolna is not configured')
    if not extra.get('HAQRECORD_VOICE_PUBLIC_URL'):
        raise HTTPException(503,'The voice callback bridge is not configured')
    # Validate required callback connections before minting. Prompt, provider
    # and timing differences are advisory and do not pause calls.
    if not extra.get('HAQRECORD_VOICE_TOOL_SECRET'):raise HTTPException(503,'The voice callback authentication is not configured.')
    agent_check=voice.check_agent(config,extra.get('HAQRECORD_VOICE_PUBLIC_URL'),force=True,tool_secret=extra.get('HAQRECORD_VOICE_TOOL_SECRET'))
    if not agent_check['ready']:
        raise HTTPException(503,{'code':'voice_configuration_changed',
            'message':'Sara settings changed or could not be verified. Restore the tested voice configuration before another call.'})
    if data.section and not agent_check.get('section_voice_ready'):
        raise HTTPException(503,'Section voice guidance is not connected yet. The text fields remain available.')
    if not voice.callback_available(extra.get('HAQRECORD_VOICE_PUBLIC_URL')):
        raise HTTPException(503,'The voice backend connection is offline. Please use text intake while it is restored.')
    case_id=None
    worker_hash=None
    if data.mode=='existing':
        # Worker session CSRF is checked separately because this creates the voice context.
        case_id=worker.require_worker(request)['case_id']
        worker_hash=auth.digest(request.cookies[worker.COOKIE])
    if data.section and not case_id:raise HTTPException(422,'Open your private case before using section guidance.')
    section=None
    if data.section:
        record=read_case_record(case_id)
        with closing(connect()) as db:
            db.row_factory=sqlite3.Row
            previous=db.execute("SELECT * FROM voice_contexts WHERE worker_hash=? AND case_id=? AND expires_at>? AND json_extract(section_json,'$.section')=? ORDER BY expires_at DESC LIMIT 1",
                (worker_hash,case_id,time.time(),data.section)).fetchone()
            previous=dict(previous) if previous else None
        old=json.loads(previous['section_json']) if previous and previous.get('section_json') and previous['case_id']==case_id and previous['worker_hash']==worker_hash else None
        if old and old['section']==data.section and not data.restart_section:
            section=old
            section['language']=data.language
            # Only the browser can report a chosen file; its content is never sent
            # into the voice context or selected by an AI callback.
            if data.section=='evidence' and data.section_values.get('workspace-file'):
                section['values']['workspace-file']=str(data.section_values['workspace-file'])[:200]
        else:
            try:section=section_voice.initial(data.section,record,data.section_values,data.language)
            except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    # Session requests are recorded for diagnostics, never capped by this app.
    with closing(auth.connect()) as db,db:
        db.execute('CREATE TABLE IF NOT EXISTS voice_mints (requested_at REAL NOT NULL)')
        db.execute('INSERT INTO voice_mints VALUES (?)',(time.time(),))
    browser_token,tool_token,csrf=secrets.token_urlsafe(32),secrets.token_urlsafe(32),secrets.token_urlsafe(32)
    context_id=str(uuid4())
    with closing(connect()) as db,db:
        # Starting a new call revokes this browser's previous call capability.
        old=request.cookies.get(COOKIE)
        if old:
            # Keep section drafts for resume, while revoking their call capability.
            db.execute('DELETE FROM voice_contexts WHERE browser_hash=? AND section_json IS NULL',(auth.digest(old),))
            db.execute('UPDATE voice_contexts SET tool_hash=hex(randomblob(32)) WHERE browser_hash=? AND section_json IS NOT NULL',(auth.digest(old),))
        if data.section:
            db.execute('UPDATE voice_contexts SET tool_hash=hex(randomblob(32)) WHERE worker_hash=? AND case_id=? AND section_json IS NOT NULL',(worker_hash,case_id))
        db.execute('DELETE FROM voice_contexts WHERE expires_at<=?',(time.time(),))
        db.execute('INSERT INTO voice_contexts (context_id,browser_hash,tool_hash,csrf,mode,case_id,expires_at,state,worker_hash) '
                   'VALUES (?,?,?,?,?,?,?,?,?)',
                   (context_id,auth.digest(browser_token),auth.digest(tool_token),csrf,data.mode,case_id,time.time()+1800,'listening',worker_hash))
        if section:db.execute('UPDATE voice_contexts SET section_json=? WHERE context_id=?',(json.dumps(section,ensure_ascii=False),context_id))
    try:
        result=httpx.post('https://api.bolna.ai/web-call/freeswitch-session',
            headers={'Authorization':'Bearer '+config['BOLNA_API_KEY']},
            json={'agent_id':config['BOLNA_AGENT_ID'],'agent_data':{'language':data.language},'user_data':{
                'voice_token':tool_token,'haqrecord_mode':data.mode,
                'language':'Hindi' if data.language=='hi' else 'English',
                'section_guidance':section_voice.guidance(section) if section else 'OFF. Use the ordinary HaqRecord conversation.',
                'haqrecord_opening':(section_voice.view(section)['next_question'] or ('इस भाग की जानकारी समझते हैं।' if data.language=='hi' else 'Let us look at the records in this section.')) if section else (
                    'नमस्ते, मैं सारा हूँ। आराम से अपनी बात बताएं।' if data.language=='hi' else 'Hello, I am Sara. Tell me what happened, in your own time.')}},timeout=20)
        if not result.is_success:raise HTTPException(502,'Bolna could not start this call. Check credits and agent access.')
        payload=result.json()
        if not isinstance(payload,dict):raise ValueError('Invalid session response')
    except (httpx.RequestError,ValueError):
        with closing(connect()) as db,db:db.execute('DELETE FROM voice_contexts WHERE context_id=?',(context_id,))
        raise HTTPException(502,'Unable to start the voice connection')
    except HTTPException:
        with closing(connect()) as db,db:db.execute('DELETE FROM voice_contexts WHERE context_id=?',(context_id,))
        raise
    with closing(connect()) as db,db:
        db.execute('UPDATE voice_contexts SET run_id=? WHERE context_id=?',(payload.get('run_id'),context_id))
    response.set_cookie(COOKIE,browser_token,httponly=True,samesite='strict',path='/',max_age=1800,
        secure=os.getenv('SESSION_COOKIE_SECURE','true').lower()=='true')
    response.headers['X-Voice-CSRF']=csrf
    return payload


@browser_router.get('/section-state')
def section_state(context=Depends(require_context)):
    if not context.get('section_json'):raise HTTPException(404,'No section voice draft is open.')
    return section_voice.view(json.loads(context['section_json']))


class SectionBrowserFile(BaseModel):
    model_config=ConfigDict(extra='forbid')
    filename:str=Field(max_length=200)


@browser_router.post('/section-file')
def section_file(data:SectionBrowserFile,context=Depends(require_context)):
    with closing(connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT section_json FROM voice_contexts WHERE context_id=?',(context['context_id'],)).fetchone()
        state=json.loads(row[0]) if row and row[0] else None
        if not state or state['section']!='evidence':raise HTTPException(403,'File selection belongs to the supporting-material section.')
        state['values']['workspace-file']=data.filename
        state['revision']+=1
        db.execute('UPDATE voice_contexts SET section_json=? WHERE context_id=?',(json.dumps(state,ensure_ascii=False),context['context_id']))
    return section_voice.view(state)


class SectionAnswer(ToolToken):
    model_config=ConfigDict(extra='forbid')
    action:Literal['read','answer','confirm','skip','correct','add_payment']='read'
    field:str=Field(default='',max_length=100)
    value_json:str=Field(default='null',max_length=8000)


@tool_router.post('/guide-section',dependencies=[Depends(require_tool)])
def guide_section(data:SectionAnswer):
    context=tool_context(data,allow_section=True)
    if not context.get('section_json'):raise HTTPException(403,'This tool is only available in a selected section call.')
    try:value=json.loads(data.value_json)
    except ValueError:raise HTTPException(422,'Provide one answer as valid JSON.')
    with closing(connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT section_json FROM voice_contexts WHERE context_id=? AND tool_hash=? AND expires_at>?',
            (context['context_id'],auth.digest(data.voice_token),time.time())).fetchone()
        if not row:raise HTTPException(401,'This section call has ended or paused.')
        state=json.loads(row[0])
        # Browser uploads and reminder saves can add choices while this block is
        # open. Refresh only this section's choices from the same attached case.
        record=read_case_record(context['case_id'])
        refreshed={f['key']:f for f in section_voice.plan(state['section'],record,state['values'])}
        for f in state['fields']:
            if f['key'] in refreshed:f['choices']=refreshed[f['key']]['choices']
        if state['read_only']:
            state['records']=record['workspace']['facts' if state['section']=='facts' else 'timeline'][-40:]
        try:updated=section_voice.advance(state,data.action,data.field,value)
        except ValueError as exc:return {**section_voice.view(state),'answer_error':str(exc),'accepted':False}
        db.execute('UPDATE voice_contexts SET section_json=? WHERE context_id=?',(json.dumps(updated,ensure_ascii=False),context['context_id']))
    return {**section_voice.view(updated),'accepted':True}


@browser_router.get('/state')
def intake_state(language:Literal['hi','en']|None=None,context=Depends(require_context)):
    draft=json.loads(context['draft_json']) if context['draft_json'] else None
    result=json.loads(context['result_json']) if context['result_json'] else None
    if context['state']=='saved' and result and context['case_id']:
        result['case']=read_case_record(context['case_id'])
    preview=json.loads(context['preview_json']) if context.get('preview_json') else None
    notes=json.loads(context['notes_json']) if context.get('notes_json') else None
    resources=json.loads(context['resources_json']) if context.get('resources_json') else None
    next_step=json.loads(context['next_step_json']) if context.get('next_step_json') else None
    if language:
        # Localize generated guidance on read; never translate or mutate testimony,
        # approved drafts, figures, uploaded originals or the voice agent's language.
        from next_steps import case_next_step,resource_action_card
        from intake_progress import intake_progress
        if notes:notes.update(intake_progress({**notes,'language':language}))
        if resources and resources.get('action_card'):
            city=resources.get('city') or resources['action_card'].get('city')
            if city in ('hyderabad','bengaluru'):resources['action_card']=resource_action_card(city,language)
        if next_step:
            record=read_case_record(context['case_id']) if context['case_id'] else None
            if record is None and preview:
                location=(preview.get('workplace_location') or '').lower()
                city='hyderabad' if 'hyderabad' in location else 'bengaluru' if 'bengaluru' in location or 'bangalore' in location else None
                record={'intake':preview,'calculation':preview['calculation'],'workspace':{'pilot_city':city}}
            if record:next_step=case_next_step(record,language)
    return {'state':context['state'],'csrf_token':context['csrf'],'case_id':context['case_id'],
        'draft_id':context['draft_id'],'draft_kind':context['draft_kind'],'draft':draft,'result':result,
        'resources':resources,'preview':preview,'notes':notes,'next_step':next_step}


def stage(context,kind,data,expected_preview_id=None):
    normalized=json.dumps(data,sort_keys=True,ensure_ascii=False)
    fingerprint=hashlib.sha256(normalized.encode()).hexdigest()
    with closing(connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        db.row_factory=sqlite3.Row
        current=db.execute('SELECT * FROM voice_contexts WHERE context_id=?',(context['context_id'],)).fetchone()
        if not current:raise HTTPException(401,'Voice session expired')
        if expected_preview_id is not None:
            latest=json.loads(current['preview_json']) if current['preview_json'] else None
            if not latest or latest['preview_id']!=str(expected_preview_id):raise HTTPException(409,'The calculation changed. Review the latest figures.')
        if current['draft_hash']==fingerprint and current['draft_kind']==kind:
            return {'status':current['state'],'draft_id':current['draft_id'],
                    'message':'This exact proposal is already on the website. Do not claim it is saved unless state is saved.'}
        if kind=='intake' and current['case_id']:
            return {'status':'case_already_open','message':'This voice session already has a saved case. Do not create another.'}
        if current['state']=='committing':raise HTTPException(409,'A browser confirmation is being processed')
        draft_id=str(uuid4())
        db.execute('UPDATE voice_contexts SET state=?,draft_id=?,draft_kind=?,draft_json=?,draft_hash=?,result_json=NULL WHERE context_id=?',
            ('awaiting_browser_approval',draft_id,kind,normalized,fingerprint,context['context_id']))
    return {'status':'awaiting_browser_approval','draft_id':draft_id,
        'message':'Proposal prepared. Ask the worker to review the screen and confirm privately. It is not saved yet.'}


class AccountNotes(ToolToken):
    original_statement:str=Field(min_length=1,max_length=10000,pattern=r'\S')
    preferred_name:str|None=Field(default=None,max_length=100)
    workplace_location:str|None=Field(default=None,max_length=300)
    employer_name:str|None=Field(default=None,max_length=200)
    language:Literal['hi','en']='hi'
    pay_basis:Literal['hourly','daily','weekly','monthly','piece']|None=None
    units_worked:int|Decimal|None=Field(default=None,gt=0,le=10000)
    rate_per_unit:str|None=Field(default=None,max_length=30)
    payments_received:str|None=Field(default=None,max_length=30)
    unresolved_questions:str=Field(default='',max_length=2000)

@tool_router.post('/capture-account',dependencies=[Depends(require_tool)])
def capture_account(data:AccountNotes):
    context=tool_context(data)
    if context['mode']!='new' or context['case_id']:
        return {'status':'case_already_open','message':'Use the already verified case; do not overwrite its account.'}
    with closing(connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        current=db.execute('SELECT notes_json,preview_json,case_id,state FROM voice_contexts WHERE context_id=?',
                           (context['context_id'],)).fetchone()
        if not current or current[2] or current[3]=='committing':
            raise HTTPException(409,'A browser confirmation is in progress')
        previous=json.loads(current[0]) if current[0] else {}
        # Tool retries and partial follow-ups must retain already supplied facts.
        # New uncertainty belongs in unresolved_questions; null is not a new
        # assertion that a previously reported payment never happened.
        serialized=data.model_dump(mode='json',exclude={'voice_token'})
        notes={**serialized,**previous}
        for key in data.model_fields_set-{'voice_token'}:
            value=serialized[key]
            if value is not None:notes[key]=value
        notes.update(source='worker_account_unconfirmed',worker_confirmed=False,saved=False)
        from intake_progress import intake_progress,quantity_unresolved
        if notes.get('units_worked') is not None and quantity_unresolved(notes):
            notes['unconfirmed_quantity_candidate']=notes['units_worked']
            notes['units_worked']=None
        progress=intake_progress(notes)
        notes['next_question']=progress['next_question']
        if notes!=previous:
            db.execute("UPDATE voice_contexts SET notes_json=?,preview_json=NULL,draft_json=NULL,draft_hash=NULL,draft_id=NULL,draft_kind=NULL,state='listening' WHERE context_id=?",
                       (json.dumps(notes,ensure_ascii=False),context['context_id']))
        elif current[1] or current[3]=='awaiting_browser_approval':
            return {'status':'account_on_screen','saved':False,
                'message':'These facts are already captured and the calculation is still on screen. Ask only about missing or conflicting information; otherwise let the worker review and save privately.'}
    return {'status':'account_on_screen','saved':False,**progress,
        'message':'The incomplete account is now visible. Ask only the next missing or conflicting detail. Do not repeat the whole account or claim a balance before calculate_reported_balance succeeds.'}


class CalculateTool(ToolToken,WageCalculation):
    adjustments_clear:bool
    original_statement:str=Field(default='',max_length=10000)
    preferred_name:str=Field(default='',max_length=100)
    workplace_location:str=Field(default='',max_length=300)
    employer_name:str=Field(default='',max_length=200)
    language:Literal['hi','en']='hi'


@tool_router.post('/calculate',dependencies=[Depends(require_tool)])
def calculate_tool(data:CalculateTool):
    context=tool_context(data)
    notes=json.loads(context.get('notes_json') or '{}')
    if notes.get('unconfirmed_quantity_candidate') is not None and notes.get('units_worked') is None:
        return reject_unconfirmed_quantity(context,notes)
    if monthly_rate_conflicts(data.original_statement or notes.get('original_statement'), data.pay_basis):
        return reject_wage_basis(context)
    if not data.adjustments_clear:
        with closing(connect()) as db,db:
            db.execute("UPDATE voice_contexts SET preview_json=NULL,draft_id=NULL,draft_kind=NULL,draft_json=NULL,draft_hash=NULL,state='needs_clarification' WHERE context_id=? AND case_id IS NULL AND state!='committing'",(context['context_id'],))
        return {'status':'needs_clarification','message':'Advances, deductions or disputed figures are unresolved. Do not state one definitive balance.'}
    calculation=calculate_wages(data)
    # Display the calculation immediately. Never depend on a second LLM tool call
    # merely to show the figures, and never mistake a preview for a saved case.
    if context['mode']=='new' and not context['case_id']:
        figures={key:data.model_dump(mode='json')[key] for key in ('pay_basis','units_worked','rate_per_unit','payments_received','reconstruction')}
        preview={'preview_id':str(uuid4()),'calculation':calculation,'figures':figures,
            **{key:getattr(data,key) for key in ('original_statement','preferred_name','workplace_location','employer_name','language')},
            'saved':False,'source':'voice_reported_figures','worker_review_required':True}
        with closing(connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT state,case_id,preview_json,notes_json FROM voice_contexts WHERE context_id=?',(context['context_id'],)).fetchone()
            if current and not current[1] and current[0]!='committing':
                notes=json.loads(current[3]) if current[3] else {}
                for key in ('original_statement','preferred_name','workplace_location','employer_name','language'):
                    if notes.get(key) and (key not in data.model_fields_set or not preview[key]):
                        preview[key]=notes[key]
                old=json.loads(current[2]) if current[2] else None
                review_fields=('figures','original_statement','preferred_name','workplace_location','employer_name','language')
                changed=not old or any(old.get(key)!=preview[key] for key in review_fields)
                if not changed:preview['preview_id']=old['preview_id']
                if changed:
                    db.execute("UPDATE voice_contexts SET state='listening',draft_id=NULL,draft_kind=NULL,draft_json=NULL,draft_hash=NULL WHERE context_id=?",(context['context_id'],))
                db.execute('UPDATE voice_contexts SET preview_json=? WHERE context_id=?',(json.dumps(preview,ensure_ascii=False),context['context_id']))
    return {'status':'calculated','calculation':calculation,'on_screen':True,
        'message':'The figures are visible on screen, not saved. The worker can review and save privately on the website. Do not ask them to repeat the whole account.'}


def reject_unconfirmed_quantity(context,notes):
    from intake_progress import intake_progress
    with closing(connect()) as db,db:
        db.execute("UPDATE voice_contexts SET preview_json=NULL,draft_id=NULL,draft_kind=NULL,draft_json=NULL,draft_hash=NULL,state='needs_clarification' WHERE context_id=? AND state!='committing'",(context['context_id'],))
    return {'status':'needs_clarification','on_screen':False,'saved':False,**intake_progress(notes),
        'message':'The captured quantity was explicitly marked unresolved. Do not calculate or prepare a case using that candidate. Obtain the worker-confirmed quantity in the agreed rate unit, update captured notes, then retry. Do not convert a month to four weeks.'}


def reject_wage_basis(context):
    with closing(connect()) as db,db:
        db.execute("UPDATE voice_contexts SET preview_json=NULL,next_step_json=NULL,draft_id=NULL,draft_kind=NULL,draft_json=NULL,draft_hash=NULL,state='needs_clarification' WHERE context_id=? AND state!='committing'",(context['context_id'],))
    return {'status':'needs_clarification','on_screen':False,
        'message':'The stated rate and supplied unit conflict or mix units. The old preview is invalid. Confirm the explicit hourly/daily/weekly/monthly/piece agreement, matching quantity, rate and actual receipts. Never silently convert months to weeks or hours to days; do not read the rejected balance.'}


class PreviewApproval(BaseModel):
    preview_id:UUID
    preferred_name:str=Field(default='Worker',min_length=1,max_length=100)
    original_statement:str=Field(min_length=1,max_length=10000,pattern=r'\S')
    workplace_location:str|None=Field(default=None,max_length=300)
    employer_name:str|None=Field(default=None,max_length=200)
    language:Literal['hi','en']='hi'
    approved:Literal[True]

@browser_router.post('/prepare-preview')
def prepare_preview(data:PreviewApproval,context=Depends(require_context)):
    if context['mode']!='new' or context['case_id']:raise HTTPException(409,'A saved case is already attached')
    preview=json.loads(context['preview_json']) if context.get('preview_json') else None
    if not preview or preview['preview_id']!=str(data.preview_id):
        raise HTTPException(409,'The calculation changed. Review the latest figures.')
    fields=CaseCreate(**preview['figures'],preferred_name=data.preferred_name,
        original_statement=data.original_statement,workplace_location=data.workplace_location,
        employer_name=data.employer_name,language=data.language,
        adjustments_checked=True,consent_to_store=True,worker_confirmed=True)
    return stage(context,'intake',{'intake':fields.model_dump(mode='json'),'calculation':calculate_wages(fields)},expected_preview_id=data.preview_id)


class IntakeTool(ToolToken,CaseCreate):
    adjustments_clear:bool


@tool_router.post('/prepare-case',dependencies=[Depends(require_tool)])
def prepare_case(data:IntakeTool):
    context=tool_context(data)
    notes=json.loads(context.get('notes_json') or '{}')
    if notes.get('unconfirmed_quantity_candidate') is not None and notes.get('units_worked') is None:return reject_unconfirmed_quantity(context,notes)
    if context['case_id']:
        return {'status':'case_already_open','message':'A case is already attached. Use read_current_case or prepare_payment; do not create another.'}
    if not data.adjustments_clear:
        return {'status':'needs_clarification','message':'Clarify disputed figures before preparing the confirmed wage calculation.'}
    fields=CaseCreate.model_validate(data.model_dump()).model_dump(mode='json')
    fields['adjustments_checked']=True
    return stage(context,'intake',{'intake':fields,'calculation':calculate_wages(data)})


@tool_router.post('/current-case',dependencies=[Depends(require_tool)])
def current_case(data:ToolToken):
    context=tool_context(data)
    if not context['case_id']:
        return {'status':'no_case_open','message':'No saved case is attached. Worker must open an existing case using the website reference and PIN, or confirm a new intake on screen.'}
    record=read_case_record(context['case_id'])
    return {'status':'case_loaded','case':record}


class PaymentTool(ToolToken):
    reminder_id:UUID|None=None
    amount:str=Field(max_length=30)
    received_on:str=Field(default='',max_length=10)
    method:Literal['cash','transfer','unknown']='unknown'
    original_statement:str=Field(min_length=1,max_length=10000)
    worker_confirmed:Literal[True]


@tool_router.post('/prepare-payment',dependencies=[Depends(require_tool)])
def prepare_payment(data:PaymentTool):
    context=tool_context(data)
    if not context['case_id']:return {'status':'no_case_open','message':'Ask the worker to open their case privately on the website first.'}
    try:
        payment=PaymentCreate(operation_id=str(uuid4()),amount=data.amount,received_on=data.received_on or None,
            method=data.method,original_statement=data.original_statement,worker_confirmed=data.worker_confirmed,reminder_id=data.reminder_id)
    except ValidationError:raise HTTPException(422,'Provide a positive payment amount with at most two decimal places and a valid date or an empty date.')
    fields=payment.model_dump(mode='json');fields.pop('operation_id')
    return stage(context,'payment',{'payment':fields,'case_id':context['case_id']})


class ReconstructTool(ToolToken):
    reconstruction:DisputeReconstruction
    original_statement:str=Field(min_length=1,max_length=10000)
    preferred_name:str=Field(default='',max_length=100)
    workplace_location:str=Field(default='',max_length=300)
    employer_name:str=Field(default='',max_length=200)
    language:Literal['hi','en']='hi'
    expected_version:int=Field(default=0,ge=0)
    reason:str=Field(default='Worker clarified the wage account.',max_length=2000,min_length=1)
    worker_confirmed:bool=False


@tool_router.post('/reconstruct-dispute',dependencies=[Depends(require_tool)])
def reconstruct_dispute(data:ReconstructTool):
    context=tool_context(data);r=data.reconstruction
    if monthly_rate_conflicts(data.original_statement,r.pay_basis):
        return reject_wage_basis(context)
    from case_workspace_service import validate_sources
    with closing(connect()) as db:validate_sources(db,context['case_id'] or '',r)
    figures={'pay_basis':r.pay_basis,'units_worked':r.units_worked,'rate_per_unit':r.rate_per_unit,
             'payments_received':r.allocated_total(),'reconstruction':r}
    if not context['case_id']:
        result=calculate_tool(CalculateTool(voice_token=data.voice_token,**figures,adjustments_clear=True,
            original_statement=data.original_statement,preferred_name=data.preferred_name,
            workplace_location=data.workplace_location,employer_name=data.employer_name,language=data.language))
        if result['status']!='calculated':return result
        result['next_question']=result['calculation'].get('next_question')
        result['message']='Provisional figures and separate payment allocations are on screen. Ask next_question if present. A promise is not received money. Browser approval is required to save.'
        return result
    if not data.worker_confirmed:
        return {'status':'needs_confirmation','calculation':calculate_wages(WageCalculation(**figures)),
                'message':'Ask the worker to confirm the changed facts before preparing this correction. Do not repeat unchanged facts.'}
    record=read_case_record(context['case_id'])
    if record['workspace']['version']!=data.expected_version:raise HTTPException(409,'Read the current case again; its version changed.')
    intake={**record['intake'],**WageCalculation(**figures).model_dump(mode='json')}
    return stage(context,'reconstruction',{'reconstruction':r.model_dump(mode='json'),
        'expected_version':data.expected_version,'reason':data.reason,'intake':intake,
        'calculation':calculate_wages(WageCalculation(**figures),sum((Decimal(p['amount']) for p in record['follow_up_payments']),Decimal('0')))})


class FollowupTool(ToolToken):
    reminder_id:UUID|None=None
    statement:str=Field(min_length=1,max_length=2000)
    worker_confirmed:Literal[True]


@tool_router.post('/prepare-no-payment-followup',dependencies=[Depends(require_tool)])
def prepare_no_payment_followup(data:FollowupTool):
    context=tool_context(data)
    if not context['case_id']:return {'status':'no_case_open','message':'Open the case privately using reference and PIN first.'}
    record=read_case_record(context['case_id'])
    return stage(context,'followup',{'followup':data.model_dump(mode='json',exclude={'voice_token'}),
        'intake':{**record['intake'],'original_statement':'Worker reports no new payment: '+data.statement},'calculation':record['calculation']})


class ReminderTool(ToolToken):
    due_at:str=Field(max_length=50)
    action:str=Field(min_length=1,max_length=1000)
    consent:Literal[True]


@tool_router.post('/prepare-reminder',dependencies=[Depends(require_tool)])
def prepare_reminder(data:ReminderTool):
    context=tool_context(data)
    if not context['case_id']:return {'status':'no_case_open','message':'Save or open the case privately first.'}
    from case_workspace import Reminder
    try:planned=Reminder(operation_id=uuid4(),due_at=data.due_at,action=data.action,consent=data.consent)
    except ValidationError:raise HTTPException(422,'Confirm the agreed date, time and timezone, and consent for an in-app reminder. No telephone call is scheduled.')
    record=read_case_record(context['case_id'])
    fields=planned.model_dump(mode='json',exclude={'operation_id'})
    return stage(context,'reminder',{'reminder':fields,'intake':{**record['intake'],
        'original_statement':'In-app reminder only: '+data.action+' · '+fields['due_at']},'calculation':record['calculation']})


class Commit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    draft_id:UUID
    approved:Literal[True]
    pin:str|None=Field(default=None,pattern=r'^[0-9]{6,12}$')
    distinct_payment_confirmed:bool=False


@browser_router.post('/confirm')
def confirm_draft(data:Commit,request:Request,response:Response,context=Depends(require_context)):
    # The model never has this browser cookie or CSRF token, and cannot approve itself.
    if context['draft_id']!=str(data.draft_id):raise HTTPException(409,'The draft changed. Review the latest figures before confirming.')
    if context['state']=='saved' and context['result_json']:
        return json.loads(context['result_json'])
    if context['state']!='awaiting_browser_approval':raise HTTPException(409,'No draft is ready for confirmation')
    draft=json.loads(context['draft_json'])
    with closing(connect()) as db,db:
        changed=db.execute('UPDATE voice_contexts SET state=? WHERE context_id=? AND state=? AND draft_id=?',
            ('committing',context['context_id'],'awaiting_browser_approval',str(data.draft_id))).rowcount
        if changed!=1:raise HTTPException(409,'Confirmation is already being processed. Refresh to see its result.')
    try:
        if context['draft_kind']=='intake':
            if not data.pin:raise HTTPException(422,'Choose your private PIN on the website; never speak it on the call.')
            payload=worker.WorkerCreate(**draft['intake'],pin=data.pin,operation_id=data.draft_id)
            result=worker.create_worker_case(payload,request,response)
            case_id=result['case']['case_id']
            with closing(connect()) as db:
                worker_hash=db.execute('SELECT token_hash FROM worker_sessions WHERE case_id=? AND csrf_token=?',
                    (case_id,result['session']['csrf_token'])).fetchone()[0]
        elif context['draft_kind']=='reconstruction':
            if not context['case_id'] or not active_worker(context):raise HTTPException(401,'Open this case privately first.')
            from case_workspace_service import apply_revision
            apply_revision(context['case_id'],DisputeReconstruction.model_validate(draft['reconstruction']),
                           draft['expected_version'],data.draft_id,draft['reason'])
            case_id=context['case_id'];worker_hash=context['worker_hash'];result={'case':read_case_record(case_id)}
        elif context['draft_kind'] in ('followup','reminder'):
            if not context['case_id'] or not active_worker(context):raise HTTPException(401,'Open this case privately first.')
            from case_workspace import no_payment, NoPaymentFollowup, remind, Reminder
            case_id=context['case_id'];worker_hash=context['worker_hash']
            if context['draft_kind']=='followup':
                record=no_payment(NoPaymentFollowup(operation_id=data.draft_id,**draft['followup']),session={'case_id':case_id})
            else:
                record=remind(Reminder(operation_id=data.draft_id,**draft['reminder']),session={'case_id':case_id})
            result={'case':record}
        else:
            if not context['case_id']:raise HTTPException(401,'No case attached')
            # Existing-case session must still be valid when approving a payment.
            if not active_worker(context):raise HTTPException(401,'The worker case session ended. Start a fresh call.')
            payload=PaymentCreate(**{**draft['payment'],'operation_id':str(data.draft_id),
                'distinct_payment_confirmed':data.distinct_payment_confirmed})
            try:payment=database.append_payment(context['case_id'],payload.model_dump(mode='json'))
            except database.PossibleDuplicate as error:raise HTTPException(409,{'code':'possible_duplicate','message':str(error)})
            except database.PaymentConflict as error:raise HTTPException(409,{'code':'operation_conflict','message':str(error)})
            if payment is None:raise HTTPException(404,'Case not found')
            case_id=context['case_id'];worker_hash=context['worker_hash'];result={'payment':payment,'case':read_case_record(case_id)}
    except Exception:
        with closing(connect()) as db,db:
            db.execute('UPDATE voice_contexts SET state=? WHERE context_id=? AND state=?',
                ('awaiting_browser_approval',context['context_id'],'committing'))
        raise
    with closing(connect()) as db,db:
        db.execute('INSERT OR IGNORE INTO voice_confirmations VALUES (?,?,?,?,?)',
            (str(data.draft_id),case_id,context['run_id'],context['draft_kind'],time.time()))
        db.execute('UPDATE voice_contexts SET state=?,case_id=?,result_json=?,worker_hash=? WHERE context_id=?',
            ('saved',case_id,json.dumps(result,ensure_ascii=False),worker_hash,context['context_id']))
    return result


@browser_router.post('/end')
def end_intake(context=Depends(require_context)):
    # Revoke the tool capability while leaving a pending draft available for private approval.
    with closing(connect()) as db,db:
        db.execute('UPDATE voice_contexts SET tool_hash=? WHERE context_id=?',
                   (auth.digest(secrets.token_urlsafe(32)),context['context_id']))
    return {'status':'voice_tools_revoked'}


from research import ResourceQuery, lookup as lookup_resources

class ResourceTool(ToolToken,ResourceQuery):
    pass

@tool_router.post('/resources',dependencies=[Depends(require_tool)])
def voice_resources(data:ResourceTool):
    context=tool_context(data)
    query=ResourceQuery.model_validate({key:getattr(data,key) for key in ResourceQuery.model_fields})
    result=lookup_resources(query)
    if context['case_id']:
        from case_workspace_service import remember_work_city
        remember_work_city(context['case_id'],data.city)
    with closing(connect()) as db,db:
        db.execute('UPDATE voice_contexts SET resources_json=?,next_step_json=NULL WHERE context_id=?',(json.dumps(result),context['context_id']))
    card=result['action_card']
    # URLs are persisted for the website, never passed into the spoken answer.
    return {'status':result['status'],'city':data.city,'organisation':card['display_name'],
            'spoken_response':card['spoken_response'],'contact_number_on_request':card['phone'],
            'links_on_screen':True,'jurisdiction_verified':False,'complaint_submitted':False,
            'instruction':'Speak the organisation name and spoken_response. The links are on screen. Never spell or read a URL. Give phone numbers only if asked.'}


class NextStepTool(ToolToken):
    language:Literal['hi','en']='hi'
    read_summary:bool=False


@tool_router.post('/next-step',dependencies=[Depends(require_tool)])
def explain_case_next_step(data:NextStepTool):
    context=tool_context(data)
    from next_steps import case_next_step,voice_next_step
    if context['case_id']:
        record=read_case_record(context['case_id'])
    else:
        preview=json.loads(context['preview_json']) if context.get('preview_json') else None
        if not preview:return {'status':'need_account','spoken_response':'Please finish your account first; I will ask only what is missing.' if data.language=='en' else 'पहले अपनी पूरी बात बताइए। फिर मैं सिर्फ़ ज़रूरी अधूरी जानकारी पूछूँगी।'}
        location=preview.get('workplace_location','').lower()
        city='hyderabad' if 'hyderabad' in location else 'bengaluru' if 'bengaluru' in location or 'bangalore' in location else None
        record={'intake':preview,'calculation':preview['calculation'],'workspace':{'pilot_city':city}}
    result=case_next_step(record,data.language)
    with closing(connect()) as db,db:
        db.execute('UPDATE voice_contexts SET next_step_json=? WHERE context_id=?',(json.dumps(result,ensure_ascii=False),context['context_id']))
    return voice_next_step(result,data.read_summary)


initialize()
