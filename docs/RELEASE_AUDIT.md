# Local release acceptance audit — 2026-10-15

Scope: the existing Flask THANA KOREAN local review release, extending the supplied
material. This audit does not assert production deployment or completion of every
future phase in the pasted design conversation.

| Requirement | Current evidence |
|---|---|
| Preserve original data and brand | Original users.json, lessons.json, progress.json byte comparisons with Desktop source pass; 12 legacy lessons; public EPS 380 questions/231 PNGs. Desktop folders untouched. |
| Both learning directions and guest sample | hub/courses routes, seeded Lao starter and preserved Korean course; test_public; browser home language switch and both catalogs. |
| Authoring, publish, stale writes, mixed quiz grading | test_courses + test_quiz_types; synthetic browser course published; answer keys stripped from learner payloads. |
| Practical media authoring and order | Browser uploaded synthetic PNG, published asset, selected from editor picker, moved text before image and question two before one, published; learner DOM P→IMG and reordered legends; image decoded at width160. media-lesson-preview.jpg. |
| Draft media publication guard | test_publish_requires_public_library_asset rejects private library media until published. Draft media still available only to staff. |
| Version history and recovery | test_history_private_and_restore_as_new_draft verifies staff-only history, restore creates a new draft and leaves live lesson unchanged; earlier browser restore checked. |
| Account and staff workflow | test_admin_entry_roles, recovery, session revocation, forged-role rejection, CSRF, login rate limits. Browser /admin sign-in→/management; original tool /legacy-admin. |
| EPS and incorrect-answer retry | Tests cover server grading, immutable results, snapshot retry after bank change, ownership, perfect-attempt rejection, complete passage groups, bank archival and verification. Browser history→fresh unanswered retry. |
| Timed mocks | test_mock deadline, autosave/resume, idempotence, owner access, verified-only settings; synthetic browser save/reload/finalize verified. |
| Vocabulary and personal review | Tests CSV preview/duplicates/drafts, audio visibility, due scheduling, saved-only private filtering; synthetic browser saved word/filter/review flow. |
| Learning feedback | Server course progress/XP/streak and sequential locks tested; browser completion→immediate next lesson, course bars and deep-link reload. Personal summary uses authenticated owner-scoped APIs. |
| Administration and premium | Role tests; synthetic dashboard/account filters; manual payment snapshot approval grants access exactly once; no real financial transaction. |
| Community and optional services | Pending posts private until moderation. Provider tests use mocked HTTP only. Local recording code exists; real microphone/codec and provider quality not claimed. |
| Mobile | Phone viewport390×844 visually inspected learner media/quiz and dashboard. Found/fixed full-height fixed bottom-nav overlay caused by inherited top:0. After fix nav height74.39; mobile quiz scored100%. Narrow320×740 checks: home,courses,dictionary,editor,management,account,mock have scrollWidth320; learner nav74.39. Viewport restored. |
| Storage/restore | SQLite compatibility source-preservation tests, current backup includes platform snapshot and excludes secret, restore isolated validation/path traversal rejection tests. |
| Clean source distribution | scripts/verify_release.py extracts source ZIP into temporary directory, initializes twice (3 lessons/6 words), checks database integrity/bootstrap permissions, public/staff/private HTTP behavior, runs all48 tests and every static JS syntax check. Passed. |

## Evidence files

- docs/media-lesson-preview.jpg and docs/mobile-lesson-preview.jpg
- docs/mobile-admin-preview.jpg and docs/admin-entry-preview.jpg
- Other earlier review screenshots are illustrative historical states.
- Automated regression: `python3 -m unittest discover -s tests -q` —48 passed.
- Reproducible distribution check: `python3 scripts/verify_release.py` —passed.

## Material limits (not hidden acceptance claims)

See FINAL_DELIVERY.md and INTEGRATIONS.md. Production migration/deployment, provider
credentials and evaluation, teacher-approved full curriculum/native recordings,
Lao pronunciation scoring, listening mock content, native app-store builds, email
and automatic banking remain external/future work. SQLite legacy serialization is
correctness-oriented and has not been load-tested for production. Docker recipe
was not built here. Physical Android/iPhone installation and microphone testing
were not performed; browser viewport checks do not prove physical-device behavior.

Code is saved locally with a source-only ZIP. No remote push, production change,
provider call, paid purchase or disclosure of private accounts is part of this release.


## AI voice authoring extension — 2026-10-15

48 tests now pass, including synthetic Azure WAV generation, SSML escaping,
cache reuse without another HTTP call, private draft audio, review-required
publication, teacher/student access, invalid text/voice/consent and audio payload,
daily cap, and an AI provenance flag in published lesson blocks. Browser verified
staff form, four language/voice options, consent and disabled generation while
credentials are absent (ai-voice-preview.jpg). No real generated voice or provider
quality is claimed: test audio is a synthetic WAV fixture, not speech.

## Listening release verification — 2026-10-16

SOURCE_REVIEW.zip was freshly extracted into an empty temporary directory.
Idempotent seeding, SQLite integrity, bootstrap permissions, public/private/staff
HTTP smoke checks, all 66 tests and every static JavaScript syntax check passed.
No runtime accounts, databases, receipts or uploaded media are included.
Synthetic browser QA verified listening authoring, independent mock settings, WAV
decoding, answer autosave/reload and 5/5 submission; listening practice rendered
audio players. A 320px listening practice viewport had no horizontal overflow.
Test audio was a synthetic tone; no real speech provider was called.
Remote staging source b623171 matches local d13b274 tree d2d67ff.

## Weighted mock scoring — local, 2026-10-16

68 isolated tests pass, including scoring snapshots, mixed category totals, old
client preservation, legacy run defaults, result/history idempotence and invalid
weight rejection. Synthetic browser checked settings save, disclosed question
points and 14/16 weighted result alongside 4/5 correct. 320px overflow check passed.
Additive scoring tables leave original mock tables and question IDs unchanged.
No staging redeploy or real provider call is claimed for this extension.

## Content mutation audit — local, 2026-10-16

Clean extracted package runs 71 tests and all JavaScript syntax checks. Tests
cover safe metadata, preview/rejected exclusion, teacher/student/anonymous denial,
literal search, stable pagination and configured endpoint coverage. Browser used
a synthetic administrator to view a course-creation event, search by actor, see
zero results for a missing query, refresh and check 320px overflow (none).
Audit is post-commit metadata, not tamper-proof or transactional with mutations.
No runtime DB, credentials or receipt/audio contents were put in source.

## Speaking exercises — local, 2026-10-16

74 isolated tests cover audio publication/provenance, filters, staff roles, rejected
accounts, owner-private progress, repeat idempotence and revision conflicts.
Synthetic browser authored/published a Korean beginner prompt with silence sample,
selected it, marked self-reported practice and saw the saved checkmark after reload.
320px learner viewport had no horizontal overflow. No microphone permission or
real voice/provider scoring was exercised. New tables are additive; no original
lesson/question IDs or JSON inputs changed. No production or staging deploy here.

## Teacher course scope — local, 2026-10-16

77 tests cover server-side draft/revision and mutation denial for unassigned
courses, immediate scope revocation, admin-only assignment, atomic invalid-input
rejection, broad default compatibility and premium preview limits. Synthetic
browser saved a restricted teacher with one course, reloaded with the same
selection and checked 320px overflow (none). Actual teacher accounts were untouched.
Shared media/dictionaries/EPS/speaking are explicitly outside course scoping.

## Personal EPS analysis — local, 2026-10-16

79 tests cover owner-only statistics, repeated exposure counts, missing snapshot
coverage, unfinished/old exclusions, mode separation and bounded periods. Browser
with a synthetic learner displayed 2/4 correct across reading/listening, changed
the period and navigated to listening practice. 320px overflow check passed.
No real learner data was used. Source release and JavaScript verification pass.

## Recovery/cache corrections — local, 2026-10-16

81 tests pass, including successful password changes invalidating pending recovery
links while failed changes preserve them. Media tests cover private/public audio,
withdrawal with conditional request headers and private range delivery; no-store
is asserted on allowed and denied responses. Existing role/publication checks
remain in the serving path. No real account credentials or media were changed.

## Speaking recording lifecycle — local, 2026-10-16

82 isolated tests pass, including Node synthetic media lifecycle checks for prompt
context immutability, stale permission/stop/data callbacks, replacement, auto-stop,
permission failure and recorder failure. Browser startup/language switching had
no console errors. No microphone permission or real recording was used.
GitHub source upload is still awaiting explicit user confirmation after automatic
approval review rejected the full-source upload; remote deployment is unchanged.

## Direct MP4 clips — local, 2026-10-16

87 tests pass. Generated H.264 and H.264/AAC fixtures are actually remuxed/decoded;
tests cover global metadata stripping, draft/public access, publication dependency,
wrong media kind, withdrawal, byte ranges, validator timeout and MP4 restore.
Isolated browser loaded a one-second 64×64 synthetic blue clip: native controls,
readyState 4, no media error; 320px layout had no horizontal overflow.
No private content or real account was used. New runtime dependency is pinned;
Linux/Render binary execution and physical devices still need acceptance.

## Lesson navigation — local, 2026-10-16

88 tests pass, including adjacent-course boundary/access flag helper checks.
Synthetic learner browser verified first-lesson previous disabled, next locked,
completion unlock, next/previous traversal and final boundary disabled. Deep-link
course language was corrected to Korean. 320px overflow check passed.
No actual student progress, production or remote source was changed.

## Homepage settings — local, 2026-10-16

91 tests pass. Tests cover admin-only editing, escaped public rendering, bounded
fields, unsafe link rejection, stale revisions, defaults and token-free audit
metadata. Isolated browser saved bilingual headings and /account help link, then
verified both languages on the homepage. 320px overflow check passed.
Actual site copy and production were not changed; no external provider was used.

## Optional email registration — local, 2026-10-16

100 tests pass. Tests cover explicit configuration, hashed challenges, expiry,
one-use/password/version checks, resend/rate limits, unique normalized email,
approval separation, account deletion cleanup, mocked SMTP retries and queue
scrubbing. Synthetic browser checked form validation, confirmation with fixed
test token and existing password, URL fragment removal and 320px layout.
No real email, SMTP server or paid provider was contacted. Live delivery and
worker scheduling remain unverified. /hub homepage context has a regression test.
