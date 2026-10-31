# HaqRecord authentication

## Create the one caseworker account

From the project terminal, run:

```powershell
.\.venv-native\Scripts\python.exe setup_account.py
```

Use the default username `caseworker` or choose your own. Enter a password of 12 to 128 characters twice. Password input is hidden. There is no public signup endpoint. A second account is refused.

Open http://127.0.0.1:8000/login and sign in. The initial private page lets you look up a saved case; the complete review dashboard is a subsequent phase.

## What is used where

| Component | Location | Purpose |
|---|---|---|
| Argon2id via pwdlib | auth.py | Salt and hash the account password |
| Local account provisioning | setup_account.py | Create the one approved account from a private terminal |
| SQLite authentication storage | auth.db | Store the password hash, expiring sessions and login-attempt counters |
| Random session IDs | auth.py | Keep session information on the server; store only a SHA-256 digest of each random ID |
| Browser cookie | haqrecord_session | HttpOnly, SameSite=Strict, eight-hour lifetime; HTTPS-only when configured |
| CSRF token and origin check | auth.py | Require a session-specific token for browser changes and logout |
| Login limiting | auth.py | Maximum five attempts per client in a 15-minute window; a successful login resets the counter |
| Service credential | .env: HAQRECORD_SERVICE_API_KEY | Authenticate Bolna/backend tool requests using X-API-Key |
| Route protection | main.py | Protect case creation, retrieval and follow-up payments |
| Public preview | web/demo.html, web/assets/demo.js | Fictional wage-calculator example without database access |

Passwords are not stored in plaintext. SHA-256 is used for high-entropy session IDs, **not** for passwords. Logout removes the session from the database immediately. Caseworker account data and sessions never appear in the frontend files.

## Guest access

The `/demo` page is public. Guests can change fictional work figures and simulate a follow-up payment. Only `/calculate` is called there; no demo cases are saved. The `/` and `/worker` pages now provide the separate worker reference-and-PIN journey. This is a calculator preview, not a live voice-call demo. Guests cannot read saved cases even if they know a reference.

## Local versus deployed configuration

For local HTTP, `.env` has `SESSION_COOKIE_SECURE=false`. Set it to `true` and use HTTPS before deploying. The default in code is `true`.

The generated `HAQRECORD_SERVICE_API_KEY` is a private credential for **our** backend. It is separate from the provider key used to call Bolna's own API. Do not paste it into chat, commit it, put it in a URL, or embed it in browser code. Configure it only in the server-side Bolna tool header when that integration is built.

The `.env` file and both database files are excluded by `.gitignore`. Keep using fictional cases during this MVP. These controls do not constitute a completed production security review.

The public `/docs` page describes the API but does not bypass authentication. Browser mutations need an `X-CSRF-Token` obtained from `/auth/session`; service requests need the private `X-API-Key` instead. The upcoming dashboard handles browser tokens automatically.

## Verification

```powershell
.\.venv-native\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv-native\Scripts\python.exe tests/test_auth.py
```

The tests use temporary account and case databases. They cover anonymous denial, demo isolation, Argon2id hashing, single-account setup, cookie attributes, authenticated payments, CSRF, logout, service-key separation, session expiry and login throttling. They do not create a real caseworker account or change saved cases.


## Worker access added

Worker accounts do not use the caseworker password. Each new worker case gets a reference and a user-chosen 6–12 digit PIN, hashed with Argon2id in the case database. Worker sessions are separate, case-bound, expire in four hours and require CSRF protection for changes. Known references alone do not grant access; an existing phone number is not used as identity. Failed PIN attempts are limited by case and client.

All new follow-up payments require an `operation_id` UUID. Reuse it for retries of the same confirmed payment. Reuse with altered details returns 409; an exact retry returns the already-recorded payment. A fresh operation that resembles an existing payment also returns 409 until the worker explicitly confirms it is a different payment. The browser handles these references automatically.

`GET /worker/my-case` and `POST /worker/payments` derive the case from the session; callers cannot choose someone else's case ID. Worker credentials do not grant caseworker or general case-API access. Existing cases created before worker PINs were added remain accessible to the caseworker; they are not automatically given worker access.

`/voice` is the first Bolna browser-call checkpoint. Minting voice sessions currently requires the approved caseworker login while we validate account configuration. The complete voice-to-case worker flow is not yet connected. See BOLNA_VOICE_SETUP.md.
