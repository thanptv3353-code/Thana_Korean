# Local sources for THANA KOREAN

Reviewed 2026-10-14. Read-only inventory; originals were not edited or imported.

## Sources

- `/Users/macbook/Desktop/EPS-TOPIK BOOK/EPS TOPIK Exam/thana-korean/`
  is the structured lesson application. Its lessons.json is byte-identical to
  the downloaded GitHub snapshot: 12 lessons, 11 homework questions,
  165 quiz questions, 270 lesson-exam questions, no video entries.
- `/Users/macbook/Desktop/EPS-TOPIK BOOK/EPS TOPIK Exam/eps-topik-deploy/eps-topik/`
  is a separate Flask question-bank application: 380 questions, 231 PNG files,
  no MP3/WAV/MP4 files found in the extracted application.

Question categories: img_word 50, blank 50, sign 180, qa 50, reading 50.
Question types: image_stem 163, text 149, image_choices 68.
Korean and Lao stems, passages and choices exist in the schema.
The verified field is true for 2 questions and false for 378; this is a stored
review flag, not proof that any particular answer is right or wrong.

## Existing behavior to reuse

- Lessons: ordered learning, homework, quizzes, lesson exams, progress and admin.
- EPS: category/subcategory selection, shuffled questions, grouped reading
  passages, answer checking, image questions and administrator question editing.
- EPS submission grades the answers supplied by the client; there is no
  server-issued exam session in the reviewed routes. A formal mock exam needs
  a complete question snapshot, unanswered-question handling and deadlines.

## Version uncertainty

The parent EPS folder has a base deployment ZIP and update ZIPs numbered through
12. Sampled files in updates 8 (payment), 9 (lock), 11 (social) and 12 (auth text)
differ from the extracted application. Archive names do not establish which
version is deployed or whether these changes were applied elsewhere.
Compare updates in order and identify the intended final behavior before import.
Do not unpack every update over the working app blindly.

## Integration requirements

Use both sources: structured lessons under Learn and the EPS bank under Practice.
Keep the THANA KOREAN brand and one account system. Preserve original identifiers
with source namespaces (lesson app versus EPS bank), and explicitly map question
answer conventions instead of assuming they match.

Retain reading-passage grouping and validate image references. Review duplicate
questions across sources before deduplication; do not remove content solely
because text matches. Review unverified answers before publication.

Migrate on copies with a manifest, record counts, checksums and a dry run.
Do not copy users.json, session secret files or credentials into public content
or commit them as migration fixtures. Live users/progress require a separate
private backup and account reconciliation process.

Audio, two-direction curriculum, speaking exercises and pronunciation feedback
remain additions. No claim is made that local data equals current live data.
