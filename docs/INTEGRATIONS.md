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

Use durable storage for both SQLite files, media and receipts. Set THANA_ENV to
production only with HTTPS termination, and change any legacy default admin
password first. No deployment, domain change, subscription purchase, GitHub push
or App Store publication was performed. The existing Render configuration is
not a durable-storage deployment plan and must be reviewed before use.


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
