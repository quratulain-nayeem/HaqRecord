import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import time
from uuid import uuid4
from contextlib import closing

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE'] = 'false'
test_key = secrets.token_urlsafe(48)
os.environ['HAQRECORD_SERVICE_API_KEY'] = test_key

import auth
import database
from main import app
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory(prefix='haqrecord-auth-test-') as temporary:
    auth.AUTH_DB = Path(temporary) / 'auth.db'
    database.DB_PATH = Path(temporary) / 'cases.db'
    auth.initialize_auth()
    database.initialise_database()
    password = secrets.token_urlsafe(24)
    auth.provision_account('test-caseworker', password)
    try:
        auth.provision_account('another-user', password)
        raise AssertionError('A second account was permitted')
    except ValueError:
        pass

    with TestClient(app) as client:
        for route in ('/', '/demo', '/login'):
            assert client.get(route).status_code == 200
        for route in ('/assets/site.css', '/assets/demo.js', '/assets/login.js'):
            assert client.get(route).status_code == 200
        assert client.get('/caseworker', follow_redirects=False).status_code == 303
        assert client.get('/cases/HR-PRIVATE').status_code == 401
        payload = {
            'days_worked': 8, 'daily_rate': 800, 'payments_received': 2500,
            'preferred_name': 'Isolated Test', 'original_statement': 'Fictional test account.',
            'consent_to_store': True, 'worker_confirmed': True,
        }
        assert client.post('/cases', json=payload).status_code == 401
        assert client.post('/cases/HR-PRIVATE/payments', json={
            'operation_id': str(uuid4()), 'amount': 1000, 'original_statement': 'Received payment.', 'worker_confirmed': True,
        }).status_code == 401
        calc = client.post('/calculate', json={
            'days_worked': 8, 'daily_rate': 800, 'payments_received': 2500,
        })
        assert calc.status_code == 200 and calc.json()['balance'] == '3900.00'
        with closing(sqlite3.connect(database.DB_PATH)) as db:
            assert db.execute('SELECT COUNT(*) FROM cases').fetchone()[0] == 0
        print('PASS: public demo works without login; all saved-case routes reject anonymous access.')

        credentials = {'username': 'test-caseworker', 'password': password}
        assert client.post('/auth/login', json=credentials,
                           headers={'Origin': 'https://evil.example'}).status_code == 403
        assert client.post('/auth/login', json={**credentials, 'password': 'wrong'}).status_code == 401
        signed_in = client.post('/auth/login', json=credentials)
        assert signed_in.status_code == 200
        cookie_header = signed_in.headers['set-cookie'].lower()
        assert 'httponly' in cookie_header and 'samesite=strict' in cookie_header
        csrf = signed_in.json()['csrf_token']
        token = client.cookies.get(auth.COOKIE)
        with closing(sqlite3.connect(auth.AUTH_DB)) as db:
            hashed_password = db.execute('SELECT password_hash FROM account').fetchone()[0]
            stored_token = db.execute('SELECT token_hash FROM sessions').fetchone()[0]
        assert hashed_password.startswith('$argon2id$') and password not in hashed_password
        assert stored_token == auth.digest(token) and stored_token != token
        assert client.get('/auth/session').json()['username'] == 'test-caseworker'
        assert client.get('/caseworker').status_code == 200
        print('PASS: Argon2id hash, single approved account, HttpOnly cookie and hashed server session verified.')

        assert client.post('/cases', json=payload).status_code == 403
        assert client.post('/cases', json=payload, headers={
            'X-CSRF-Token': csrf, 'Origin': 'https://evil.example',
        }).status_code == 403
        created = client.post('/cases', json=payload, headers={'X-CSRF-Token': csrf})
        assert created.status_code == 201
        case_id = created.json()['case_id']
        updated = client.post(f'/cases/{case_id}/payments', json={
            'operation_id': str(uuid4()), 'amount': 1000, 'original_statement': 'Received another INR 1000.',
            'worker_confirmed': True,
        }, headers={'X-CSRF-Token': csrf})
        assert updated.status_code == 201
        assert updated.json()['case']['calculation']['balance'] == '2900.00'
        assert client.get('/cases/' + case_id).status_code == 200
        assert client.post('/auth/logout').status_code == 403
        assert client.post('/auth/logout', headers={'X-CSRF-Token': csrf}).status_code == 200
        assert client.get('/cases/' + case_id).status_code == 401
        client.cookies.set(auth.COOKIE, token)
        assert client.get('/auth/session').status_code == 401
        client.cookies.clear()
        print('PASS: CSRF protection, authenticated case creation/payment and immediate logout revocation.')

        assert client.get('/cases/' + case_id, headers={'X-API-Key': 'wrong'}).status_code == 401
        assert client.get('/cases/' + case_id, headers={'X-API-Key': test_key}).status_code == 200
        assert client.get('/auth/session', headers={'X-API-Key': test_key}).status_code == 401
        assert client.get('/caseworker', headers={'X-API-Key': test_key}, follow_redirects=False).status_code == 303
        print('PASS: separate service key works for case APIs and does not grant a browser login.')

        os.environ['SESSION_COOKIE_SECURE'] = 'true'
        secure_login = client.post('/auth/login', json=credentials)
        assert 'secure' in secure_login.headers['set-cookie'].lower()
        client.cookies.clear()
        os.environ['SESSION_COOKIE_SECURE'] = 'false'
        client.post('/auth/login', json=credentials)
        with closing(sqlite3.connect(auth.AUTH_DB)) as db, db:
            db.execute('UPDATE sessions SET expires_at = ?', (time.time() - 1,))
        assert client.get('/auth/session').status_code == 401
        client.cookies.clear()
        for _ in range(5):
            assert client.post('/auth/login', json={**credentials, 'password': 'wrong'}).status_code == 401
        assert client.post('/auth/login', json=credentials).status_code == 429
        print('PASS: HTTPS cookie flag, session expiry and login attempt limiting.')

print('All authentication tests passed against temporary databases. Existing case data untouched.')
