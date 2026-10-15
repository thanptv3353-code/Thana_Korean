# THANA KOREAN repository review

Reviewed 2026-10-14. Repository: https://github.com/thanptv3353-code/Thana_Korean

## Scope and evidence

Static review of the downloaded default branch, including app.py, templates,
JavaScript, deployment configuration and lesson JSON. This is not a production
audit. The repository's data may differ from the live server. No live data,
deployment, domain configuration or remote repository was modified.

## Existing implementation

- Python Flask API with HTML/CSS and plain JavaScript; no Next.js application.
- JSON files for accounts, lessons and progress; process-local in-memory state.
- Registration requiring administrator approval; password login and sessions.
- Sequential lessons unlocked after a 70% lesson exam score.
- Homework, multiple-choice quizzes and lesson exams; best score and attempt count.
- Admin APIs for accounts, lesson CRUD, ordering, questions, YouTube links,
  progress overview and ZIP data backup.
- Repository lesson snapshot: 12 lessons, 11 homework questions, 165 quiz
  questions, 270 exam questions, zero video entries. YouTube support exists,
  but no video entries are present in this snapshot.
- Lao and Korean lesson title fields exist; this is not a complete bilingual UI
  or two independent learning tracks.

## Missing relative to the supplied plan

- Target and instruction languages, courses and modules, track-specific progression.
- Public sample lesson and redesigned mobile navigation/continue-learning flow.
- Central vocabulary library, audio library and bulk import with duplicate review.
- Microphone recording, listen-and-repeat, playback comparison and speaking editor.
- Exam sessions with server-controlled deadlines, question snapshots, configurable
  blueprints, listening questions and historical answer analysis.
- XP ledger, levels and timezone-aware streaks without duplicate rewards.
- Lesson blocks, draft/review/publish lifecycle, revision history and role permissions.
- Google sign-in, recovery flow, premium entitlement/payment integration.
- PWA configuration, AI assessment, community and native applications.

## Issues to address before production expansion

1. JSON state is loaded once per process. A thread lock does not coordinate
   separate workers; writes can overwrite another worker's changes. Use a
   transactional database and durable media storage before scaling.
2. Authorization relies on the role saved in the login session. Recheck the
   current account status and role on protected requests so rejection/deletion
   revokes an existing session.
3. The repository documents a default administrator credential and bootstraps
   one in code. Replace bootstrap with explicit private configuration and rotate
   any live account still using that default; do not print credentials in reports.
4. Registration accepts four-character passwords. Add stronger password rules,
   login throttling, recovery and CSRF protection for cookie-authenticated writes.
5. Grading converts submitted values to integers without validation; malformed
   input can fail requests. Validate answer types/ranges and question structure.
6. Empty exams grade as 0%, so a lesson without exam questions cannot satisfy
   the 70% progression rule. Define an explicit no-exam completion policy.
7. Current exams return correct answers after submission and have no timed exam
   session. Preserve this for practice but implement separate mock-exam behavior.

## Implementation order

1. Obtain a live-server backup and identify current hosting/authentication before
   migration. Preserve lesson IDs, account password hashes, progress and entitlements.
2. Build database migration with validation, dry run, idempotency, restore checks
   and explicit legacy-ID mappings. Test on copies, never overwrite source JSON.
3. Implement the two learning tracks, mobile learner UI and structured admin editor.
   Include basic audio/recording practice in this phase, not only phase three.
4. Extend the question bank, timed exams, vocabulary/import and reward system.
5. Integrate provider-backed assessment and payments after separate evaluation.
   Recognition of the expected text must not be labelled pronunciation accuracy.
   Korean and Lao assessment need separate benchmarks and fallback behavior.

Framework selection remains provisional: the supplied Next.js/TypeScript plan is
possible, but retaining Flask is also possible. Decide after evaluating migration
and maintenance needs, rather than rewriting solely to match a suggested stack.

## Verification limits

Counts were calculated from data/lessons.json. Feature conclusions come from
route and UI source inspection. No application runtime or deployment tests were
performed as part of this review. No claim is made that this checkout is the code
currently deployed at thanakorean.com.
