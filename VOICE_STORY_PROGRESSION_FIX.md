# Story progression correction — 31 October 2026

The next completed call lasted 112 seconds. Sarvam was actually used and captured work location, weekly agreement, a month’s duration and the unpaid-wage issue across successive fragments. The prior recognition-provider repair was therefore active, but the conversation still failed: repeated standalone “finish your story” acknowledgements interrupted narration, and the final response did not progress after non-payment was stated. No case/calculation tools were called. The provider again labelled termination `user_hung_up`; the exact disconnection cause is not established.

The previous listening addendum overemphasized waiting for an obviously finished utterance. That contributed to the acknowledgement loop. It has been replaced with an explicit transition using the accumulated account, not only the latest recognition fragment. No special “I’m finished” wording or perfectly complete final sentence is required.

Changes:

- `voice_listening.py`: bans standalone finish-your-story/listening fillers; separates narration from the next useful question; provides an example of month duration plus weekly wages without converting the month to four weeks. No new provider/model switch or timing increase was made.
- `intake_progress.py`: a deterministic operation selects one missing fact from captured notes. Weekly rate known + month duration + no exact weeks → ask completed weeks. Confirmed weeks + known rate + explicit zero receipts → calculation, not another request to finish or repeat facts. Unknown money remains unknown.
- `voice_backend.capture_account`: preserves accumulated values and explicit zero, stores unconfirmed notes and returns `next_action` / `next_question`. It does not save a case or invent a balance.
- `register_resolution_tools.py`: connects the already implemented `capture_worker_account` callback. It runs without a spoken pre-call filler. The `--refresh-listening` flag publishes the owned listening block and tool together. Main, per-language and rich-text instructions were verified after provider normalization; the local `SARA_BACKEND_PROMPT.md` matches the owned sections.
- `web/assets/worker-flow.js`: shows the backend’s next question alongside the captured notes.

For a fictional equivalent of the reported account, the selected next question is “आपने कुल कितने हफ़्ते का काम पूरा किया?” Once four weeks are explicitly confirmed, the next action is `calculate_reported_balance`; four weeks were not inferred from a month. Rate and money already received are retained. A calculation remains a tool result and private browser approval is still required to save.

Checks: `test_intake_progress.py`, `test_early_account.py`, `test_voice_listening.py`, `test_voice_agent_guard.py`, `test_voice_backend.py`, and browser review regressions passed. Actual agent read-back confirmed the capture tool/instructions are published; the live website reports ready/callback connected. The current change has not yet been validated in another spoken conversation. Static tests establish the backend progression and configuration, not live conversational success.

The complete user transcript and pipeline entries remain only in ignored `.tools/` review files. This report intentionally contains no worker identity or case contents. No worker case or payment was created from the reviewed call.
