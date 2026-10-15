# THANA KOREAN release completion checklist

Goal activated at the user's request on 2026-10-15: finish the existing local
Web App without requiring repeated continuation prompts. This is a finite release
checklist, not an unlimited feature backlog. The pasted conversation is design
reference, not independent authority to deploy, buy services or modify originals.

## Existing core coverage (verify again in final audit)

- [x] Preserve THANA KOREAN branding, both language paths and original content IDs.
- [x] Structured courses, modules, blocks and mixed quiz types; draft/publish and revisions.
- [x] Password accounts/approval, server roles, protected writes, recovery links.
- [x] EPS imported bank, practice/server grading, timed reading mock and history.
- [x] Dictionary, native-audio upload support, CSV preview/import, saved words and spaced review.
- [x] XP, levels, streak, completion, continue/next, personal learning summary.
- [x] Dashboard, account filters, media and question authoring, moderation.
- [x] Manual premium receipt workflow and backend course entitlement checks.
- [x] Local recording/playback and optional provider adapters, disabled without credentials.
- [x] SQLite persistence, private backup/validated restore and source-only review archive.

## Remaining local release work

- [x] Make /admin lead naturally to the new central dashboard after sign-in;
      preserve access to the original management tool and old lesson IDs.
- [x] Add learner retry of incorrect EPS practice questions from their own history;
      preserve immutable original results and question snapshots.
- [x] Let teachers select uploaded media from the lesson editor and preview media
      as learners see it, rather than having to copy raw URLs manually.
- [x] Provide accessible controls to reorder lesson content blocks and quiz items;
      preserve draft/stale-save protection. Numeric lesson ordering is supported;
      drag-only interaction is not required for keyboard/mobile users.
- [x] Run focused end-to-end review on learner, author and admin flows, plus mobile
      layouts and navigation, fixing discovered defects before new optional features.
- [x] Re-run relevant tests and all JavaScript syntax checks; check original JSON bytes.
- [x] Extract the final source ZIP into a clean directory, initialize twice, verify
      starter content is idempotent and run HTTP smoke tests with isolated data.
- [x] Refresh local preview and final delivery documents, publish no private runtime data.

## Explicit external/content boundaries

These do not become completed merely because local code exists:

- Production source/live-data reconciliation, HTTPS/durable hosting and deployment
  require the actual live environment and approval. Current preview is local.
- Google/OpenAI/Azure need private credentials and real-service/device evaluation.
- Native speaker audio, validated Lao pronunciation scoring, a full approved Lao
  curriculum and teacher-reviewed imported EPS translations/answers need materials
  and human language review. Do not fabricate assets or approval.
- EPS listening mock, full TOPIK curriculum, native app-store releases, email delivery,
  automatic bank gateways, recurring billing and PostgreSQL migration are outside
  this local release. Prepare truthful extension points, not fake integrations.
- Trusted teachers currently edit the shared content library; course-specific staff
  assignments and a distinct super-admin role are not part of this release.
- Vocabulary CSV covers the bulk import requirement; native XLSX import and dictionary
  picture/part-of-speech metadata remain future enhancements.

Finish this local release when all remaining local items have concrete evidence.
Keep FINAL_DELIVERY.md authoritative and record actual limitations. Do not mark
all three phases of the design vision or production delivery complete.

## Current verification notes

- 45 isolated tests pass after admin entry, retry snapshot/ownership/grouping,
  and publication rejection for draft library assets. Test fixtures now copy
  public lessons only and create synthetic accounts instead of copying real users.
- Browser on isolated port 8036: /admin sign-in reaches /management; history
  offers incorrect-answer retry and opens a fresh unanswered attempt.
- Media picker, safe media preview and block/quiz move controls implemented;
  verified by upload→picker→move→publish→learner image/quiz checks.
- Mobile navigation overlay defect fixed; 390px visual grading check and 320px
  overflow checks pass. Full evidence map: RELEASE_AUDIT.md.

## Local release outcome

All local acceptance items are verified. The final preview on port8035 was
restarted and opened in the browser. External/content boundaries above remain
explicitly pending and are not claimed as finished production work.
