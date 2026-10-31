import hashlib
import os
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(os.getenv('HAQRECORD_DB_PATH') or str(Path(__file__).with_name('haqrecord.db')))


class PaymentConflict(ValueError):
    pass


class PossibleDuplicate(ValueError):
    pass


def initialise_database():
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.executescript('''
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, record_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS payment_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL REFERENCES cases(case_id), event_json TEXT NOT NULL,
                operation_id TEXT, request_hash TEXT
            );
            CREATE INDEX IF NOT EXISTS payment_events_case ON payment_events(case_id, sequence);
            CREATE TABLE IF NOT EXISTS worker_access (
                case_id TEXT PRIMARY KEY REFERENCES cases(case_id),
                pin_hash TEXT NOT NULL, operation_id TEXT NOT NULL UNIQUE,
                request_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS worker_sessions (
                token_hash TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
                csrf_token TEXT NOT NULL, expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS worker_attempts (
                bucket TEXT PRIMARY KEY, attempts INTEGER NOT NULL, window_start REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS case_revisions (
                case_id TEXT NOT NULL, version INTEGER NOT NULL, operation_id TEXT NOT NULL,
                request_hash TEXT NOT NULL, snapshot_json TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(case_id, version), UNIQUE(case_id, operation_id)
            );
            CREATE TABLE IF NOT EXISTS case_evidence (
                source_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, operation_id TEXT NOT NULL,
                filename TEXT NOT NULL, mime TEXT NOT NULL, content BLOB NOT NULL, sha256 TEXT NOT NULL,
                description TEXT NOT NULL, fictional INTEGER NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(case_id, operation_id)
            );
            CREATE TABLE IF NOT EXISTS case_fact_sources (
                case_id TEXT NOT NULL, operation_id TEXT NOT NULL, request_hash TEXT NOT NULL,
                annotation_json TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(case_id,operation_id)
            );
            CREATE TABLE IF NOT EXISTS case_reminders (
                reminder_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, operation_id TEXT NOT NULL,
                request_hash TEXT NOT NULL, due_at TEXT NOT NULL, action TEXT NOT NULL, state TEXT NOT NULL,
                created_at TEXT NOT NULL, completed_by TEXT, UNIQUE(case_id,operation_id)
            );
            CREATE TABLE IF NOT EXISTS case_followup_notes (
                case_id TEXT NOT NULL, operation_id TEXT NOT NULL, request_hash TEXT NOT NULL,
                statement TEXT NOT NULL, reminder_id TEXT, created_at TEXT NOT NULL, PRIMARY KEY(case_id,operation_id)
            );
        ''')
        columns = {row[1] for row in connection.execute('PRAGMA table_info(payment_events)')}
        for column in ('operation_id', 'request_hash'):
            if column not in columns:
                connection.execute(f'ALTER TABLE payment_events ADD COLUMN {column} TEXT')
        connection.execute('CREATE UNIQUE INDEX IF NOT EXISTS unique_payment_operation '
                           'ON payment_events(case_id, operation_id) WHERE operation_id IS NOT NULL')
    from resolution_store import migrate
    migrate()


def save_case(record):
    record['case_id'] = f'HR-{uuid4().hex.upper()}'
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute('INSERT INTO cases VALUES (?, ?, ?)',
                           (record['case_id'], record['created_at'], json.dumps(record, ensure_ascii=False)))
    return record


def get_case(case_id):
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute('BEGIN')
        row = connection.execute('SELECT record_json FROM cases WHERE case_id = ?', (case_id,)).fetchone()
        if row is None:
            return None
        payments = connection.execute('SELECT event_json FROM payment_events WHERE case_id = ? ORDER BY sequence',
                                      (case_id,)).fetchall()
    record = json.loads(row[0])
    record['follow_up_payments'] = [json.loads(item[0]) for item in payments]
    return record


def append_payment(case_id, payment):
    normalized = dict(payment)
    # Preconditions can change between retries; they are not the payment identity.
    normalized.pop('expected_balance_version', None)
    for optional in ('promise_id','source_id'):
        if normalized.get(optional) is None:
            normalized.pop(optional, None)
    normalized['amount'] = f'{Decimal(payment["amount"]):.2f}'
    operation_id = str(payment['operation_id'])
    request_hash = hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
    with closing(sqlite3.connect(DB_PATH, timeout=15)) as connection, connection:
        connection.execute('BEGIN IMMEDIATE')
        row = connection.execute('SELECT record_json FROM cases WHERE case_id = ?', (case_id,)).fetchone()
        if row is None:
            return None
        previous_request = connection.execute(
            'SELECT request_hash, event_json FROM payment_events WHERE case_id = ? AND operation_id = ?',
            (case_id, operation_id),
        ).fetchone()
        if previous_request:
            if previous_request[0] != request_hash:
                raise PaymentConflict('This operation reference was already used for different payment details.')
            return json.loads(previous_request[1])
        original = json.loads(row[0])
        if payment.get('expected_balance_version'):
            from case_service import read_case_record
            from resolution import balance_version
            if payment['expected_balance_version'] != balance_version(read_case_record(case_id)):
                raise PaymentConflict('The account changed. Review the new balance before confirming this payment.')
        promise_id = payment.get('promise_id')
        if payment.get('source_id') and not connection.execute('SELECT 1 FROM reply_sources WHERE source_id=? AND case_id=?', (payment['source_id'],case_id)).fetchone():
            raise PaymentConflict('This source does not belong to the case.')
        if promise_id:
            promise_row = connection.execute("SELECT payload FROM resolution_events WHERE case_id=? AND event_id=? AND kind='promise_recorded'", (case_id,promise_id)).fetchone()
            if not promise_row:
                raise PaymentConflict('This promise does not belong to the case.')
            promised = Decimal(json.loads(promise_row[0])['amount'])
        from dispute_models import DisputeReconstruction
        revision = connection.execute('SELECT snapshot_json FROM case_revisions WHERE case_id=? ORDER BY version DESC LIMIT 1', (case_id,)).fetchone()
        reconstruction = json.loads(revision[0]) if revision else original['intake'].get('reconstruction')
        if original.get('record_type')=='work_diary' and not reconstruction:
            raise PaymentConflict('Keep diary receipts in their work entries. Confirm which work belongs to a wage case before adding case payments.')
        base_balance = Decimal(original['calculation']['balance'])
        if reconstruction:
            r = DisputeReconstruction.model_validate(reconstruction)
            base_balance = r.earned_total() - r.allocated_total()
        prior_events = [json.loads(item[0]) for item in connection.execute(
            'SELECT event_json FROM payment_events WHERE case_id = ? ORDER BY sequence', (case_id,)
        ).fetchall()]
        amount = Decimal(payment['amount'])
        if payment.get('source_id') and not payment.get('distinct_payment_confirmed'):
            reviewed=connection.execute("SELECT payload FROM resolution_events WHERE case_id=? AND kind='reply_reviewed' ORDER BY sequence DESC",(case_id,)).fetchall()
            matching=next((p for p in (json.loads(row[0]) for row in reviewed) if p.get('source_id')==payment['source_id']),{})
            already_counted=matching.get('advance_already_included')=='yes'
            source=connection.execute('SELECT result FROM reply_sources WHERE case_id=? AND source_id=?',(case_id,payment['source_id'])).fetchone()
            assertions=json.loads(source[0]).get('assertions',[]) if source else []
            if already_counted and any(a['kind']=='claimed_payment' and a.get('amount') and Decimal(a['amount'])==amount for a in assertions):
                raise PossibleDuplicate('You confirmed this claimed advance was already counted. Confirm a separate additional payment before adding this amount again.')
        if promise_id:
            already = sum((Decimal(e['amount']) for e in prior_events if e.get('promise_id') == promise_id),Decimal('0'))
            if already + amount > promised:
                raise PaymentConflict('This would exceed the recorded promise. Confirm a separate additional payment instead.')
        if not payment.get('distinct_payment_confirmed'):
            if reconstruction:
                for item in r.payments:
                    if (item.status == 'received' and item.allocation == 'this_case' and item.worker_confirmed
                            and item.amount == amount and (not item.received_on or not payment.get('received_on')
                            or item.received_on.isoformat() == payment['received_on'])):
                        raise PossibleDuplicate('This may be a payment already included in the reconstructed account. Confirm a distinct new payment before adding it.')
            for event in prior_events:
                if (Decimal(event['amount']) == amount
                        and (event.get('received_on') is None or payment.get('received_on') is None
                             or event.get('received_on') == payment.get('received_on'))
                        and ('unknown' in (event.get('method', 'unknown'), payment.get('method', 'unknown'))
                             or event.get('method') == payment.get('method'))):
                    raise PossibleDuplicate(
                        'A payment with the same amount, date and method is already recorded. '
                        'Ask whether this is the same payment. Only confirm a distinct payment if the worker says it is another payment.'
                    )
        prior_total = sum((Decimal(event['amount']) for event in prior_events), Decimal('0'))
        previous = base_balance - prior_total
        updated = previous - amount
        event = {
            'payment_id': f'PAY-{uuid4().hex.upper()}', 'operation_id': operation_id,
            'recorded_at': datetime.now(timezone.utc).isoformat(), 'source': 'reported_by_worker',
            'amount': f'{amount:.2f}', 'received_on': payment.get('received_on'),
            'method': payment.get('method', 'unknown'),
            'original_statement': payment['original_statement'], 'worker_confirmed': payment['worker_confirmed'],
            'distinct_payment_confirmed': payment.get('distinct_payment_confirmed', False),
            'reminder_id': payment.get('reminder_id'),
            'promise_id': promise_id,
            'source_id': payment.get('source_id'),
            'previous_balance': f'{previous:.2f}', 'updated_balance': f'{updated:.2f}',
            'explanation': f'Worker reported another INR {amount:.2f}. Recorded balance: {previous:.2f} - {amount:.2f} = {updated:.2f}.',
        }
        if payment.get('reminder_id'):
            reminder = connection.execute('SELECT state,completed_by FROM case_reminders WHERE reminder_id=? AND case_id=?',
                                          (payment['reminder_id'],case_id)).fetchone()
            if not reminder or reminder[0] != 'pending':
                raise PaymentConflict('The follow-up reminder is unavailable or already completed.')
            connection.execute("UPDATE case_reminders SET state='completed',completed_by=? WHERE reminder_id=? AND case_id=?",
                               (operation_id,payment['reminder_id'],case_id))
        connection.execute('INSERT INTO payment_events (case_id,event_json,operation_id,request_hash) VALUES (?,?,?,?)',
                           (case_id, json.dumps(event, ensure_ascii=False), operation_id, request_hash))
    return event


initialise_database()
