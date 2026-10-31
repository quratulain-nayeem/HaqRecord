"""Measure fresh-process memory with fictional temporary data and no API calls.

Run `python profile_runtime.py` on the target host. Windows reports working set;
Linux reports resident memory. This is a benchmark, not a memory-limit guarantee.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
from uuid import uuid4

ROOT=Path(__file__).resolve().parent
SCENARIOS=('idle','pin1','pin2','pin4','upload5mb')


def memory():
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(k,ctypes.c_size_t) for k in (
                'peak','current','quota1','quota2','quota3','quota4','pagefile','peak_pagefile','private')]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetCurrentProcess.restype=wintypes.HANDLE
        api=ctypes.WinDLL('psapi',use_last_error=True)
        api.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        result=Counters();result.cb=ctypes.sizeof(result)
        if not api.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(result),result.cb):raise ctypes.WinError()
        current,peak=result.current,result.peak
    else:
        import resource
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
        current=None
        status=Path('/proc/self/status')
        if status.exists():
            for line in status.read_text().splitlines():
                if line.startswith('VmRSS:'):current=int(line.split()[1])*1024
    return {'current_mib':round(current/1024**2,1) if current is not None else None,'peak_mib':round(peak/1024**2,1)}


def probe(scenario):
    with tempfile.TemporaryDirectory(prefix='haq-runtime-profile-') as folder:
        os.environ.update(HAQRECORD_DB_PATH=str(Path(folder)/'cases.db'),HAQRECORD_AUTH_DB_PATH=str(Path(folder)/'auth.db'),
            HAQRECORD_DEMO='true',SESSION_COOKIE_SECURE='false')
        import uvicorn
        from deploy_app import app
        import auth
        idle=memory()
        if scenario.startswith('pin'):
            count=int(scenario[3:]);hashed=auth.PASSWORDS.hash('928371');barrier=Barrier(count)
            def verify(_):barrier.wait();return auth.PASSWORDS.verify('928371',hashed)
            with ThreadPoolExecutor(max_workers=count) as pool:assert all(pool.map(verify,range(count)))
        elif scenario=='upload5mb':
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                result=client.post('/worker/cases',json={'operation_id':str(uuid4()),'pin':'928371','preferred_name':'Fictional profile',
                    'original_statement':'Fictional five days at 1000, 1000 received.','language':'en','pay_basis':'daily','units_worked':5,
                    'rate_per_unit':'1000','payments_received':'1000','consent_to_store':True,'worker_confirmed':True,'adjustments_checked':True})
                result.raise_for_status();csrf=result.json()['session']['csrf_token']
                result=client.post('/worker/workspace/evidence',headers={'X-CSRF-Token':csrf},json={'operation_id':str(uuid4()),
                    'filename':'fictional-profile.txt','mime':'text/plain','content_base64':base64.b64encode(b'x'*(5*1024*1024)).decode(),
                    'description':'Fictional memory profile','fictional':True,'consent_to_store':True})
                result.raise_for_status()
        print(json.dumps({'scenario':scenario,'platform':sys.platform,'deployment':'single process','idle':idle,'after':memory()}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--scenario',choices=SCENARIOS);args=parser.parse_args()
    if args.scenario:probe(args.scenario);return
    for scenario in SCENARIOS:
        result=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--scenario',scenario],cwd=ROOT,
            capture_output=True,text=True,encoding='utf-8',timeout=90)
        if result.returncode:raise SystemExit('Benchmark failed for '+scenario+'\n'+result.stderr)
        print(result.stdout.strip(),flush=True)


if __name__=='__main__':main()
