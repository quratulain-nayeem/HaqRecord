"""Memory admission, unchanged Argon2, cancellation and streamed packet checks."""
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import io
import os
from pathlib import Path
import sys
import tempfile
import time
from threading import Barrier, Event, Lock
from unittest.mock import patch
from uuid import uuid4
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import anyio
from pwdlib import PasswordHash
from memory_budget import BoundedPasswordHash,BoundedUploads,memory_heavy

class SlowHasher:
    def __init__(self):self.active=0;self.peak=0;self.lock=Lock();self.release=Event();self.entered=Event()
    def verify(self,*args):
        with self.lock:self.active+=1;self.peak=max(self.peak,self.active)
        self.entered.set();assert self.release.wait(5)
        with self.lock:self.active-=1
        return True
    hash=verify

fake=SlowHasher();bounded=BoundedPasswordHash(fake);barrier=Barrier(4)
@memory_heavy
def extraction():return fake.verify()
def job(index):barrier.wait();return extraction() if index==3 else bounded.verify('x','y')
with ThreadPoolExecutor(max_workers=4) as pool:
    jobs=[pool.submit(job,i) for i in range(4)]
    assert fake.entered.wait(3)
    time.sleep(.08) # Let all contenders try while the first operation is held.
    assert fake.active==1 and fake.peak==1
    fake.release.set();assert all(j.result(timeout=5) for j in jobs)
assert fake.peak==1
native=PasswordHash.recommended();passwords=BoundedPasswordHash(native)
old=native.hash('fictional-pin');new=passwords.hash('fictional-pin')
assert old.split('$')[1:4]==new.split('$')[1:4]
assert passwords.verify('fictional-pin',old) and native.verify('fictional-pin',new)
with patch.object(native,'verify',side_effect=RuntimeError('fictional failure')):
    try:passwords.verify('x','y');raise AssertionError('Expected failure')
    except RuntimeError:pass
with ThreadPoolExecutor(max_workers=1) as pool:assert pool.submit(passwords.verify,'fictional-pin',old).result(timeout=3)
print('PASS: PIN checks and extraction share one memory slot; original Argon2 parameters and hashes remain valid; exceptions release the slot.')

async def check_upload_gate():
    entered=anyio.Event();release=anyio.Event();waiter_ready=anyio.Event();waiter_done=anyio.Event();calls=[];cancel=[]
    async def app(scope,receive,send):
        calls.append(scope['name'])
        if scope['name']=='first':entered.set();await release.wait();raise ValueError('fictional upload failure')
    middleware=BoundedUploads(app)
    async def invoke(name,path='/worker/workspace/evidence'):
        try:await middleware({'type':'http','path':path,'name':name},None,None)
        except ValueError:pass
    async def waiter():
        with anyio.CancelScope() as scope:
            cancel.append(scope);waiter_ready.set();await invoke('cancelled')
        waiter_done.set()
    async with anyio.create_task_group() as tasks:
        tasks.start_soon(invoke,'first');await entered.wait()
        tasks.start_soon(waiter);await waiter_ready.wait();await anyio.sleep(.04)
        assert calls==['first'] # Waiting upload body has not reached the application.
        await invoke('voice','/bolna/tools/guide-section');assert calls==['first','voice']
        cancel[0].cancel();await waiter_done.wait();release.set()
    await invoke('after-failure');assert calls==['first','voice','after-failure']
anyio.run(check_upload_gate)
print('PASS: large uploads queue before body reading; voice stays available; cancelled waiters and failed uploads leak no permit.')

os.environ['SESSION_COOKIE_SECURE']='false'
with tempfile.TemporaryDirectory(prefix='haq-memory-regression-') as folder:
    os.environ.update(HAQRECORD_DB_PATH=str(Path(folder)/'cases.db'),HAQRECORD_AUTH_DB_PATH=str(Path(folder)/'auth.db'))
    import auth,database,voice_backend
    from fastapi.testclient import TestClient
    from deploy_app import app
    import case_workspace
    client=TestClient(app);stranger=TestClient(app)
    saved=client.post('/worker/cases',json={'operation_id':str(uuid4()),'pin':'928371','preferred_name':'Fictional worker',
        'original_statement':'Fictional five days at 1000; 1000 received.','language':'en','pay_basis':'daily','units_worked':5,
        'rate_per_unit':'1000','payments_received':'1000','consent_to_store':True,'worker_confirmed':True,'adjustments_checked':True}).json()
    csrf={'X-CSRF-Token':saved['session']['csrf_token']}
    content=base64.b64encode(os.urandom(1536*1024)) # Valid UTF-8, incompressible enough to roll a ZIP to disk.
    response=client.post('/worker/workspace/evidence',headers=csrf,json={'operation_id':str(uuid4()),'filename':'fictional-large.txt',
        'mime':'text/plain','content_base64':base64.b64encode(content).decode(),'description':'Fictional stream test','fictional':True,'consent_to_store':True})
    assert response.status_code==201,response.text
    factory=case_workspace.tempfile.SpooledTemporaryFile;buffers=[]
    def spool(*args,**kwargs):value=factory(*args,**kwargs);buffers.append(value);return value
    with patch('case_workspace.tempfile.SpooledTemporaryFile',side_effect=spool):response=client.get('/worker/workspace/packet')
    assert response.status_code==200 and len(response.content)==int(response.headers['content-length'])
    assert buffers[0]._rolled and buffers[0].closed
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        original=next(n for n in archive.namelist() if n.startswith('supporting-material/'))
        assert archive.read(original)==content
        assert {'case-packet.html','case-record.json','resolution-report.html','help-summary.txt'}<=set(archive.namelist())
    assert stranger.get('/worker/workspace/packet').status_code==401
    paths={path for path in app.openapi()['paths'] if path.startswith('/bolna/tools/')}
    assert '/bolna/tools/guide-section' in paths and '/bolna/tools/prepare-case' in paths
    with patch('voice_backend.dotenv_values',return_value={'HAQRECORD_VOICE_TOOL_SECRET':'fictional-low-memory-secret'}):
        for path in paths:
            result=client.post(path,json={});assert result.status_code==401,(path,result.status_code)
        result=client.post('/bolna/tools/calculate',headers={'Authorization':'Bearer fictional-low-memory-secret'},json={})
        assert result.status_code==422 and result.json()['saved'] is False
    assert client.get('/health').status_code==200
    print('PASS: ZIP rolls to disk and closes; all originals and reports survive; access checks remain; combined deployment serves authenticated callbacks and safe validation errors.')
