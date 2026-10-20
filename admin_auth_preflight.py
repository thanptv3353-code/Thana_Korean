"""Fail-closed production administrator authentication validation."""
from contextlib import closing
from pathlib import Path
import sqlite3
from runtime_readiness import modern_hash


def verify_firebase_identity(uid):
    from firebase_auth_routes import sdk
    auth, app = sdk()
    return auth.get_user(uid, app=app)


def validate_admin_authentication(users, database, environment, verify_identity=None):
    """No account changes. Firebase-only admins require explicit bindings and live lookup.

    A successful lookup proves identity availability, not completed end-user login.
    Errors deliberately contain no identities, credentials or provider diagnostics.
    """
    verify_identity = verify_identity or verify_firebase_identity
    firebase_admins = []
    for username, user in users.items():
        if user.get('role') not in ('admin', 'superadmin'):
            continue
        if modern_hash(user.get('pw')):
            continue
        if (user.get('pw') is not None or user.get('auth_method') != 'firebase_only'
                or user.get('status') != 'approved' or user.get('username') != username
                or not isinstance(user.get('firebase_uid'), str) or not user['firebase_uid']
                or environment.get('THANA_FIREBASE_AUTH_ENABLED') != '1'
                or environment.get('FIREBASE_AUTH_EMULATOR_HOST')):
            raise RuntimeError('Configure secure administrator authentication before production')
        firebase_admins.append((username, user['firebase_uid']))
    if not firebase_admins:
        return
    try:
        path = Path(database).resolve()
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro')) as db:
            db.execute('PRAGMA query_only=ON')
            for username, uid in firebase_admins:
                binding = db.execute('SELECT username,enabled FROM firebase_account_bindings WHERE uid=?', (uid,)).fetchone()
                if binding != (username, 1):
                    raise ValueError('Binding unavailable')
                identity = verify_identity(uid)
                if identity.uid != uid or identity.disabled is not False:
                    raise ValueError('Identity unavailable')
    except Exception:
        raise RuntimeError('Verify Firebase administrator bindings and server access before production') from None
