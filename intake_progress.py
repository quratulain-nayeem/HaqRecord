"""Choose one next intake step from accumulated facts, never from a last fragment."""
from decimal import Decimal, InvalidOperation
import re


def quantity_unresolved(notes):
    question=notes.get('unresolved_questions') or ''
    return bool(re.search(r'(?:how\s+many|confirm|clarify|unclear|unknown|not\s+(?:yet\s+)?confirmed).{0,70}(?:weeks?|days?|hours?|months?|quantity|work\s+period)|(?:weeks?|days?|hours?|quantity).{0,40}(?:unclear|unknown|not\s+confirmed)|कितने.{0,30}(?:हफ़्ते|हफ्ते|दिन|घंटे|महीने)|(?:अवधि|हफ़्ते|हफ्ते).{0,30}(?:पुष्टि|स्पष्ट)',question,re.I))


def _money(value,allow_zero=False):
    try:
        number=Decimal(str(value))
        return number.is_finite() and (number>=0 if allow_zero else number>0) and number==number.quantize(Decimal('.01'))
    except (InvalidOperation,TypeError,ValueError):return False


def intake_progress(notes):
    hi=notes.get('language','hi')=='hi'
    basis=notes.get('pay_basis')
    units={'hourly':('घंटे','hours'),'daily':('दिन','days'),'weekly':('हफ़्ते','weeks'),'monthly':('महीने','months'),'piece':('इकाइयां','pieces')}
    if basis not in units:
        return {'next_action':'ask_rate_unit','next_question':'मज़दूरी किस हिसाब से तय हुई थी—दिन, हफ़्ते, महीने या किसी और हिसाब से?' if hi else 'How was your pay agreed: per day, week, month, or another unit?'}
    try:
        quantity=Decimal(str(notes.get('units_worked')))
        quantity_known=quantity.is_finite() and quantity>0
    except (InvalidOperation,TypeError,ValueError):quantity_known=False
    if not quantity_known or quantity_unresolved(notes):
        return {'next_action':'ask_work_quantity','next_question':f'आपने कुल कितने {units[basis][0]} का काम पूरा किया?' if hi else f'How many {units[basis][1]} of work did you complete under that agreement?',
                'instruction':'Ask this one missing detail, then wait. A month of work is not automatically four weeks. Do not ask the worker to finish the story again.'}
    if not _money(notes.get('rate_per_unit')):
        return {'next_action':'ask_rate','next_question':'इस इकाई के हिसाब से कितने रुपये तय हुए थे?' if hi else 'How many rupees were agreed per unit?'}
    if not _money(notes.get('payments_received'),allow_zero=True):
        return {'next_action':'ask_received','next_question':'इस काम के अब तक कुल कितने रुपये वास्तव में मिले हैं?' if hi else 'How much money have you actually received for this work so far?'}
    return {'next_action':'calculate_reported_balance','next_question':None,
            'instruction':'Core wage figures are known. Use the calculation tool after any genuinely unresolved advance/deduction clarification. Do not ask already answered questions or wait for a special story-finished phrase.',
            'known_figures':{key:notes[key] for key in ('pay_basis','units_worked','rate_per_unit','payments_received')}}
