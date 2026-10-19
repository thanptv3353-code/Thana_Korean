"""Read-only working transfer using an explicitly authorized gcloud session.

No Auth password export, API writes, rule changes or Cloud Storage export job.
Run on the operator's authorized Cloud Shell, not in automated release tests.
"""
import datetime
import json
import math
import os
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request

PROJECT='korean-lao-exam'
COLLECTIONS=('thana_users','thana_usernames','thana_announcements','thana_lessons',
 'thana_progress','thana_settings','thana_phrases','thana_lesson_meta',
 'thana_grammar_overrides','thana_payments','thana_eps_overrides','thana_phone_orders',
 'thana_seasonal_overrides','thana_seasonal_exam_groups','thana_seasonal_exam_results',
 'users','examConfig','examGroups','examResults','paymentProofs','paymentSettings')


def value(raw):
    if not isinstance(raw,dict) or len(raw)!=1:raise ValueError('Invalid Firestore value')
    kind,item=next(iter(raw.items()))
    if kind=='nullValue':return None
    if kind=='booleanValue' and isinstance(item,bool):return item
    if kind in ('stringValue','timestampValue','bytesValue','referenceValue') and isinstance(item,str):return item
    if kind=='integerValue' and isinstance(item,str):return int(item)
    if kind=='doubleValue':
        number=float(item)
        return number if math.isfinite(number) else {'firestoreDouble':str(item)}
    if kind=='geoPointValue' and isinstance(item,dict):return item
    if kind=='arrayValue' and isinstance(item,dict):return [value(v) for v in item.get('values',[])]
    if kind=='mapValue' and isinstance(item,dict):return {k:value(v) for k,v in item.get('fields',{}).items()}
    raise ValueError('Unsupported Firestore value')


def collect(get_json,read_time,limit=20000):
    collections={};total=0
    for collection in COLLECTIONS:
        docs=[];page='';seen=set()
        prefix=f'projects/{PROJECT}/databases/(default)/documents/{collection}/'
        while True:
            query={'pageSize':100,'readTime':read_time}
            if page:query['pageToken']=page
            url='https://firestore.googleapis.com/v1/'+prefix[:-1]+'?'+urllib.parse.urlencode(query)
            response=get_json(url)
            if not isinstance(response,dict) or 'error' in response:raise ValueError('Firestore read failed')
            for doc in response.get('documents',[]):
                name=doc.get('name','');fields=doc.get('fields',{})
                if not isinstance(name,str) or not name.startswith(prefix) or '/' in name[len(prefix):] or not isinstance(fields,dict):raise ValueError('Unexpected document identity')
                total+=1
                if total>limit:raise ValueError('Transfer limit exceeded')
                docs.append({'id':name[len(prefix):],'data':{k:value(v) for k,v in fields.items()},'firestore_fields':fields})
            page=response.get('nextPageToken','')
            if not page:break
            if not isinstance(page,str) or page in seen:raise ValueError('Invalid pagination')
            seen.add(page)
        collections[collection]=docs
    return {'project':PROJECT,'collections':collections}


def main():
    token=subprocess.check_output(['gcloud','auth','print-access-token'],text=True,stderr=subprocess.DEVNULL).strip()
    if not token:raise ValueError('Authorize the gcloud session first')
    def get_json(url):
        req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token},method='GET')
        with urllib.request.urlopen(req,timeout=45) as response:return json.load(response)
    read_time=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
    payload=collect(get_json,read_time)
    destination=Path.home()/('thana-working-transfer-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
    with os.fdopen(os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w',encoding='utf-8') as output:
        json.dump(payload,output,ensure_ascii=False,allow_nan=False)
    print('Working transfer file:',destination.name)
    print('Collection document counts:',json.dumps({k:len(v) for k,v in payload['collections'].items()},sort_keys=True))
    print('Firestore only; Auth identities and subcollections are not exported. Source documents were not changed.')

if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Transfer failed. No source records were changed; no usable transfer is claimed.')
