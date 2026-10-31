# Hindi/Hinglish recognition and early case details

The latest inspected 50-second call contained only hello near the end. The user confirmed speaking Hindi/Hinglish before that. The call's English listening profile and only about two seconds of detected user speech indicate missing or unrecognized input; the logs alone do not prove a hardware microphone fault. No wage account or tools reached the conversation, so there were no details to fill.

Current Bolna configuration: Sarvam Saaras v4 in Hindi and English profiles, Sarvam Bulbul v3 Simran voice, existing Azure gpt-4.1-mini model retained. Explicit-request language switching retained. Linear delay 1800ms; base endpointing 1000ms. This is a controlled code-mixed speech configuration, not a verified cure for turn detection. The config guard checks effective inherited settings so harmless provider normalization does not block calls.

New capture_worker_account tool puts a partial unconfirmed account on screen before calculation. Unknown values remain null, not zero; notes are source-labeled and do not create a saved case. A meaningful correction invalidates an old preview. Backend calculations and explicit browser approval/PIN are still necessary to save. Received payments must remain separate from unpaid periods.

Optional Check my microphone: browser-only sound meter and input selector. Audio is not recorded or uploaded by this check. It proves local sound capture, not remote transcription. Streams close before the call starts and on consent withdrawal/navigation. The selected input is passed through the SDK's documented audio constraints option.

Offline tests: private partial notes, incomplete fields, no accidental saving, stale-figure invalidation, guard, case preview, PIN approval and payment deduplication. Live API read-back verifies six tools and current configuration; no paid voice call was created. Actual microphone and spoken recognition require the user's check.

Reference: https://www.bolna.ai/docs/sarvam-transcriber
SDK audio option: https://github.com/bolna-ai/web-call
