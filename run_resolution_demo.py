"""Isolated fictional demo. No real provider calls, messages or filings."""
import argparse
import base64
import json
import os
import socket
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parent
DEMO=(ROOT/'.tools/demo').resolve()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reset',action='store_true',help='Reset ONLY the isolated fictional databases; stop port 8002 first.')
    parser.add_argument('--seed-only',action='store_true')
    args=parser.parse_args()
    DEMO.mkdir(parents=True,exist_ok=True)
    if args.reset:
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1',8002))==0:raise SystemExit('Stop the fictional demo on port 8002 before resetting it.')
        for name in ('cases.db','auth.db'):
            for suffix in ('','-wal','-shm','-journal'):
                target=(DEMO/(name+suffix)).resolve()
                if target.parent!=DEMO:raise SystemExit('Unsafe reset path')
                target.unlink(missing_ok=True)
        (DEMO/'access.json').unlink(missing_ok=True)
    os.environ.update(HAQRECORD_DB_PATH=str(DEMO/'cases.db'),HAQRECORD_AUTH_DB_PATH=str(DEMO/'auth.db'),
                      HAQRECORD_DEMO='true',SESSION_COOKIE_SECURE='false')
    import database
    import auth
    from main import app
    from fastapi.testclient import TestClient
    access=DEMO/'access.json'
    if not access.exists():
        with TestClient(app) as client:
            response=client.post('/worker/cases',json={'operation_id':str(uuid4()),'pin':'928371','preferred_name':'Fictional Worker',
                'original_statement':'Fictional sample: five days at Rs 1000 per day. Rs 1000 wages already received.',
                'language':'hi','pay_basis':'daily','units_worked':5,'rate_per_unit':'1000','payments_received':'1000',
                'workplace_location':'Hyderabad','employer_name':'Fictional Employer','adjustments_checked':True,
                'worker_confirmed':True,'consent_to_store':True})
            response.raise_for_status();saved=response.json()
            headers={'X-CSRF-Token':saved['session']['csrf_token']}
            for filename,origin in [('employer-message.txt','employer_message'),('sample-acknowledgement.txt','official_correspondence')]:
                source=client.post('/worker/resolution/sources',headers=headers,json={'operation_id':str(uuid4()),'filename':filename,
                    'mime':'text/plain','content_base64':base64.b64encode((ROOT/'demo_fixtures'/filename).read_bytes()).decode(),
                    'origin':origin,'message_date':'2026-10-29' if origin=='employer_message' else '2026-10-31',
                    'language':'hi','fictional':True,'consent_to_store':True})
                source.raise_for_status()
            access.write_text(json.dumps({'case_id':saved['case']['case_id'],'pin':'928371','fictional':True},indent=2),encoding='utf-8')
    info=json.loads(access.read_text(encoding='utf-8'))
    print('FICTIONAL demo only. Separate storage; direct providers and recipient link activation are disabled.')
    print('Open http://127.0.0.1:8002/ and choose Continue my case.')
    print('Fictional reference:',info['case_id'],' Fictional PIN:',info['pin'])
    if not args.seed_only:
        import uvicorn
        uvicorn.run(app,host='127.0.0.1',port=8002,access_log=False)


if __name__=='__main__':main()
