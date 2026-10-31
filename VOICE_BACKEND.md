# Sara connected to the HaqRecord backend

## Current working scope

Sara has four custom tools: `calculate_reported_balance`, `prepare_case`, `read_current_case`, and `prepare_payment`.

The tools use the existing daily/weekly calculations and SQLite case records. Sara does not invent a balance or generate her own case number. An unconfirmed or disputed adjustment produces a clarification result instead of one supposedly definitive balance.

Open http://127.0.0.1:8000/voice . New intake does not require caseworker login. For an existing-case call, first open the case at `/worker` using its reference and PIN, then choose the existing-case option on `/voice`.

## New-case acceptance test

1. Use fictional information. Tell Sara you worked four weeks at INR 1,000 per week and received INR 1,000.
2. Confirm the figures and clarify advances/deductions.
3. Sara should call the calculation backend and explain the INR 3,000 reported balance.
4. Agree to prepare the case. A draft should appear on the website.
5. Check the account and figures, choose a PIN privately, and approve saving.
6. The website returns the real reference. Tell Sara you approved it; she can read the saved case through the case-bound tool.
7. No government complaint has been submitted.

For a follow-up, open the same case with its reference/PIN, start an existing-case voice call, report another INR 1,000 actually received, then approve the payment on the website. The recorded balance becomes INR 2,000. Retry protection preserves a single payment entry.

## Permissions and confirmation

- A call has separate random browser and tool tokens, stored only as hashes in the case database. Contexts expire after 30 minutes.
- Every public tool request needs a service credential **and** the current call's token.
- Tools cannot choose arbitrary case IDs. The backend attaches an existing case only after worker reference/PIN verification.
- PINs are entered privately on the website and never sent to Bolna or included in an agent tool.
- Tools prepare changes; they cannot approve them. Browser approval requires the private cookie, a CSRF token and the exact draft version.
- Repeated proposals/confirmations do not create repeated case/payment entries. Payment entry storage also checks operation IDs and possible duplicates.
- Ending a call revokes its tool token while leaving a pending draft available for private confirmation. Signing out of the worker case invalidates the call's access to saved case data.

## Temporary callback bridge

Bolna cannot call localhost directly. A separate server on port 8001 exposes only the protected tool routes and a simple health check. Cloudflare provides a temporary HTTPS address for this server. The dashboard, worker pages, general case APIs, authentication APIs and API documentation are not exposed by this tunnel.

The address is temporary and changes when the tunnel restarts. Keep the bridge/tunnel running during the demo. After a computer restart, run from the project terminal:

```powershell
.\start_voice_bridge.ps1
```

This opens a new callback address and updates the agent's tool URLs using the local `SARA_BACKEND_PROMPT.md`. Keep the main server running separately. Avoid restarting the bridge during a live call. Secrets and tunnel runtime files are excluded from Git.

## Prompt source

Bolna Studio stores a published rich-text `composition_by_language` as well as the plain `agent_prompts` string. The connector updates both so later saves do not silently restore the old generated script. Refresh Studio before editing remotely changed settings. The local `SARA_BACKEND_PROMPT.md` is the reference used when reconnecting.

## Verification and remaining work

`tests/test_voice_backend.py` checks voice calculation, staging, private confirmation/PIN, real database saving, payment retries, cross-session isolation and logout using temporary fictional records. The HTTPS callback was also checked externally with fictional figures. These checks do not replace a person testing tool calls during an actual voice conversation.

Official-source discovery for Hyderabad and Bengaluru is connected through Exa (EXA_API_KEY required for fresh searches); see VOICE_RESOURCE_FIXES.md. Verified jurisdiction-specific routing, complaint preparation, evidence uploads, submission records and reminders remain later phases. Sara must not claim those functions are connected.
