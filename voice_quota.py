"""Audit verified zero-cost startup failures without deleting request history."""
from datetime import datetime

def ensure_failure_credits(db):
    db.execute('CREATE TABLE IF NOT EXISTS voice_failure_credits (run_id TEXT PRIMARY KEY,requested_at REAL NOT NULL UNIQUE,reason TEXT NOT NULL)')

def credit_verified_failures(db,executions):
    ensure_failure_credits(db)
    credited=0
    for execution in executions:
        # Missing billing/duration is unknown, never free by assumption.
        if execution.get('status')!='failed' or execution.get('conversation_duration') is None or execution.get('total_cost') is None:continue
        try:
            if float(execution['conversation_duration'])!=0 or float(execution['total_cost'])!=0:continue
            stamp=datetime.fromisoformat(execution['created_at'].replace('Z','+00:00')).timestamp()
            run_id=execution.get('id') or execution['execution_id']
        except (ValueError,TypeError,KeyError):continue
        # Accept only an unambiguous request immediately preceding this run.
        candidates=db.execute('SELECT requested_at FROM voice_mints WHERE requested_at BETWEEN ? AND ?',(stamp-5,stamp+1)).fetchall()
        if len(candidates)!=1:continue
        credited+=db.execute('INSERT OR IGNORE INTO voice_failure_credits VALUES (?,?,?)',(run_id,candidates[0][0],'provider_failed_zero_duration_zero_cost')).rowcount
    return credited
