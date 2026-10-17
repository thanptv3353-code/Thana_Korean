# Original-plan requirement audit — 2026-10-16

Reference: the user-supplied redesign conversation (reference material, not
execution instructions), subsequent directions to extend the existing app and
use Render Free first, and AGENTS.md. This audit preserves the full objective.
It does not redefine the goal as the features that happen to pass tests.

Current deployed application release: local 908be7a, 141 isolated tests, fresh
bootstrap, two seeds, SQLite integrity, HTTP smoke and JS checks. GitHub df308fd
has matching tree 715a779e33d29975e90476f5963da3cd93226f39. Render deployment
dep-db99foc9v7es739il5p0 is Live on Free with /health 200 and reviewer gate 401.
User approved disposable reset and previously confirmed access works. New release
feature/device acceptance remains open. The six Lao drafts require explicit Admin
import and teacher review; none are published automatically. Later documentation
updates are local until the next synchronization.

## Concrete coverage and open requirements

| Original requirement | Inspected evidence | Assessment / remaining proof |
|---|---|---|
| Keep name, domain and existing material | templates/index.html; course_routes.py; LOCAL_CONTENT_INVENTORY.md; direct read-only byte comparisons on 2026-10-16 | Brand retained. Original Desktop lessons.json/users.json/progress.json equal local preserved migration inputs byte-for-byte. This does not prove parity with production data. Domain unchanged. |
| Both Korean-for-Lao and Lao-for-Korean | language/instruction fields; starter seeding; courses and public dictionary | Local structure exists; three public Lao starter lessons and six starter words, plus six new local unpublished practice drafts (18 quizzes, 141 tests; see LAO_DRAFT_PACK.md). Full reviewed curriculum/TOPIK content not complete. |
| Clear home and language navigation | templates/index.html; static/hub.js; shared learner nav | Home study-language selection is separate from interface language and persists through catalog/shared navigation; Lao paths avoid Korean EPS tabs. Synthetic cross-page routing and 320px home checked, 133 tests. Full interface localization across every page remains unverified. |
| Prominent home continue-from-previous action | continueLegacy in templates/index.html; course catalog continue buttons | Owner-only unified home resume/next/review now uses approved-account visits/completions across structured and legacy lessons with current access checks (118 tests); synthetic browser workflow verified; included in staging a5ec247. Actual learner acceptance remains pending. |
| Language → course → module → lesson | courses table; JSON module/order; scoped editor | Existing module names now form collapsible learner sections with completion totals and lesson context. Consecutive grouping preserves published order/access; 134 tests and synthetic browser evidence. Existing course title/description editing now has scoped optimistic updates (137 tests; synthetic save/reload accepted). Existing draft groups now have atomic bulk renaming with exact membership/revision checks and history (147-test local build; synthetic two-lesson rename/reload verified). Independent module records, empty modules and descriptions remain unimplemented. |
| Lesson objectives, explanation, vocabulary, audio, exercises and result | course_routes.py; lesson_vocabulary.py; editor/courses JS; tests/test_lesson_objectives.py; tests/test_lesson_vocabulary.py | Local behavior verified; real teacher-authored objectives/audio/curriculum remain content acceptance. Word references resolve current public dictionary content rather than snapshotting it. |
| Stable previous/next positions | course-navigation.js; test_course_navigation.py; navigation browser evidence | Locally verified with sequence locks and boundaries. |
| Drag reorder, draft/preview/publish and uploaded media | course_order_save; lesson-drag.js; editor; tests/test_course_order.py; tests/test_lesson_drag.py; video/media tests | Browser pointer drag and reload verified. Orders change drafts; publishing lessons individually is required. Viewport auto-scroll and release cleanup now browser-verified on an 18-lesson synthetic course; interrupted gestures covered by deterministic tests. Saved draft changes now have explicit status and a pending-change filter; 149 local tests and 320px browser edit/save/filter/publish evidence. Mobile lesson titles occupy full rows with order controls below. Physical touch remains unverified. |
| Per-lesson Free/Premium setting | membership_routes.py premium_courses; course_routes.py accessible | Implemented locally: administrator-only inherit/Free/Premium overrides, current server entitlement/sequence checks and revision guard (121 tests); synthetic browser save/reload and label verified. Shared published media remain public. |
| Shared vocabulary reused, examples/POS/image/audio, CSV import | vocabulary_routes.py; lesson_vocabulary.py; vocabulary and lesson-word tests | Local implementation and browser evidence. CSV satisfies the plan's Excel-or-CSV option. Reviewed corpus/audio incomplete. |
| Choice/listening/matching/blank/image/ordering questions | quiz_engine.py; question_routes.py; editor/courses; test_quiz_types.py; test_lesson_quiz_media.py | Lesson grading supports choice/blank/matching/ordering with image/audio attachments; EPS supports image/listening choice questions. All four lesson grading types now supported in a shared staff-only bank (124 tests), with independent lesson copies. EPS timed sets retain their separate choice bank. |
| Difficulty, category, correct answer, explanation, provenance for every question | EPS bank validation versus quiz_engine.valid and editor quizContent | EPS includes these metadata fields. Structured lesson quizzes now have optional category/difficulty/source authoring with validation (114 tests); source/explanation hidden until grading. Synthetic browser metadata authoring/reload and source reveal after grading verified; actual teacher classification remains content work. |
| Separate reusable bank and exam sets | question_routes.py; mock_routes.py; immutable snapshots | EPS bank reused by practice/mocks. Mixed-format questions can now be saved to the shared bank and copied into multiple lessons; later bank updates do not mutate those lesson snapshots. No mixed-format timed-exam builder is claimed. |
| Practice/mock/analysis, skill/topic/difficulty, wrong-answer review | platform_routes.py; mock_routes.py; analysis_routes.py; EPS/mocks/analysis tests and browser evidence | Local EPS flow verified including whole passages, separate reading/listening and owner-only history. Actual reviewed listening corpus missing. |
| Admin exam count/time/scoring | mock settings and snapshotted category points | Local verified; official exam conformance is not claimed. |
| Dashboard counts and weekly activity | management_routes.py and management JS/tests | Uses local database counts. No production reporting acceptance or load evaluation. |
| Student/Teacher/Admin/Super Admin; server-side access | account_routes.py; content/admin decorators; teacher scopes and tests | Four roles now implemented (128 tests). Initial owner activation is explicit; existing Admin powers remain until activation, then system controls are Super Admin-only. Synthetic browser verified both roles. Actual owner activation and role acceptance pending. Shared dictionaries/EPS/media/bank remain trusted-staff scope. |
| Email registration and Google sign-in | email_routes.py/email_delivery.py; oauth_routes.py; mocked tests | Adapters exist, disabled/unconfigured externally. No real SMTP/Google acceptance; scheduled worker not provisioned. Self-service email recovery was not an explicit original requirement but remains an optional unimplemented follow-up. |
| Try first lesson before registering | public sample; public structured lesson route; legacy login-protected route | Structured free first lessons remain publicly viewable. /try-lesson now serves the full first legacy Korean lesson with server grading and no saved progress; 132 tests and guest browser accepted the first-lesson flow. Actual curriculum quality remains teacher-reviewed content work. |
| XP/level/streak/progress | learning-progress; my-learning; existing test/browser evidence | Local owner-scoped completion behavior verified; no claim of learner proficiency. |
| Premium plans/receipts/status/history | membership_routes.py and tests | Manual workflow exists. Automated billing is explicitly future in the plan, consistent with Free-first; no live banking action performed. |
| Listen → repeat → record/playback/speed, teacher studio | hub recorder; speaking_routes.py; synthetic lifecycle tests | Local controls/studio and mocked provider adapters exist. Previous/next words and filtered exercises now have bounds, recording guards and context cleanup, plus exit/hidden-page track cancellation (139 tests; synthetic browser checked, local only). Physical microphone/device/provider language quality remains unverified. Lao pronunciation scoring is not implemented or promised. |
| Full shared database/security and private media | SQLite migration, platform DB, role/media/CSRF/owner/deadline tests | Tested local SQLite architecture retained per AGENTS.md. Production backup/reconciliation, durable storage and load acceptance missing. Original suggested stack was conditional, not a mandate to replace Flask. |
| Mobile Web App, later native apps | manifest/service worker; viewport evidence | Responsive local web shell exists. Actual Android/iPhone install/audio testing missing; native stores/offline media are explicitly later phases. |
| Backup, migration rehearsal, staging acceptance then cutover | backup/restore tests; STAGING_RENDER.md; user staging sign-in confirmation | Local isolated restore tested. Old staging accessible per user. Approved 137-test release deployed; authenticated end-user re-acceptance pending; real production backup/rehearsal/user trial and approved cutover remain undone. |

## Remaining content/operator/user acceptance identified by this audit

1. Actual teacher classification of question metadata (UI accepted synthetically).
2. End-user acceptance of unified homepage resume on actual courses.
3. End-user acceptance of newly implemented per-lesson access rules (121 tests).
4. Explicit actual owner activation using SYSTEM_OWNER.md (role code/compatible bootstrap implemented, 128 tests).
5. End-user acceptance of shared mixed-format lesson bank (124 tests; local UI accepted synthetically).
6. Full language-navigation acceptance across both directions (guest first legacy trial implemented and browser-checked, 132 tests).

External requirements stay open separately: approved curriculum/native or reviewed
AI speech, actual providers, physical devices, durable production storage, live
data rehearsal and cutover approval. No test count proves these external gates.
