"""Conservative checks for explicitly stated rate units, not work duration."""
import re


def monthly_rate_conflicts(statement, pay_basis):
    # Preserve the existing function name for callers. Durations such as
    # 'worked five months' do not establish a rate unit.
    patterns={'monthly':(
        r'\bper\s+month\b|\bmonthly\s+(?:salary|wages?|rate|pay)\b|'
        r'\b(?:har|prati)\s+mahin[ae]\b|\bek\s+mahine\s+ki\b|'
        r'(?:हर|प्रति)\s+महीने|(?:एक\s+)?महीने\s+की\s+(?:सैलरी|तनख्वाह|मज़दूरी|मजदूरी|\d)|'
        r'मासिक\s+(?:वेतन|सैलरी|दर)'),
        'weekly':r'\bper\s+week\b|\bweekly\s+(?:salary|wages?|rate|pay)\b|हर\s+हफ़्ते|प्रति\s+सप्ताह',
        'daily':r'\bper\s+day\b|\bdaily\s+(?:wages?|rate|pay)\b|प्रति\s+दिन|हर\s+दिन\s+\d',
        'hourly':r'\bper\s+hour\b|\bhourly\s+(?:wages?|rate|pay)\b|प्रति\s+घंट[ाे]|हर\s+घंटे',
        'piece':r'\bper\s+(?:piece|item)\b|\bpiece\s+rate\b|प्रति\s+(?:इकाई|पीस)'}
    explicit={unit for unit,pattern in patterns.items() if re.search(pattern,statement or '',re.I)}
    return len(explicit)>1 or bool(explicit and pay_basis not in explicit)
