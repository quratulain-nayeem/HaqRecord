# Hindi speech and repetition incident — 31 October 2026

The latest reviewed 136-second call contained one explicit request for Hindi.
The language detector switched to Hindi and did not log a subsequent switch back.
Nevertheless, an automatic English waiting sentence appeared before account-capture
callbacks. Hindi model replies were Romanized, contained English interface terms,
repeated the worker's name and acknowledgements, and sometimes asked two questions.
The text establishes these problems; it does not establish the acoustic cause of
the reported mumbling. Private call logs remain in ignored `.tools` files.

Bolna's `compute_function_pre_call_message` in `bolna/helpers/utils.py` chooses its
default announcement for null or other falsey configurations. Consequently the
earlier `None` intended to silence account capture actually restored English audio.
A nonempty language map with empty Hindi and English values selects empty output.

`voice_listening.py` now applies that explicit silent map to both definitions and
parameters of HaqRecord callback tools, preserving schemas, URLs and credentials.
Both registration scripts also emit this setting so later registration does not
restore the fallback. Provider-owned tools are untouched.

The synchronized speech instructions require natural Devanagari Hindi in Hindi
mode, one question per turn, short responses, no repeated name prefixes or full
recaps after corrections, and no duplicate acknowledgement of a language switch.
The Hindi system handoff itself now uses Devanagari. Synthesizer model, voice,
speed, streaming settings and chunk buffer were preserved.

Validation: `test_voice_listening.py` covers serialized and list tool definitions,
nested function definitions, credential/schema preservation, unrelated tools and
idempotence. Voice configuration guard, intake progression and save-path tests
passed. The provider accepted the update (HTTP 200); a fresh read matched every
submitted field, including all prompt representations. A new live call is still
needed to assess actual audio clarity and generated-response adherence.
