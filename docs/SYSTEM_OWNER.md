# Super Admin activation and compatibility

Four roles are implemented: student, teacher, admin, superadmin. Super Admin has
administration/content access plus system control. Once any Super Admin record
exists, ordinary Admin cannot assign roles, alter administrator account status,
issue administrator recovery links, configure teacher course permissions, edit
homepage system settings, change the global membership plan or download the full
private backup. Admin retains content, learner status, payment review and lesson/
course access management. Existing server membership and teacher-scope checks
continue to apply to learners/teachers.

Until the initial owner is deliberately configured, approved legacy Admins keep
their prior system powers. The dashboard displays that compatibility state.
Installing this code does not promote/demote an existing account. Once configured,
a rejected/disabled Super Admin does not restore legacy Admin system powers.
Keep an approved owner and private backups; permission endpoints reject removal
of the last approved Super Admin and self-removal. All role checks use current
server account data; a forged session role does not grant access.

## Existing private runtime

An operator chooses the intended existing approved administrator. Update any old
password through /account first; activation requires the modern PBKDF2 format.
Take and retain a private backup, stop the server (activation is an offline
operation), and set THANA_DATA_DIR and THANA_PLATFORM_DB to the actual private
runtime locations. Never point these at preserved Desktop source inputs.

Run a dry-run first:

```
python scripts/activate_system_owner.py --username YOUR_EXISTING_ADMIN
```

Then explicitly activate the chosen account:

```
python scripts/activate_system_owner.py --username YOUR_EXISTING_ADMIN --apply
```

The script requires explicit THANA_DATA_DIR, rejects non-admin/non-approved
accounts and refuses to create a second initial owner. It never prints passwords
or hashes. Activation updates only the selected account role/auth version and
invalidates its old sessions; sign in again after restarting. Further owner/staff
role assignments use the Super Admin account in Management. HTTP permission
changes enter the existing audit; the offline script prints its operator result
and is not an independent immutable audit ledger.

## Fresh installation only

An operator may explicitly set THANA_BOOTSTRAP_SUPERADMIN=1 before the first
startup of an empty runtime. The existing private bootstrap password mechanism
then creates the initial admin username with superadmin role. Default is 0.
The flag never changes any existing account, even when changed later. Render
Free runtime resets lose account data; this flag is an operator choice for a new
empty runtime, not persistent storage. It was not enabled on the actual service.

## Evidence and limits

128 isolated tests pass, including current-role enforcement, owner content/
system access, ordinary-admin direct denial, protected recovery, permission
changes, forged-role denial, dry-run/activation session invalidation and the fresh
bootstrap flag leaving existing administrators unchanged. Synthetic browser
verified hidden system controls and disabled role fields for ordinary Admin,
then visible system controls for Super Admin. 320px layout had no overflow.
No actual user account was promoted or demoted; activation remains an operator
step. Role separation is included in staging a5ec247 (137-test release). Actual owner activation is still pending; the initial-owner flag remains off. Later speaking fixes through local dc219a6 are not deployed.
