"""Expose only authenticated Bolna callback routes, never the dashboard/case APIs."""
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from voice_backend import tool_router
from voice_tool_errors import validation_error
from resolution_voice import router as resolution_tool_router

app=FastAPI(title='HaqRecord voice callback bridge',docs_url=None,redoc_url=None,openapi_url=None)
app.include_router(tool_router)
app.include_router(resolution_tool_router)
app.add_exception_handler(RequestValidationError,validation_error)


@app.get('/health')
def health():
    return {'status':'ok'}
