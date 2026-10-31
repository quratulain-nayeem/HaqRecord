from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from dispute_models import DisputeReconstruction
from wage_basis import monthly_rate_conflicts


class WageCalculation(BaseModel):
    reconstruction: DisputeReconstruction | None = None
    pay_basis: Literal['hourly', 'daily', 'weekly', 'monthly', 'piece'] = Field(default='daily', description='Confirmed rate unit; never silently convert units.')
    units_worked: int | Decimal | None = Field(default=None, gt=0, le=10000, description='Confirmed quantity in the explicit rate unit; partial periods require confirmation.')
    rate_per_unit: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2, description='Confirmed rupees per day, week or month matching pay_basis exactly.')
    # Compatibility for the original daily-wage API and saved cases.
    days_worked: int | Decimal | None = Field(default=None, gt=0, le=10000)
    daily_rate: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    payments_received: Decimal = Field(ge=0, max_digits=16, decimal_places=2)

    @model_validator(mode='after')
    def resolve_units(self):
        if self.pay_basis != 'daily' and (self.days_worked is not None or self.daily_rate is not None):
            raise ValueError('Use units_worked and rate_per_unit for weekly/monthly wages.')
        if self.units_worked is None:
            self.units_worked = self.days_worked
        if self.rate_per_unit is None:
            self.rate_per_unit = self.daily_rate
        if self.units_worked is None or self.rate_per_unit is None:
            raise ValueError('Provide completed days/weeks/months and the agreed rate.')
        if not (self.reconstruction and self.reconstruction.work_periods) and Decimal(self.units_worked)*self.rate_per_unit != (Decimal(self.units_worked)*self.rate_per_unit).quantize(Decimal('.01')):
            raise ValueError('Confirm an amount without fractional paise.')
        if self.pay_basis == 'daily':
            if self.days_worked is not None and self.days_worked != self.units_worked:
                raise ValueError('Conflicting days worked.')
            if self.daily_rate is not None and self.daily_rate != self.rate_per_unit:
                raise ValueError('Conflicting daily rates.')
            self.days_worked, self.daily_rate = self.units_worked, self.rate_per_unit
        if self.reconstruction:
            r = self.reconstruction
            if (r.pay_basis != self.pay_basis or r.units_worked != self.units_worked
                    or r.rate_per_unit != self.rate_per_unit or r.allocated_total() != self.payments_received):
                raise ValueError('The reported totals must match the reconstruction. Promises and unallocated payments are not received for this case.')
        return self


class CaseCreate(WageCalculation):
    preferred_name: str = Field(min_length=1, max_length=100, pattern=r'\S')
    original_statement: str = Field(min_length=1, max_length=10000, pattern=r'\S')
    language: Literal['hi', 'en'] = 'hi'
    workplace_location: str | None = Field(default=None, max_length=300)
    employer_name: str | None = Field(default=None, max_length=200)
    adjustments_checked: bool = False
    consent_to_store: Literal[True]
    worker_confirmed: Literal[True]

    @model_validator(mode='after')
    def agreement_matches_statement(self):
        if monthly_rate_conflicts(self.original_statement, self.pay_basis):
            raise ValueError('The account mixes rate units or conflicts with the selected unit. Confirm the agreement; never silently convert months to weeks or hours to days.')
        return self


class PaymentCreate(BaseModel):
    expected_balance_version: str | None = Field(default=None,min_length=64,max_length=64)
    promise_id: UUID | None = None
    source_id: UUID | None = None
    reminder_id: UUID | None = None
    operation_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    received_on: date | None = None
    method: Literal['cash', 'transfer', 'unknown'] = 'unknown'
    original_statement: str = Field(min_length=1, max_length=10000, pattern=r'\S')
    worker_confirmed: Literal[True]
    distinct_payment_confirmed: bool = False
