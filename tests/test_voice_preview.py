import os,sys,tempfile
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE']='false'
import httpx
from fastapi.testclient import TestClient
import auth,database,voice_backend as vb
from main import app
from bridge_app import app as bridge_app

with tempfile.TemporaryDirectory(prefix='haq-preview-') as folder:
 database.DB_PATH=Path(folder)/'cases.db';auth.AUTH_DB=Path(folder)/'auth.db'
 database.initialise_database();auth.initialize_auth();vb.initialize()
 a=TestClient(app);other=TestClient(app);bridge=TestClient(bridge_app)
 config={'HAQRECORD_VOICE_PUBLIC_URL':'https://example.test','HAQRECORD_VOICE_TOOL_SECRET':'test-service-only'}
 headers={'Authorization':'Bearer test-service-only'}
 with patch('voice_backend.voice.check_agent',return_value={'ready':True,'status':'verified'}),patch('voice_backend.dotenv_values',return_value=config),patch('voice_backend.voice.settings',return_value={'BOLNA_API_KEY':'test','BOLNA_AGENT_ID':'test-agent'}),patch('voice_backend.voice.callback_available',return_value=True),patch('voice_backend.httpx.post',return_value=httpx.Response(200,json={'run_id':'fictional-preview-run'})) as mint:
  with patch('voice_backend.voice.check_agent',return_value={'ready':False,'status':'configuration_changed'}):
   assert a.post('/voice/intake/session',json={'consent_to_voice_processing':True,'language':'en'}).status_code==503
   assert mint.call_count==0
  import time
  with closing(auth.connect()) as db,db:
   db.execute('CREATE TABLE IF NOT EXISTS voice_mints (requested_at REAL NOT NULL)')
   db.executemany('INSERT INTO voice_mints VALUES (?)',[(time.time(),)]*100)
  # Old quota rows, immediate retries, and more than ten requests from the same
  # browser/IP must not hit an app-imposed voice-attempt restriction.
  for attempt in range(12):
   started=a.post('/voice/intake/session',json={'consent_to_voice_processing':True,'language':'en'})
   assert started.status_code==200,started.text
  print('PASS: 12 immediate voice requests accepted despite 100 existing recent requests; provider mocked, no real calls.')
  assert mint.call_args.kwargs['json']['agent_data']=={'language':'en'}
  token=mint.call_args.kwargs['json']['user_data']['voice_token']
  csrf=a.get('/voice/intake/state').json()['csrf_token']
  figures={'voice_token':token,'pay_basis':'weekly','units_worked':4,'rate_per_unit':'1000','payments_received':'1000','adjustments_clear':True,'original_statement':'Fictional account: worked four weeks at 1000 and received 1000.','workplace_location':'Hyderabad','language':'en'}
  assert bridge.post('/bolna/tools/calculate',json=figures,headers=headers).status_code==200
  assert bridge.post('/bolna/tools/next-step',json={'voice_token':token,'language':'hi'},headers=headers).status_code==200
  original=a.get('/voice/intake/state').json()
  english=a.get('/voice/intake/state?language=en').json()
  hindi=a.get('/voice/intake/state?language=hi').json()
  assert english['next_step']['title']=='What can you do next?'
  assert hindi['next_step']['title']=='अब क्या कर सकते हैं?'
  assert english['preview']==original['preview']==hindi['preview']
  assert a.get('/voice/intake/state').json()['next_step']==original['next_step']
  assert a.get('/voice/intake/state?language=unknown').status_code==422
  print('PASS: Hindi/English guidance follows display language without changing original account, figures, stored next step or voice language.')
  state=a.get('/voice/intake/state').json();preview=state['preview']
  assert preview['calculation']['balance']=='3000.00' and not preview['saved']
  assert state['draft'] is None and state['case_id'] is None
  assert preview['original_statement']==figures['original_statement']
  assert other.get('/voice/intake/state').status_code==401
  approved={'preview_id':preview['preview_id'],'original_statement':preview['original_statement'],'preferred_name':'Fictional test','approved':True,'language':'en'}
  assert a.post('/voice/intake/prepare-preview',json=approved).status_code==403
  security={'X-CSRF-Token':csrf}
  assert a.post('/voice/intake/prepare-preview',json={**approved,'preview_id':str(uuid4())},headers=security).status_code==409
  assert a.post('/voice/intake/prepare-preview',json={**approved,'approved':False},headers=security).status_code==422
  proposal=a.post('/voice/intake/prepare-preview',json=approved,headers=security)
  assert proposal.status_code==200,proposal.text
  assert a.get('/voice/intake/state').json()['case_id'] is None
  commit={'draft_id':proposal.json()['draft_id'],'approved':True,'pin':'684295'}
  saved=a.post('/voice/intake/confirm',json=commit,headers=security)
  assert saved.status_code==200,saved.text
  assert saved.json()['case']['calculation']['balance']=='3000.00'
  again=a.post('/voice/intake/confirm',json=commit,headers=security)
  assert again.status_code==200 and again.json()['case']['case_id']==saved.json()['case']['case_id']
  print('PASS: first calculation appears before prepare_case; worker can save it with private PIN and explicit approval; retries do not create another case.')
  b=TestClient(app)
  with closing(auth.connect()) as db,db:db.execute('DELETE FROM voice_mints')
  assert b.post('/voice/intake/session',json={'consent_to_voice_processing':True,'language':'hi'}).status_code==200
  token=mint.call_args.kwargs['json']['user_data']['voice_token'];figures['voice_token']=token
  bridge.post('/bolna/tools/calculate',json=figures,headers=headers)
  previous=b.get('/voice/intake/state').json();old=previous['preview']['preview_id'];csrf=previous['csrf_token']
  bridge.post('/bolna/tools/calculate',json={**figures,'units_worked':3},headers=headers)
  assert b.post('/voice/intake/prepare-preview',json={**approved,'preview_id':old},headers={'X-CSRF-Token':csrf}).status_code==409
  bridge.post('/bolna/tools/calculate',json={**figures,'adjustments_clear':False},headers=headers)
  state=b.get('/voice/intake/state').json();assert state['preview'] is None and state['draft'] is None
  print('PASS: stale revisions cannot save outdated figures; newly unresolved adjustments clear the earlier preview.')
