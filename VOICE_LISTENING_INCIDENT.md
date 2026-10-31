# Listening incident and repair — 31 October 2026

Reviewed the latest 53.2-second call (22:02 IST) and its pipeline events. The stored transcript has only introductory fragments and a hello, not the worker’s full account. Raw pipeline metadata confirms the English speech-recognition profile used Deepgram while the language detector repeatedly detected Hindi. This is evidence of a recognition/configuration mismatch; it is not evidence that the worker failed to describe the problem.

The provider marked the call `user_hung_up`. That label does not establish that the worker intentionally pressed End; it does not prove an agent-initiated hangup either. The transcript contains no goodbye. Its exact disconnection cause remains unconfirmed. The old 300-second duration limit does not explain a 53-second call.

Separately, the published configuration still enabled LLM-determined hangup with an obsolete end-after-read-back cancellation prompt, a 45-second silence timeout and a 300-second duration cap. Those could cut off other conversations and contradicted the intended worker-controlled ending.

Applied and read back from the actual provider:

- Hindi and English recognition both use Sarvam `saaras:v4`, retaining the respective language codes. The English override no longer silently uses Deepgram.
- Endpointing remains 2500 ms; response delay is 2500 ms (previously 1850). One-word caller interruption stays enabled; latency optimization stays off.
- LLM-determined hangup is off, cancellation prompt and automatic goodbye are cleared, and silence/duration hangup values are zero. The worker must use End conversation when finished. Provider-side/network failures are still possible; these settings are not a promise of unlimited connectivity.
- A marked listening addendum is synchronized into the local, main, per-language and rich-text prompts. Job-title fragments are not treated as complete issues; a mid-story hello is not a language-switch instruction; an interrupted explanation must stop; missing recognition is acknowledged without blaming the worker.
- The selected speech-synthesis voice, LLM, tools, callback URLs, facts and saved cases were preserved. A private agent rollback snapshot is under `.tools/agent-before-listening-*.json`. Full transcript/pipeline material remains in ignored `.tools/` files, not in this report.
- `voice_agent_guard.py` now blocks a session mint if the known-bad recognition profile or automatic-hangup behavior returns. Prompt/timing-only changes remain advisory. Owned prompt sections are compared independently so internal call variables are preserved.
- The browser now distinguishes an unexpected connection end without claiming the worker or agent caused it. Figures already displayed remain available for review.

Code: `voice_listening.py`, `repair_voice_listening.py`, `voice_agent_guard.py`, `SARA_BACKEND_PROMPT.md`, `web/assets/worker-flow.js`. The repair command defaults to read-only; `--apply` changes only the owned listening policy and preserves unrelated settings.

Validation: listening-policy/idempotence tests, configuration drift/blocked mint policy tests, connected voice backend regression, monthly calculation regression, SDK error classification, review preservation and availability tests passed. The live app reports ready and callback connected; remaining warnings concern optional capture/workspace tools. No replacement live conversation was started or represented as tested speech quality.

Next live check: refresh the page, choose हिन्दी for Hindi/Hinglish, start a new call, and give the full initial account with natural hesitations. Sara should let the account finish, retain the active language, then ask one necessary follow-up. Use End conversation when done. Check the resulting transcript against what was spoken before calling the recognition repair validated.

Technical references checked: [Bolna’s Sarvam integration and code-mixed recognition](https://www.bolna.ai/docs/sarvam-transcriber), [chosen starting-language behavior](https://www.bolna.ai/docs/customizations/start-call-in-language), and the [official task-manager implementation](https://github.com/bolna-ai/bolna/blob/master/bolna/agent_manager/task_manager.py), whose hangup conditions require positive silence/duration values. These references establish configuration semantics, not the quality of a new call.
