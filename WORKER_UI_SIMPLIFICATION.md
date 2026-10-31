# Worker UI review — 31 October 2026

The figure read-out and correction actions now have their own spaced row with
large outlined buttons. They stack on small screens and wrap long labels.

Help and summaries share spoken-help controls: pause/continue, start again, stop.
These controls appear while reading is active, use the selected display language,
and stop old speech when the language changes. They do not control Sara's live
call or erase case details. Spoken help is shorter in Hindi and English.

The saved case opens with balances and a small menu: tell Sara, hear the case,
money received/promised, understand a message, ask for money, and reminders.
Long forms open after choosing a task. Further help, diary, history and detailed
corrections remain available through expandable sections. Money received and
money promised are separate choices. The reminder shortcut opens just the reminder
form. Original story, payment history, receipts, advanced case editing and local
support details remain available without occupying the initial case view.

Repeated introduction text was shortened or removed. Consent, private PIN steps,
payment confirmations, original-source distinctions and filing limitations remain.
File guidance uses everyday words instead of provider implementation details.

Display-language changes now rebuild a focused case editor while preserving
typed fields, payment rows and open sections. The calculation must still be
previewed and approved before a correction is saved. Voice state accepts an
optional display-language query for generated next-step guidance and intake
questions. This only changes the response view: original statements, source
documents, financial figures, stored drafts and the live voice language are not
rewritten. Responses from an older language request cannot replace the current
voice review. Existing session and CSRF protections apply.

Checked in real headless Chrome at mobile and desktop widths with fictional
records in temporary databases. Covered reply review, promises, requests and
approval, payments, reminders, standalone diary, focused-field language changes,
spoken-help controls, figure-button spacing, and draft/PIN preservation. Also
ran relevant backend and voice regression checks. Browser checks exercise speech
controls with a synthesis spy; they do not verify physical speaker output or
accessibility with actual workers.
