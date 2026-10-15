# Render Free staging

User selected Free on 2026-10-15. Deployment is prepared but not yet online.
The existing thana-korean service (srv-d9argmjeo5us73dfbf4g) uses main,
commit a7fc75d. Do not modify or sync its Blueprint.

## Selected configuration

Use render.staging.yaml from a separate staging branch in a NEW Blueprint.
Service: thana-korean-stage-demo. Python 3.11, locked dependencies,
Gunicorn, auto deploy off, health endpoint /health. No custom domain or disk.
Runtime data lives in /tmp/thana-stage-demo and can disappear on every restart
or deploy. Use synthetic accounts only; this is not durable production hosting.
The app displays a bilingual demo notice. AI, speech and TTS are disabled.

HTTP Basic reviewer access protects everything except /health; pages are noindex
and no-store. User is reviewer. Render generates THANA_STAGING_PASSWORD and
THANA_BOOTSTRAP_PASSWORD privately. Retrieve them personally from Render's
Environment page; never paste them into chat or Git. The latter is the fresh
app administrator password, distinct from the reviewer gate. Free has no Shell.

## Acceptance checklist

- [ ] Push sanitized source on a separate branch, excluding runtime accounts.
- [ ] Create a NEW Free staging service with the custom Blueprint file.
- [ ] Verify live /health 200 and reviewer gate at /.
- [ ] Verify HTTPS review and app sign-in with synthetic data.
- [ ] Check Android/iPhone audio, microphone and PWA install.

## Local verification

52 isolated tests pass. Production-mode initialization, secure cookies, staging
gate and file permissions were rehearsed with temporary synthetic data. Real
Gunicorn restart smoke checks passed. Runtime identity survives process restart
only while the data directory remains; Render Free does not guarantee this.
Docker was not built because no engine is installed. Actual Render runtime and
online provisioning are not yet verified.

Use /api/admin/backup as an authenticated administrator for a private application
backup before disposable data is lost. Restore only into an empty directory.
Persistent production data will require a later durable-storage decision.
Original render.yaml, main and production domain must remain unchanged.

References checked 2026-10-15:
- https://render.com/docs/blueprint-spec
- https://render.com/docs/disks
- https://render.com/docs/python-version
