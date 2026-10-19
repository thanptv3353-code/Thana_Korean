# Production cutover status and procedure

The current user decision is free-only migration preparation while keeping the
real website unchanged. Production replacement and paid hosting are deferred.
This source document contains no private runtime observations or account data.

Before a later authorized cutover:

1. Verify actual deployed source, domain ownership and hosting target. Never infer
   them from the repository or a similarly named service.
2. Obtain/validate the actual private working transfer. Preserve original IDs,
   unknown records and source semantics; never guess identity ownership.
3. Verify a durable private runtime and storage suitable for SQLite/media.
   Disposable free-service storage is not durable production storage.
4. Rehearse identity/history/scoped access and content/media migration privately.
   Original folders stay read-only; no real credentials/data enter source bundles.
5. Configure official Firebase authentication with explicit bindings and current
   local permissions. Resolve the production Firebase-only administrator preflight
   before enabling accounts. No password export or security-rule weakening.
6. Review translations, answers and all media; explicitly publish only approved
   content. Keep draft media/receipts protected and provider flags disabled unless
   configured and independently verified.
7. Run release checks and real mobile/learner/admin acceptance, including access,
   grading, exam deadlines, history, receipts and failure/recovery behavior.
8. Apply only the specifically authorized hosting/domain change, then verify the
   actual live result. Source upload, successful build or health alone is not proof
   of a completed production migration.

The user previously waived an archival backup of the old site. Do not add a new
backup prerequisite. A validated private migration working transfer is still
necessary to move the data correctly before replacing its source. No paid service
purchase is authorized by this document.
