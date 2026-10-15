# THANA KOREAN

A bilingual Lao–Korean learning web app, extending the original Flask project.
The brand and existing lesson IDs are preserved. This checkout is a local review
version; it has not replaced thanakorean.com.

## Start

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/init_content.py
.venv/bin/python app.py
```

Open http://127.0.0.1:8035. Existing imported accounts are preserved. A genuinely
fresh installation creates an administrator with a random password in the private
`data/bootstrap_credentials.txt`, unless `THANA_BOOTSTRAP_PASSWORD` is configured.
Never publish that file. Existing installations do not receive a password change.
Use `/account` to change your own password. Production mode refuses the legacy
default administrator credential.

## Main pages

| Page | Purpose |
|---|---|
| `/` | Bilingual home, practice and speaking |
| `/courses` | Unified legacy and structured courses |
| `/learn` | Preserved lesson application and password sign-in |
| `/mock-exam` | Timed reading mock exams with saved-answer resume |
| `/dictionary`, `/review` | Vocabulary, audio and spaced review |
| `/account`, `/membership` | Profile, password, recovery and Premium |
| `/community`, `/tutor` | Moderated discussion and optional tutor |
| `/management` | Role-aware dashboard and account/payment settings |
| `/editor`, `/question-editor` | Structured lessons and EPS bank editing |
| `/media-studio`, `/vocabulary-studio`, `/studio` | Assets, vocabulary, EPS review |
| `/admin`, `/legacy-admin` | Central dashboard sign-in; original admin tools |

## Data

Legacy JSON is imported once into `data/legacy.sqlite3`; original JSON files are
not overwritten. New content, progress and administration use
`data/platform.sqlite3`. Media and receipt files are private runtime files and
are ignored by Git. Use both `THANA_DATA_DIR` and `THANA_PLATFORM_DB` when setting
an external persistent storage directory. Accounts are never copied from the
repository into a fresh external data directory; bundled public lessons are.

The administrator backup exports current legacy JSON, a platform DB snapshot,
media and private receipts. Restore only into an isolated empty directory:

```sh
python3 scripts/restore_backup.py backup.zip /private/tmp/thana-restore
python3 scripts/restore_backup.py backup.zip /private/tmp/thana-restore --apply
```

The first command validates without writing. The second refuses existing data.
Run the restored copy with both storage environment variables pointing to that
directory. Validate counts, accounts and media before any production cutover.

## Optional services

See `.env.example` and `docs/INTEGRATIONS.md`. The app does not automatically load
dotenv. Google sign-in, OpenAI Tutor and Azure speech remain disabled until their
credentials and configuration are supplied. No external paid service was called
during development. Premium receipt collection also starts disabled; an
administrator sets a price and payment instructions before enabling it.

## Checks and handoff

```sh
python3 -m unittest discover -s tests -v
```

Tests use isolated databases and synthetic accounts. Browser QA also uses
synthetic accounts in a separate server. See `docs/START_HERE.md` and
`docs/FINAL_DELIVERY.md` for current scope and remaining deployment work.

The SQLite implementation serializes legacy requests for consistency. It is not
a normalized PostgreSQL migration. PWA installation is an optional web shell;
full offline learning and native App Store applications are not included.

## Staging preparation

See `docs/STAGING_RENDER.md` for a separate Render review service. The candidate
`render.staging.yaml` uses durable storage and private reviewer access. It has
not been applied to a hosting account. Run `python3 scripts/verify_staging.py`
for isolated production-mode initialization and restart checks.
