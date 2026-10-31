# Voice and resource fixes — 25 October 2026

## What failed in the real call
Bolna's execution log reported `ERROR CALLING API: request blocked by outbound URL policy` for calculation and case preparation. The configured temporary tunnel hostname no longer resolved. No callback reached the local backend. Replacing Sarvam does not resolve a callback connectivity failure.

## Current configuration
The restored callback URL passed a real HTTPS health and authenticated weekly-calculation check. Public bridge exposes tool callbacks only, not case APIs or dashboard. Callback URLs remain temporary: keep the bridge and tunnel running. The connector now refuses to publish an unreachable URL, and session creation checks health before requesting a paid voice session. This checks reachability, not whether every Bolna tool invocation will succeed.

Both worker pages disable browser auto-translation so their own Hindi/English dictionaries control the UI. Reload an already-translated Chrome tab once; choose Show original if Chrome retains its previous translation.

Current listening test: Deepgram Nova-3 for separate Hindi and English profiles, endpointing 2500ms, incremental_delay 1200ms, interruption threshold one word. Bolna rejected language=multi, so the supported per-language hi/en profiles are used. Sarvam Bulbul v3 Simran still speaks; conversation model retained. The earlier Sarvam endpointing setting was not effective for that adapter, as Bolna's engine documentation explains. Language switching is now caller_requested, and minting supplies agent_data.language from the website. These settings need a real spoken test; they are not a semantic sentence-completion guarantee.

Case preview fix: calculate_reported_balance now persists its figures and supplied account in the browser's private voice context. The page shows those figures before prepare_case is called. A worker can confirm the account and privately enter a PIN to save from that preview, without relying on another model tool call. This is still explicit browser approval, not automatic saving. Stale/uncertain previews cannot be approved. See VOICE_PREVIEW_FIXES.md.


## Exa (current search provider)
Add `EXA_API_KEY` only to root `.env`. No key is needed to view curated official links. Search uses `POST https://api.exa.ai/search`, x-api-key authentication, type auto, six results, and includeDomains. No additional SDK is needed. Exa replaces Perplexity; there is no fallback call to Perplexity.

The website and Sara use the same provider-independent resource endpoint. Metadata-only searches return official-source titles and URLs, with no separately requested content extraction, summaries or answer generation. Discovered links do not prove jurisdiction, eligibility or published requirements. Cache keys include the provider so previous-provider results are not reused as Exa results.

Website: Find your next step → choose confirmed work city and issue → official sources first → fresh search if wanted. Sara has find_official_resources with the same limits. Intake works for other locations, but resource search currently supports Hyderabad and Bengaluru only; no claim of India-wide jurisdiction coverage.

Privacy: only enumerated city and issue leave the backend. Names, narrative, evidence, PIN, contact information, case ID and amounts are excluded. Search restricted to government and official legal-aid domains. Returned source URLs are checked again. Model-generated offices, contacts, eligibility and deadlines are not displayed as facts. Source cards are discovery results, not an adjudication or verified office jurisdiction. Directory references checked 2026-10-25: Telangana official department page and Karnataka official legal-aid contact page. No official complaint is submitted.

One Exa search request per fresh lookup; 24-hour cache by city and issue; ten fresh requests globally per day, including failed attempts. No automatic paid retries. Failures retain available directory links. External API not tested live without the key; request format and responses tested with fixtures.

## Validation
Authentication, weekly calculation, PIN access, append-only payments, payment retries, voice draft/browser approval, resource capability checks, source allowlist, private-field rejection, caching and limits checked with isolated databases. Live HTTPS calculation returned 3000 for 4 weeks × 1000 less 1000. No saved real case or payment created during checks. A fresh spoken call remains necessary to judge pause handling and verify the provider's complete tool flow.

References:
- https://exa.ai/docs/reference/search
- https://www.bolna.ai/docs/tool-calling/custom-function-schema
- https://www.telangana.gov.in/departments/labour-employment-training-and-factories/
- https://karnataka.nalsa.gov.in/contact-us/
