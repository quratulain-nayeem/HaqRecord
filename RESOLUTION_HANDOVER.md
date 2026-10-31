# HaqRecord resolution workflow handover

Implementation and verification date: 31 October 2026 (India).

The existing FastAPI/SQLite application was extended in place. Bolna, Sarvam voice configuration, the selected voice/model/timing, case/PIN authentication, original case statements, earlier payment events, and existing corrections were preserved. The existing provider configuration has advisory differences from older tuning expectations; these do not block calls. No worker message or government complaint was sent.

## What works and where to find it

| Flow | UI entry | Implementation |
|---|---|---|
| Existing Hindi/English voice intake | Home → Tell us what happened | Existing `voice.py`, `voice_backend.py`, `web/assets/worker-flow.js`; the existing reconstruction callback is now connected in Bolna |
| Continue privately on a shared phone | Home → Continue my case | Existing `worker.py`, `auth.py`; reference + Argon2id PIN, expiring session, CSRF and attempt limits |
| Reply originals, extraction and reconciliation | Case → Explain a reply or document | `resolution.py`, `reply_sources.py`, `extract_reply_worker.py`, `web/assets/resolution.js` |
| Existing advance versus new payment | Reply → Save clarification | The original, review, promise and actual payment remain separate; a previously counted sourced advance prompts duplicate review |
| Promises and receipts | Case → Other options → Record a payment | Exact decimal amounts; promise dates require confirmation; actual payments use the existing transaction/idempotency ledger |
| Correct a received payment | Record a payment → Correct a previously recorded payment | An atomic signed correction is appended; original remains unchanged |
| Partial periods and changed rates | History and documents → Confirm partial work periods or different rates | Confirmed quantities, explicit hourly/daily/weekly/monthly/piece units, separate periods and backend arithmetic; no month/week conversion or invented average rate |
| Payment request | Case → Help me ask for my money | Backend draft from confirmed facts, exact-version approval, read-aloud, copy, download, user-initiated share with copy/download fallback, separate worker report of sending |
| Optional recipient response | Approved request → Optional private recipient response link | Expiring/revocable 256-bit capability; only token hashes stored; fragment token avoids access logs; recipient sees only approved text/name; assertions never mutate ledger |
| Deterministic next action | Immediately below case figures | `resolution.next_action`; unsafe contact skips confrontation; overdue promise asks whether money arrived; zero wages does not withdraw a complaint |
| In-app reminder | Record a payment → In-app reminders | Exact India time, separate consent, stopping supported; no SMS/call/email/background delivery claim |
| Preparation and acknowledgement | Other options → Help me take the next step | Preparation fields, copy controls, checklist, printable packet, worker submission report, source-backed confirmation of visible office/reference/date/documents and next action |
| Work diary without a dispute | Home → Record today’s work → Create private work diary | A separate reference/PIN diary book; entries do not change dispute totals until explicit inclusion; linking already-counted work adds no money |
| Diary inclusion and history | Work diary entry → Include uncounted work, or link already-counted work | Entry references and transaction-level duplicate-allocation guards; receipts can reference one existing payment rather than creating two |
| Voice corrections and follow-up | Case → Speak with Sara | `resolution_voice.py`, `RESOLUTION_VOICE_PROMPT.md`: case-bound read/proposal tools; recollection, promise, correction, work-period, diary, filing and reminder proposals require private browser approval |
| Download documents | History and documents → Full packet ZIP | Existing `case_workspace.py` packet now also includes `resolution-report.html` and private original reply files; printable HTML uses Unicode fonts and escaped source text |
| Delete private data | History and documents → Delete this private record and originals | Typed attached reference + CSRF; active originals, ledger, diary, sessions and history removed together. Downloaded copies, operator backups and provider-retained data need separate removal; physical erasure is not guaranteed |

New UI assets: `web/assets/resolution.js`, `web/assets/resolution.css`, `web/respond.html`, `web/assets/recipient.js`. Both `web/worker.html` and `web/voice-connected.html` load the extension. Existing evidence/reconstruction screens remain available below the main action. Language changes preserve the saved case and in-progress form values; changing an approved document requires a new approved version.

## Extraction capabilities and honest limits

- UTF-8 text works locally. Text-bearing PDFs work locally through pypdf. The local interpreter is explicitly labelled literal-amount rules plus worker review; it is not represented as unrestricted AI document understanding. Unclear, negated, malformed or unsupported monetary wording requires clarification.
- With `SARVAM_API_KEY`, the adapter makes real Sarvam requests for PNG/JPEG transcription, uploaded PCM WAV transcription, and structured text explanation in Hindi/English. Model output is schema validated; amounts, document fields and dates require source excerpts and subsequent worker confirmation. The original remains private and unchanged. No tool execution or ledger access is given to the extraction model.
- Bolna’s existing voice model can read the attached source data through the case-bound summary tool, explain it conversationally and stage a review. Source data is explicitly untrusted in both prompts and tool results.
- Maximum file size 5 MB; PDF 20 pages; image 16 megapixels; PCM WAV 29 seconds. Unsupported types are rejected by real content validation. A scanned/unreadable PDF requests a readable transcript or image; full scanned-PDF OCR is not implemented. WhatsApp access is not implemented: users paste/upload files themselves. Other compressed voice-note formats require conversion to the listed PCM WAV format.
- Processing runs in a captured child process with a 50-second deadline. Statuses distinguish processing, ready for review, clarification, missing configuration and failure. No success is reported before a real write. Failed/blocked sources can be retried; if the web process itself is killed mid-job, an operator must reset that source’s processing state before retrying. There is no durable job queue.
- Per-case limits: 100 originals / 100 MB, at most 20 new originals per 15 minutes. Source contents, credentials and provider response bodies are excluded from error logs. Existing extractions are not authenticated evidence.

Provider contracts were checked against [Sarvam transcription documentation](https://docs.sarvam.ai/api-reference/speech-to-text/transcribe) and [Sarvam chat V2 documentation](https://docs.sarvam.ai/api-reference/chat/chat-completions-v2). Adapter HTTP tests use labelled fixtures, not claims of live provider accuracy.

## External requirements still outstanding

| Dependency | Current state | Smallest remaining step |
|---|---|---|
| Direct image/audio/general document interpretation | No direct Sarvam credential configured | Add `SARVAM_API_KEY` server-side, then run real image and WAV samples and confirm output; Bolna credentials do not grant direct API access |
| Usable recipient links outside this computer | Full application public URL not configured | Deploy the full app with HTTPS and persistent private storage, set `HAQRECORD_PUBLIC_APP_URL`; the callback-only tunnel is not a public case/recipient deployment |
| Verified guided government filing | Preparation-only fallback shipped | Verify one current live form and employment/jurisdiction scenario, including exact fields/documents, then add a verified registry version. Do not simply flip the flag |
| Live Hindi and English conversations | Credentials/route readiness checked; spoken conversations not performed | A person must speak the fictional cases in each language and inspect speech understanding, interruptions, language switching and approval. Automated fixtures/headless read-aloud activation do not establish audible or conversational performance |
| External reminders | Not configured; UI never claims sent | A separate supported scheduler/channel and transport consent would be needed; current reminders intentionally appear only on opening the case |

`support_routes.json` records the source and date of the route check. The current [SAMADHAN landing page](https://samadhan.labour.gov.in/) is a JavaScript application; authenticated form/coverage was not verified. [Legacy portal guidance](https://reportsamadhan.labour.gov.in/faqs/) directs fresh Labour Code filing to the newer portal. The [older Ministry description](https://labour.gov.in/sites/default/files/pib2038690.pdf) was not treated as proof of current legal applicability. No statutory eligibility, deadline, jurisdiction or autonomous filing claim was introduced. Hyderabad/Bengaluru remain pilot choices; neither city alone determines eligibility.

## Configuration and startup

Install production dependencies with `.venv-native\Scripts\python.exe -m pip install -r requirements.txt`. New dependencies are pinned pypdf and Pillow; browser verification uses optional `requirements-dev.txt` Playwright and installed Chrome. No frontend build or new service stack is required.

Existing variables retained: `BOLNA_API_KEY`, `BOLNA_AGENT_ID`, `HAQRECORD_VOICE_TOOL_SECRET`, `HAQRECORD_VOICE_PUBLIC_URL`, `SESSION_COOKIE_SECURE`, service authentication settings and optional `EXA_API_KEY`.

New variables documented without values in `.env.example`:

- `SARVAM_API_KEY`; optional `HAQRECORD_REPLY_MODEL` defaults to `gemma4`.
- `HAQRECORD_PUBLIC_APP_URL` for the complete public app, HTTPS only. Keep unset until actually deployed.
- `HAQRECORD_DB_PATH`, `HAQRECORD_AUTH_DB_PATH` for isolated processes.
- `HAQRECORD_DEMO=true` disables direct provider access, live call issuance and recipient-link activation in the fictional demo.

Normal local start remains `powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-HaqRecord.ps1`. Newly launched reload servers have a finite graceful-shutdown timeout and no access log. Startup lists all known callback URLs in `VOICE_CONNECTION_URLS.txt`; it does not silently rewrite Bolna. A temporary tunnel still requires restarting after a machine/network restart and keeping enabled callback URLs in sync.

`register_resolution_tools.py` defaults to read-only review. `--apply` publishes the existing reconstruction callback plus the two resolution tools and updates only the owned prompt extension/rate schema; `--verify` checks current publication without another write. It preserves the existing prompt prefix and provider/model/voice/timing. Provider-assigned tool IDs/default metadata are preserved. No call is minted by registration. The tools were published and then verified against the actual agent in this implementation.

## Migrations and rollback

`database.initialise_database()` invokes `resolution_store.migrate()`. This adds `resolution_events`, `reply_sources`, `response_links` and a `schema_migrations` entry `resolution_v1`. It does not rewrite old cases, drop tables or alter original payment entries. Richer period/payment metadata is stored in the existing JSON snapshots/events. Exact money remains Decimal serialized as strings.

A SQLite-consistent snapshot of both private databases was saved under `.tools/pre-resolution-use/` before exposing the finished workflow. It contains original case data plus empty additive workflow tables; it is not a backup from before the additive schema creation. Keep it private. The earliest `.tools/agent-before-resolution-*.json` is the provider rollback snapshot from before this implementation’s tools; subsequent snapshots include intermediate improvements.

For code rollback, stop the project services and restore the previous project files. Leave additive tables in place. Older code does not understand newly created diary books, partial-unit records or richer periods, so export/reconcile new records before returning to older code. To restore the paired pre-use SQLite snapshots, stop services and deliberately replace the matching case/auth databases from that snapshot; this discards records created after it. Do not copy over a live SQLite database or delete ledger tables to roll back a UI change. Provider rollback uses the saved original agent configuration through the existing authenticated Bolna v2 agent update interface; preserve callback hostname validity and verify it afterward. None of those destructive rollback steps were executed.

Retention: active records remain until the worker deletes them; there is no automatic expiry policy. Deletion includes the activity history and originals. Operator backups and third-party retention have separately disclosed limits.

## Checks performed

- Baseline: 12 Python scripts and five Node scripts; one pre-existing Python assertion rejected monthly wages despite implemented monthly support. Updated that stale expectation; the actual monthly arithmetic regression remains tested.
- Final suite: all 16 Python scripts and five Node scripts passed, including the four new source/resolution/foundation/browser scripts. Tests use temporary databases; no existing worker cases were used as fixtures.
- Arithmetic: 5000−1000=4000; already-counted advance unchanged; 1500 promise unchanged; later actual 1500 gives 2500 once. Same operation replay is idempotent; separate equal payments can be confirmed; known sourced advance repetition is challenged. Reimbursement fixture yields 6000 earnings, 1500 wages received, 4500 unpaid. Hourly/piece/partial-period/changed-rate paths and append-only payment correction are checked.
- Privacy/security: ownership, CSRF, failed writes, stale revision, real file type, unreadable amounts, malicious source text, absent providers, expired/revoked/incorrect recipient tokens, no GET side effects, recipient inability to change ledger, diary allocation, deletion and session revocation.
- Actual headless Chrome at 360×800 and desktop: reply review, promise, exact request approval, language and form continuity, payment, diary and standalone diary creation; no JavaScript errors or horizontal overflow. Keyboard read-aloud activation checked; actual audible speech/provider dialogue not claimed.
- Rendered the printable HTML and visually inspected Hindi glyphs/mobile English and Hindi screenshots. Review images are under `.tools/resolution-review/`. Packet ZIP contains original reply sources as separate private files.
- Live application/provider configuration checks: website and callback health, new callback authentication rejection and agent readiness. The unrelated selected voice/model/provider/timing were verified unchanged. No new real voice conversation, external message or government submission occurred.

The existing FastAPI/Starlette TestClient deprecation warning remains; it does not fail these checks. There is no configured lint/build command beyond Python compilation, JavaScript syntax checks and the repository’s script tests.

## Fictional demonstration

Run `.venv-native\Scripts\python.exe -B run_resolution_demo.py --reset`, then open `http://127.0.0.1:8002/`. The printed reference and fictional PIN reopen the sample. `--seed-only` prepares it without starting a server. Stop port 8002 before using `--reset` again. Reset only touches the explicit database files under `.tools/demo/`, never production cases. Direct voice/OCR requests and recipient-link activation are disabled in this isolated mode; no mock is substituted for them.

The example originals are `demo_fixtures/employer-message.txt` and `demo_fixtures/sample-acknowledgement.txt`. See `DEMO_SCRIPT.md` for the three-minute walkthrough and `EVALUATION_TEMPLATE.md` for future usability/cost measurements. The isolated demo uses the same real app and persistence operations; it is not a disconnected mock screen. A live voice demo requires a separately isolated callback environment attached to the same demo database, or a separately provisioned demo agent; do not point real worker callbacks at this fictional store.
