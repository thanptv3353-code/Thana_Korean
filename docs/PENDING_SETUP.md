# Remaining acceptance and external setup — 2026-10-16

Current staging: GitHub df308fd, exact local 908be7a, 141-test release, Render
Free deployment dep-db99foc9v7es739il5p0 verified Live on 2026-10-17 after explicit
user approval of disposable reset. Speaking fixes and the draft-only Lao pack
import are included. No six-draft auto-import/publication occurs. User confirmed
access worked before this deploy; fresh feature/device acceptance is pending.
Subsequent interactive staff quiz rehearsal passes 144 tests locally and is not deployed. FINAL_DELIVERY.md is authoritative; later documentation changes are local only.

## Next acceptance, in order

| Gate | Current evidence | Needed to close it |
|---|---|---|
| Latest staging learner/admin use | Render health 200, reviewer 401; isolated browser workflows pass | User opens staging in their working Chrome/mobile browser, signs in, opens Korean and Lao lessons and Admin, and reports exact failing step or success. User reports access works; full lesson/admin-path acceptance is not inferred from that short response. |
| Microphone and audio | Synthetic recorder/navigation/hidden-page tests pass; no real microphone used | On actual Android/iPhone, listen, grant microphone permission personally, record/stop/play back, leave speaking and confirm capture stops. The new navigation/hidden-page fixes are deployed and need actual device evaluation. |
| Curriculum and recordings | Original lessons/EPS retained; three public Lao starters, six starter words and six new local unpublished practice drafts | A competent teacher reviews answers/translations/objectives/audio and supplies/approves the additional Lao/Korean/TOPIK curriculum. Use content-readiness and question review tools. Do not label generated content as teacher-approved. |
| Actual Super Admin | Four roles and protected controls tested with synthetic accounts | Operator explicitly chooses the intended owner and follows SYSTEM_OWNER.md. No actual account is promoted automatically. |
| Durable production and migration | Free staging is disposable; isolated restore rehearsed | Obtain actual production backup privately, reconcile data, rehearse migration/restore on durable storage and obtain cutover approval. Do not put backup/accounts in Git or chat. |

## Optional services remain disabled

These require the user's provider/account choice and private configuration, not
more mock results. Never paste keys/passwords into chat, source or browser code.

- Azure AI voice: actual region/resource, THANA_TTS_ENABLED, key and regional
  voice availability/cost verification; a competent speaker reviews each sample.
- Azure recognition/Korean pronunciation and OpenAI tutor: independent flags,
  credentials and real learner/provider evaluation in INTEGRATIONS.md. Lao
  transcription is not pronunciation scoring.
- Google sign-in: actual OAuth registration/callback and live sign-in acceptance.
- SMTP email registration: private SMTP setup plus an actual outbox worker and
  inbox/spam/one-use verification testing. Self-service email password recovery
  remains an optional unimplemented feature.

Native Android/iOS store apps, full offline media and automatic banking remain
later phases in the supplied plan. The current artifact is the Flask mobile web
app/PWA shell. Full interface localization across every page and production
performance have not been established by viewport checks or a test count.

Run `python3 scripts/verify_release.py` for isolated source-package verification.
Source ZIP excludes runtime databases, accounts, credentials, uploads and receipts.
