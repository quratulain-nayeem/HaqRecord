# Case preview and listening repair

Latest inspected call: calculate_reported_balance returned HTTP 200 and a balance of INR 2000 for three weeks at 1000 less 1000 received. No prepare_case invocation followed. The frontend previously rendered only a prepare_case draft, silently discarding a successful calculation. That was an application bug; the successful callback alone did not prove end-to-end case creation.

## Changes
- Store a private calculation preview with a revision ID and any account/name/location/employer supplied by Sara's first calculation call.
- Render it immediately, with earned/received/remaining and editable account details. Preview is explicitly unsaved and worker-review-required.
- Save from browser approval through prepare-preview and the existing PIN/confirm path. Case number is generated only after commit. Missing account text must be supplied rather than invented.
- Enforce the revision check inside the staging transaction. Changed calculations invalidate older drafts; unresolved adjustments clear earlier figures and prevent stale approval. Retries remain idempotent; original payment records remain append-only.
- Keep tool authentication, case binding, server session, same-origin and CSRF controls. No PIN enters the voice tool or any external research request.
- Start calls in the website language via agent_data.language. Restrict mid-call language switching to caller_requested.
- Controlled speech-recognition test: Deepgram Nova-3, hi/en profiles, endpointing 2500ms; linear delay 1200ms, interruption threshold 1, latency optimization off. Sarvam Simran speech and existing conversation model retained. The platform rejects nova-3 language=multi, so no unsupported multi setting is deployed.
- Exa search results: hide duplicate URLs and use the source hostname for empty/punctuation-only titles. No new office or procedure is fabricated.

## Validation
test_voice_preview.py: first calculation exposes preview before prepare_case; wrong browser/CSRF/approval/revision rejected; private PIN saves the correct balance; retries reuse the case; revised or uncertain figures cannot save a stale preview. Uses isolated fictional records.
test_voice_backend.py: existing case creation, payment deduplication, browser approval, case-bound access and logout revocation still pass.
Agent API read-back confirms Hindi/English Deepgram profiles, endpointing, delay, interruption threshold, explicit-request switching and five backend tools.
An isolated visual fixture verifies the page shows fictional figures without prepare_case. It does not prove microphone quality or the complete provider voice flow. A real spoken call is still required to judge pauses and recognition.

References:
- https://www.bolna.ai/docs/agent-setup/engine-tab
- https://www.bolna.ai/docs/customizations/multilingual-config-reference
- https://www.bolna.ai/docs/customizations/start-call-in-language
