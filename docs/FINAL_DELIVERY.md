# THANA KOREAN delivery status

## Current source status — 2026-10-19

The latest implementation passes 202 isolated tests plus clean extracted-source,
bootstrap, SQLite, HTTP and JavaScript syntax checks. This is implementation and
synthetic workflow evidence, not confirmation of production readiness or a live
provider integration. No production or staging deployment was performed for this
source release. The user selected free-only preparation and keeping the real
website unchanged. No paid plan was purchased.

Source synchronization is pending final guarded verification. Source packages
contain implementation, synthetic tests and public curriculum only. Credentials,
real accounts/history/payment data, private operational observations, runtime
paths, databases, media, receipts and screenshots are excluded. Private migration
working notes are kept outside the repository and source bundle.

## Implemented

- Existing Flask architecture, SQLite compatibility store and original content IDs.
- Korean/Lao course authoring, draft/publication revisions, staff roles/scopes,
  lesson access, sequencing and manual membership/receipt review.
- Existing EPS practice/timed mock exams, server deadlines, speaking exercises,
  dictionary/review progress and optional integrations disabled until configured.
- Public legacy Firebase curriculum parsing without executing JavaScript: original
  lesson/question IDs, additive review drafts, source provenance and overrides.
- Private transfer inspection, idempotent runtime candidate construction, original
  UID bindings, separate general/EPS/seasonal scope states and history journals.
- Disabled Firebase sign-in bridge: official SDK verification/revocation checks,
  recent authentication, explicit UID binding, current local roles/status/version,
  HTTPS/CSRF/rate limits and short Secure/HttpOnly session cookies. No auto-linking
  by email, username or client role claims; no password transfer.
- Optional legacy username login form using the existing public Firebase lookup
  and direct Google authentication; no credential/token browser persistence.
- Original string-ID EPS review bank, immutable source, editable review revision,
  shared protected-library media mapping and publication readiness gates.
- Offline recovered-image import with checksum/decode/size/path validation,
  private unpublished output, rollback cleanup and preservation of manual edits.
- Original EPS learner practice: publication-filtered catalog, owned snapshots,
  one active session, resume/cancel, idempotent grades and own history. Answers
  remain hidden until submitted; unanswered items reveal no solutions and consume
  no trial. Original per-question progress/trial flags merge monotonically.
- General/seasonal payment flags do not grant original EPS repeat access. Current
  staff or an explicitly enabled EPS entitlement permits repeat practice.

Original EPS practice is untimed and is not an official examination. Existing
server-enforced timed-exam deadlines remain unchanged. Listening-pair publication
and selection preserve available paired material. Unsubmitted choices are not
autosaved; resume restores the question set.

## Verification and limits

Synthetic tests cover roles, scope isolation, ownership, CSRF, strict answer
validation, publication/media gates, hidden answers, snapshots, quota/replay,
source-ID preservation, private draft access, import idempotency and rollback.
Isolated browser QA checked 320px layouts for account sign-in, original EPS staff
review/media mapping and learner practice through grading/history. It does not
establish real-device microphone, provider, production login or teaching quality.

Source verification and synthetic tests do not include real paid-provider calls.
Speech recognition is not pronunciation accuracy; Lao pronunciation scoring is
not validated. Staff review markers are attestations, not automated quality proof.
Source media and lesson translations still require content review.

## Still required

- Configure and verify Firebase backend credentials, explicit real UID bindings,
  current sign-in restrictions and actual mobile login before activation.
- Support verified Firebase-only administrators in production password preflight;
  do not create/export passwords to bypass that gate.
- Review all actual identity/history/payment mappings and unresolved records.
  Do not guess ownership or merge unrelated legacy account collections.
- Complete/review missing media, translations and curriculum, then explicitly
  publish approved content. Draft import/review does not publish automatically.
- Verify actual target receipt and durable storage, free-hosting limitations,
  deployment settings and real end-to-end learner/admin acceptance.
- Complete remaining legacy histories and operational cutover checks. Production
  cutover remains deferred under the user's current free-only decision.

See FIREBASE_MIGRATION.md for source-only procedures and INTEGRATIONS.md for
optional service configuration. Real operational observations are intentionally
not included in this public source handoff.
