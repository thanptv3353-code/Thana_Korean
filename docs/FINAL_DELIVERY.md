# THANA KOREAN local web application handoff

## Latest source synchronization — 2026-10-16

After explicit user authorization, sanitized source from local commit 64e8445
was uploaded to GitHub branch codex/staging-review-20261015 as commit
fe1eca20c6ec9ca21b8b828ed112f5d0a1fe95ca. The remote commit and branch ref
were read back; its complete tree matches the tested local tree
791f590165d44dd6726e2f121abb5cf6ac8b4772. Runtime accounts, databases,
credentials, receipts, uploaded media and backups were excluded. The existing
100-test release validation applies to this source snapshot.

This records source upload only. Render deployment remains b623171; the newer
features described below as local have not yet been verified on Render.
Production and the main branch were not changed.

This is the current authoritative status; older DEVELOPMENT_STATUS entries are
incremental history. Completed as a local review build on 2026-10-15. A separate Render Free staging service was deployed on 2026-10-15;
production/domain and payments were not changed.

## Implemented

| Area | Working local behavior |
|---|---|
| Navigation | /admin sign-in opens central dashboard; original admin available at /legacy-admin; Lao/Korean home, shared learner navigation, legacy/new course catalog |
| Existing material | Preserved 12 lessons, 165 quizzes, 270 lesson exam questions, 11 homework tasks; EPS 380 questions and 231 images |
| Authoring | Search/filter lessons by title, module and publication status; courses, modules, ordered lessons, text/audio/image/YouTube blocks, media picker and actual media preview, block/quiz move controls, draft/published snapshots, revision history and restore to draft, stale-edit protection |
| Assessment | Choice, fill-blank variants, matching and ordering; answer stripping and server grading |
| Personal summary | Completed lessons, XP/level/streak, due vocabulary count and recent practice/mock results at /my-learning; private APIs scoped to signed-in learner |
| Learning | Optional sequential unlocking, course search, per-course completion bars, continue/next lesson and deep links, completion, unified legacy/new XP, level and activity streak in UTC+7 |
| EPS | Practice, incorrect-answer snapshot retries, complete-passage grouping, editable bank, archival, verification, timed reading mock, deadline enforcement, answer autosave/resume, result/history/category analysis |
| Vocabulary | Bilingual search, examples, categories, CSV preview/import/duplicates, per-language audio, self-rated spaced review, private saved-word lists and saved-only review |
| Assets | Reusable image/audio/short-MP4 library, image re-encoding, draft/public visibility, protected uploads |
| Accounts | Existing password login and approvals, profile, 8–128-character new passwords, versioned PBKDF2, session invalidation on password change, login attempt limiting, single-use admin-assisted recovery |
| Administration | Role-aware dashboard, weekly activity, searchable accounts with status filters, account roles/status, content/media/question tools and account audit events |
| Premium | Configurable manual price/instructions, private receipts, review, one-time entitlement grant, server-side premium course checks |
| Community | Learner posts pending staff moderation, private pending visibility, publication and basic posting rate limit |
| Providers | Staff Azure AI voice generation, cached private WAV drafts and review-before-publish; Google OIDC adapter; OpenAI Responses Tutor; Azure WAV recognition and Korean pronunciation adapter, all disabled pending credentials |
| Storage | Transactional SQLite compatibility migration for legacy schemas plus platform SQLite; original JSON untouched |
| Operations | Full private backup, validated restore into empty directory, environment guide, Docker recipe, health route and safe bootstrap for fresh installs |
| Mobile | Responsive web UI, manifest/icons and offline notice; no private data cached by service worker |

## Validation

- 110 isolated unit/integration tests pass (Flask, storage, grading, access,
  deadline, recovery, payments, upload visibility, import, providers with mocked
  HTTP responses, restore validation and traversal rejection).
- Browser QA used a separate server with a synthetic administrator and synthetic
  course. Verified password sign-in, dashboard, course creation/publishing,
  learner content, completion/XP, mock answer save, reload resume and submission.
- Public dictionary search and Lao/Korean home switching also checked in browser.
- Editor title search, combined publication filter and unsaved new-lesson course
  protection checked in an isolated browser session.
- Saved-word add/filter and saved-only review checked in browser; regression
  checks cover authentication, draft exclusion, idempotence and preserving due
  dates when a saved word is removed and re-added.
- Personal summary sign-in and signed-in empty-state/real due-word count checked
  with synthetic learner data.
- Learner browser QA verified sequential lock → completion → next lesson,
  immediate catalog unlock, progress bar and lesson deep-link reload. Staff
  browser QA verified revision list and restore into an unsaved draft.
- Account search, combined status filters and empty-result state checked with a
  synthetic administrator. Course access settings now report and display saved
  Free/Premium and sequence values, with a persistence regression test.
- JavaScript syntax checks completed for the application scripts.
- Extracted SOURCE_REVIEW.zip into an empty temporary directory: fresh account
  bootstrap, starter seeding twice without duplicates, health and home routes pass.
- Phone viewport QA at 390px verified media/quiz grading and dashboard; 320px
  overflow checks pass. Fixed bottom navigation overlay and checkbox sizing.
- Clean extracted source runs all 45 tests, seeds twice, validates SQLite and
  bootstrap permissions, and passes public/private/staff HTTP smoke checks.
- Full acceptance evidence is mapped in RELEASE_AUDIT.md.
- Final local preview on port 8035 restarted and its home inspected in browser.
- Original users.json, lessons.json and progress.json still match the supplied
  local legacy application's bytes. Source folders on Desktop were not edited.

## Boundaries and pending external work

This is the implemented local Web App scope, not a claim that every future item
in the initial vision is finished:

- No production deployment or live-data reconciliation. Confirm the code/data
  actually running at thanakorean.com, take its backup and dry-run migration.
- No real API keys were used. Google, OpenAI and Azure adapters need configuration
  and live service/device evaluation. Provider-backed tests used mocks only.
- Lao speech is transcription only; no Lao pronunciation scoring is promised.
  Korean provider scores appear only if returned. Neither adapter was benchmarked
  against real learners. Native voice assets still require recording/upload.
- This remains Flask/SQLite, not Next.js/PostgreSQL. Legacy requests are serialized
  for correctness. Production load/performance and normalized PostgreSQL migration
  are not implemented or tested.
- The Lao course contains three introductory authored lessons, not an entire
  approved curriculum. EPS imported translations/answers require teacher review.
- Teachers share dictionaries, media, EPS and speaking authoring. Administrators
  may restrict structured course access using teacher assignments. Existing
  teachers keep broad course access until restriction is explicitly configured.
  Only administrators manage accounts,
  receipts, payment settings and entitlements.
- Manual receipt verification is implemented; automatic bank gateways, refunds,
  full accounting and automatic recurring billing are not.
- The PWA shell is installable where supported, but full offline lesson/audio
  download and native Android/iOS store builds are not included.
- Self-service email recovery and email delivery are not configured. Recovery is
  staff-assisted, with a 30-minute single-use link.
- Audit logging covers account/recovery activity, lesson revisions and the listed
  content mutations. It is not immutable and cannot be treated as an independent
  security ledger; logging occurs after the content transaction commits.
- MP3 validates headers rather than decoding every file. Device microphone,
  permission/codec behavior and real mobile install flows need testing.
- Docker deployment is prepared but not built/run here. The old Render YAML is
  not a validated persistent-storage production configuration.

## Review sequence

1. Use START_HERE.md to inspect the learner and administration pages locally.
2. Review source content and language labels; add native audio and approve EPS.
3. Configure optional services only when ready; see INTEGRATIONS.md.
4. Change any existing legacy default administrator password via /account.
5. Validate an isolated restore, then plan a staged production cutover.

The source snapshot is retained locally as SOURCE_REVIEW.zip. Private backups
can be downloaded by an administrator; no private backup is in the source bundle.
Do not publish private backups or runtime databases. SOURCE_REVIEW.zip excludes
accounts, credentials, databases, receipts and uploaded runtime files.

AI voice authoring added after the initial local release: staff media studio,
Korean/Lao stock voice options, text consent, daily cap, SSML escaping, WAV
validation, reusable cache and AI provenance labels. Tests mock synthesis only;
Azure credentials, regional voice availability and pronunciation review remain
pending. See INTEGRATIONS.md.

Staging preparation: user selected Render Free for a separate disposable demo.
The Blueprint uses no disk and disables paid providers; reviewer protection and
a bilingual data-reset notice are implemented. 52 tests pass. Render reports Live for commit 628f0d4, with health 200 and reviewer gate 401.
The user confirms /health returns status: ok on mobile data. Direct HTTPS from
this machine still fails, but the user subsequently confirms both reviewer and
admin sign-in work. Free staging deployment and access acceptance are complete.
See STAGING_RENDER.md for evidence and private login instructions.
No production service was modified.

## Content review queue (local, after staging release)

Added /content-readiness for approved administrators and teachers, linked from
management. Lists active EPS questions with unverified effective review state or
missing Lao text counterparts, and published vocabulary missing Korean/Lao audio
links. Includes counts, search, type filtering, 30-item pages and direct editor
links selecting the exact item. Review overrides take precedence; archived EPS
and draft vocabulary are excluded. It checks presence, not translation quality,
remote audio availability or pronunciation. It never edits content automatically.

54 tests pass, including role denial, review precedence, exclusions, missing
translations/audio and pagination. JavaScript syntax checks pass. Isolated browser
QA with a synthetic teacher verified report rendering, search, empty state and
EPS editor deep link. This addition is included in staging release b623171.

## EPS explanations and dictionary metadata

Teachers can assign EPS difficulty and Korean/Lao explanations. Practice filters
by assigned level; reading passage groups are retained whole. Explanations and
answer keys are withheld until grading, including retry and timed-mock payloads.
Completed practice has an owner-only, no-store history review endpoint. Original
snapshot explanations survive later bank edits; mock results also retain the
original question and explanations. History offers review for practice and mocks.

Vocabulary authoring now supports part of speech and library images, with a
picker and image preview; the dictionary displays both. Optional CSV columns
part_of_speech/image_url survive preview/import as drafts. A separate additive
metadata table preserves existing vocabulary IDs and the old nine-column table.
A public word or active EPS item requires a published image asset. Frontend EPS
image attributes are escaped. Admin-only EPS review navigation is hidden for
teachers; their bank editor remains available.

59 isolated tests pass, covering snapshot privacy, effective difficulty, complete
passage grouping, result ownership, image publication guards, metadata preservation
for old clients and CSV draft import. Browser used synthetic data on isolated8036:
author saved metadata → dictionary displayed/decoded image and part of speech;
advanced-only practice selected the three synthetic questions, grading revealed
bilingual explanations, and history reopened the original explanations. Question
editor difficulty/explanation loading and saving were verified.

The extended vision and unfinished work are tracked in PLAN_STATUS.md. This
batch is included in staging release b623171.

## Listening practice and mock exams

Staff can author reading/listening questions and choose published library audio.
Listening practice and timed mocks have separate catalogs, settings and histories;
old question IDs and reading defaults are preserved. Native audio controls allow
replay; this is practice, not a claim of official EPS playback rules. AI provenance
is derived from stored generation metadata. No real listening corpus is seeded.

The server excludes unavailable audio and incomplete passage groups from new
selection, preserves snapshots, enforces deadlines and resumes saved attempts.
66 isolated tests cover mode isolation, audio publication/access, grouping, exact
size selection, answer privacy, owner checks and immutable results. Synthetic
browser QA verified authoring, five audio players, real WAV decoding, answer save,
reload resume and 5/5 submission. The WAV was a test tone, not reviewed speech.
Real device playback and teacher-reviewed listening material remain pending.

2026-10-16 staging update: manually deployed source b623171 on the existing Free
service (deployment dep-db8nth6q1p3s738omssg). Build and startup logs report live,
health 200 and unauthenticated root 401. No production service was changed.

## Configurable mock scoring (local, not yet deployed)

Administrators can set 1–100 points per correct answer by category, independently
for reading and listening. Unspecified categories default to one point. Wrong or
unanswered questions earn zero. The rubric is snapshotted when an attempt starts;
later edits do not change active or completed attempts. Results and history show
weighted points alongside raw correct counts; existing results retain compatibility.
Old clients that omit weights preserve the saved rubric. This is custom practice
scoring, not an official EPS pass threshold or weighting claim.

68 isolated tests pass. Added checks cover mixed-category totals, immutable
scoring after settings edits, invalid weights, legacy attempts and history. Browser
QA used synthetic admin/audio/questions: save 2/4-point categories, start, answer
four of five and submit → 14/16 points, 4/5 correct. A 320px result viewport had no
horizontal overflow. The full extracted release and JavaScript checks also pass.

## Content administration audit (local, not yet deployed)

Successful course/lesson, vocabulary/import/audio, EPS bank/review, mock settings,
media/TTS review, moderation, membership settings/payment review and legacy lesson
mutations now record actor, action, item IDs and timestamp. Read-only import
previews, rejected requests and learner actions are excluded. Request bodies,
query strings, credentials, audio and receipt contents are never copied.

Administrators can search the audit by actor/action/target, refresh and page
through 100 entries at a time. Teachers can generate content events but cannot
read the administrator log. The endpoint uses no-store. This is metadata history,
not a before/after diff or tamper-proof ledger. A failed audit write emits an
operator error after the content commit; it cannot roll that commit back.

71 isolated tests cover safe metadata, rejected/preview exclusions, staff/read
roles, literal search and pagination. JavaScript and extracted release checks pass.

Synthetic browser QA verified audit rendering, actor search, empty results, refresh
and a 320px viewport without horizontal overflow.

## Dedicated speaking exercises (local, not yet deployed)

Teachers and administrators can author Korean/Lao prompts with title, translation,
beginner/intermediate/advanced level and library sample audio at /speaking-studio.
Publication requires public audio; withdrawing an audio asset hides the exercise
from new learner selection. AI sample provenance comes from stored metadata.
The existing speaking area filters exercises by language/level and loads their
reference text, translation and sample into listening/recording controls.

Learners may explicitly mark a prompt practiced. This is owner-scoped self-report,
not pronunciation scoring, mastery or proof of recording. No audio is uploaded
for this action. A changed exercise revision requires a fresh practice report;
repeated reports on one revision preserve the original time. Author updates reject
stale revisions. Speaking authoring participates in content mutation audit.

74 isolated tests pass. Synthetic browser QA created/published a prompt, selected
it in the learner view, saved a self-report and confirmed its persisted checkmark
after reload. A 320px viewport had no horizontal overflow. Test sample is silence;
no microphone permission, real speech quality or real provider result is claimed.
Teacher-approved exercise content and physical device recording remain pending.

## Teacher course assignment (local, not yet deployed)

Administrators configure /teacher-assignments: broad access (the preserved default)
or only selected structured courses. Restricted teachers cannot create new
courses; an administrator must create and assign them. An empty restricted list
allows no course authoring. The server filters draft/answer-bearing course lists
and denies unassigned lesson creation/save/publish/unpublish, sequence changes
and revision/history access, even by direct API. Course dashboard counts follow
the configured scope. Assigned staff preview access does not grant preview access
to other premium courses; normal learner entitlement/prerequisite checks apply.

Assignments are read on every request; role/status rejection still overrides
them. Dictionaries, EPS, media and speaking exercises remain shared staff tools.
No actual teacher permissions were changed: QA used isolated synthetic accounts.
77 tests pass, including cross-course denial, revision privacy, revocation, empty
scope, broad default compatibility, admin-only assignment, atomic validation and
premium non-bypass. Browser verified assignment save/reload and 320px layout.

## Personal EPS analysis (local, not yet deployed)

/learning-analysis aggregates completed practice and mock exposures by skill,
category and mode over 7/30/90/365 days, ordered by lowest raw correct-answer
percentage. It shows unanswered and unverified counts and links back to the
selected reading/listening practice mode. Repeated attempts count again; these
are observed answer rates, not independent unique-question or language mastery
scores. Weighted exam points are deliberately separate from correctness rates.
Legacy practice without snapshots is excluded and counted in a coverage notice;
unfinished attempts are excluded. Stored snapshots/results determine statistics,
not the current question bank. The no-store API scopes all queries to the signed-in
approved account and returns no answer keys, prompt text or other learners' data.

79 isolated tests pass, covering exposure totals, repeats, periods, missing
snapshots, unfinished exclusion and cross-account privacy. Synthetic browser
verified reading/listening groups (2/4 total), period selection and listening
practice navigation. A 320px viewport had no horizontal overflow. My Learning
now labels both skills and displays weighted mock points with raw correct counts.

## Account recovery and media cache corrections (local)

Successful password replacement now marks all outstanding recovery tokens for the
account used, for both authenticated password changes and recovery. A failed
current-password check leaves a valid recovery link unchanged. Successful recovery
adds a token-free account audit event. All /media/ responses now use no-store,
including draft/public/range responses and access-denied responses. Requests
continue to check current publication and account role before serving bytes.
This header governs new responses; it cannot retract files already downloaded.

81 tests pass. Regression checks demonstrate outstanding link rejection after
password change, unchanged credentials after attempted reuse, draft access denial,
published audio responses, revoked audio with conditional request headers, and
staff range-response cache headers. All tests use synthetic accounts/runtime.

## Speaking recording lifecycle corrections (local)

A recording captures its language/reference when recording starts. Prompt/language
changes clear old playback, provider consent and previous analysis; controls stay
locked while microphone access/recording/stop is pending. Cancellation ignores
late permission and recorder events and releases audio tracks, including pagehide.
A provider submission captures its blob/reference before asynchronous conversion
and ignores stale results after cancellation. Samples/device synthesis pause when
recording starts. Auto-stop is 30 seconds, matching the configured speech endpoint.

82 tests pass, including a synthetic Node recorder lifecycle suite: immutable
prompt context, late permission cancellation, late stop/data suppression, replacing
a recording, auto-stop, denied permission and recorder failure. This uses fake
media objects, not a physical microphone. Browser verified page startup and Lao
language switching without console errors; no microphone permission was requested.
Physical-device recording/codec evaluation remains pending.

## Direct MP4 lesson clips (local, not yet deployed)

Staff can upload H.264 MP4 with optional AAC audio (10 MB, 5 minutes, at most
1920×1080 pixels). imageio-ffmpeg 0.6.0 supplies the local FFmpeg dependency.
Validation uses local file/pipe protocols, bounded timeouts, one concurrent video
check and one decoder thread. The clip is remuxed with global metadata removed
and faststart enabled, then fully decoded before storing it as private draft
media. No external upload, remote URL fetch or paid provider is used.

The media studio, course media picker, editor preview and learner view support
native MP4 controls alongside existing YouTube blocks. Publishing a lesson requires
its video asset to be published. Shared library publication makes the media URL
public; this is not a private paid-video streaming service. Draft serving and
withdrawal retain staff/publication checks and no-store, including range requests.
Private backups include MP4; validated restore accepts MP4 only in media paths.

87 tests pass, covering actual generated H.264/AAC decoding, metadata removal,
upload/draft/publication, kind mismatch, withdrawal, range delivery, timeout
recovery, learner role denial and backup restoration. Isolated browser loaded a
synthetic blue clip with duration 1s, 64×64, readyState 4 and no media error.
320px overflow check passed. Physical-device playback and Linux/Render execution
of the new dependency remain unverified. No real lesson video was used.

## Adjacent lesson navigation (local)

Structured lessons now show previous/next controls in a stable position. They
follow adjacent catalog order within one course, retain server-provided locks,
and permit revisiting completed lessons. The first/last boundary is explicit.
Deep links select the actual course language and retain it in the URL.
Leaving a lesson pauses native media and clears embedded video sources.
Late lesson loads and completion responses are guarded from replacing a newer
lesson view; completed progress still refreshes the catalog.

88 tests pass. Added Node checks cover first/middle/last boundaries, locked flags,
legacy exclusion, missing IDs and course separation. Existing server tests retain
prerequisite/membership enforcement. Synthetic browser verified locked next →
completion → unlock, next/previous traversal, correct language from a deep link
and disabled final-course boundary. 320px overflow check passed.

## Homepage settings (local)

Administrators can edit Lao/Korean homepage headings, subtitles and an optional
public help link at /site-settings. Brand identity remains THANA KOREAN. Settings
are plain text, escaped into HTML attributes/content and switched via textContent.
Help links accept HTTPS without embedded credentials or a simple local page path;
blank hides the link. Public copy is explicitly labeled as public in the editor.

One additive SQLite record stores settings and revision. Saves reject stale
revisions and unknown fields; restoring defaults first loads an unsaved draft.
Changes are recorded by the content audit. Server secrets/provider flags are
not exposed or editable through this form. Existing defaults remain unchanged
unless an administrator saves a new value.

91 tests pass, including role denial, safe rendering, invalid URL/field rejection,
stale-save protection and audit metadata. Synthetic browser saved bilingual copy
and a local help link, verified public Lao/Korean switching and 320px layout.
No real homepage settings, production or remote source were changed.

## Optional email registration and verification (local)

/email-account supports username + email registration, private queued verification
messages, password-confirmed one-time links (30 minutes) and rate-limited resend.
New accounts remain students pending administrator approval. Both verification
and approval are required for these accounts to log in; legacy username signup
remains available. No email-based account merging or automatic role grants occur.
Links bind to account password version; replacement invalidates old verification.
Email-required accounts remain blocked if their platform email row is missing.
Deleting a student clears its email record/challenges and pending message body.

Email registration is disabled unless explicit server SMTP/origin configuration
is valid. Web requests only queue messages; scripts/deliver_email.py is the
explicit delivery worker. It requires verified STARTTLS/587 or TLS/465, leases
jobs, retries with backoff and clears recipient/body after delivery or expiry.
The private outbox temporarily contains verification links: keep its SQLite DB
and backups private. Source packages contain neither queue nor credentials.
ASCII email addresses are supported; users still log in with their username.
Self-service email password recovery is not added by this registration feature.

100 tests pass, including verification/approval separation, replay/expiry, resend,
rate limits, normalized uniqueness, password-version binding, account deletion,
mocked SMTP delivery/retry/scrubbing and STARTTLS/TLS context validation. Synthetic
browser verified form validation, explicit confirmation with a fixed test token,
fragment removal, same-page new-link handling and 320px layout. No real email
was sent. Live SMTP delivery, worker scheduling and provider acceptance are pending.
Also corrected /hub to use the same homepage settings context as /.


## Course levels and catalog filtering (local, not yet uploaded)

The editor can assign beginner/intermediate/advanced/EPS-TOPIK or unspecified
level to each structured course. Existing structured and legacy courses remain
unspecified until a teacher classifies them; no source lesson/question IDs change.
An additive course_levels table retains the five-column courses schema and
idempotent initialization. Learners see bilingual level labels and can combine
the level filter with language and text search. Levels describe the course;
they do not certify learner proficiency or alter membership/prerequisite access.

The staff endpoint checks current course assignment and role, validates its exact
payload and rejects stale revisions. Successful updates enter the content audit.
102 isolated tests pass, including default compatibility, all level transitions,
public/admin readback, stale-save denial, audit events, malformed payloads and
restricted/unassigned/student/anonymous mutation denial. The extracted release
also passes fresh bootstrap, seeding twice, SQLite integrity, HTTP smoke and all
static JavaScript syntax checks. Isolated browser QA saved a synthetic course
level, reloaded to confirm persistence, and verified beginner/advanced filters
combined with text search and empty results. The learner catalog had no horizontal
overflow at 320px. Evidence: docs/course-level-preview.png (local screenshot,
excluded from the source bundle). No real course classification was changed.


## Draft lesson list reordering (local)

The editor offers draggable lesson rows and accessible up/down buttons. A whole
course order request includes every lesson ID and current revision. The server
checks staff assignment, rejects missing/duplicate/foreign IDs and stale lists,
and applies changed draft positions/history revisions in one SQLite transaction.
Published snapshots, question IDs, lesson IDs and completion records are preserved.
Teachers review and publish each lesson separately to apply its new order publicly;
partial publication can temporarily produce equal public positions (stable ID tie
ordering still applies). This is not an atomic whole-course publish action.

Filtering disables reorder controls; unsaved lesson edits block reordering.
Pending requests lock course switching and lesson editing. Successful requests
record course-level mutation metadata in the content audit. Existing lesson
revision history retains content before each changed position.

104 isolated tests pass. New tests cover atomic draft-only changes, unchanged
published order/content, history revisions, no-op behavior, stale-list rejection,
malformed/duplicate/incomplete/foreign IDs and current teacher/student/anonymous
permissions. Full extracted release checks and static JavaScript syntax pass.
Synthetic browser verified up/down persistence after reload, filtered disabled
controls, unsaved-edit protection and 320px layout with no horizontal overflow.
The initial HTML5 row drag attempt was inconclusive and has been replaced by
explicit pointer handles (see acceptance below). Earlier screenshot evidence is
local at docs/course-order-preview.png and excluded from source bundles.


## Pointer lesson drag acceptance (local)

The ↕ button now captures pointer input explicitly, handles cancellation/lost
capture, ignores secondary pointers/buttons and requires movement before dropping.
A click alone never changes order. Dropping outside the current list or onto the
same lesson does nothing. Filter/dirty/pending checks run again at release.
Keyboard up/down controls and server revision/assignment checks remain in place.

105 tests pass, including synthetic Node pointer lifecycle tests for successful
movement, cancellation, lost capture, no movement, blocked starts/releases,
secondary pointer/button rejection and outside/same-target drops. Full extracted
release and JavaScript checks pass. Browser pointer drag moved the first synthetic
lesson into the third position, and reload retained the new order. Console had
no errors and 320px layout had no horizontal overflow. Evidence is local at
docs/course-drag-preview.png (excluded from source packages). Touch hardware,
auto-scroll beyond the viewport and physical-device acceptance were not tested.


## Reusable lesson vocabulary (local, not yet uploaded)

Teachers can search the published shared dictionary inside the block editor and
insert a word reference, then preview and publish the lesson. The lesson keeps
the existing vocabulary ID rather than duplicating its translation/examples.
Editor and learner cards display current Korean/Lao text, part of speech,
examples and available image/audio. Shared dictionary edits therefore affect
all lessons referring to that word; this is explicitly described in the picker.
Word references are live, unlike the lesson's text/quiz publication snapshot.

Publication rejects missing/unpublished words. Public lesson payloads resolve
only the currently published word and overwrite any client-supplied copied word
payload. A withdrawn/deleted word becomes an unavailable notice, never draft
text; a missing/withdrawn library image is omitted. Media URLs continue through
their existing access checks. Shared words are public dictionary content even
when referenced by a premium lesson; the course itself retains its membership
and prerequisite checks. Existing lesson/question/word IDs remain unchanged.

108 isolated tests pass, including reference validation, current updates,
withdrawal/deletion, ignored injected copies, draft save versus publish guards,
missing-image omission and premium course denial. Extracted release verification
and JavaScript syntax pass. Synthetic browser selected a shared word, previewed,
published and viewed its bilingual card/examples as a learner; 320px layout had
no horizontal overflow. No real curriculum was edited. Screenshot evidence is
local at docs/lesson-vocabulary-preview.png and excluded from source bundles.


## Lesson learning objectives (local)

Structured lesson authoring now includes optional learning objectives, limited to
2000 characters by the server and editor. Preview and learner view display plain
text before the main lesson blocks. Blank/older lessons hide the section.
Objectives are part of the existing draft/published JSON and revision snapshots;
saving a new draft does not change published objectives. No database migration
or original source lesson modification is needed.

110 isolated tests pass. Coverage includes bilingual multiline objectives,
draft/publication separation, historical snapshots, old content without the field,
type/length rejection and the 2000-character boundary. Full extracted release
and JavaScript syntax checks pass. Synthetic browser authored and published
bilingual objectives and confirmed they appear before learner content. Screenshot
evidence is local at docs/lesson-objectives-preview.png, excluded from bundles.
Teacher-reviewed objectives for actual courses remain content work.
