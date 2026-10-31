"""Worker-reported reconstruction, with money received separate from promises."""
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReportedPayment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    payment_id: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    status: Literal['received', 'promised']
    allocation: Literal['this_case', 'other_job', 'reimbursement', 'unresolved'] = 'unresolved'
    worker_confirmed: bool = False
    received_on: date | None = None
    method: Literal['cash', 'transfer', 'unknown'] = 'unknown'
    statement: str = Field(min_length=1, max_length=2000)
    source_ids: list[str] = Field(default_factory=list, max_length=10)


class WorkPeriod(BaseModel):
    model_config=ConfigDict(extra='forbid')
    quantity: Decimal=Field(gt=0,max_digits=10,decimal_places=3)
    rate: Decimal=Field(gt=0,max_digits=12,decimal_places=2)
    description: str=Field(min_length=1,max_length=1000)
    source_ids: list[str]=Field(default_factory=lambda:['worker_account'],max_length=10)
    worker_confirmed: Literal[True]

    @model_validator(mode='after')
    def exact_paise(self):
        if self.quantity*self.rate != (self.quantity*self.rate).quantize(Decimal('.01')):raise ValueError('Confirm amounts without fractional paise.')
        if any(len(s)>100 for s in self.source_ids):raise ValueError('Source reference too long.')
        return self


class DisputeReconstruction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pay_basis: Literal['hourly', 'daily', 'weekly', 'monthly', 'piece']
    units_worked: int | Decimal = Field(gt=0, le=10000)
    rate_per_unit: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payments: list[ReportedPayment] = Field(default_factory=list, max_length=50)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=20)
    fact_sources: dict[str, list[str]] = Field(default_factory=dict, max_length=10)
    work_periods: list[WorkPeriod]=Field(default_factory=list,max_length=30)

    @model_validator(mode='after')
    def unique_payments(self):
        ids = [p.payment_id for p in self.payments]
        if len(ids) != len(set(ids)):
            raise ValueError('Each payment needs its own stable identifier; do not repeat a payment.')
        if self.work_periods:
            if sum((p.quantity for p in self.work_periods),Decimal(0))!=self.units_worked:raise ValueError('Confirm quantities in the same explicit unit; do not convert months to weeks.')
            if self.rate_per_unit!=self.work_periods[0].rate:raise ValueError('Keep the first confirmed rate; do not invent an average rate.')
        elif Decimal(self.units_worked)*self.rate_per_unit != (Decimal(self.units_worked)*self.rate_per_unit).quantize(Decimal('.01')):
            raise ValueError('Confirm amounts without fractional paise.')
        if any(len(q) > 2000 for q in self.unresolved_questions):
            raise ValueError('An unresolved question is too long.')
        if any(k not in ('rate_per_unit', 'units_worked', 'pay_basis', 'workplace_location', 'employer_name')
               or len(v) > 10 or any(len(s) > 100 for s in v) for k, v in self.fact_sources.items()):
            raise ValueError('Use supported fact names and at most ten source references per fact.')
        return self

    def earned_total(self):
        return sum((p.quantity*p.rate for p in self.work_periods),Decimal(0)) if self.work_periods else Decimal(self.units_worked)*self.rate_per_unit

    def allocated_total(self):
        return sum((p.amount for p in self.payments if p.status == 'received'
                    and p.allocation == 'this_case' and p.worker_confirmed), Decimal('0'))


def reconstruction_summary(data: DisputeReconstruction, additional_received=Decimal('0')):
    earned = data.earned_total()
    received = data.allocated_total() + additional_received
    pending = [p for p in data.payments if p.status == 'received'
               and (p.allocation not in ('other_job','reimbursement') or not p.worker_confirmed) and not (p.allocation == 'this_case' and p.worker_confirmed)]
    unallocated = sum((p.amount for p in pending), Decimal('0'))
    promised = sum((p.amount for p in data.payments if p.status == 'promised'
                    and p.allocation not in ('other_job','reimbursement')), Decimal('0'))
    questions = [f'Was the INR {p.amount:.2f} {p.method if p.method != "unknown" else "received"} payment for this job or another job? Confirm its allocation.'
                 for p in pending]
    questions_hi = [f'₹{p.amount:.2f} का भुगतान इसी काम का था या दूसरे काम का? कृपया पुष्टि करें।' for p in pending]
    questions += data.unresolved_questions
    return {
        'total_earned': f'{earned:.2f}', 'payments_received': f'{received:.2f}',
        'balance': f'{earned - received:.2f}', 'unallocated_received': f'{unallocated:.2f}',
        'promised_amount': f'{promised:.2f}', 'balance_if_unallocated_applies': f'{earned - received - unallocated:.2f}',
        'provisional': bool(questions), 'unresolved_questions': questions,
        'next_question': questions[0] if questions else None,
        'next_question_hi': questions_hi[0] if questions_hi else None,
        'payment_items': [p.model_dump(mode='json') for p in data.payments],
        'work_periods': [p.model_dump(mode='json') for p in data.work_periods],
    }
