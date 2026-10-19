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

202 isolated tests and clean source/bootstrap/SQLite/HTTP/JS checks passed.
Browser QA used isolated synthetic accounts/public material at 320px. No real
provider integration or production readiness is established by these tests.
Real credentials, actual account/history/payment reconciliation, missing-media
and language review, durable hosting and device/end-to-end acceptance remain
required. Private working observations/results are intentionally outside source.
