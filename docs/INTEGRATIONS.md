# Optional integrations

All credentials belong in private server environment variables, never in browser
JavaScript or Git. Actual third-party integration has not been exercised with
live credentials in this development session.

## Google sign-in

Install requirements, then set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and
GOOGLE_REDIRECT_URI (for example the HTTPS domain's `/auth/google/callback`).
Register that exact redirect URI in the Google OAuth client. Authlib performs
OIDC validation/state handling. Only openid/email/profile scopes are requested;
Google subject identifiers are used and email-based auto-linking is disabled.
New Google accounts remain pending until administrator approval, matching the
preserved registration policy. No refresh tokens are retained.

Reference: https://developers.google.com/identity/protocols/oauth2/web-server

## OpenAI Tutor

Set THANA_AI_ENABLED=1, OPENAI_API_KEY and THANA_AI_MODEL to a model available to
your API account. Until then the tutor explicitly operates as dictionary lookup.
When enabled, the learner chooses the checkbox to send the question to OpenAI.
The server calls the Responses API with `store: false`, published vocabulary
context, a response limit and 50 requests/account/day. No password, account
profile or private lesson content is sent. Provider response/data policies and
language quality still need review before production use.

Reference: https://developers.openai.com/api/docs/guides/migrate-to-responses

## Microsoft Azure speech

Set THANA_SPEECH_ENABLED=1, AZURE_SPEECH_KEY and AZURE_SPEECH_RESOURCE (resource
name, not an arbitrary URL). The browser shows a separate consent control,
converts the recording to 16kHz mono PCM WAV, and sends at most 30 seconds through
the backend. The backend uses the documented Azure short-audio REST endpoint.

Korean requests include pronunciation-assessment parameters; scores are shown
only when the provider actually returns them. Lao uses transcription only and
never inherits Korean pronunciation scores. Recognition of the expected words
is not proof of correct pronunciation. Real learner recordings, device codecs,
service availability and Lao accuracy must be evaluated before enabling this
for production. A 50 requests/account/day limit is applied.

References:
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text-short
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=pronunciation-assessment

## Payments

The current implementation is manual receipt review. Administrators configure
price/currency/duration and their own payment instructions in `/management`.
It performs no bank transfer or gateway charge. Receipts are available only to
the owner and administrator. Approval grants a time-limited entitlement once;
repeated approval is rejected. Request price/duration are snapshotted so later
plan changes do not silently change existing requests. Automated gateway
integration, refunds and accounting reconciliation are not implemented.

## Hosting

A separate Render Free staging demo is deployed at
https://thana-korean-stage-demo.onrender.com/ with synthetic data, reviewer
access and paid providers disabled. Free storage is disposable; this does not
satisfy durable production storage requirements. See STAGING_RENDER.md for
current deployment evidence, private access instructions and outstanding HTTPS
verification. Production service and domain were not changed; no paid plan
was purchased. Before production migration, back up actual data and validate
restore/migration on durable storage with HTTPS and modern admin passwords.


## AI voice authoring (Azure TTS)

The staff media studio now includes text-to-speech authoring. Set
THANA_TTS_ENABLED=1, AZURE_SPEECH_KEY and AZURE_SPEECH_REGION (for example the
actual resource region, not an arbitrary URL). This is independent from the
recognition flag. Standard voices are offered for Korean (SunHi/InJoon) and Lao
(Keomany/Chanthavong); availability must be confirmed for the selected resource.
No live synthesis was performed during development.

A teacher/admin explicitly consents to sending each text to Microsoft Azure.
Only that text and selected stock voice are sent, never account details or
credentials in the browser. Input is limited to 1000 characters; each account
has a 20 generation-attempt daily UTC cap. Failed provider calls count toward
that cap. Generated WAV is validated and stored as private draft media; the
teacher listens, marks it reviewed and then publishes it separately. This human
check is self-attestation, not automated proof of pronunciation quality. The
media studio labels AI provenance; published structured audio blocks display an
AI label. Source text/voice metadata is available only to content staff.

Repeated identical text+voice uses the saved file. Shared caching follows the
existing trusted staff/shared-library model. Generation can cost money when
configured; deployment operators should also set provider-side spending limits.
Keys and enabled flags are not configured by this implementation. Backup already
includes platform metadata and generated media; source packages exclude them.

Reference: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech

## Optional email registration / SMTP worker

Default: disabled. To enable the implemented username + email registration flow,
set THANA_EMAIL_ENABLED=1, THANA_PUBLIC_URL to the actual HTTPS origin (no path),
THANA_EMAIL_FROM, THANA_SMTP_HOST, THANA_SMTP_PORT (587 or 465),
THANA_SMTP_USERNAME and THANA_SMTP_PASSWORD privately on the server.
No credentials belong in web settings, source or chat. Registration remains
separate from administrator approval and login continues to use username.

Web requests enqueue verification mail in the private platform database; they do
not send SMTP. Run `python scripts/deliver_email.py --limit 20` in the configured
server environment with THANA_PLATFORM_DB set to its initialized private DB.
An operator must arrange worker execution; no Render cron/paid service was created.
The worker requires certificate-verified TLS (465) or STARTTLS (587), leases jobs
and retries up to five attempts with backoff. Delivery is at least once.
Delivered/expired/terminally failed message recipient/body fields are cleared.

Pending outbox bodies contain temporary verification links and are private backup
data. Do not export the queue or publish its SQLite file. Verification links are
short-lived, one use, require the registration password and bind to password
version. Resending invalidates older links. No real SMTP delivery was performed;
transport tests used mocks, and browser confirmation used synthetic account data.
Verify actual inbox/spam behavior and worker operation before enabling for users.
This feature does not implement self-service email password recovery.

Disabling the email flag stops new email signup/resend; it does not bypass the
verification requirement for accounts already registered through this flow.


Media Studio additionally offers 48 source-pack vocabulary recording prompts.
Loading a prompt does not send it to Azure; it clears consent and asks before
replacing existing text. These prompts do not track later live lesson edits.
Letter lessons require special review of letter names versus actual sounds.
This helper is locally verified (157 tests), not yet deployed; no audio was generated.
