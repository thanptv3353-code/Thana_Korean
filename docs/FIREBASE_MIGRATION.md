# Firebase migration procedures

This document describes tooling, not real-user migration results. Keep all actual
transfers, candidate databases, media, receipts, operational notes and derived
private statistics outside source bundles and commits. The public legacy site
uses Firebase project korean-lao-exam; its static curriculum is preserved as a
public migration input. Do not assume a local repository equals the deployed app.

## Source semantics

Firebase Auth UID is authoritative. Firestore profiles are not passwords. Preserve
original IDs and distinguish general, EPS and seasonal paid scopes. Lesson
results, EPS boolean maps and missed-word records have different meanings. Do not
infer identity by splitting document IDs or by matching email/username. Preserve
unknown data raw for explicit reconciliation; do not invent expiry, exam scores,
timestamps, account activation or payment approvals.

The optional read-only collector uses an explicitly authorized gcloud session,
fixed Firestore GETs, pagination and one read time. It excludes credential/config
collections and does not export Auth passwords or subcollections. It does not
change Firestore, rules, hosting or billing. Existing working transfers should be
reused rather than reread merely because a browser download cannot be observed.

## Offline preparation

Use private placeholder paths appropriate to the operator's machine:

```sh
python scripts/prepare_firebase_migration.py /path/to/private/transfer.json
python scripts/prepare_firebase_migration.py /path/to/private/transfer.json --stage-db /path/to/private/new-source.sqlite3
python scripts/build_firebase_runtime.py /path/to/private/transfer.json /path/to/private/new-candidate
```

The inspector validates project/allowlist/document identities, duplicate IDs,
JSON/typed-field consistency and unresolved ownership/roles. Staging creates only
private source tables. Fresh runtime candidates preserve non-deleted source
profiles with no local passwords, disabled UID bindings, raw source records and
unpublished content. Ambiguous identities reject; no existing destination is
overwritten. Deleted profiles are not reactivated. Explicit credential/binding,
production-preflight and acceptance work remains before any real use.

## Public curriculum and original EPS

static_data_parser.py parses declarative literals/references/spreads without
executing JavaScript. scripts/extract_firebase_static.py preserves complete public
source provenance/hashes. Additive curriculum import preserves original IDs,
existing staff edits and publication/revision state. Supply private overrides on
the first real import; base-only rehearsals belong in isolated synthetic DBs.

The original EPS bank uses string IDs in a separate table from the existing
integer-ID local exam bank. Immutable source, current answers/explanations,
optimistic revisions and staff review/publication are separate states. Reimport
does not overwrite staff edits. Source verified flags are not new review consent.

Media inventory retains question stems, audio and all image answer choices. The
public collector accepts only fixed-origin allowlisted paths, rejects redirects
and non-media/HTML responses, limits sizes and writes private receipts. The local
collector reads originals without modifying them and produces checksum-bearing
review candidates, not proof of semantic correspondence.

```sh
python scripts/import_recovered_eps_media.py --database /path/to/private/runtime/platform.sqlite3 --candidates /path/to/private/candidates --library /path/to/private/runtime/media
# After reviewing the dry run, repeat with --apply.
```

Stop that target server first. The importer validates the complete receipt and
original checksums, source path membership, decode/pixel/byte constraints, then
creates private unpublished sanitized images. Deterministic journal/IDs support
repeat import, preserve staff titles/publications/manual mappings and reject
changed/conflicting entries. SQL failure removes only newly created files.

Staff media mappings accept only matching existing library assets. They retain
original paths and require both question and shared mapping revisions. A change
invalidates every affected review. Unmapped, deleted or unpublished media prevents
readiness; all image-choice dependencies are required. Draft URLs retain staff
access checks. Review/mapping/import does not publish media or learner content.

## Access and history

General/seasonal scope states unlock only corresponding original courses through
enabled bindings. EPS scope does not grant unrelated course/global membership.
Source unpaid/missing defaults remain unpaid and source scopes stay distinct.
Passed lesson results require exact known owner/lesson, valid score and original
timezone-aware completion time. Failed results do not become passed under a new
threshold. Existing local completions are preserved, not overwritten.

Original EPS correct/attempted/freeUsed boolean maps merge by exact UID and
question ID without downgrading newer flags. Independent source flags remain
independent. Unknown IDs/owners or invalid maps remain reported/raw; no historical
exam attempts/scores/times are fabricated. Missed-word and unrelated legacy exam
collections require their own explicit mapping.

## Learner publication and practice

Staff publication requires current reviewed revision and all media ready.
Publication becomes stale on content/media mapping changes. Learner practice uses
only ready current publications, owned immutable snapshots and one active session.
It is untimed practice, not an official exam. Existing timed exams keep their own
server deadlines. Answers/explanations are hidden until answered; unanswered
questions reveal no solution and consume no free trial. Grades are idempotent,
owned history is private and original EPS trial/repeat permissions are enforced.
Unsubmitted choices are not autosaved.

## Verification and remaining gates

### Missed-word continuity

Candidate building now maps the original missed-word dictionary by exact phrase
ID against the public main curriculum with reviewed source overrides applied.
An unambiguous Korean/Lao pair becomes an unpublished vocabulary draft using its
original ID and a private saved-word link for the explicitly mapped source owner.
Original positive integer miss counts remain separate from spaced-review grades,
due dates and completions. No vocabulary publication or entitlement is granted.
Staff can review/publish these drafts in the existing Vocabulary Studio, after
which the owner sees them under saved words and saved-word review.

Unmapped/ambiguous IDs, invalid counts, existing vocabulary collisions and unknown
or deleted owners remain unresolved/source-only; no text-based identity matching
or automatic aliasing occurs. Seasonal phrases use a different source namespace
and are not guessed into the main review deck. The private import journal retains
the source document. Reimport preserves staff edits, review schedules and learner
removals; it does not re-save a word already removed after migration. Changing an
already journaled source document requires explicit review, as with other history.

Existing runtime candidates are not automatically updated by a code deployment.
Build a separate new private candidate and reconcile its report before selecting
a target. Real migration results and actual device acceptance remain unverified.

Run `python scripts/check_runtime_readiness.py /path/to/private/runtime` for an
offline structural check. It reads existing SQLite files without starting the
app, writes no data, makes no provider calls and omits account identifiers from
its output. Exit 1 means a structural blocker; exit 0 means only those offline
checks passed. `production_ready` always remains false: enabled UID rows alone
cannot establish working Firebase credentials or real sign-in, and this command
does not bypass the application's production startup checks. Keep its output
private along with other migration working observations.

The 229-test release check passed, together
with clean source/bootstrap/SQLite/HTTP/JS checks.
Browser QA used isolated synthetic accounts/public material at 320px. No real
provider integration or production readiness is established by these tests.
Real credentials, actual account/history/payment reconciliation, missing-media
and language review, durable hosting and device/end-to-end acceptance remain
required. Private working observations/results are intentionally outside source.


## Original seasonal result history

New candidates normalize only thana_seasonal_exam_results belonging to exact
non-deleted thana_users identities with matching UID/username bindings. Original
result IDs and group IDs are retained. Integer scores/totals, rounded percentages,
pass flags and timezone-qualified timestamps must agree with the original seasonal
exam format. Invalid or unresolved records remain source-only; changed journal
inputs require explicit review. No score is added to new mock exams, XP, lesson
completion, entitlements or exam-attempt limits.

The My Learning page reads /api/platform/original-history in pages. The server
requires an approved current account, matching local Firebase UID and enabled
original binding for every request; it returns only that owner's summary fields
with no-store caching. It exposes no raw source, personal names or answer keys.
This preserves historical claims, not proof of a proctored examination. Legacy
EPS examResults uses a separate identity namespace and remains unapplied until
its ownership is explicitly reconciled. Existing candidates/deployments do not
automatically receive imported results. Browser checks used synthetic data only.
