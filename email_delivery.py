"""Private verification outbox and explicit SMTP worker; web requests never send."""
import os,re,smtplib,ssl,sqlite3,time,secrets
from email.message import EmailMessage
from urllib.parse import urlparse


def normalize_email(value):
    if not isinstance(value,str) or len(value)>254:return None
    value=value.strip().lower()
    if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+",value):return None
    local,domain=value.rsplit('@',1)
    if len(local)>64 or local.startswith('.') or local.endswith('.') or '..' in local or any(part.startswith('-') or part.endswith('-') for part in domain.split('.')):return None
    return value


def configuration(env=None):
    e=os.environ if env is None else env
    if e.get('THANA_EMAIL_ENABLED')!='1':return None
    try:
        base=e.get('THANA_PUBLIC_URL','').rstrip('/');u=urlparse(base)
        if any(ch.isspace() or ch=='\\' for ch in base):return None
        if u.port is not None and not 1<=u.port<=65535:return None
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.path:return None
        host=e.get('THANA_SMTP_HOST','');port=int(e.get('THANA_SMTP_PORT','587'));sender=normalize_email(e.get('THANA_EMAIL_FROM',''))
        if not re.fullmatch(r'[a-zA-Z0-9.-]+',host) or port not in (465,587) or not sender or not e.get('THANA_SMTP_USERNAME') or not e.get('THANA_SMTP_PASSWORD'):return None
        return {'base':base,'host':host,'port':port,'sender':sender,'username':e['THANA_SMTP_USERNAME'],'password':e['THANA_SMTP_PASSWORD']}
    except ValueError:return None


def send_message(cfg,recipient,body):
    message=EmailMessage();message['From']=cfg['sender'];message['To']=recipient;message['Subject']='THANA KOREAN · Verify your email / 이메일 확인';message.set_content(body)
    context=ssl.create_default_context()
    if cfg['port']==465:
        with smtplib.SMTP_SSL(cfg['host'],cfg['port'],timeout=15,context=context) as smtp:
            smtp.login(cfg['username'],cfg['password']);smtp.send_message(message)
    else:
        with smtplib.SMTP(cfg['host'],cfg['port'],timeout=15) as smtp:
            smtp.ehlo();smtp.starttls(context=context);smtp.ehlo();smtp.login(cfg['username'],cfg['password']);smtp.send_message(message)


def deliver_pending(path,limit=20):
    cfg=configuration()
    if not cfg:raise ValueError('Email delivery is not configured')
    counts={'sent':0,'failed':0,'expired':0}
    c=sqlite3.connect(path);c.row_factory=sqlite3.Row
    try:
        for _ in range(min(max(limit,1),20)):
            stamp=time.time();lease=secrets.token_hex(16)
            with c:
                c.execute('BEGIN IMMEDIATE')
                expired=c.execute("UPDATE email_outbox SET state='expired',recipient='',body='',lease='' WHERE state IN ('pending','sending') AND expires<=?",(stamp,)).rowcount;counts['expired']+=expired
                row=c.execute("SELECT * FROM email_outbox WHERE expires>? AND available<=? AND (state='pending' OR (state='sending' AND lease_until<=?)) ORDER BY id LIMIT 1",(stamp,stamp,stamp)).fetchone()
                if not row:break
                c.execute("UPDATE email_outbox SET state='sending',lease=?,lease_until=?,attempts=attempts+1 WHERE id=?",(lease,stamp+120,row['id']))
            try:send_message(cfg,row['recipient'],row['body'])
            except (OSError,smtplib.SMTPException):
                attempts=row['attempts']+1;terminal=attempts>=5
                with c:c.execute("UPDATE email_outbox SET state=?,available=?,lease='',recipient=CASE WHEN ? THEN '' ELSE recipient END,body=CASE WHEN ? THEN '' ELSE body END WHERE id=? AND lease=?",('failed' if terminal else 'pending',time.time()+min(900,60*2**attempts),terminal,terminal,row['id'],lease))
                counts['failed']+=1
            else:
                with c:c.execute("UPDATE email_outbox SET state='sent',sent=?,recipient='',body='',lease='' WHERE id=? AND lease=?",(time.time(),row['id'],lease))
                counts['sent']+=1
    finally:c.close()
    return counts
