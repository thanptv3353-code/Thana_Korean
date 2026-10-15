# THANA KOREAN local web application handoff

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
| Assets | Reusable image/audio library, image re-encoding, draft/public visibility, protected uploads |
| Accounts | Existing password login and approvals, profile, 8–128-character new passwords, versioned PBKDF2, session invalidation on password change, login attempt limiting, single-use admin-assisted recovery |
| Administration | Role-aware dashboard, weekly activity, searchable accounts with status filters, account roles/status, content/media/question tools and account audit events |
| Premium | Configurable manual price/instructions, private receipts, review, one-time entitlement grant, server-side premium course checks |
| Community | Learner posts pending staff moderation, private pending visibility, publication and basic posting rate limit |
| Providers | Staff Azure AI voice generation, cached private WAV drafts and review-before-publish; Google OIDC adapter; OpenAI Responses Tutor; Azure WAV recognition and Korean pronunciation adapter, all disabled pending credentials |
| Storage | Transactional SQLite compatibility migration for legacy schemas plus platform SQLite; original JSON untouched |
| Operations | Full private backup, validated restore into empty directory, environment guide, Docker recipe, health route and safe bootstrap for fresh installs |
| Mobile | Responsive web UI, manifest/icons and offline notice; no private data cached by service worker |

## Validation

- 52 isolated unit/integration tests pass (Flask, storage, grading, access,
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
- Teachers are trusted content staff across the content library. Course-specific
  teacher assignments are not implemented. Only administrators manage accounts,
  receipts, payment settings and entitlements.
- Manual receipt verification is implemented; automatic bank gateways, refunds,
  full accounting and automatic recurring billing are not.
- The PWA shell is installable where supported, but full offline lesson/audio
  download and native Android/iOS store builds are not included.
- Self-service email recovery and email delivery are not configured. Recovery is
  staff-assisted, with a 30-minute single-use link.
- Audit logging covers account/recovery activity and lesson revisions; it is not
  a comprehensive immutable audit of every endpoint.
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
