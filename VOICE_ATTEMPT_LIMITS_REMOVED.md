# Voice attempt limits removed at user request

Removed the app-imposed ten-per-day session cap, thirty-second cooldown and voice-start IP rate limit from browser intake. The legacy staff voice-session endpoint also allows immediate repeat requests. Request history is retained as diagnostics and is not used to deny voice requests. No case or payment records were changed.

Bolna settings, provider account restrictions, the existing five-minute call duration, microphone consent, required backend connectivity checks, same-origin/CSRF protections, PIN access, payment deduplication and Exa limits are unchanged. Repeated connected calls can consume Bolna credits. No real provider call is started during validation.

Regression checks seed 100 recent requests then make 12 immediate mocked intake requests from one browser/IP. Both voice endpoints accept immediate retries; case approval and access protections remain tested.
