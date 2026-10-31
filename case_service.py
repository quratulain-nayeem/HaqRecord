from datetime import datetime, timezone
from decimal import Decimal

from case_models import WageCalculation
from database import get_case
from dispute_models import reconstruction_summary


def calculate_wages(data: WageCalculation, additional_received=Decimal('0')):
    earned = data.reconstruction.earned_total() if data.reconstruction else data.rate_per_unit * data.units_worked
    plural={'hourly':'hours','daily':'days','weekly':'weeks','monthly':'months','piece':'pieces'}[data.pay_basis]
    received = data.payments_received + additional_received
    balance = earned - received
    result = {
        'currency': 'INR',
        'pay_basis': data.pay_basis,
        'units_worked': str(data.units_worked) if isinstance(data.units_worked,Decimal) else data.units_worked,
        'rate_per_unit': f'{data.rate_per_unit:.2f}',
        'days_worked': (str(data.units_worked) if isinstance(data.units_worked,Decimal) else data.units_worked) if data.pay_basis == 'daily' else None,
        'daily_rate': f'{data.rate_per_unit:.2f}' if data.pay_basis == 'daily' else None,
        'total_earned': f'{earned:.2f}',
        'payments_received': f'{received:.2f}',
        'balance': f'{balance:.2f}',
        'calculation': (
            f'{data.units_worked} {plural} '
            f'x {data.rate_per_unit:.2f} = {earned:.2f}; '
            f'{earned:.2f} - {received:.2f} = {balance:.2f}'
        ),
        'note': 'Based on confirmed supplied figures, assuming no other adjustments. Not a legal determination.',
    }
    if data.reconstruction:
        result.update(reconstruction_summary(data.reconstruction, additional_received))
        if data.reconstruction.work_periods:
            result['calculation']=' + '.join(f'{p.quantity} {plural} x {p.rate:.2f}' for p in data.reconstruction.work_periods)+f' = {earned:.2f}; minus {received:.2f} received = {balance:.2f}'
        if result['provisional']:
            result['note'] = 'Provisional reported balance before allocating uncertain payments. Promises are not payments. Not a legal finding.'
    return result


def new_case_record(data):
    questions = []
    if not data.employer_name:
        questions.append('Employer or contractor details not yet collected.')
    if not data.workplace_location:
        questions.append('Workplace location not yet collected.')
    questions.extend([
        'Work dates not yet collected.',
        'Safe reminder preferences not yet collected.',
    ])
    if not data.adjustments_checked:
        questions.append('Advance inclusion and deductions not yet checked.')
    return {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'status': 'confirmed_intake',
        'complaint_status': 'not_prepared',
        'source': 'reported_by_worker',
        'intake': data.model_dump(mode='json'),
        'calculation': calculate_wages(data),
        'unresolved_questions': questions,
    }


def read_case_record(case_id):
    record = get_case(case_id)
    if record is None:
        return None
    record['original_calculation'] = dict(record['calculation'])
    intake = dict(record['intake'])
    extra_received = sum(
        (Decimal(event['amount']) for event in record['follow_up_payments']), Decimal('0')
    )
    # A confirmed correction is an append-only revision; original intake stays intact.
    from case_workspace_service import workspace_state
    workspace = workspace_state(case_id, record)
    if record.get('record_type')=='work_diary' and not workspace['reconstruction']:
        record['workspace']=workspace
        record['voice_confirmations']=[]
        return record
    if workspace['reconstruction']:
        r = workspace['reconstruction']
        intake.update(pay_basis=r['pay_basis'],units_worked=r['units_worked'],rate_per_unit=r['rate_per_unit'],
                      payments_received=workspace['allocated_total'],reconstruction=r,days_worked=None,daily_rate=None)
    record['calculation'] = calculate_wages(WageCalculation(**intake), extra_received)
    record['workspace'] = workspace
    if workspace['reminders']:
        record['unresolved_questions']=[q for q in record['unresolved_questions'] if q!='Safe reminder preferences not yet collected.']
    if workspace['pilot_city']:
        record['unresolved_questions']=[q for q in record['unresolved_questions'] if q!='Workplace location not yet collected.']
    record['unresolved_questions'] = list(dict.fromkeys(record['unresolved_questions'] + record['calculation'].get('unresolved_questions', [])))
    record.setdefault('complaint_status', 'not_prepared')
    # Keep a permanent source link even after temporary call capabilities expire.
    import sqlite3
    from contextlib import closing
    import database
    with closing(sqlite3.connect(database.DB_PATH)) as connection:
        has_table = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='voice_confirmations'").fetchone()
        if has_table:
            links = connection.execute('SELECT draft_id,run_id,kind,confirmed_at FROM voice_confirmations WHERE case_id=? ORDER BY confirmed_at', (case_id,)).fetchall()
            record['voice_confirmations'] = [dict(zip(('draft_id','run_id','kind','confirmed_at'), row)) for row in links]
    return record
