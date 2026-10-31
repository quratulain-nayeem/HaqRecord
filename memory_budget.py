"""Bound heavy operations without reducing password strength or file limits.

The gates are process-local: deploy ONE server worker for small-memory hosting.
Lightweight case reads and voice callbacks never acquire either gate.
"""
from functools import wraps
from threading import RLock, Semaphore

import anyio

_heavy=RLock()
_uploads=Semaphore(1)
_source_jobs=RLock()


def memory_heavy(function):
    @wraps(function)
    def bounded(*args,**kwargs):
        with _heavy:
            return function(*args,**kwargs)
    return bounded


def single_source_job(function):
    @wraps(function)
    def bounded(*args,**kwargs):
        with _source_jobs:
            return function(*args,**kwargs)
    return bounded


class BoundedPasswordHash:
    """Keep pwdlib/Argon2 parameters and existing hashes completely unchanged."""
    def __init__(self,password_hash):self._hash=password_hash

    @memory_heavy
    def hash(self,*args,**kwargs):return self._hash.hash(*args,**kwargs)

    @memory_heavy
    def verify(self,*args,**kwargs):return self._hash.verify(*args,**kwargs)


class BoundedUploads:
    """Queue big request bodies BEFORE reading them, including background work.

    Non-blocking acquisition avoids tying up the server's thread pool or event
    loop while another upload is running. Cancellation while waiting owns no
    permit; every acquired permit is released even on disconnect or failure.
    """
    paths={'/worker/workspace/evidence','/worker/resolution/sources','/worker/workspace/packet'}

    def __init__(self,app):self.app=app

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope.get('path') not in self.paths:
            return await self.app(scope,receive,send)
        while not _uploads.acquire(blocking=False):
            await anyio.sleep(.02)
        try:
            await self.app(scope,receive,send)
        finally:
            _uploads.release()
