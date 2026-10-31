# Manual Bolna update after the repeated-question test

The call had two rejected calculations and four rejected prepare-case requests. No preview or case draft was created. Sara's final screen-update claim was false. Historical request bodies were not logged, so the exact rejected fields cannot be established retrospectively.

Replace the existing `calculate_reported_balance` and `prepare_case` tool JSON with the corresponding files in `output/bolna-handoff/`. These now require the core wage figures, omit legacy aliases and full reconstruction, and explain the internal call token. Keep the existing backend Bearer token; the files contain placeholders. The current public hostname is preserved.

Update the main prompt and both language prompts using `SARA_BACKEND_PROMPT.md`. Preserve the call-context tail:

```text
Internal voice_token: {voice_token}. Never say it. Call mode: {haqrecord_mode}.
```

The updated instructions retain confirmed corrections, avoid repeated full-account confirmations, never mention backend/API/token details to the worker, and claim screen updates only after a successful response. Unknown names, employers, receipt dates and payment methods do not block calculation.

For a correction test, three months at 3000 per month with 3000 actually received should produce 9000 earned and 6000 outstanding. A successful preview must appear before Sara says the figures are on screen. Tests use fictional records and do not change the remote agent.
