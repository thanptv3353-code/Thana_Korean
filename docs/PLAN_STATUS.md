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
| Course hierarchy and lesson authoring | Courses/modules/ordered blocks, media picker, mixed quizzes, draft/publish/revisions, access and sequential rules, bounded direct MP4 clips and native preview/player, adjacent previous/next controls | Device playback acceptance; drag interaction if needed alongside keyboard controls |
| EPS practice and analysis | Bank/editor, snapshots, server grading, incorrect retries, complete passage groups, difficulty filter, bilingual answer explanations and private historical review; configurable category points with immutable run rubrics; owner-only multi-attempt analysis by category/skill/period | Teacher-reviewed listening audio content |
| Timed exams | Reading/listening mocks, separate settings, server deadline, save/resume, immutable results and category analysis | Real-device audio acceptance |
| Shared vocabulary | CSV preview/deduplication/draft import, examples, images, part of speech, both language audio uploads, saved words and spaced review | Full reviewed vocabulary corpus; native XLSX is optional because the design allows Excel or CSV |
| Speaking | Word selection, uploaded sample audio, speed control, temporary recording/playback, optional recognition/Korean scoring adapter, teacher-authored exercises/levels and revision-aware self-report | Teacher-reviewed exercise content; real microphone/device evaluation; native audio; validated provider quality. Lao pronunciation scoring is not implemented |
| Accounts and roles | Username/password, approval, admin/teacher/student checks, recovery, profile, optional Google adapter, administrator-configured teacher course scope, optional email registration/verification and private SMTP outbox worker | Live SMTP/worker acceptance; self-service email password recovery; distinct super-admin role if retained in final scope |
| Motivation and personal summary | XP, level, UTC+7 streak, progress, continue/next and owner-scoped summary | User feedback/acceptance on actual courses |
| Premium | Manual plan/receipts, administrator review, time-limited entitlements, course enforcement | Automatic banking/recurring billing remain future, consistent with Free-first instruction |
| Administration | Central dashboard, content/user/media/question tools, account audit, trend, moderation, content readiness queue, searchable content mutation metadata, bilingual homepage/help-link settings | Private live-service configuration remains external; before/after audit diffs and independent tamper-resistant logging remain future |
| Data preservation and migration | Original JSON preserved, transactional SQLite, isolated backup/restore, preserved IDs | Actual production backup/reconciliation and migration rehearsal with the live data, before cutover |
| Mobile web and apps | Responsive pages, manifest/icons and safe offline notice | Physical Android/iPhone install/audio tests; full offline lesson downloads and native stores are later phases |
| Hosting/release | Separate Render Free staging, user confirmed health + reviewer/admin sign-in | Listening release b623171 deployed after user confirmed no staging data to preserve. Free deploys reset ephemeral files. Durable production storage still requires a decision |

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
- Provider tests use mocks; no real AI call or paid resource has been enabled.

Open items above are intentionally not claimed complete. Building an adapter or
showing a disabled control is not proof that its external service works.
