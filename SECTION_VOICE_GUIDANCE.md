# Voice guidance inside each case-record block

Each of the five blocks under Build your case record has its own Bolna microphone:

| Block | Voice behavior |
| --- | --- |
| Check agreement and payments | Ask only its rate unit, quantity, rate, sources, individual payment rows, reason and unresolved points. A worker can request another payment row. |
| Add supporting material and link facts | Ask about browser file choice or skip, description, fictional/demo status, storage choice, source, fact, value, unresolved points and interpretation confirmation. |
| Facts and sources | Explain only the displayed facts and source links; no editable fields or new questionnaire. |
| Follow up | Ask the reminder and follow-up fields. Skip reminder-only fields when a new reminder is declined; skip received-money fields when no payment arrived. |
| Case history | Explain only the displayed timeline; no editable fields or new questionnaire. |

The worker selects Hindi or English before starting. The per-call language remains
fixed; selecting a different display language does not silently change the voice
call. Pause before starting again in another language. Hindi instructions require
Devanagari responses. Sara receives one current field/question at a time from the
deterministic section plan, along with its existing value and allowed choices.

Voice answers update an unsaved draft in the block. They never submit a form,
calculate/save a correction, upload a file, create a reminder, or tick the final
agreement approval checkbox. Existing preview/approval/save buttons and their
validation remain in use. Explicit yes/no answers are required for boolean fields;
blank or missing consent is never assumed. A worker may skip unknown answers.
Required skipped fields still need completing before their form can be saved.

Files are selected only with the browser's file control. The voice context receives
the chosen filename, not file contents; a voice callback cannot choose a file or
assert an upload. Skipping file choice skips upload-only questions and continues
with the fact-linking fields. Uploading and linking remain separate browser actions.

Pause ends the SDK call and revokes its tool capability, retaining draft answers
and question progress. Continue starts a fresh call at the retained step. Restart
begins the question plan again using the pre-voice field snapshot, preserving the
actual browser file selection. Other section drafts remain resumable for the
private worker session until context expiry. Pausing is implemented with stop and
reconnect because the SDK's mute method only mutes the microphone, not the agent.

The browser sends an authenticated, CSRF-protected section identifier and field
snapshot when minting a call. The server constructs its own allowlist/question
plan. `guide_case_section` accepts one scoped answer, skip, explicit confirmation,
correction or payment-row addition. Out-of-section fields and other case tools are
rejected for scoped capabilities. Read-only blocks cannot accept answers. Updates
are serialized, re-check the live tool capability and require the same active
private worker session. Revoked/expired call tokens cannot add answers.

Bolna receives dynamic `section_guidance` and `haqrecord_opening` values at session
creation. The agent's main prompt, Hindi/English prompts and rich compositions
include section instructions, and its callback uses the existing authenticated
bridge. Readiness verifies this connection before minting a section call. General
intake remains available outside section mode. Synthesizer, voice and LLM settings
were preserved. The official SDK documents dynamic prompt/welcome variables and
the `start`, `stop` and microphone-only mute methods:
[Bolna web-call SDK](https://github.com/bolna-ai/web-call).

Validation uses fictional temporary cases and mocked provider sessions. Backend
checks cover scope, choice/type validation, no writes to the saved case, file
selection, skip branches, read-only blocks, pause/revoke, cross-section resume,
restart and authentication. Real headless Chrome checks all five microphone
buttons, draft filling, unchanged final approval, pause/continue/restart, Hindi
file choice and mobile layout. Existing case/payment/voice checks also pass.
The published agent was read back and its section readiness verified. These tests
do not establish live speech recognition or the agent's audible adherence; those
require a real worker call.
