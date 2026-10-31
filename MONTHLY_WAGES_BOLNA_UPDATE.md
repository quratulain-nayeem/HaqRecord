# Monthly wages and worker-controlled hangup

Local backend and screens now accept daily, weekly and monthly agreements. They do not convert calendar months into weeks. Explicit monthly-rate wording submitted with weekly/daily units is rejected and invalidates the previous voice preview. This safeguard detects explicit phrases; it is not a general natural-language verifier.

## Required manual Bolna changes

Replace these existing tool cards using the generated JSON files in `output/bolna-handoff/`:

- `calculate_reported_balance.json`
- `prepare_case.json`

If already connected, also replace `capture_worker_account.json` and `reconstruct_wage_dispute.json`. All rate-bearing tools must accept `monthly`. Other callback URLs stay unchanged. Keep the existing backend Bearer token: generated cards deliberately contain a credential placeholder. Save the agent after updating.

Apply the monthly-unit and correction instructions from `SARA_BACKEND_PROMPT.md` to the main prompt and both language prompts. The tools must receive monthly / 5 / 2000 / 8000 for the reported five-month example. The backend then returns 10000 earned and 2000 outstanding.

## Call ending

All app-owned five-minute browser timers have been removed. The local connection script no longer imposes a five-minute provider timeout. It does not remove timeout settings already saved remotely; do not run that script to update the agent.

Read-only inspection of the currently published agent found:

- `call_terminate`: 300 seconds
- `hangup_after_silence`: 45 seconds
- `hangup_after_LLMCall`: true

On Bolna, disable silence hangup and automatic/LLM hangup if those controls are available. Under Call Management, remove/disable Total Call Timeout if Bolna supports that option. The official documentation describes a maximum duration but does not establish that 0 or -1 means unlimited. Do not use either value without provider confirmation. If the dashboard requires a positive timeout, a completely unrestricted call cannot be promised from our app alone; ask Bolna how to disable its enforced duration.

No remote Bolna settings were changed by this fix.

## Checks

Isolated tests exercise monthly calculation, rejecting a monthly-to-weekly mismatch and clearing the preview, private case saving, preserving monthly units in assistance summaries, and a later payment reducing the same case balance. Existing daily/weekly, reconstruction, browser review and microphone checks also pass. No real calls are made by these tests.
