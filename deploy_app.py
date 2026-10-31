"""Single-process website + authenticated callbacks for small-memory hosting.

Run with one Uvicorn worker and no development reloader. main:app and
bridge_app:app remain available for the existing split local setup.
"""
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler

from main import app
from voice_backend import tool_router
from resolution_voice import router as resolution_tools
from voice_tool_errors import validation_error

app.include_router(tool_router)
app.include_router(resolution_tools)


async def scoped_validation_error(request,error):
    if request.url.path.startswith('/bolna/tools/'):
        return await validation_error(request,error)
    return await request_validation_exception_handler(request,error)


app.add_exception_handler(RequestValidationError,scoped_validation_error)
