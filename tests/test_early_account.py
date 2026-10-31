import os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE']='false'
import httpx
from fastapi.testclient import TestClient
import auth,database,voice_backend as vb
from main import app
from bridge_app import app as bridge_app
with tempfile.TemporaryDirectory(prefix='haq-early-account-') as folder:
 database.DB_PATH=Path(folder)/'cases.db';auth.AUTH_DB=Path(folder)/'auth.db'
 database.initialise_database();auth.initialize_auth();vb.initialize()
 a=TestClient(app);other=TestClient(app);bridge=TestClient(bridge_app)
 config={'HAQRECORD_VOICE_PUBLIC_URL':'https://example.test','HAQRECORD_VOICE_TOOL_SECRET':'isolated-secret'}
 headers={'Authorization':'Bearer isolated-secret'}
 with patch('voice_backend.dotenv_values',return_value=config),patch('voice_backend.voice.settings',return_value={'BOLNA_API_KEY':'test','BOLNA_AGENT_ID':'test-agent'}),patch('voice_backend.voice.callback_available',return_value=True),patch('voice_backend.voice.check_agent',return_value={'ready':True,'status':'verified'}),patch('voice_backend.httpx.post',return_value=httpx.Response(200,json={'run_id':'fictional-early-intake'})) as mint:
  assert a.post('/voice/intake/session',json={'consent_to_voice_processing':True,'language':'hi'}).status_code==200
  token=mint.call_args.kwargs['json']['user_data']['voice_token']
  notes={'voice_token':token,'original_statement':'Fictional worker: weekly agreement, first week paid, later weeks unpaid.','workplace_location':'Hyderabad','pay_basis':'weekly','payments_received':'1000','unresolved_questions':'Total completed weeks still need confirmation.'}
  assert bridge.post('/bolna/tools/capture-account',json=notes).status_code==401
  captured=bridge.post('/bolna/tools/capture-account',json=notes,headers=headers)
  assert captured.status_code==200,captured.text
  assert captured.json()['next_action']=='ask_work_quantity'
  assert captured.json()['next_question']
  state=a.get('/voice/intake/state').json();known=state['notes']
  english=a.get('/voice/intake/state?language=en').json()['notes']
  hindi=a.get('/voice/intake/state?language=hi').json()['notes']
  assert english['next_question'].startswith('How many weeks')
  assert hindi['next_question'].startswith('आपने कुल कितने')
  assert english['original_statement']==hindi['original_statement']==known['original_statement']
  assert a.get('/voice/intake/state').json()['notes']==known
  assert known['original_statement']==notes['original_statement'] and known['units_worked'] is None
  assert not known['worker_confirmed'] and not known['saved']
  assert state['preview'] is None and state['draft'] is None and state['case_id'] is None
  assert other.get('/voice/intake/state').status_code==401
  figures={'voice_token':token,'pay_basis':'weekly','units_worked':4,'rate_per_unit':'1000','payments_received':'1000','adjustments_clear':True,'original_statement':notes['original_statement']}
  assert bridge.post('/bolna/tools/calculate',json=figures,headers=headers).status_code==200
  assert a.get('/voice/intake/state').json()['preview']['calculation']['balance']=='3000.00'
  preview=a.get('/voice/intake/state').json()['preview']
  assert preview['workplace_location']=='Hyderabad'
  assert bridge.post('/bolna/tools/capture-account',json=notes,headers=headers).status_code==200
  assert a.get('/voice/intake/state').json()['preview']['preview_id']==preview['preview_id']
  csrf=a.get('/voice/intake/state').json()['csrf_token']
  proposal=a.post('/voice/intake/prepare-preview',json={
   'preview_id':preview['preview_id'],'preferred_name':'Fictional Worker',
   'original_statement':preview['original_statement'],'approved':True},headers={'X-CSRF-Token':csrf})
  assert proposal.status_code==200,proposal.text
  draft_id=proposal.json()['draft_id']
  assert bridge.post('/bolna/tools/capture-account',json=notes,headers=headers).status_code==200
  state=a.get('/voice/intake/state').json()
  assert state['draft_id']==draft_id and state['state']=='awaiting_browser_approval'
  # A partial retry must not erase the earlier payment or invalidate approval.
  assert bridge.post('/bolna/tools/capture-account',json={
   'voice_token':token,'original_statement':notes['original_statement'],
   'payments_received':None},headers=headers).status_code==200
  assert a.get('/voice/intake/state').json()['draft_id']==draft_id
  corrected=bridge.post('/bolna/tools/capture-account',json={**notes,'units_worked':None,'unresolved_questions':'Worker corrected the period; clarify before calculation.'},headers=headers)
  assert corrected.status_code==200
  state=a.get('/voice/intake/state').json();assert state['preview'] is None and state['draft'] is None
  assert state['notes']['payments_received']=='1000'
  stale=a.post('/voice/intake/confirm',json={'draft_id':draft_id,'approved':True,'pin':'684295'},headers={'X-CSRF-Token':csrf})
  assert stale.status_code==409
  # Calculation may omit account text: the initial spoken account is retained.
  assert bridge.post('/bolna/tools/calculate',json={k:v for k,v in figures.items() if k!='original_statement'},headers=headers).status_code==200
  preview=a.get('/voice/intake/state').json()['preview']
  assert preview['original_statement']==notes['original_statement']
  assert preview['workplace_location']=='Hyderabad'
  revised=bridge.post('/bolna/tools/calculate',json={**figures,'original_statement':'Corrected fictional account, same figures.'},headers=headers)
  assert revised.status_code==200
  updated=a.get('/voice/intake/state').json()['preview']
  assert updated['preview_id']!=preview['preview_id']
  proposal=a.post('/voice/intake/prepare-preview',json={
   'preview_id':updated['preview_id'],'preferred_name':'Fictional Worker',
   'original_statement':updated['original_statement'],'approved':True},headers={'X-CSRF-Token':csrf})
  assert proposal.status_code==200,proposal.text
  commit={'draft_id':proposal.json()['draft_id'],'approved':True,'pin':'684295'}
  saved=a.post('/voice/intake/confirm',json=commit,headers={'X-CSRF-Token':csrf})
  assert saved.status_code==200,saved.text
  assert saved.json()['case']['calculation']['balance']=='3000.00'
  assert a.post('/voice/intake/confirm',json=commit,headers={'X-CSRF-Token':csrf}).json()['case']['case_id']==saved.json()['case']['case_id']
  assert a.post('/worker/login',json={'case_id':saved.json()['case']['case_id'],'pin':'684295'}).status_code==200
  assert a.get('/worker/my-case').json()['calculation']['balance']=='3000.00'
 print('PASS: initial account appears before any calculation, unknown facts stay unknown, notes remain private/unsaved, and corrections invalidate stale figures without erasing earlier payments.')
