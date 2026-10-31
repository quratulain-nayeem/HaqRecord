"""Monthly rates stay monthly through preview, correction, saving and follow-up."""
import os, sys, tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE']='false'
import httpx
from fastapi.testclient import TestClient
import auth, database, voice_backend as vb
from main import app
from bridge_app import app as bridge_app
from case_models import WageCalculation
from case_service import calculate_wages
from wage_basis import monthly_rate_conflicts

assert not monthly_rate_conflicts('Worked five months at 700 per day','daily')
assert monthly_rate_conflicts('Worked five months, 2000 per month','weekly')
assert monthly_rate_conflicts('Har mahine 2000 milte hain','weekly')
assert monthly_rate_conflicts('हर महीने 2000 रुपये तय थे','weekly')
for basis,units in [('monthly',5),('weekly',5),('daily',5)]:
    c=calculate_wages(WageCalculation(pay_basis=basis,units_worked=units,rate_per_unit='2000',payments_received='8000'))
    assert c['total_earned']=='10000.00' and c['balance']=='2000.00'
    assert {'monthly':'months','weekly':'weeks','daily':'days'}[basis] in c['calculation']

with tempfile.TemporaryDirectory() as folder:
    database.DB_PATH=Path(folder)/'cases.db';auth.AUTH_DB=Path(folder)/'auth.db'
    database.initialise_database();auth.initialize_auth();vb.initialize()
    a=TestClient(app);bridge=TestClient(bridge_app)
    config={'HAQRECORD_VOICE_PUBLIC_URL':'https://example.test','HAQRECORD_VOICE_TOOL_SECRET':'test-service-only'}
    headers={'Authorization':'Bearer test-service-only'}
    with patch('voice_backend.voice.check_agent',return_value={'ready':True,'status':'verified'}),patch('voice_backend.dotenv_values',return_value=config),patch('voice_backend.voice.settings',return_value={'BOLNA_API_KEY':'test','BOLNA_AGENT_ID':'test-agent'}),patch('voice_backend.voice.callback_available',return_value=True),patch('voice_backend.httpx.post',return_value=httpx.Response(200,json={'run_id':'fictional-monthly'})) as mint:
        assert a.post('/voice/intake/session',json={'consent_to_voice_processing':True,'language':'en'}).status_code==200
        token=mint.call_args.kwargs['json']['user_data']['voice_token']
        data={'voice_token':token,'pay_basis':'weekly','units_worked':20,'rate_per_unit':'2000','payments_received':'8000','adjustments_clear':True,'original_statement':'Worked five months at 2000 per month, received 8000.','language':'en','workplace_location':'Hyderabad'}
        # A previously displayed calculation must disappear when a unit conflict arrives.
        old={**data,'original_statement':'Unspecified agreement.'}
        assert bridge.post('/bolna/tools/calculate',json=old,headers=headers).json()['calculation']['balance']=='32000.00'
        rejected=bridge.post('/bolna/tools/calculate',json=data,headers=headers)
        assert rejected.json()['status']=='needs_clarification',rejected.text
        assert a.get('/voice/intake/state').json()['preview'] is None
        data.update(pay_basis='monthly',units_worked=5)
        result=bridge.post('/bolna/tools/calculate',json=data,headers=headers)
        assert result.json()['calculation']['balance']=='2000.00',result.text
        invalid=bridge.post('/bolna/tools/calculate',json={**data,'units_worked':'unclear'},headers=headers)
        assert invalid.status_code==422 and invalid.json()['on_screen'] is False
        assert a.get('/voice/intake/state').json()['preview'] is None
        result=bridge.post('/bolna/tools/calculate',json=data,headers=headers)
        assert result.json()['calculation']['balance']=='2000.00'
        state=a.get('/voice/intake/state').json(); preview=state['preview'];csrf=state['csrf_token']
        assert preview['figures']['pay_basis']=='monthly' and preview['calculation']['units_worked']==5
        approval={'preview_id':preview['preview_id'],'original_statement':data['original_statement'],'preferred_name':'Fictional Raju','approved':True,'language':'en'}
        prepared=a.post('/voice/intake/prepare-preview',json=approval,headers={'X-CSRF-Token':csrf})
        assert prepared.status_code==200,prepared.text
        state=a.get('/voice/intake/state').json()
        saved=a.post('/voice/intake/confirm',json={'draft_id':state['draft_id'],'approved':True,'pin':'684295'},headers={'X-CSRF-Token':csrf})
        assert saved.status_code==200,saved.text
        record=saved.json()['case'];assert record['calculation']['balance']=='2000.00'
        summary=a.get('/worker/workspace/next-step?language=en').json()
        assert 'months' in str(summary) and '2000.00' in str(summary)
        payment=bridge.post('/bolna/tools/prepare-payment',json={'voice_token':token,'amount':'1000','original_statement':'Received a separate 1000 for this case.','worker_confirmed':True,'method':'cash'},headers=headers)
        assert payment.status_code==200,payment.text
        state=a.get('/voice/intake/state').json()
        paid=a.post('/voice/intake/confirm',json={'draft_id':state['draft_id'],'approved':True},headers={'X-CSRF-Token':csrf})
        assert paid.status_code==200,paid.text
        assert paid.json()['case']['calculation']['balance']=='1000.00'
        assert paid.json()['case']['calculation']['pay_basis']=='monthly'
print('PASS: monthly 10000 earned / 8000 received / 2000 outstanding; invalid conversion clears preview; private save and later payment preserve months.')

for file in ['web/assets/worker-flow.js','web/assets/voice-connected.js','web/assets/voice.js']:
    s=Path(file).read_text(encoding='utf-8')
    assert '300000' not in s and 'maxCallSeconds' not in s
print('PASS: no app-imposed five-minute call timer in browser entry points.')
