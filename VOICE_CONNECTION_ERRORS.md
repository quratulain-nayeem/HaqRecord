# Connection failure investigation

Bolna records one call as failed with zero conversation duration and zero total cost. A subsequent call connected for three seconds and was ended from the recipient/browser side. The full spoken journey has not been validated. Backend and configuration checks are healthy; this does not establish whether an individual browser-to-Bolna connection will succeed.

The SDK wraps rejected start() errors in cause2, while emitted error events use cause. Our UI previously lost HTTP quota/provider details in the rejected path, falling back to a misleading internet warning. Both cause forms are now handled. Errors distinguish daily limit, cooldown, unavailable/busy/denied microphone, unavailable service, provider mint rejection, failed call connection, blocked playback and unknown voice failure. Unknown voice failures no longer blame internet access.

The app had reached ten daily session requests. A provider-verified failed startup with zero duration and zero cost now has an audit entry in voice_failure_credits. Its original voice_mints row remains. The daily cap remains ten; the thirty-second cooldown counts all attempts. Only an unambiguous matching request immediately preceding a failed provider execution can receive this exclusion. Missing cost/duration is unknown and not eligible. This adjustment does not alter cases, payments or the provider account balance.

Microphone permission/device availability is checked locally before requesting a short-lived provider session. Failed microphone preflight cannot mint a session. The probe tracks are stopped before the SDK starts. The optional sound meter remains browser-only and does not record/upload audio.

Validation: Node test_voice_connection_errors.cjs covers SDK cause/cause2, microphone preflight without session creation, probe cleanup and quota classification. Python test_voice_preview.py covers the daily-limit recovery while keeping the cap enforced and private case saving. Worker/voice regression checks pass with temporary records. No additional real call was started during this repair. Voice provider/model settings were not changed.
