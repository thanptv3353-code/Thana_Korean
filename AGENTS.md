# THANA KOREAN development

Read docs/FINAL_DELIVERY.md and docs/INTEGRATIONS.md before extending this app.
Use the existing Flask architecture and preserve original lesson/question IDs.
The user has authorized routine implementation and local verification without
repeated confirmation. Continue within that scope; do not invent live integration
results or assume this repository equals the currently deployed website.

Do not modify the two original Desktop source folders. Runtime data is SQLite;
source JSON is a preserved migration input. Keep credentials, databases, media
receipts and backups outside commits/source bundles. Use isolated data/database
paths and synthetic accounts for tests. Do not call real paid providers in tests.

Run meaningful tests and JavaScript syntax checks after behavior changes.
Server-enforce account roles, membership, lesson access and exam deadlines.
Never equate speech recognition with pronunciation accuracy; Lao scoring has
not been validated. Private audio/receipt URLs must retain access checks.

Source files include independent modules installed through platform_routes.py.
New database tables are initialized idempotently; avoid destructive migrations.
Maintain docs/FINAL_DELIVERY.md as current status rather than appending ambiguous
claims of complete production readiness.
