from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from memory_budget import BoundedUploads

from auth import browser_session, require_case_access, router as auth_router
from case_models import CaseCreate, PaymentCreate, WageCalculation
from case_service import calculate_wages, new_case_record, read_case_record
from database import PaymentConflict, PossibleDuplicate, append_payment, save_case
from voice import router as voice_router
from worker import router as worker_router
from voice_backend import browser_router as voice_intake_router
from case_workspace import router as workspace_router
from resolution import router as resolution_router, public_router as recipient_router
import resolution_voice  # Registers browser confirmation before routers are included.

app = FastAPI(title='HaqRecord')
app.add_middleware(BoundedUploads)
UI_ROOT = Path(__file__).resolve().parent / 'web'
from research import router as resource_router
app.include_router(resource_router)
app.include_router(auth_router)
app.include_router(voice_router)
app.include_router(worker_router)
app.include_router(voice_intake_router)
app.include_router(workspace_router)
app.include_router(resolution_router)
app.include_router(recipient_router)
app.mount('/assets', StaticFiles(directory=UI_ROOT / 'assets'), name='assets')


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    if request.url.path in ('/', '/demo', '/login', '/caseworker', '/voice', '/voice-test', '/worker'):
        extra = "connect-src 'self' https: wss:; media-src 'self' blob:; " if request.url.path in ('/','/worker','/voice','/voice-test') else ''
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; " + extra +
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers['Permissions-Policy'] = 'microphone=(self)'
    return response


@app.get('/', include_in_schema=False)
@app.get('/worker', include_in_schema=False)
def worker_page():
    return FileResponse(UI_ROOT / 'worker.html')


@app.get('/demo', include_in_schema=False)
def public_demo():
    return FileResponse(UI_ROOT / 'demo.html')


@app.get('/login', include_in_schema=False)
def login_page():
    return FileResponse(UI_ROOT / 'login.html')


@app.get('/caseworker', include_in_schema=False)
def caseworker_page(request: Request):
    if browser_session(request) is None:
        return RedirectResponse('/login', status_code=303)
    return FileResponse(UI_ROOT / 'caseworker.html')


@app.get('/voice', include_in_schema=False)
def voice_page():
    return FileResponse(UI_ROOT / 'voice-connected.html')


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/calculate')
def calculate(data: WageCalculation):
    return calculate_wages(data)


@app.post('/cases', status_code=201, dependencies=[Depends(require_case_access)])
def create_case(data: CaseCreate):
    return save_case(new_case_record(data))


@app.get('/cases/{case_id}', dependencies=[Depends(require_case_access)])
def read_case(case_id: str):
    record = read_case_record(case_id)
    if record is None:
        raise HTTPException(404, 'Case not found')
    return record


@app.post('/cases/{case_id}/payments', status_code=201, dependencies=[Depends(require_case_access)])
def add_followup_payment(case_id: str, data: PaymentCreate):
    try:
        payment = append_payment(case_id, data.model_dump(mode='json'))
    except PaymentConflict as error:
        raise HTTPException(409, {'code': 'operation_conflict', 'message': str(error)})
    except PossibleDuplicate as error:
        raise HTTPException(409, {'code': 'possible_duplicate', 'message': str(error)})
    if payment is None:
        raise HTTPException(404, 'Case not found')
    return {'payment': payment, 'case': read_case(case_id)}


@app.get('/voice-test', include_in_schema=False)
def legacy_voice_test():
    return FileResponse(UI_ROOT / 'voice.html')
