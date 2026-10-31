"""Workers can access only the case attached to their reference-and-PIN session."""
import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import closing
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

import auth
import database
from case_models import CaseCreate, PaymentCreate
from case_service import new_case_record, read_case_record

router = APIRouter(prefix='/worker', tags=['Worker access'])
COOKIE = 'haqrecord_demo_worker' if os.getenv('HAQRECORD_DEMO')=='true' else 'haqrecord_worker'
SESSION_SECONDS = 4 * 60 * 60


def connect():
    db = sqlite3.connect(database.DB_PATH, timeout=15)
    db.execute('PRAGMA foreign_keys = ON')
    return db


def rate_limit(buckets, limit=5):
    now = time.time()
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        for bucket in buckets:
            row = db.execute('SELECT attempts,window_start FROM worker_attempts WHERE bucket=?', (bucket,)).fetchone()
            if row and now - row[1] < 900 and row[0] >= limit:
                raise HTTPException(429, 'Too many attempts. Try again in 15 minutes.')
        for bucket in buckets:
            row = db.execute('SELECT attempts,window_start FROM worker_attempts WHERE bucket=?', (bucket,)).fetchone()
            count, start = (row[0], row[1]) if row and now - row[1] < 900 else (0, now)
            db.execute('INSERT OR REPLACE INTO worker_attempts VALUES (?,?,?)', (bucket, count + 1, start))
        db.execute('DELETE FROM worker_attempts WHERE window_start < ?', (now - 86400,))


def check_json_origin(request):
    auth.check_origin(request)
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
        raise HTTPException(415, 'Send details as JSON')


def start_session(case_id, request, response):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with closing(connect()) as db, db:
        old = request.cookies.get(COOKIE)
        if old:
            db.execute('DELETE FROM worker_sessions WHERE token_hash=?', (auth.digest(old),))
        db.execute('DELETE FROM worker_sessions WHERE expires_at <= ?', (time.time(),))
        db.execute('INSERT INTO worker_sessions VALUES (?,?,?,?)',
                   (auth.digest(token), case_id, csrf, time.time() + SESSION_SECONDS))
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite='strict',
                        secure=os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true', path='/')
    return {'case_id': case_id, 'csrf_token': csrf}


def require_worker(request: Request):
    token = request.cookies.get(COOKIE, '')
    with closing(connect()) as db:
        row = db.execute('SELECT case_id,csrf_token FROM worker_sessions WHERE token_hash=? AND expires_at>?',
                         (auth.digest(token), time.time())).fetchone() if token and len(token) <= 256 else None
    if row is None:
        raise HTTPException(401, 'Open your case using its reference and PIN')
    session = {'case_id': row[0], 'csrf_token': row[1]}
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        auth.check_origin(request)
        if not secrets.compare_digest(request.headers.get('x-csrf-token', ''), session['csrf_token']):
            raise HTTPException(403, 'Refresh your case session before making changes')
    return session


class WorkerCreate(CaseCreate):
    pin: str = Field(pattern=r'^[0-9]{6,12}$')
    operation_id: UUID


@router.post('/cases', status_code=201)
def create_worker_case(data: WorkerCreate, request: Request, response: Response):
    check_json_origin(request)
    client = request.client.host if request.client else 'unknown'
    rate_limit(['create:' + client])
    intake = CaseCreate.model_validate(data.model_dump())
    record = new_case_record(intake)
    fingerprint = hashlib.sha256(json.dumps(record['intake'], sort_keys=True).encode()).hexdigest()
    operation_id = str(data.operation_id)
    pin_hash = auth.PASSWORDS.hash(data.pin)
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('SELECT case_id,pin_hash,request_hash FROM worker_access WHERE operation_id=?',
                              (operation_id,)).fetchone()
        if existing:
            if existing[2] != fingerprint or not auth.PASSWORDS.verify(data.pin, existing[1]):
                raise HTTPException(409, 'This save reference was used for different details.')
            case_id = existing[0]
        else:
            case_id = 'HR-' + uuid4().hex.upper()
            record['case_id'] = case_id
            if intake.reconstruction:
                from case_workspace_service import validate_sources
                validate_sources(db,case_id,intake.reconstruction)
            db.execute('INSERT INTO cases VALUES (?,?,?)',
                       (case_id, record['created_at'], json.dumps(record, ensure_ascii=False)))
            db.execute('INSERT INTO worker_access VALUES (?,?,?,?)',
                       (case_id, pin_hash, operation_id, fingerprint))
    session = start_session(case_id, request, response)
    return {'session': session, 'case': read_case_record(case_id),
            'message': 'Case saved with HaqRecord. No government complaint has been submitted.'}


class WorkerLogin(BaseModel):
    case_id: str = Field(min_length=1, max_length=100)
    pin: str = Field(pattern=r'^[0-9]{6,12}$')


@router.post('/login')
def worker_login(data: WorkerLogin, request: Request, response: Response):
    check_json_origin(request)
    case_id = data.case_id.strip().upper()
    client = request.client.host if request.client else 'unknown'
    buckets = ['login-ip:' + client, 'login-case:' + auth.digest(case_id)]
    rate_limit(buckets)
    with closing(connect()) as db:
        row = db.execute('SELECT pin_hash FROM worker_access WHERE case_id=?', (case_id,)).fetchone()
    valid = auth.PASSWORDS.verify(data.pin, row[0] if row else auth.DUMMY_HASH)
    if not row or not valid:
        raise HTTPException(401, 'Incorrect case reference or PIN')
    with closing(connect()) as db, db:
        for bucket in buckets:
            db.execute('DELETE FROM worker_attempts WHERE bucket=?', (bucket,))
    return start_session(case_id, request, response)


@router.get('/session')
def worker_session(session=Depends(require_worker)):
    return session


@router.get('/my-case')
def worker_case(session=Depends(require_worker)):
    record = read_case_record(session['case_id'])
    if record is None:
        raise HTTPException(404, 'Case not found')
    return record


@router.post('/payments', status_code=201)
def worker_payment(data: PaymentCreate, session=Depends(require_worker)):
    try:
        payment = database.append_payment(session['case_id'], data.model_dump(mode='json'))
    except database.PaymentConflict as error:
        raise HTTPException(409, {'code': 'operation_conflict', 'message': str(error)})
    except database.PossibleDuplicate as error:
        raise HTTPException(409, {'code': 'possible_duplicate', 'message': str(error)})
    if payment is None:
        raise HTTPException(404, 'Case not found')
    return {'payment': payment, 'case': read_case_record(session['case_id'])}


@router.post('/logout')
def worker_logout(request: Request, response: Response, session=Depends(require_worker)):
    with closing(connect()) as db, db:
        db.execute('DELETE FROM worker_sessions WHERE token_hash=?', (auth.digest(request.cookies[COOKIE]),))
    response.delete_cookie(COOKIE, path='/', httponly=True, samesite='strict')
    return {'message': 'Your case has been closed on this browser'}
