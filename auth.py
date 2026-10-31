"""One local caseworker account, revocable sessions, and service authentication."""
import hashlib
import os
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from pwdlib import PasswordHash

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
AUTH_DB = Path(os.getenv('HAQRECORD_AUTH_DB_PATH') or str(ROOT / 'auth.db'))
COOKIE = 'haqrecord_demo_session' if os.getenv('HAQRECORD_DEMO')=='true' else 'haqrecord_session'
SESSION_SECONDS = 8 * 60 * 60
PASSWORDS = PasswordHash.recommended()  # Argon2id; includes a random salt.
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
router = APIRouter(prefix='/auth', tags=['Authentication'])


def connect():
    return sqlite3.connect(AUTH_DB, timeout=10)


def initialize_auth():
    with closing(connect()) as db, db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS account (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                csrf_token TEXT NOT NULL,
                expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS login_attempts (
                client TEXT PRIMARY KEY,
                attempts INTEGER NOT NULL,
                window_start REAL NOT NULL
            );
        ''')


def provision_account(username, password):
    username = username.strip()
    if not username or len(username) > 100:
        raise ValueError('Username must contain 1 to 100 characters.')
    if len(password) < 12 or len(password) > 128:
        raise ValueError('Use a password between 12 and 128 characters.')
    password_hash = PASSWORDS.hash(password)
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM account').fetchone():
            raise ValueError('An account already exists. Public registration is disabled.')
        db.execute('INSERT INTO account VALUES (1, ?, ?)', (username, password_hash))


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def check_origin(request):
    origin = request.headers.get('origin')
    if origin and origin.rstrip('/') != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Request origin is not allowed')


def browser_session(request):
    token = request.cookies.get(COOKIE, '')
    if not token or len(token) > 256:
        return None
    with closing(connect()) as db:
        row = db.execute(
            'SELECT s.csrf_token, a.username FROM sessions s CROSS JOIN account a '
            'WHERE s.token_hash = ? AND s.expires_at > ? AND a.id = 1',
            (digest(token), time.time()),
        ).fetchone()
    return {'csrf_token': row[0], 'username': row[1]} if row else None


def require_browser(request: Request):
    session = browser_session(request)
    if session is None:
        raise HTTPException(401, 'Caseworker login required')
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        check_origin(request)
        supplied = request.headers.get('x-csrf-token', '')
        if not secrets.compare_digest(supplied, session['csrf_token']):
            raise HTTPException(403, 'Refresh your session before making changes')
    return session


def require_case_access(request: Request):
    supplied = request.headers.get('x-api-key')
    if supplied is not None:
        expected = os.getenv('HAQRECORD_SERVICE_API_KEY', '')
        if not expected or not secrets.compare_digest(digest(supplied), digest(expected)):
            raise HTTPException(401, 'Invalid service credential')
        return {'service': 'bolna'}
    return require_browser(request)


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


@router.post('/login')
def login(data: LoginInput, request: Request, response: Response):
    check_origin(request)
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
        raise HTTPException(415, 'Send login details as JSON')
    now = time.time()
    # Use the actual peer, not an untrusted X-Forwarded-For header.
    client = request.client.host if request.client else 'unknown'
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        attempt = db.execute(
            'SELECT attempts, window_start FROM login_attempts WHERE client = ?', (client,)
        ).fetchone()
        if attempt and attempt[0] >= 5 and now - attempt[1] < 900:
            raise HTTPException(429, 'Too many attempts. Try again in 15 minutes.')
        count, started = (attempt[0], attempt[1]) if attempt and now - attempt[1] < 900 else (0, now)
        db.execute(
            'INSERT OR REPLACE INTO login_attempts VALUES (?, ?, ?)',
            (client, count + 1, started),
        )
        account = db.execute('SELECT username, password_hash FROM account WHERE id = 1').fetchone()
    valid = PASSWORDS.verify(data.password, account[1] if account else DUMMY_HASH)
    if not account or data.username != account[0] or not valid:
        raise HTTPException(401, 'Invalid username or password')
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with closing(connect()) as db, db:
        db.execute('DELETE FROM sessions WHERE expires_at <= ?', (now,))
        old = request.cookies.get(COOKIE)
        if old:
            db.execute('DELETE FROM sessions WHERE token_hash = ?', (digest(old),))
        db.execute('INSERT INTO sessions VALUES (?, ?, ?)',
                   (digest(token), csrf, now + SESSION_SECONDS))
        db.execute('DELETE FROM login_attempts WHERE client = ?', (client,))
    response.set_cookie(
        COOKIE, token, max_age=SESSION_SECONDS, httponly=True,
        secure=os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true',
        samesite='strict', path='/',
    )
    return {'username': account[0], 'csrf_token': csrf}


@router.get('/session')
def session_status(request: Request):
    return require_browser(request)


@router.post('/logout')
def logout(request: Request, response: Response):
    require_browser(request)
    with closing(connect()) as db, db:
        db.execute('DELETE FROM sessions WHERE token_hash = ?',
                   (digest(request.cookies[COOKIE]),))
    response.delete_cookie(COOKIE, path='/', httponly=True, samesite='strict')
    return {'message': 'Signed out'}


initialize_auth()
