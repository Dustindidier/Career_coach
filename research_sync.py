"""Authenticated daily-research handoff. No direct database writes or credentials on disk."""
import argparse
import base64
import copy
import json
import os
import re
import threading
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from domain import validate_workspace, valid_application_deadline, valid_career_path
from intelligence import canonical_url


def identity(row):
    return tuple(re.sub(r'\W+', ' ', row.get(k, '').lower()).strip() for k in ('company', 'title', 'location'))


def merge_batch(workspace, rows, run_id, now):
    if not isinstance(rows, list) or len(rows) > 10:
        raise ValueError('Supply zero to ten reviewed research records.')
    # Validate the entire incoming batch before changing anything.
    for row in rows:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k].strip() for k in ('company','title','sourceUrl','posting','availabilityEvidence','verifiedAt','salary','location')):
            raise ValueError('Each record needs a source, description, pay, location and dated availability evidence.')
        if not canonical_url(row['sourceUrl']) or not valid_application_deadline(row.get('applicationDeadline')) or not valid_career_path(row.get('careerPath')):
            raise ValueError('Each record needs a valid employer link, deadline evidence and career ladder.')
        if not all(isinstance(row.get(k),list) and all(isinstance(v,str) for v in row[k]) for k in ('fitReasons','concerns')):
            raise ValueError('Each record needs fit reasons and concerns.')
    result=copy.deepcopy(workspace)
    profile=result['profile'];meta=profile.setdefault('dailyResearch',{})
    if meta.get('lastRunId')==run_id:
        return result,dict(added=meta.get('lastAdded',0),skipped=0,duplicateRun=True)
    existing=result['jobs']+profile.get('discovery',[])
    urls={canonical_url(x.get('sourceUrl','')) for x in existing}
    identities={identity(x) for x in existing}
    added=skipped=0
    for row in rows:
        key=canonical_url(row['sourceUrl']);name=identity(row)
        if key in urls or name in identities:
            skipped+=1;continue
        profile.setdefault('discovery',[]).append({**row,'id':str(uuid.uuid4()),'decision':'pending','jobId':'','decisionReason':'','decidedAt':'','researchRunId':run_id})
        urls.add(key);identities.add(name);added+=1
    meta.update(lastRunId=run_id,lastRunAt=now,lastStatus='succeeded',lastAdded=added,lastSkipped=skipped,
                lastNote='Research completed; no qualifying new roles found.' if not added else 'New researched roles added to Discover for review.')
    if not validate_workspace(result):raise ValueError('Resulting workspace failed validation; nothing saved.')
    return result,dict(added=added,skipped=skipped,duplicateRun=False)


class AppClient:
    def __init__(self,base,user,password):
        if not password:raise ValueError('App authentication is required.')
        self.base=base.rstrip('/')
        self.auth='Basic '+base64.b64encode((user+':'+password).encode()).decode()
    def request(self,path,data=None,etag=None):
        headers={'Authorization':self.auth,'Content-Type':'application/json'}
        if etag:headers['If-Match']=etag
        request=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,
            method='PUT' if data is not None else 'GET',headers=headers)
        with urllib.request.urlopen(request,timeout=40) as response:
            raw=response.read();return (json.loads(raw) if raw else None),response.headers.get('ETag')


@contextmanager
def connect(render_service_id=None):
    if not render_service_id:
        base=os.environ.get('NEXT_CHAPTER_URL','')
        if not base.startswith('https://'):raise ValueError('Set NEXT_CHAPTER_URL to the authenticated HTTPS app URL.')
        yield AppClient(base,os.environ.get('CAREER_USER','owner'),os.environ.get('CAREER_PASSWORD',''))
        return
    if not re.fullmatch(r'srv-[a-z0-9]+',render_service_id):raise ValueError('Invalid Render service ID.')
    # Authenticated app mirror for environments whose outbound policy excludes the hosted hostname.
    # Server storage credentials remain inside the server; mutations use its normal user API + ETag.
    token=os.environ.get('RENDER_API_KEY','')
    if not token:raise ValueError('Render access is not configured; do not proceed without app access.')
    request=urllib.request.Request('https://api.render.com/v1/services/'+render_service_id+'/env-vars?limit=100',headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(request,timeout=30) as response:
        config={r['envVar']['key']:r['envVar']['value'] for r in json.load(response)}
    for key in ('SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY','CAREER_PASSWORD'):
        if not config.get(key):raise ValueError('Required app configuration is unavailable.')
    import server
    server.SUPABASE_URL=config['SUPABASE_URL'];server.SUPABASE_KEY=config['SUPABASE_SERVICE_ROLE_KEY']
    server.AUTH_USER=config.get('CAREER_USER','owner');server.AUTH_PASSWORD=config['CAREER_PASSWORD']
    httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:yield AppClient('http://127.0.0.1:'+str(httpd.server_port),server.AUTH_USER,server.AUTH_PASSWORD)
    finally:httpd.shutdown();httpd.server_close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-service-id')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('read')
    imp=sub.add_parser('import');imp.add_argument('batch');imp.add_argument('--run-id')
    schedule=sub.add_parser('schedule');schedule.add_argument('metadata')
    args=parser.parse_args()
    private=Path('.career-private');private.mkdir(exist_ok=True)
    with connect(args.render_service_id) as client:
        if args.command=='read':
            w,etag=client.request('/api/workspace');brief,_=client.request('/api/research-context')
            (private/'daily-research-workspace.json').write_text(json.dumps({'etag':etag,'body':w},indent=2))
            (private/'daily-research-brief.json').write_text(json.dumps(brief,indent=2))
            print(json.dumps({'read':True,'revision':brief['revision'],'briefPath':str(private/'daily-research-brief.json'),'workspacePath':str(private/'daily-research-workspace.json')}))
            return
        now=datetime.now(timezone.utc).isoformat()
        if args.command=='import':
            file=Path(args.batch)
            if file.stat().st_size>700000:raise ValueError('Batch exceeds 700 KB.')
            rows=json.loads(file.read_text())
            run_id=args.run_id or 'daily:'+datetime.now(ZoneInfo('America/New_York')).date().isoformat()
        else:
            metadata=json.loads(Path(args.metadata).read_text())
            if not isinstance(metadata.get('automationId'),str) or not metadata['automationId'] or metadata.get('enabled') is not True:
                raise ValueError('Use metadata from a confirmed enabled scheduler task.')
        for attempt in range(3):
            w,etag=client.request('/api/workspace')
            if args.command=='import':updated,stats=merge_batch(w,rows,run_id,now)
            else:
                updated=copy.deepcopy(w);updated['profile'].setdefault('dailyResearch',{}).update(metadata);stats={'scheduleSaved':True}
            if not validate_workspace(updated):raise ValueError('Invalid update.')
            if updated==w:print(json.dumps(stats));return
            (private/'daily-research-save-backup.json').write_text(json.dumps({'etag':etag,'body':w}))
            try:client.request('/api/workspace',updated,etag)
            except urllib.error.HTTPError as error:
                if error.code==409 and attempt<2:continue
                raise
            verified,_=client.request('/api/workspace')
            if args.command=='import':
                if verified['profile']['dailyResearch'].get('lastRunId')!=run_id:raise ValueError('Run persistence not confirmed.')
                expected={r['id'] for r in updated['profile'].get('discovery',[]) if r.get('researchRunId')==run_id}
                if not expected.issubset({r['id'] for r in verified['profile'].get('discovery',[])}):raise ValueError('Research records not confirmed.')
            else:
                if verified['profile']['dailyResearch'].get('automationId')!=metadata['automationId']:raise ValueError('Schedule persistence not confirmed.')
            print(json.dumps({'saved':True,**stats}));return


if __name__=='__main__':
    main()
