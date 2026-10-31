"""Private case workspace: source records, corrections and in-app follow-ups."""
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

import database
from dispute_models import DisputeReconstruction, reconstruction_summary


def now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def workspace_state(case_id, record):
    with closing(sqlite3.connect(database.DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        revisions = [dict(r) for r in db.execute('SELECT version,snapshot_json,reason,created_at FROM case_revisions WHERE case_id=? ORDER BY version', (case_id,))]
        sources = [dict(r) for r in db.execute('SELECT source_id,filename,mime,sha256,description,fictional,created_at FROM case_evidence WHERE case_id=? ORDER BY created_at', (case_id,))]
        annotations = [dict(r) for r in db.execute('SELECT annotation_json,created_at FROM case_fact_sources WHERE case_id=? ORDER BY created_at', (case_id,))]
        reminders = [dict(r) for r in db.execute('SELECT reminder_id,due_at,action,state,created_at,completed_by FROM case_reminders WHERE case_id=? ORDER BY due_at', (case_id,))]
        notes = [dict(r) for r in db.execute('SELECT statement,reminder_id,created_at FROM case_followup_notes WHERE case_id=? ORDER BY created_at', (case_id,))]
    snapshot = json.loads(revisions[-1]['snapshot_json']) if revisions else record['intake'].get('reconstruction')
    allocated = DisputeReconstruction.model_validate(snapshot).allocated_total() if snapshot else Decimal(str(record['intake']['payments_received']))
    source_ids = {s['source_id'] for s in sources}
    facts = []
    for key, value in [('rate_per_unit', snapshot['rate_per_unit'] if snapshot else record['intake']['rate_per_unit']),
                       ('units_worked', snapshot['units_worked'] if snapshot else record['intake']['units_worked'])]:
        refs = (snapshot or {}).get('fact_sources', {}).get(key, []) or ['worker_account']
        facts.append({'fact': key, 'value': str(value), 'source_ids': refs,
                      'status': 'worker_reported', 'unresolved': 'Supporting material is not independently verified.' if any(x in source_ids for x in refs) else 'No supporting document linked.'})
    latest_annotations={}
    for a in annotations:
        value={**json.loads(a['annotation_json']),'created_at':a['created_at']}
        latest_annotations[(value['fact'],value['source_id'])]=value
    facts += list(latest_annotations.values())
    for source in sources:
        source['status'] = 'supplied_supporting_material_not_verified'
        source['fictional'] = bool(source['fictional'])
    timeline = [{'at': record['created_at'], 'kind': 'intake', 'description': record['intake']['original_statement']}]
    timeline += [{'at': r['created_at'], 'kind': 'correction', 'description': r['reason'], 'version': r['version']} for r in revisions]
    timeline += [{'at': s['created_at'], 'kind': 'evidence', 'description': s['filename'], 'source_id': s['source_id']} for s in sources]
    timeline += [{'at': a['created_at'],'kind':'source_note','description':json.loads(a['annotation_json'])['value']} for a in annotations]
    timeline += [{'at': p['recorded_at'], 'kind': 'payment', 'description': p['explanation']} for p in record.get('follow_up_payments', [])]
    timeline += [{'at': n['created_at'], 'kind': 'follow_up', 'description': n['statement']} for n in notes]
    for reminder in reminders:
        reminder['due'] = reminder['state'] == 'pending' and datetime.fromisoformat(reminder['due_at']) <= datetime.now(timezone.utc)
        reminder['channel'] = 'in_app_only'
        timeline.append({'at':reminder['created_at'],'kind':'reminder','description':'In-app reminder: '+reminder['action']})
    city = (record['intake'].get('workplace_location') or '').lower()
    city_notes=[f for f in latest_annotations.values() if f['fact']=='workplace_location' and f.get('worker_confirmed')]
    if city_notes:city=max(city_notes,key=lambda f:f['created_at'])['value'].lower()
    pilot_city = 'hyderabad' if 'hyderabad' in city else 'bengaluru' if 'bengaluru' in city or 'bangalore' in city else None
    questions = reconstruction_summary(DisputeReconstruction.model_validate(snapshot))['unresolved_questions'] if snapshot else []
    questions += [f['unresolved'] for f in facts if f.get('unresolved') and f.get('worker_confirmed') is False]
    if questions:question=questions[0]
    elif any(r['due'] for r in reminders):question='Has any money arrived for this case since the last update?'
    elif not pilot_city:question='Where did you work: Hyderabad or Bengaluru?'
    elif not sources:question='Do you have a message, payment record or attendance record to link to this account?'
    else:question=f'Would you like to check the official support sources for {pilot_city.title()}?'
    question_hi = (reconstruction_summary(DisputeReconstruction.model_validate(snapshot)).get('next_question_hi') if snapshot else None)
    if not question_hi:
        if questions:question_hi=question
        elif any(r['due'] for r in reminders):question_hi='पिछली जानकारी के बाद क्या इस मामले के कुछ पैसे मिले हैं?'
        elif not pilot_city:question_hi='काम कहाँ किया: हैदराबाद या बेंगलुरु?'
        elif not sources:question_hi='क्या इस खाते से जोड़ने के लिए कोई संदेश, भुगतान या हाज़िरी का रिकॉर्ड है?'
        else:question_hi='क्या आप अपने काम के शहर के आधिकारिक सहायता स्रोत देखना चाहते/चाहती हैं?'
    return {'version': len(revisions), 'reconstruction': snapshot, 'allocated_total': str(allocated),
            'sources': sources, 'facts': facts, 'reminders': reminders, 'timeline': sorted(timeline,key=lambda e:e['at']),
            'next_question': question, 'next_question_hi':question_hi, 'pilot_city': pilot_city, 'outbound_calls_enabled': False}


def remember_work_city(case_id, city):
    """Append a confirmed city learned during resource lookup; retain original intake."""
    value='Hyderabad' if city=='hyderabad' else 'Bengaluru'
    with closing(sqlite3.connect(database.DB_PATH,timeout=15)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT annotation_json FROM case_fact_sources WHERE case_id=? ORDER BY created_at DESC',(case_id,)).fetchall()
        latest=next((json.loads(row[0]) for row in old if json.loads(row[0]).get('fact')=='workplace_location' and json.loads(row[0]).get('worker_confirmed')),None)
        if latest and latest['value']==value:return
        note={'fact':'workplace_location','value':value,'source_id':'worker_account','worker_confirmed':True,
              'unresolved':'','status':'worker_reported_not_independently_verified'}
        db.execute('INSERT INTO case_fact_sources VALUES (?,?,?,?,?)',(case_id,str(uuid4()),fingerprint(note),json.dumps(note),now()))


def validate_sources(db, case_id, snapshot):
    refs = {s for p in snapshot.payments for s in p.source_ids}
    refs.update(s for values in snapshot.fact_sources.values() for s in values)
    refs.update(s for p in snapshot.work_periods for s in p.source_ids)
    for source in refs - {'worker_account'}:
        if db.execute('SELECT 1 FROM reply_sources WHERE case_id=? AND source_id=?',(case_id,source)).fetchone():continue
        if source.startswith('diary:'):
            if db.execute("SELECT 1 FROM resolution_events WHERE case_id=? AND event_id=? AND kind='diary_recorded'",(case_id,source[6:])).fetchone():continue
        if not db.execute('SELECT 1 FROM case_evidence WHERE case_id=? AND source_id=?', (case_id,source)).fetchone():
            raise HTTPException(422, 'A source reference does not belong to this case.')


def apply_revision(case_id, snapshot, expected_version, operation_id, reason):
    body = {'snapshot': snapshot.model_dump(mode='json'), 'expected_version': expected_version, 'reason': reason}
    digest = fingerprint(body)
    with closing(sqlite3.connect(database.DB_PATH,timeout=15)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT request_hash,version FROM case_revisions WHERE case_id=? AND operation_id=?', (case_id,str(operation_id))).fetchone()
        if old:
            if old[0] != digest:raise HTTPException(409,'This operation was already used for different facts.')
            return old[1]
        if not db.execute('SELECT 1 FROM cases WHERE case_id=?',(case_id,)).fetchone():raise HTTPException(404,'Case not found')
        version = db.execute('SELECT COALESCE(MAX(version),0) FROM case_revisions WHERE case_id=?',(case_id,)).fetchone()[0]
        if version != expected_version:raise HTTPException(409,'The case changed. Reload and review the current version before confirming.')
        validate_sources(db,case_id,snapshot)
        db.execute('INSERT INTO case_revisions VALUES (?,?,?,?,?,?,?)',
                   (case_id,version+1,str(operation_id),digest,json.dumps(body['snapshot'],ensure_ascii=False),reason,now()))
    return version+1


def safe_filename(value):
    return re.sub(r'[^a-zA-Z0-9._-]', '_', value.replace('\\','/').split('/')[-1])[:100] or 'evidence'


def save_evidence(case_id, operation_id, filename, mime, content, description, fictional):
    digest = hashlib.sha256(content).hexdigest()
    with closing(sqlite3.connect(database.DB_PATH,timeout=15)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT source_id,sha256,filename,mime,description,fictional FROM case_evidence WHERE case_id=? AND operation_id=?',(case_id,str(operation_id))).fetchone()
        if old:
            if tuple(old[1:]) != (digest,safe_filename(filename),mime,description,int(fictional)):
                raise HTTPException(409,'The upload reference was already used for different material.')
            return old[0]
        size,count = db.execute('SELECT COALESCE(SUM(length(content)),0),COUNT(*) FROM case_evidence WHERE case_id=?',(case_id,)).fetchone()
        if size+len(content)>20*1024*1024 or count>=30:raise HTTPException(413,'This case has reached its evidence storage limit (20 MB / 30 files).')
        source_id = 'SRC-'+uuid4().hex
        db.execute('INSERT INTO case_evidence VALUES (?,?,?,?,?,?,?,?,?,?)',
                   (source_id,case_id,str(operation_id),safe_filename(filename),mime,content,digest,description,int(fictional),now()))
    return source_id
