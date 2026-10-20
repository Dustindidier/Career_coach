"""Bounded public employer feeds. No login, browser automation, or paid APIs."""
import json
import re
import urllib.request
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]
    def handle_data(self, data):self.parts.append(data)

def plain(value):
    parser=PlainText();parser.feed(value or '')
    return ' '.join(' '.join(parser.parts).split())

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):return None

def request_text(url, body=None):
    request=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,
        headers={'Accept':'application/json, text/html','Content-Type':'application/json','User-Agent':'NextChapter/3.0'},
        method='POST' if body is not None else 'GET')
    # Never follow a provider redirect into an arbitrary or private destination.
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=25) as response:
        raw=response.read(5_000_001)
    if len(raw)>5_000_000:raise ValueError('Feed exceeds the 5 MB safety limit; narrow the source.')
    return raw.decode('utf-8',errors='replace')

def request_json(url, body=None):return json.loads(request_text(url,body))

def board_url(provider, value):
    p=urlsplit(value)
    if p.scheme!='https' or p.username or p.password or p.port is not None:
        raise ValueError('Use an HTTPS careers URL without credentials or a port.')
    host=(p.hostname or '').lower()
    if provider=='workday':
        match=re.fullmatch(r'([a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com',host)
        if not match:raise ValueError('Use a tenant.wdN.myworkdayjobs.com careers URL.')
        parts=[x for x in p.path.split('/') if x]
        if parts and re.fullmatch(r'[a-z]{2}-[A-Z]{2}',parts[0]):parts=parts[1:]
        if not parts or not re.fullmatch(r'[A-Za-z0-9_-]+',parts[0]):raise ValueError('Include the Workday career-site name in the URL.')
        return 'https://'+host,match[1],parts[0]
    if provider=='icims' and re.fullmatch(r'[a-z0-9-]+\.icims\.com',host):
        return 'https://'+host,'',''
    raise ValueError('Use a public employer portal at a supported provider domain.')

def item(identifier, company, title, url, description='', location='', provider='', posted='', summary=False):
    return {'id':identifier,'company':company,'title':title,'sourceUrl':url,'posting':plain(description)[:40000],
            'location':location,'provider':provider,'postedAt':posted,'descriptionStatus':'summary' if summary else 'full'}

def parse_icims(html, origin, company):
    jobs=[]
    for card in re.split(r'\biCIMS_JobCardItem\b',html)[1:]:
        href=re.search(r'href\s*=\s*[\"\x27]([^\"\x27]*?/jobs/\d+/[^\"\x27]+?/job(?:[^\"\x27]*)?)[\"\x27]',card,re.I)
        title=re.search(r'<h3\b[^>]*>(.*?)</h3>',card,re.I|re.S)
        if not href or not title:continue
        url=urljoin(origin,unescape(href[1]));p=urlsplit(url)
        if p.scheme!='https' or p.netloc!=urlsplit(origin).netloc:continue
        location=re.search(r'>\s*Location\s*</span>\s*<span\b[^>]*>(.*?)</span>',card,re.I|re.S)
        identity=re.search(r'/jobs/(\d+)/',p.path)
        jobs.append(item('icims:'+company+':'+identity[1],company,plain(title[1]),origin+p.path,
                         location=plain(location[1]) if location else '',provider='icims',summary=True))
    return jobs

def fetch_source(provider, board, query=''):
    warnings=[];raw=[];partial=False;searched=False
    fetched=datetime.now(timezone.utc).isoformat()
    if provider in ('workday','icims'):
        origin,tenant,site=board_url(provider,board)
        if provider=='workday':
            searched=True;total=0
            for offset in range(0,60,20):
                data=request_json(origin+'/wday/cxs/'+tenant+'/'+site+'/jobs',{'appliedFacets':{},'limit':20,'offset':offset,'searchText':query})
                if not isinstance(data.get('jobPostings'),list):raise ValueError('Workday returned an unexpected response; coverage is unknown.')
                batch=data['jobPostings'];total=int(data.get('total',len(batch)))
                for job in batch:
                    external=job.get('externalPath','')
                    if not external.startswith('/job/'):continue
                    raw.append(item('workday:'+tenant+':'+external,tenant,job.get('title',''),origin+'/'+site+external,
                        location=job.get('locationsText',''),provider=provider,posted=job.get('postedOn',''),summary=True))
                if not batch or offset+len(batch)>=total:break
            partial=total>offset+len(batch)
        else:
            seen=set()
            for page in range(3):
                html=request_text(origin+'/jobs/search?ss=1&pr='+str(page)+'&in_iframe=1')
                batch=parse_icims(html,origin,urlsplit(origin).hostname.split('.')[0])
                if not batch:
                    if re.search(r'no (?:jobs|results|positions)|0 results',plain(html),re.I):break
                    raise ValueError('Portal response could not be parsed or access was denied; job coverage is unknown.')
                new=[j for j in batch if j['sourceUrl'] not in seen]
                if not new:
                    partial=True;warnings.append('The portal repeated a page. Scan stopped with partial coverage.');break
                raw.extend(new);seen.update(j['sourceUrl'] for j in new)
                if len(batch)<20:break
            else:partial=True
        warnings.append('This portal supplies listing summaries. Open the original job and paste its full description before tailoring.')
    else:
        if provider not in ('greenhouse','lever','ashby','smartrecruiters') or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',board):
            raise ValueError('Choose a supported provider and a valid employer board slug.')
        slug=quote(board)
        if provider=='greenhouse':
            data=request_json('https://boards-api.greenhouse.io/v1/boards/'+slug+'/jobs?content=true')
            if not isinstance(data.get('jobs'),list):raise ValueError('Unexpected Greenhouse feed shape.')
            raw=[item('greenhouse:'+board+':'+str(j['id']),board,j.get('title',''),j.get('absolute_url',''),j.get('content',''),j.get('location',{}).get('name',''),provider,j.get('updated_at','')) for j in data['jobs']]
            # Greenhouse updated_at is an update time, not an original posted date.
            for j in raw:j['updatedAt']=j.pop('postedAt')
        elif provider=='lever':
            data=request_json('https://api.lever.co/v0/postings/'+slug+'?mode=json')
            if not isinstance(data,list):raise ValueError('Unexpected Lever feed shape.')
            raw=[item('lever:'+board+':'+str(j['id']),board,j.get('text',''),j.get('hostedUrl',''),j.get('descriptionPlain',j.get('description','')),j.get('categories',{}).get('location',''),provider) for j in data]
        elif provider=='ashby':
            data=request_json('https://api.ashbyhq.com/posting-api/job-board/'+slug)
            if not isinstance(data.get('jobs'),list):raise ValueError('Unexpected Ashby feed shape.')
            raw=[item('ashby:'+board+':'+str(j['id']),board,j.get('title',''),j.get('jobUrl',''),j.get('descriptionPlain',j.get('descriptionHtml','')),j.get('location',''),provider,j.get('publishedAt','')) for j in data['jobs'] if j.get('isListed',True)]
        else:
            for offset in (0,100,200):
                data=request_json('https://api.smartrecruiters.com/v1/companies/'+slug+'/postings?limit=100&offset='+str(offset))
                if not isinstance(data.get('content'),list):raise ValueError('Unexpected SmartRecruiters feed shape.')
                batch=data['content'];total=int(data.get('totalFound',len(batch)))
                raw.extend(item('smartrecruiters:'+board+':'+str(j['id']),j.get('company',{}).get('name',board),j.get('name',''),
                    'https://jobs.smartrecruiters.com/'+slug+'/'+str(j['id']),location=', '.join(str(j.get('location',{}).get(k,'')) for k in ('city','region','country') if j.get('location',{}).get(k)),provider=provider,posted=j.get('releasedDate',''),summary=True) for j in batch)
                if not batch or offset+len(batch)>=total:break
            partial=total>offset+len(batch)
            warnings.append('SmartRecruiters listing summaries may omit full descriptions; verify the original before tailoring.')
    terms=[word.lower() for word in query.split() if word.strip()]
    matched=[j for j in raw if j['title'] and j['sourceUrl'] and (searched or not terms or all(t in (j['title']+' '+j['posting']+' '+j['location']).lower() for t in terms))]
    if len(matched)>100:partial=True
    if partial:warnings.append('A scan/result cap was reached; this is a partial dataset, not the entire employer inventory.')
    return {'jobs':[{**j,'lastSeenAt':fetched} for j in matched[:100]],
            'meta':{'provider':provider,'checkedAt':fetched,'scanned':len(raw),'matched':len(matched),'returned':min(len(matched),100),
                    'partial':partial,'warnings':warnings,'query':query}}

def fetch_jobs(provider, board, query=''):
    """Compatibility wrapper; UI uses fetch_source to retain coverage diagnostics."""
    return fetch_source(provider,board,query)['jobs']
