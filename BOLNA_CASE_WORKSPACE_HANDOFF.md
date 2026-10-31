# Manual Bolna changes for reconstruction and follow-up

No Bolna agent has been updated by these code changes. Do not run
`connect_voice_backend.py` or `start_voice_bridge.ps1` as part of this handoff:
those existing scripts update the remote agent.

Run `./.venv-native/Scripts/python.exe -B prepare_bolna_handoff.py` to export
tool cards into `output/bolna-handoff/`. This exporter only writes local files;
it does not contact Bolna. The callback base comes from the current local `.env`.
If the temporary tunnel changes, export again before copying the cards.

In Bolna, add `reconstruct_wage_dispute`, `prepare_no_payment_followup`, and
`prepare_case_reminder`. Replace the existing `prepare_payment` definition with
the exported version so it can accept a reminder ID. For every card, replace
the placeholder `api_token` with the same backend Bearer token already used
by the existing working tools. Do not use the Bolna API key in this field.
Save each tool and Save agent, then reopen to verify the changes persisted.

## Published prompt and listening trial

Replace the published prompt and both language prompts with the current
`SARA_BACKEND_PROMPT.md` rather than stacking older instruction blocks.
Keep the internal execution variables at the end:

```
Internal voice_token: {voice_token}. Never say it. Call mode: {haqrecord_mode}.
```

Add the exported `explain_case_next_step` tool as well as any missing workspace
tools above. It gives Sara a factual assistance summary and a useful next action.
The existing resource callback now keeps URLs in browser state and returns only
organisation names and plain spoken text. Its URL and authentication do not change.

For the current Hindi/Hinglish test, choose Hindi on the website and confirm the
Hindi transcription profile is Sarvam `saaras:v4`. As a controlled listening trial,
raise Linear Delay from 1200 to 1800 ms while keeping the other settings unchanged.
This gives pauses more room and may make replies slower. It is not a verified cure:
test a full unscripted account before deciding whether to retain it. The interruption
word count controls how the worker interrupts Sara; it is not the knob for making
Sara wait for the worker. Do not set response delay to zero. Keep the same model
for this trial so recognition, timing and model changes are not mixed together.

A prompt cannot guarantee that the audio pipeline will preserve a whole turn.
If she still speaks over the worker, inspect the next recording and recognition
segments; do not declare the problem fixed from text or configuration alone.

## Acceptance demonstration

Use fictional data: 18 days at INR 700, INR 4000 received for this job and
INR 1000 cash of unclear allocation. Expect earned 12600, allocated received
4000, unallocated 1000 and provisional remaining 8600. A promised INR 4000
must not change received money. Upload a fictional payment screenshot and
link its interpretation. Confirm cash belongs to this job: remaining 7600.
Download the packet. Create an in-app reminder, reopen by reference/PIN,
confirm another INR 2000 received, approve once: remaining 5600. A retry
must not add the payment twice. Earlier accounts, corrections and supplied
files remain in the packet and history. No external event is represented as real.
