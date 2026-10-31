"""Additive private workflow storage. No document assertion changes a ledger."""
import json
import hashlib
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def transaction():
    import database
    with closing(sqlite3.connect(database.DB_PATH, timeout=15)) as db, db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN IMMEDIATE')
        yield db


def migrate():
    with transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY,applied_at TEXT NOT NULL)')
        db.execute('''CREATE TABLE IF NOT EXISTS resolution_events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL REFERENCES cases(case_id),
            event_id TEXT NOT NULL UNIQUE, operation_id TEXT NOT NULL, request_hash TEXT NOT NULL,
            kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(case_id, operation_id))''')
        db.execute('CREATE INDEX IF NOT EXISTS resolution_case ON resolution_events(case_id,sequence)')
        db.execute('''CREATE TABLE IF NOT EXISTS reply_sources (
            source_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
            operation_id TEXT NOT NULL, request_hash TEXT NOT NULL, filename TEXT NOT NULL,
            mime TEXT NOT NULL, content BLOB NOT NULL, origin TEXT NOT NULL, message_date TEXT,
            fictional INTEGER NOT NULL, status TEXT NOT NULL, result TEXT NOT NULL,
            created_at TEXT NOT NULL, UNIQUE(case_id,operation_id))''')
        db.execute('''CREATE TABLE IF NOT EXISTS response_links (
            token_hash TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
            request_id TEXT NOT NULL, expires_at REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL)''')
        db.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?)',('resolution_v1',now()))


def events(db, case_id):
    return [{**dict(row), 'payload': json.loads(row['payload'])} for row in db.execute(
        'SELECT * FROM resolution_events WHERE case_id=? ORDER BY sequence', (case_id,))]


def revision(db, case_id):
    return db.execute('SELECT count(*) FROM resolution_events WHERE case_id=?', (case_id,)).fetchone()[0]


def prior(db, case_id, operation_id, digest):
    row = db.execute('SELECT * FROM resolution_events WHERE case_id=? AND operation_id=?',
                     (case_id, str(operation_id))).fetchone()
    if row:
        if row['request_hash'] != digest:
            raise HTTPException(409, 'This operation was already used for different details.')
        return {**dict(row), 'payload': json.loads(row['payload'])}


def append(db, case_id, operation_id, expected_revision, kind, payload, request_payload=None):
    digest = fingerprint(request_payload if request_payload is not None else {'kind': kind, 'payload': payload})
    old = prior(db, case_id, operation_id, digest)
    if old:
        return old
    if revision(db, case_id) != expected_revision:
        raise HTTPException(409, 'The case changed. Review the current version before confirming.')
    event = dict(event_id=str(uuid4()), operation_id=str(operation_id), kind=kind, payload=payload, created_at=now())
    db.execute('INSERT INTO resolution_events(case_id,event_id,operation_id,request_hash,kind,payload,created_at) VALUES(?,?,?,?,?,?,?)',
               (case_id,event['event_id'],str(operation_id),digest,kind,json.dumps(payload,ensure_ascii=False),event['created_at']))
    return event


def get_event(db, case_id, event_id, kind=None):
    row = db.execute('SELECT * FROM resolution_events WHERE case_id=? AND event_id=?', (case_id,event_id)).fetchone()
    if not row or (kind and row['kind'] != kind):
        raise HTTPException(404, 'This case item is unavailable.')
    return {**dict(row), 'payload': json.loads(row['payload'])}
