"""Offline, read-only migration checks. Never enables authentication or publication."""
import json
from pathlib import Path
import re
import sqlite3
from contextlib import ExitStack


def modern_hash(value):
    if not isinstance(value, str):
        return False
    match = re.fullmatch(r'pbkdf2_sha256\$(\d{6,7})\$([0-9a-f]{32})\$([0-9a-f]{64})', value)
    return bool(match and 100_000 <= int(match[1]) <= 1_000_000)


def inspect_runtime(directory):
    """Return only check names/results: no usernames, UIDs, passwords or paths."""
    root = Path(directory).resolve()
    checks = {}
    with ExitStack() as stack:
        databases = {}
        for name in ('legacy', 'platform'):
            path = root / (name + '.sqlite3')
            if not path.is_file() or path.is_symlink():
                checks[name + '_database'] = False
                continue
            try:
                db = sqlite3.connect(path.as_uri() + '?mode=ro')
                stack.callback(db.close)
                db.execute('PRAGMA query_only=ON')
                checks[name + '_database'] = db.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
                if checks[name + '_database']:
                    databases[name] = db
            except sqlite3.Error:
                checks[name + '_database'] = False
        if len(databases) == 2:
            try:
                row = databases['legacy'].execute("SELECT content FROM documents WHERE name='users.json'").fetchone()
                users = json.loads(row[0]) if row else None
                if not isinstance(users, dict) or not all(isinstance(u, dict) for u in users.values()):
                    raise ValueError('Invalid accounts')
                admins = [u for u in users.values() if u.get('role') in ('admin', 'superadmin') and u.get('status') == 'approved']
                checks['approved_administrator_exists'] = bool(admins)
                bindings = databases['platform'].execute('SELECT uid,username,enabled FROM firebase_account_bindings').fetchall()
                enabled = {(uid, username) for uid, username, flag in bindings if type(flag) is int and flag == 1}
                # This is structural evidence only. Enabled rows cannot prove provider access.
                checks['administrator_authentication_structure'] = bool(admins) and all(
                    modern_hash(u.get('pw')) or
                    (u.get('pw') is None and u.get('auth_method') == 'firebase_only'
                     and isinstance(u.get('firebase_uid'), str) and bool(u['firebase_uid'])
                     and (u['firebase_uid'], u.get('username')) in enabled)
                    for u in admins)
                checks['enabled_bindings_match_approved_accounts'] = all(
                    username in users and users[username].get('username') == username
                    and users[username].get('status') == 'approved'
                    and users[username].get('firebase_uid') == uid
                    for uid, username in enabled)
                checks['account_schema'] = True
            except (sqlite3.Error, ValueError, TypeError, KeyError):
                checks['account_schema'] = False
    return dict(status='offline-checks-only', checks=checks,
                blockers=[key for key, ok in checks.items() if not ok],
                production_ready=False,
                required_external_checks=['Production startup preflight', 'Firebase credentials and real sign-in',
                                          'Content/media review and publication', 'Durable target storage',
                                          'Real learner and administrator acceptance'])
