# Resolution workflow implementation map

Baseline: FastAPI (`main.py`, `bridge_app.py`), SQLite (`database.py`, `auth.py`), Pydantic domain models, browser JavaScript with no build step. Local launch: `Start-HaqRecord.ps1`. No repository-scoped AGENTS.md was found. The enclosing Git root is outside this project; preserve the existing working tree and do not stage unrelated files.

| Capability | Before | Implementation |
|---|---|---|
| Hindi/English microphone intake | Implemented; automated fixtures pass, live speech requires a speaker | Preserve `voice_backend.py`, `voice.py`, `web/assets/worker-flow.js` |
| Private case return, PIN hashing, CSRF | Working | Preserve `worker.py`, `auth.py` |
| Exact balances, promises separate, retry protection | Working for daily/weekly/monthly complete periods | Extend `case_models.py`, `database.py` without replacing stored cases |
| Corrections, evidence, packet, reminders | Working; supporting files are not extracted | Preserve `case_workspace.py`, `case_workspace_service.py` |
| Reply reconciliation | Missing | `reply_sources.py`, `resolution.py`, `resolution_store.py`, `web/assets/resolution.js` |
| Payment requests and recipient responses | Missing | Approved immutable snapshots and scoped expiring tokens in resolution modules |
| Next-action selection | Partial general support directory | Deterministic resolution state selector; preserve existing resource directory |
| Guided filing | Unverified | Versioned `support_routes.json`; preparation and source-labelled acknowledgement import; no claim of autonomous filing |
| Work diary | Missing | Confirmed standalone entries and explicit allocation references in resolution modules |
| Isolated demo | Public calculator only | Separate database launch/reset and fictional workflow fixtures |

Baseline checks: all Python scripts except `tests/test_worker_voice.py` passed; all five Node scripts passed. The worker test still expects monthly calculation to fail, predating monthly support (`tests/test_monthly_wages.py` passes). FastAPI emits an existing TestClient deprecation warning. Baseline tests use temporary databases. No real call, message, or government submission was made.

Migration policy: additive CREATE TABLE IF NOT EXISTS; preserve cases, original statements, payment events, and revisions. Rollback by stopping processes and restoring a pre-change SQLite backup, or running the old app with new additive tables left in place. Do not drop ledger tables to roll back UI code. Detailed final instructions are in `RESOLUTION_HANDOVER.md`.
