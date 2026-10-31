import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intake_progress import intake_progress

notes={'language':'hi','original_statement':'A fictional construction worker in Hyderabad worked a month at Rs 1000 per week; no wages received.',
       'preferred_name':'Fictional Worker','workplace_location':'Hyderabad','pay_basis':'weekly','rate_per_unit':'1000','units_worked':None,'payments_received':'0'}
step=intake_progress(notes)
assert step['next_action']=='ask_work_quantity' and step['next_question']=='आपने कुल कितने हफ़्ते का काम पूरा किया?'
assert '4' not in step['next_question'] and 'पूरी कीजिए' not in step['next_question']
notes['units_worked']=4
notes['unresolved_questions']='How many weeks exactly did you work in that month?'
assert intake_progress(notes)['next_action']=='ask_work_quantity'
notes['unresolved_questions']=''
step=intake_progress(notes)
assert step['next_action']=='calculate_reported_balance' and step['next_question'] is None
assert step['known_figures']['payments_received']=='0'
notes['rate_per_unit']='1500'
assert intake_progress(notes)['next_action']=='calculate_reported_balance'
notes['payments_received']=None
assert intake_progress(notes)['next_action']=='ask_received'
notes['payments_received']='unknown'
assert intake_progress(notes)['next_action']=='ask_received'
notes['payments_received']='0';notes['language']='en';notes['units_worked']=None
assert 'weeks' in intake_progress(notes)['next_question']
print('PASS: accumulated month-duration/weekly-rate story asks exact weeks once; confirmed weeks advance to calculation; zero receipts persist; unknown money is not zero; corrected rate does not restart intake.')
