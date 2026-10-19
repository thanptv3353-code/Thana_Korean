"""Build a private, non-activating identity/access reconciliation plan."""
from collections import Counter
from firebase_migration import inspect_transfer


def reconcile_transfer(payload):
    """Preserve UID ownership and separate paid scopes; never invent login or expiry."""
    inspect_transfer(payload)
    collections=payload['collections']
    profiles={row['id']:row['data'] for row in collections.get('thana_users',[])}
    usernames=Counter(p.get('username').strip().casefold() for p in profiles.values()
                      if isinstance(p.get('username'),str) and p['username'].strip())
    identities=[]
    for uid,profile in profiles.items():
        name=profile.get('username');issues=[]
        if not isinstance(name,str) or not name.strip():issues.append('missing_username')
        elif usernames[name.strip().casefold()]>1:issues.append('username_collision')
        if profile.get('role') not in ('admin','student'):issues.append('unknown_role')
        if type(profile.get('approved')) is not bool:issues.append('ambiguous_approval')
        if profile.get('deletedAt') is not None:issues.append('deleted_profile')
        scopes={}
        for field,scope in (('paid','general'),('epsPaid','eps'),('seasonalPaid','seasonal')):
            flag=profile.get(field,False)
            # Original isLessonLocked/paid-topic guards treat an absent flag as unpaid.
            scopes[scope]='paid' if flag is True else 'unpaid' if flag is False else 'unresolved'
            if type(flag) is not bool:issues.append('ambiguous_'+field)
        identities.append(dict(firebase_uid=uid,username=name,source_role=profile.get('role'),
            approved=profile.get('approved') is True,scopes=scopes,
            absent_paid_fields=[field for field in ('paid','epsPaid','seasonalPaid') if field not in profile],issues=issues,
            activation='blocked_pending_verified_firebase_auth',entitlement_application='pending_scope_mapping'))
    progress=[]
    for row in collections.get('thana_progress',[]):
        data=row['data'];uid=data.get('uid')
        # Never infer identity by splitting composite IDs or by an email/name match.
        kind='lesson' if isinstance(data.get('lessonId'),str) else 'eps' if any(k in data for k in ('correct','attempted','freeUsed')) else 'missed_words' if 'words' in data else 'unclassified'
        issues=[]
        if not isinstance(uid,str) or uid not in profiles:issues.append('unknown_owner')
        if kind=='lesson':
            score,total=data.get('score'),data.get('total')
            if type(score) not in (int,float) or type(total) not in (int,float) or total<=0 or not 0<=score<=total:issues.append('invalid_score')
            if type(data.get('passed')) is not bool:issues.append('ambiguous_passed')
        if kind=='unclassified':issues.append('unknown_progress_kind')
        progress.append(dict(document_id=row['id'],firebase_uid=uid,kind=kind,
            lesson_id=data.get('lessonId') if kind=='lesson' else None,issues=issues,
            application='pending_review',source=data))
    reasons=Counter(issue for item in identities+progress for issue in item['issues'])
    return dict(project=payload['project'],status='private-review-only',identities=identities,
        progress=progress,summary=dict(profiles=len(identities),progress=len(progress),
            progress_kinds=dict(Counter(p['kind'] for p in progress)),issues=dict(reasons),
            activated_accounts=0,applied_entitlements=0,applied_progress=0),
        limitations=['Firebase Auth verification required','Paid scopes require explicit target mapping',
            'Legacy EPS users and payment documents retained in raw transfer; not applied',
            'No active account, role, password, expiry or ownership is created by this plan'])
