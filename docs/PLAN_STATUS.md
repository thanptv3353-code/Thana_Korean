# THANA KOREAN implementation status

Source: user-supplied redesign conversation (reference material), subsequent user
instructions to extend the existing app, use Free hosting first and continue.
This file tracks the remaining vision; previous local-release checklists do not
make unfinished requirements complete or remove them from the longer-term plan.
Production changes still require the user's approval. Original Desktop sources
must remain untouched. Current architecture is the authorized existing Flask app.

| Plan area | Implemented evidence | Remaining work / acceptance |
|---|---|---|
| Brand and two learning directions | Home, Korean legacy material, Lao starter, catalogs and shared navigation | Teacher-approved expansion of the Lao and Korean curriculum; full TOPIK material |
| Course hierarchy and lesson authoring | Courses/modules/ordered blocks, media picker, mixed quizzes, draft/publish/revisions, access and sequential rules | Direct video file upload; drag interaction if needed alongside keyboard controls |
| EPS practice and analysis | Bank/editor, snapshots, server grading, incorrect retries, complete passage groups, difficulty filter, bilingual answer explanations and private historical review | Teacher-reviewed listening audio content; configurable score weighting |
| Timed exams | Reading/listening mocks, separate settings, server deadline, save/resume, immutable results and category analysis | Real-device audio acceptance |
| Shared vocabulary | CSV preview/deduplication/draft import, examples, images, part of speech, both language audio uploads, saved words and spaced review | Full reviewed vocabulary corpus; native XLSX is optional because the design allows Excel or CSV |
| Speaking | Word selection, uploaded sample audio, speed control, temporary recording/playback, optional recognition/Korean scoring adapter | Dedicated speaking exercises/levels; real microphone/device evaluation; native audio; validated provider quality. Lao pronunciation scoring is not implemented |
| Accounts and roles | Username/password, approval, admin/teacher/student checks, recovery, profile, optional Google adapter | Email registration/verification and delivery; course-specific teacher assignment; distinct super-admin role if retained in final scope |
| Motivation and personal summary | XP, level, UTC+7 streak, progress, continue/next and owner-scoped summary | User feedback/acceptance on actual courses |
| Premium | Manual plan/receipts, administrator review, time-limited entitlements, course enforcement | Automatic banking/recurring billing remain future, consistent with Free-first instruction |
| Administration | Central dashboard, content/user/media/question tools, account audit, trend, moderation, content readiness queue | Broader system settings and comprehensive content-change audit coverage |
| Data preservation and migration | Original JSON preserved, transactional SQLite, isolated backup/restore, preserved IDs | Actual production backup/reconciliation and migration rehearsal with the live data, before cutover |
| Mobile web and apps | Responsive pages, manifest/icons and safe offline notice | Physical Android/iPhone install/audio tests; full offline lesson downloads and native stores are later phases |
| Hosting/release | Separate Render Free staging, user confirmed health + reviewer/admin sign-in | Local additions after commit628f0d4 are not deployed. Preserve any wanted staging data before a Free deploy resets ephemeral files. Durable production storage still requires a decision |

## Latest local batch

- Staff content readiness queue and exact-item editor links (54 tests).
- EPS difficulty/explanations, private history review, dictionary image/part-of-
  speech authoring and CSV metadata import (59 tests).
- Images must be valid library images; publishing/activating content cannot expose
  a private image. Original imported questions are not silently assigned levels.
- Listening authoring/practice/mocks, published audio guards, separate settings and
  saved attempts (66 tests); synthetic browser playback/save/reload/submit passed.
- Provider tests use mocks; no real AI call or paid resource has been enabled.

Open items above are intentionally not claimed complete. Building an adapter or
showing a disabled control is not proof that its external service works.
