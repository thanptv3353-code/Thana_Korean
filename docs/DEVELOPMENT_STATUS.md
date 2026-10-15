# THANA KOREAN development status

2026-10-14 — First local development increment, extending Flask.

## Delivered

- New mobile-friendly home at `/`, with Lao/Korean navigation labels.
- Existing lesson application at `/learn`, retaining all original IDs and data.
- Public sample drawn from the first existing lesson.
- EPS bank imported with source checksum and image-reference validation; no
  private accounts, secrets or ZIP updates imported.
- Authenticated EPS practice, question snapshots, scoring of unanswered items,
  ownership validation, repeat-submit protection and SQLite history.
- Admin EPS answer/verification review at `/studio` after login at `/admin`.
  Review decisions persist in SQLite without rewriting imported source JSON.
- Browser-voice playback when a matching voice exists, rate selection,
  microphone recording and local playback with a 60-second recording limit.
- Live account status/role checks for protected legacy routes, and safe grading
  of malformed legacy answers.

## Run locally

```
python3 -c 'from app import app; app.run(port=8035, debug=False)'
```

Open http://127.0.0.1:8035. Existing accounts and approval behavior are retained.
`THANA_DATA_DIR` can isolate legacy account/lesson/progress data for tests.
`THANA_PLATFORM_DB` can select the SQLite file for new practice/review records.
Use durable storage for that file when deploying. The current preview uses a
throwaway `/private/tmp/thana-preview.sqlite3`; those preview results are not
production records.

## Validation

Five isolated Flask tests pass: public routes/sample answer stripping, account
revocation, practice validation/scoring/idempotency/history, forged admin session
role denial and malformed legacy grading. JavaScript syntax checks pass for the
new learner and review scripts. Browser checks confirmed home rendering, sample
content and Lao/Korean switching. Microphone permission/recording and device
voice availability were not tested on actual learner phones.

Original users.json, lessons.json and progress.json match the supplied local
lesson application's bytes after development and tests.

## Remaining roadmap

This increment does not complete the full plan. The Lao curriculum is visibly
marked as preparing; the current sources contain Korean-learning material, not
an approved Lao course. Additional work includes structured courses/modules,
full bilingual lesson UI, draft/block editor, vocabulary/audio asset library,
legacy database migration, CSRF/rate limiting/recovery, default-admin credential
replacement, timed mock exams, rewards, PWA, premium payments and AI assessment.
Legacy accounts/lessons/progress still use JSON and process-local state; run a
single worker locally until transactional persistence migration is completed.

SQLite is suitable for this local increment, not a declaration that the planned
PostgreSQL production migration is complete. Production data, domains, GitHub
pushes and deployments have not been changed. EPS ZIP updates still require
version reconciliation before their payment/social/lock behavior is adopted.

## Second increment — structured course authoring

Delivered `/editor` (admin) and `/courses` (learner), with target-language
selection, course/module/lesson ordering, text/audio-link blocks, quizzes and
answer explanations. Authoring is backed by SQLite. Each save records a revision;
optimistic concurrency rejects stale edits. Public lessons use an independent
published snapshot so saving a draft does not silently update a live lesson.
Administrators can explicitly unpublish. Drafts and answers are hidden from
public lesson APIs.

Added 3 authored Lao starter lessons with Korean explanations: greetings,
thanks and introducing a name. These are a short trial course, not a complete
Lao curriculum, and have no native-speaker audio recordings. The seed script is
idempotent and does not replace existing records:

```
python3 scripts/seed_lao_starter.py --publish
```

Authenticated completion grades the published quiz, stores first completion,
awards 20 XP once per structured lesson, and calculates level and streak from
completion dates in UTC+7. Legacy lesson scores have not been converted to XP.
New course progress is independent of preserved legacy progress. Structured
lessons are currently freely selectable; prerequisite unlocking is a later step.

All cookie-authenticated write routes now require session-bound CSRF tokens.
Both legacy and new JavaScript clients fetch and send those tokens. HttpOnly
and SameSite=Lax are configured. Login throttling, recovery and credential
bootstrap replacement remain pending.

Nine isolated tests pass, including draft visibility, publishing, stale-edit
rejection, unpublishing, quiz answer stripping, repeated-completion XP, unsafe
audio URL rejection, permissions, non-object JSON and CSRF. Syntax checks pass
for all six learner/admin scripts. Browser verification confirmed the new Lao
catalog and lesson rendering. Full admin UI and microphone/device coverage
remain incomplete.

The local preview now uses `data/platform.sqlite3` (ignored by Git), rather than
the previous disposable preview database. Earlier disposable EPS attempts are
not automatically imported. The legacy JSON files and both supplied source
folders remain unchanged. Production hosting and PostgreSQL migration are
still pending.

## Third increment — timed reading mock exams

Added `/mock-exam`: configurable question count and duration, server-controlled
expiry, per-answer persistence, page-reload resume, category score analysis,
answer review and mock history. Reading-passage groups remain intact when
assembling a paper. Each run snapshots the questions and answers for stable
grading even if an administrator subsequently edits the bank. Only one active
run is reused per account. Deadline enforcement, ownership and finalization are
transactional; late answers cannot change the result, and repeated submissions
return the same result. Unanswered questions count against the full paper total.

Configuration is available in `/studio`, including a verified-questions-only
option. Default local configuration is 20 questions in 20 minutes using the
existing bank, with a visible warning that many questions await review. These
are training defaults, not claims about official EPS-TOPIK exam specifications.
The current mock includes reading/image/text questions, not listening.

Twelve isolated tests pass, including server deadline enforcement, saved-answer
resume, late-answer rejection, stable repeated finalization, ownership checks,
admin-only settings and insufficient verified bank handling. New JavaScript
syntax checks pass. Phone network-loss, background-tab timing and full audio
coverage still need device verification. The countdown is display-only; the
server deadline remains authoritative. Only successfully saved answers survive
navigation, so learners should check the save indicator before leaving.

Expired runs are finalized when accessed or when history is requested; no
background scheduler is required for scoring. Mock history is separate from
ordinary EPS practice and structured-course XP.

## Fourth increment — shared dictionary and audio studio

Added `/dictionary` and admin `/vocabulary-studio`, with Korean/Lao search,
examples, categories, draft/public state and native audio per language. Six
authored starter words are available; this is not a full dictionary. CSV import
supports a dry-run preview, duplicate detection and all-invalid-row rejection
before inserting drafts. Imported records require explicit publishing.

Added MP3/WAV uploads (10 MB maximum), randomized asset names and visibility
checks: draft word audio is available only to the administrator. WAV data is
parsed and checked for truncation; MP3 uses a header check and requires further
codec/decode validation for stricter production acceptance. Replacing audio
leaves the old file on disk; orphan cleanup/backup policies are pending.
Media is stored under the configurable legacy DATA directory and must be on
persistent storage in deployment. It is ignored by Git.

The speaking page can select a dictionary word and play its uploaded native
sample before recording. Device voice remains a fallback where available.
Uploaded audio URLs can also be used in structured lesson audio blocks, but
word publishing still controls those asset URLs; publish the source word when
using its audio in a public lesson.

Fifteen isolated tests pass, covering preview versus commit, duplicate
idempotency, draft visibility, invalid imports, audio rejection, valid WAV
upload, private/public media access and admin-only writes. Original account,
lesson and progress files remain untouched. No native recordings have been
invented or uploaded as part of authoring the starter words.

## Fifth increment — legacy persistence and fuller backups

Legacy account, lesson and progress schemas now use a SQLite compatibility
store (`THANA_DATA_DIR/legacy.sqlite3`). Original JSON is imported once and is
never overwritten by runtime saves. Every request refreshes the legacy state
inside a database transaction; a process/thread lock and SQLite write lock
coordinate existing legacy mutations across workers. Failed requests roll back.
This serializes requests and is an intermediate correctness migration, not a
normalized PostgreSQL implementation or a high-concurrency performance claim.

The admin backup now exports current legacy documents from SQLite, a consistent
SQLite snapshot of new platform records and the uploaded audio directory. It
excludes the session secret. ZIP backups contain private account data and must
be retained privately. Restoring still requires an isolated environment and
validation before changing a running deployment. Keep both SQLite files and
media on durable storage; the free-hosting ephemeral-disk issue is not solved
by changing file format.

Seventeen isolated tests pass, including one-time import, reopening persisted
state, preservation of source bytes, and backup of current database records.
The original local and GitHub lesson snapshots remain unchanged.

## Sixth increment — installable web shell

Added manifest, 192/512px icons, root-scoped service worker and a bilingual
offline notice. Supported browsers may add the app to their home screen over
HTTPS or localhost. Only public CSS/icons/offline content is cached; accounts,
API responses, lessons, exams and audio are not cached. This is an installable
shell, not full offline learning. Installation on real Android/iOS devices is
still unverified.

Current local preview uses the persistent workspace databases. Remaining work:
normalized PostgreSQL migration, vocabulary spaced review, unified legacy/new
course navigation and progress, full admin localization, recovery/login limits,
production bootstrap credentials, teacher roles, payment/provider integrations,
real voice assets and AI assessment, native applications and device QA.
