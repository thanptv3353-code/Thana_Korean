# Render Free staging

User selected Free on 2026-10-15. A separate Free service deployed successfully (Live, 58.7 seconds).
The existing thana-korean service (srv-d9argmjeo5us73dfbf4g) uses main,
commit a7fc75d. Do not modify or sync its Blueprint.

## Latest successful update — 2026-10-17

Deployment dep-db99foc9v7es739il5p0: Deploy succeeded | Live, 1m01s, started
04:32:17 GMT+7. User explicitly approved the 141-test source and disposable reset.
Source df308fd3c6780e984bad84f2f0c1fdd84bbbf171 has the exact local 908be7a tree
715a779e33d29975e90476f5963da3cd93226f39. Logs confirm Gunicorn startup,
repeated /health 200 and anonymous HEAD/root 401. Free plan remains unchanged.
No providers or Super Admin activation enabled. Screenshot: docs/render-141-live.png.

Speaking navigation/lifecycle and Lao draft import are deployed. To create the
six unpublished drafts in this ephemeral runtime, sign in as app Admin, open
/editor, expand the Lao draft pack panel and import. Startup only adds the three
public starters. Teacher review and explicit publication are separate actions.
Fresh end-user/device acceptance is pending; previous user success is not proof
of all new workflows. Earlier release records below are historical.

## Previous prepared update (now deployed)

Authorized staging branch source now points to df308fd3c6780e984bad84f2f0c1fdd84bbbf171,
exact local 908be7ab5f27e2b349423860b3d3c61bbd10ce0f tree
715a779e33d29975e90476f5963da3cd93226f39. 141 tests/clean extracted release pass.
Adds local speaking navigation/lifecycle and explicit draft-only Lao pack import.
No automatic import/publication, providers or owner activation. Auto-deploy stays
off; approval was received and this snapshot is now deployed as recorded above.

## Current release — 2026-10-16

User approved deploying b78bbae and losing disposable test data. GitHub source
is a5ec247ff03e604c9623fb77974cb708e60bc4fc, tree
098133d18fa44314b45112640e349f7c350b8081, exactly matching local b78bbae.
Deployment dep-db94kgvbtjjs73955rqg reports Deploy succeeded | Live after 1m07s,
started 23:01:07 GMT+7 and Live 23:02:15. Logs show repeated /health 200 and
anonymous root 401. 137 isolated tests, clean extracted source and JS checks
passed before upload. No credentials/runtime files were uploaded; original
Desktop inputs still compare byte-for-byte. Evidence: docs/render-137-live.png.
End-user acceptance of this latest release remains pending. Super Admin owner
activation, live external providers and production cutover were not performed.
Earlier release records below are historical evidence, not the current version.

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

- [x] Sanitized source uploaded on codex/staging-review-20261015, commit 628f0d4.
  Remote tree bdebf993052d352b188e3b707e75a56f16b7c120 matches the tested local tree.
- [x] Created NEW Free service srv-db89708m7kps73di7p5g with custom Blueprint.
  Blueprint exs-db896u1srm7s73drqtcg, name thana-korean-free-staging.
- [x] Render deployment logs confirm /health 200 and / 401.
- [x] Public HTTPS /health: user reports `status: ok` from mobile data on
  2026-10-15. This verifies that endpoint from that network; it does not prove
  authenticated app flows. Direct access from this machine still fails during
  connection/TLS establishment. No certificate verification was bypassed.
- [x] User confirms both reviewer gate and admin app sign-in work on 2026-10-15.
- [ ] Check Android/iPhone audio, microphone and PWA install.

## Local verification

52 isolated tests pass. Production-mode initialization, secure cookies, staging
gate and file permissions were rehearsed with temporary synthetic data. Real
Gunicorn restart smoke checks passed. Runtime identity survives process restart
only while the data directory remains; Render Free does not guarantee this.
Docker was not built because no engine is installed. Render Python 3.11 dependencies installed and Gunicorn started successfully.
The source was deployed as commit 628f0d44a90fec40caac918a9123a81af49ae534.

Use /api/admin/backup as an authenticated administrator for a private application
backup before disposable data is lost. Restore only into an empty directory.
Persistent production data will require a later durable-storage decision.
Original render.yaml, main and production domain must remain unchanged.

References checked 2026-10-15:
- https://render.com/docs/blueprint-spec
- https://render.com/docs/disks
- https://render.com/docs/python-version

## Online review access

URL: https://thana-korean-stage-demo.onrender.com/
Dashboard: https://dashboard.render.com/web/srv-db89708m7kps73di7p5g
Environment: https://dashboard.render.com/web/srv-db89708m7kps73di7p5g/env

First gate: reviewer / THANA_STAGING_PASSWORD from the private Environment page.
Then /account: admin / THANA_BOOTSTRAP_PASSWORD for the fresh app account.
Do not share either value in chat. No original learner accounts were migrated.
The original production service was not edited. A local screenshot records the
Free plan, branch and Live deployment status (render-free-live.jpg).

Git CLI push failed because the stored credential was rejected. The connected
GitHub API uploaded sanitized blobs/tree and created a separate commit/branch;
its tree SHA equals the tested local tree. Local source commits have different
commit SHAs; main remains at the original commit. Documentation-only revisions
may follow on the staging branch; application auto deploy is off.

## Connectivity recheck

A subsequent check still shows the staging service Live in Render. From this
machine, both the original thana-korean.onrender.com and the new staging host
resolve to 216.24.57.16 / 216.24.57.18 but HTTPS requests time out. Earlier attempts
also reported TLS connection closed. This suggests a shared connectivity problem,
not proof of an app defect or a working external route. No network/security
settings were changed. The user subsequently reported `status: ok` from mobile
network /health. This establishes public reachability from that device/network;
the exact cause of this machine's failure remains undiagnosed. The user then
confirmed both reviewer and admin sign-in succeed. Physical-device audio and
install behavior remain future acceptance checks.

## Staging provisioning acceptance

Completed on 2026-10-15: separate Free service, sanitized branch, locked runtime,
private reviewer gate, paid providers disabled, live server health and user
confirmation of both reviewer and admin sign-in. Online sign-in evidence is the
user's report, not an automated browser test from this machine. No credentials
were requested in chat or published. The deployment step is complete.

Android/iPhone audio and install checks are separate device acceptance; provider
microphone scoring remains disabled and is not part of Free demo provisioning.
Production cutover, durable storage, live providers and curriculum expansion
remain future work; this acceptance does not claim they are completed.

## Listening release — 2026-10-16

User authorized redeployment with no staging data to preserve. Source b623171
(tree d2d67ff, local d13b274) includes the readiness queue, EPS explanations,
dictionary metadata and listening authoring/practice/mocks. Deployment
dep-db8nth6q1p3s738omssg built successfully; gunicorn started, health returned
200 and the reviewer gate returned 401. No public-browser acceptance of this
new version is claimed from the restricted in-app browser.


## Approved objectives release — 2026-10-16

User explicitly confirmed there was no staging data to preserve and authorized
redeployment of local d4d94b9. Source-only GitHub upload created c82e5da7dd8a4bacf2214e43b2378db1ca75f3d1;
its complete tree c5ddc83207377b197e823cb009252a8a5b8ba600 exactly matches
the authorized local commit. Different commit IDs reflect the GitHub API parent/
commit creation, not different files. Remote ref and commit were read back.

Automatic approval review initially rejected Deploy latest commit due to this
commit-ID ambiguity. After explicit tree equality checks, Render's Deploy a
specific commit for c82e5da was accepted. Deployment dep-db8suj49v7es73dp2sgg
reported Deploy succeeded | Live in 58.6 seconds. Logs show gunicorn startup,
GET /health 200 and unauthenticated root HEAD/GET 401. The build installed the
pinned imageio-ffmpeg Linux wheel; this does not prove actual Linux MP4 decoding.
Screenshot evidence: docs/render-objectives-live.png (local, source-excluded).

Scope: the approved 110-test snapshot (course levels, pointer draft ordering,
shared lesson vocabulary and objectives, plus earlier features). Newer local
question-media/metadata work is not deployed. Provider/email flags were not
enabled. Same Free service, reviewer protection and disposable data policy.
Production, main and domain were not modified. Full end-user re-acceptance is
pending; no alternate public-page access path was attempted after the earlier
browser-policy restriction. Use an ordinary external browser to review staging.
