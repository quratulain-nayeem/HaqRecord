# Prevent stale agent settings from breaking web calls

The inspected call used a different published configuration from the one previously verified: a 35,838-character Hindi prompt, Sarvam transcription, auto language switching, four tools, and callback URLs differing from current .env. The current API also showed those replaced settings. The source of that save is unknown; do not attribute it to the user without evidence.

The local SARA_BACKEND_PROMPT.md is now a shorter single source for the agent and both language profiles. It limits read-back to once, preserves received payments across later yes/no answers, distinguishes paid/unpaid periods from total periods, and directs tool progression instead of repeated summaries. Model identity is retained. Hindi feminine grammar and all safety/consent boundaries remain.

voice_agent_guard.py compares the published prompt, language prompts, listening profiles, timing, language-switch policy, five callback URLs and first-calculation account field against the local configuration. Status checks cache for 30 seconds; session mint checks force a fresh read. Changed or unavailable configuration blocks BEFORE provider mint and BEFORE the session-request counter. No automatic overwrite of intentional Studio changes occurs. This check prevents silent use of known obsolete settings; it does not prove future LLM response quality or microphone recognition.

If an older Agent Studio tab is open, reload it before editing/saving. Saving old editor state may replace current API changes. Restore the tested configuration using start_voice_bridge.ps1 (or connect_voice_backend.py while the existing public callback is healthy). Intentional future tuning should update the connector and guard expectations together.

Tests verify drift detection, cached versus forced checks, and rejected call mint without a paid provider request. Existing preview saving, private PIN, stale-revision checks and payment deduplication still pass. Live website readiness reports configuration verified and callback connected. A new spoken test is still required to judge conversational behaviour. No new real voice call or case was created by these checks.
