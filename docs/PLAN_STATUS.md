# THANA KOREAN implementation status

Source: user-supplied redesign conversation (reference material), subsequent user
instructions to extend the existing app, use Free hosting first and continue.
This file tracks the remaining vision; previous local-release checklists do not
make unfinished requirements complete or remove them from the longer-term plan.
Production changes still require the user's approval. Original Desktop sources
must remain untouched. Current architecture is the authorized existing Flask app.

| Plan area | Implemented evidence | Remaining work / acceptance |
|---|---|---|
| Brand and two learning directions | Home, guest first-lesson trial, Korean legacy material, Lao starter, catalogs and shared navigation | 48 newly authored local foundation drafts (24 per direction; 206 exercises) await owner review/audio. Intermediate/advanced and full TOPIK expansion remain pending. |
| Course hierarchy and lesson authoring | Courses/modules/ordered blocks, optional lesson objectives, per-lesson Free/Premium, per-question library image/audio, media picker, shared mixed-format question bank and mixed quizzes, draft/publish/revisions, access and sequential rules, bounded direct MP4 clips and native preview/player, adjacent previous/next controls, staff-assigned course levels and learner level filter | Physical-device playback/touch acceptance |
| EPS practice and analysis | Bank/editor, snapshots, server grading, incorrect retries, complete passage groups, difficulty filter, bilingual answer explanations and private historical review; configurable category points with immutable run rubrics; owner-only multi-attempt analysis by category/skill/period | Teacher-reviewed listening audio content |
| Timed exams | Reading/listening mocks, separate settings, server deadline, save/resume, immutable results and category analysis | Real-device audio acceptance |
| Shared vocabulary | CSV preview/deduplication/draft import, examples, images, part of speech, both language audio uploads, saved words and spaced review, reusable lesson word references | Full reviewed vocabulary corpus; native XLSX is optional because the design allows Excel or CSV |
| Speaking | Word selection, uploaded sample audio, speed control, temporary recording/playback, optional recognition/Korean scoring adapter, teacher-authored exercises/levels and revision-aware self-report | Teacher-reviewed exercise content; real microphone/device evaluation; native audio; validated provider quality. Lao pronunciation scoring is not implemented |
| Accounts and roles | Username/password, approval, Super Admin/Admin/Teacher/Student checks, recovery, profile, optional Google adapter, administrator-configured teacher course scope, optional email registration/verification and private SMTP outbox worker | Live SMTP/worker acceptance; self-service email password recovery; explicit initial Super Admin activation and live role acceptance (compatibility retains legacy Admin powers until activated) |
| Motivation and personal summary | XP, level, UTC+7 streak, progress, unified homepage resume/next, continue/next and owner-scoped summary | User feedback/acceptance on actual courses |
| Premium | Manual plan/receipts, administrator review, time-limited entitlements, course enforcement | Automatic banking/recurring billing remain future, consistent with Free-first instruction |
| Administration | Central dashboard, content/user/media/question tools, account audit, trend, moderation, content readiness queue, searchable content mutation metadata, bilingual homepage/help-link settings | Private live-service configuration remains external; before/after audit diffs and independent tamper-resistant logging remain future |
| Data preservation and migration | Original JSON preserved, transactional SQLite, isolated backup/restore, preserved IDs | Actual production backup/reconciliation and migration rehearsal with the live data, before cutover |
| Mobile web and apps | Responsive pages, manifest/icons and safe offline notice | Physical Android/iPhone install/audio tests; full offline lesson downloads and native stores are later phases |
| Hosting/release | Separate Render Free staging, user confirmed health + reviewer/admin sign-in | 149-test source d4f0b9f deployed with exact local 2477ffb tree; Render dep-db9de6vavr4c73dlablg Live, health 200/reviewer 401, after explicit reset approval. Latest authenticated end-user acceptance pending. Free deploys reset ephemeral files. Durable production storage still requires a decision |

## Latest local batch

- Staff content readiness queue and exact-item editor links (54 tests).
- EPS difficulty/explanations, private history review, dictionary image/part-of-
  speech authoring and CSV metadata import (59 tests).
- Images must be valid library images; publishing/activating content cannot expose
  a private image. Original imported questions are not silently assigned levels.
- Listening authoring/practice/mocks, published audio guards, separate settings and
  saved attempts (66 tests); synthetic browser playback/save/reload/submit passed.
- Configurable category points for reading/listening mocks (68 tests), browser
  checked 14/16 weighted points versus 4/5 raw correct answers; local only.
- Speaking exercise authoring and language/level filters, private revision-aware
  practice self-report (74 tests); synthetic browser saved/reloaded progress.
- Teacher course scope, private draft/revision enforcement and assignment UI
  (77 tests); synthetic browser saved/reloaded one assigned course.
- Personal EPS analysis across completed attempts, period filters, unanswered and
  unverified counts, and skill-aware practice links (79 tests); local only.
- Outstanding recovery-link revocation on password replacement and no-store
  media responses (81 tests); local only.
- Recording context capture, cancellation/track cleanup, stale-result suppression
  and 30-second auto-stop (82 tests, synthetic media only); local only.
- Bounded MP4 uploads, full local decode validation, native lesson player and
  backup/restore (87 tests); synthetic browser decoded a real generated clip.
- Adjacent previous/next lesson controls, deep-link language correction and
  stale-view guards (88 tests); synthetic browser verified sequential traversal.
- Administrator homepage copy/help-link settings with revision guard and public
  text escaping (91 tests); synthetic browser verified both language versions.
- Optional email registration/verification, private queued SMTP delivery and
  password/version/approval enforcement (100 tests); live delivery remains pending.
- Course levels with preserved unspecified defaults, scoped revision-protected
  editing and combined catalog filter (102 tests); synthetic browser verified
  persistence, combined filters/empty results and 320px layout.
- Whole-course draft ordering with revision guards, history and scoped access;
  keyboard buttons/browser persistence verified (104 tests). Public order changes
  only when lessons are individually published.
- Explicit pointer drag handles replace inconclusive HTML5 row dragging; browser
  drag and reload persistence verified (105 tests), including cancellation guards.
- Shared published dictionary words can be inserted into lesson blocks by ID,
  with live public resolution and withdrawal guards (108 tests); synthetic
  browser verified picker, preview, publication and learner rendering.
- Optional lesson objectives in draft/publication/history with plain-text learner
  display (110 tests); synthetic browser verified authoring and published view.
- Per-question library image/audio picker and learner controls with kind/public
  guards and unchanged grading/privacy (112 tests); synthetic browser verified
  actual image decoding, media selection/publication and 100% grading.
- Embedded quiz category/difficulty/provenance authoring and server validation
  (114 tests); provenance withheld until grading; synthetic browser now verified
  metadata persistence, public labels and post-grading source.
- Unified owner-only homepage resume across legacy/structured visits and
  completions, current access checks and deletion cleanup (118 tests); synthetic
  browser verified visit→home resume→completion→next recommendation.
- Per-lesson inherit/Free/Premium overrides with server entitlement/sequence
  enforcement and admin-only revision guards (121 tests); synthetic browser
  verified save/reload and the lesson Premium label.
- Shared mixed-format lesson bank with staff-only answers, optimistic revisions,
  archive/restore and independent lesson copies (124 tests); synthetic browser
  verified save/search/copy/publish/archive/restore and 320px layout.
- Distinct Super Admin with opt-in initial activation, protected system controls
  and legacy compatibility (128 tests); synthetic browser checked ordinary Admin
  denial/hidden controls and owner access. No actual account role changed.
- Public full first-lesson trial with writing, unsaved server quiz/review grading
  and locked-media/answer protections (132 tests); guest browser verified 7% for
  one of 15 correct and 320px layout.
- Independent study/interface language preferences with shared navigation (133 tests); synthetic cross-page routing and 320px home checked.
- Long-course pointer edge auto-scroll with interruption cleanup; expanded gesture checks and real 18-lesson browser drag/reload verified (133 tests).
- Learner module sections with per-section completion totals and course/module context (134 tests); browser verified keyboard expansion, cross-module navigation, completion and 320px layout. Independent module CRUD remains unimplemented.
- Existing structured course title/description editing with server scopes, optimistic revisions and unsaved edit guards (137 tests); synthetic browser save/reload and learner text verified.
- Speaking previous/next word/exercise navigation, bounded visible queues, recording-state guards and old audio cleanup (138 tests); synthetic Korean/Lao/empty-filter and 320px browser checked. Local after the 137-test staging release.
- Speaking view exit/hidden-document cleanup releases pending/active capture and suppresses late audio (139 tests, synthetic only); non-speaking initial hash and return-state browser checked. Local only.
- Six additional Korean-instruction Lao practice drafts and 18 mixed quizzes, explicit Admin import with idempotence/edit preservation and collision rollback (141 tests); local drafts populated, none published. Full reviewed curriculum still pending.
- Interactive staff draft quiz rehearsal with all four types, course scopes and no saved learning/authoring state (144 tests); browser verified correct grading, stale draft rejection and corrected 320px result layout. Local only after 141-test staging.
- Provider tests use mocks; no real AI call or paid resource has been enabled.

Open items above are intentionally not claimed complete. Building an adapter or
showing a disabled control is not proof that its external service works.


## Requirement-by-requirement audit

REQUIREMENTS_AUDIT.md maps the original plan to inspected code/tests and explicit
missing behavior. Per-lesson membership rules and embedded quiz metadata have since been added.
The mixed-format bank now supports explicit lesson copies. Super Admin separation is now implemented; activating an actual owner remains
an explicit operator step.
These code gaps remain part of the objective alongside the external acceptance.
