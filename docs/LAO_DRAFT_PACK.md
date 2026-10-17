# Lao beginner practice drafts v1

Six original Korean-instruction practice lessons supplement the three preserved
Lao starters. They are a review/number practice pack, not a full Lao curriculum.

| Lesson | Module | Objective |
|---|---|---|
| 숫자 1–5 | 숫자 | Match and enter five number words |
| 숫자 6–10 | 숫자 | Distinguish the next five number words |
| 학교와 책 | 생활 단어 | Distinguish school/book vocabulary |
| 회사와 물 | 생활 단어 | Distinguish company/water vocabulary |
| 인사와 감사 복습 | 복습 | Distinguish greeting/thanks in context |
| 기초 단어 종합 복습 | 복습 | Review words and number order |

Each contains an objective, Korean explanation, teacher-review notice and three
questions: 18 total across choice, blank, matching and ordering. No native/AI audio
is bundled, no audio was synthesized and there is no pronunciation score.

Number spellings/values were checked against the number table in Simon Ager's
[Numbers in Lao](https://www.omniglot.com/language/numbers/lao.htm), accessed
2026-10-16. The pack uses the common combined spelling ໜຶ່ງ for 1; a teacher must
review spelling variants, Korean explanation, examples and accepted answers.
The other six word pairs reuse this project's existing starter vocabulary.
The explanations/questions are authored for this pack, not copied lessons or a
claim of review/endorsement by the reference author. No third-party audio/images
or book pages were copied. No romanization or tone accuracy is asserted.

## Review locally

Open /editor as Admin/Super Admin and choose
`라오어 기초 · 교사 검토용 초안`. All six drafts were added to the existing local
runtime on 2026-10-16 with author `local-authoring`, with zero published lessons.
Review each draft, amend the questions/accepted spelling variants, add reviewed
sample audio if desired and use the existing preview/publish controls explicitly.
The original Desktop sources and the three starter lesson IDs were not edited.

## Import into another initialized runtime

Editor → `＋ ຮ່າງບົດພາສາລາວ / 라오어 초안 묶음` → add six drafts.
The server requires a currently approved Admin/Super Admin, CSRF and exact pack
identifier. No new runtime is populated automatically on startup/deploy.

Course ID: `lao-beginner-review-v1`; lesson IDs derive from stable pack keys.
Import is atomic and idempotent. Existing course metadata, lesson drafts,
publications and revisions are preserved, including teacher edits. Foreign-course
lesson ID or course-language collisions reject the entire import. Re-import does
not recreate an initial history record for an existing lesson or reset a level.

141 isolated tests and JS/release checks pass. Synthetic browser verified import,
preview, repeated import and 320px layout. This does not certify teaching quality.
The pack/UI and speaking fixes are now deployed as df308fd on 2026-10-17. The
actual staging drafts require explicit Admin import; deployment does not copy
the local SQLite drafts or publish them. User has confirmed access now works; broader latest
lesson/mobile/content acceptance remains separate.
