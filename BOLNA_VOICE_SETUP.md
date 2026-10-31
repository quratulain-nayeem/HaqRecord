# First checkpoint: a real browser voice conversation

This is a smoke test, not yet a complete voice-to-case integration. Do not count it as working until a person actually speaks and hears the configured agent.

## Set up the agent

1. Open https://platform.bolna.ai and create a separate agent named HaqRecord Voice Test.
2. Select Sarvam for transcription and speech generation, with a language/voice combination available in your account. Enable Hindi/English or the supported multilingual configuration and test both languages separately. Configure a conversation model in Bolna as well.
3. Set a maximum call duration of 300 seconds (five minutes) in the provider settings. Disable retained recordings if available for this smoke test; otherwise disclose the provider retention and use fictional information only.
4. Use a prompt along these lines:

   You are HaqRecord, an AI assistant being tested with fictional unpaid-wage examples. Introduce yourself as AI. Speak Hindi/Hinglish or English according to the person’s preference. Ask one short question at a time. Clarify daily versus weekly wages, rate, completed days/weeks and payments actually received. Ask whether payments include advances. Read back the facts and allow corrections. Do not invent legal routes, save cases, claim a complaint was filed, or state a calculated balance; calculation tools are not connected in this first test. Never ask for names, phone numbers, PINs or private evidence in this smoke test.

5. Copy the agent ID. Generate a Bolna API key from the Developers area.
6. In the **top-level** project `.env`, set:

   ```dotenv
   BOLNA_API_KEY=your_actual_bolna_api_key
   BOLNA_AGENT_ID=your_actual_agent_id
   ```

Do not put the key in a browser script or send it in chat. `HAQRECORD_SERVICE_API_KEY` is a different credential: it lets Bolna call our backend later.

## Run the test

1. Keep the FastAPI server running.
2. Create the one caseworker account using `setup_account.py` if you have not done so, then sign in at `/login`.
3. Open http://127.0.0.1:8000/voice . The page checks configuration without exposing keys.
4. Select the language and agree to audio processing. Start the test and allow your browser microphone.
5. Say the four-weeks / INR 1,000 per week example. Verify two-way audio, number recognition, interruption, correction and language behavior.
6. End the call. Check its execution reference and provider usage in Bolna. A minted session alone does not prove voice works.

The backend calls the official session endpoint and returns ephemeral connection credentials. It requires the approved browser session plus CSRF protection. The user-requested removal of app-imposed voice attempt restrictions allows immediate repeated session requests. Provider credit, capacity and account restrictions still apply.

## Current boundary

Guest voice is not enabled during this initial validation. The guest calculator remains available without login. Worker access and case-bound tool calls are the next step. Public voice must receive its own abuse limits before being enabled.

## Official references

- https://github.com/bolna-ai/web-call
- https://www.bolna.ai/blog/browser-calls-kamailio-freeswitch
- https://www.bolna.ai/docs/sarvam-transcriber
- https://www.bolna.ai/docs/sarvam-voice


## Preserve tuning when using Agent Studio

Reload Agent Studio before making another change, so an older open editor does not overwrite API changes. After saving, verify that the focused SARA_VOICE_TEST_PROMPT.md prompt is still active, both language transcribers retain endpointing=2000, incremental_delay=1500, and call_terminate=300. A longer endpointing pause is a tuning starting point, not a guarantee that semantic sentence boundaries will be recognized. Judge it with a fresh listening test.

Sara uses feminine Hindi self-reference such as “समझ गई” and “कर सकती हूँ”. The voice remains Simran. Changing the language model is a separate experiment from turn detection.
