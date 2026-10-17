# Remaining acceptance and external setup — 2026-10-16

Current staging: GitHub 62b0a48, exact tested local f2baf2a tree
642d82eb6c3ff50aa4990749763a87b5e42330dc, 155 isolated tests and clean extracted
source verification. After explicit user release/reset approval, Render Free
dep-db9dtonavr4c73dmsje0 succeeded Live (1m11s, 09:35:14 GMT+7, 2026-10-17).
Logs confirm 48 unpublished foundation drafts imported (24 per direction),
/health 200 and reviewer gate 401. Staging Start Command explicitly initializes,
imports missing foundation drafts and serves; local blueprint matches this saved
setting, while deployed source 62b0a48's blueprint still has the earlier command.
Six separate Lao practice drafts still require explicit import. User confirmed
prior mobile access; acceptance of these latest authenticated workflows remains
pending. Later status/configuration edits are local. FINAL_DELIVERY.md is authoritative.

## Next acceptance, in order

| Gate | Current evidence | Needed to close it |
|---|---|---|
| Latest staging learner/admin use | Render health 200, reviewer 401; isolated browser workflows pass | User opens staging in their working Chrome/mobile browser, signs in, opens Korean and Lao lessons and Admin, and reports exact failing step or success. User reports access works; full lesson/admin-path acceptance is not inferred from that short response. |
| Microphone and audio | Synthetic recorder/navigation/hidden-page tests pass; no real microphone used | On actual Android/iPhone, listen, grant microphone permission personally, record/stop/play back, leave speaking and confirm capture stops. The new navigation/hidden-page fixes are deployed and need actual device evaluation. |
| Curriculum and recordings | Original material retained; the agent authored and imported locally and on staging 48 foundation drafts (24 per direction), with 206 exercises and full review manuscript | The user will review and request corrections as instructed. A local Media Studio helper prepares 48 vocabulary recording prompts plus all/either-language ZIP downloads (158 tests), without generating audio. Local editor media search/type filters/preview and duplicate protection are verified in the 159-test release. Add reviewed audio before claiming listening coverage. Intermediate/advanced/full TOPIK expansion remains additional authoring; these drafts are not presented as independently reviewed. |
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
