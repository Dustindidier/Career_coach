"""Free identity, provenance, and preparation helpers.
Canonicalization design adapted from Career Ops (MIT); see THIRD_PARTY_NOTICES.md.
"""
import hashlib
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING = {'gclid','fbclid','msclkid','trackingid','refid','li_fat_id','mc_cid','mc_eid'}
STOP = set('the and for with from that this have will your our are not you tell about time when how give example describe situation what were was into role job team'.split())


def canonical_url(value):
    try:
        p = urlsplit(value.strip())
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
            return ''
        host = p.hostname.lower()
        if '..' in host:
            return ''
        host = host[:-1] if host.endswith('.') else host
        if host == 'linkedin.com' or host.endswith('.linkedin.com'):
            match = re.search(r'/jobs/view/(?:[^/]*-)?(\d+)', p.path)
            if match:
                return 'https://www.linkedin.com/jobs/view/' + match[1]
        if host == 'indeed.com' or host.endswith('.indeed.com'):
            job_id = dict(parse_qsl(p.query)).get('jk', '')
            if re.fullmatch(r'[a-zA-Z0-9_-]+', job_id):
                return 'https://www.indeed.com/viewjob?jk=' + job_id
        port = p.port
        netloc = host + ((':' + str(port)) if port and port not in (80,443) else '')
        # Keep functional parameters (including gh_jid, ref, source) and hash routes.
        query = [(k,v) for k,v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in TRACKING]
        fragment = p.fragment if p.fragment.startswith(('/', '!/')) else ''
        return urlunsplit(('https', netloc, p.path.rstrip('/') or '/', urlencode(sorted(query, key=lambda item:item[0])), fragment))
    except (ValueError, AttributeError):
        return ''


def tokens(text):
    return {w for w in re.findall(r'[^\W_]+', str(text).lower()) if len(w)>2 and w not in STOP}


def duplicate_check(candidate, existing):
    key = canonical_url(candidate.get('sourceUrl', ''))
    if key:
        for item in existing:
            if canonical_url(item.get('sourceUrl','')) == key:
                return {'status':'exact', 'recordId':item['id'], 'title':item.get('title',''), 'reason':'Same canonical posting URL; tracking parameters ignored.'}
    company = re.sub(r'\W+', ' ', candidate.get('company','').lower()).strip()
    title = tokens(candidate.get('title',''))
    description = tokens(candidate.get('posting',''))
    if company in ('', 'employer not verified', 'unknown'):
        return {'status':'new'}
    for item in existing:
        if item.get('id') == candidate.get('id'):
            continue
        other_company = re.sub(r'\W+', ' ', item.get('company','').lower()).strip()
        if company != other_company:
            continue
        other_title = tokens(item.get('title',''))
        other_description = tokens(item.get('posting',''))
        similar_description = len(description)>25 and len(other_description)>25 and len(description & other_description)/len(description | other_description)>=0.8
        same_title = bool(title) and title == other_title
        if same_title or similar_description:
            return {'status':'possible','recordId':item['id'],'title':item.get('title',''),
                    'reason':'Similar role at the same named employer; different requisitions may be distinct. Review before combining.'}
    return {'status':'new'}


def rank_stories(stories, question, focus=''):
    query = tokens(question + ' ' + focus)
    ranked=[]
    for story in stories:
        if not isinstance(story,dict):
            continue
        tag=tokens(story.get('tags','')); title=tokens(story.get('title',''))
        body=tokens(str(story.get('action',''))+' '+str(story.get('outcome','')))
        matched=query & (tag|title|body)
        score=3*len(query&tag)+2*len(query&title)+len(query&body)
        if score:
            ranked.append({'id':story.get('id',''),'title':story.get('title',''),'matchedTerms':sorted(matched)[:8],
                           'confirmed':story.get('confirmed') is True,'weight':score})
    ranked.sort(key=lambda item:(-int(item['confirmed']),-item['weight'],item['title']))
    return [{k:v for k,v in item.items() if k!='weight'} for item in ranked[:3]]


def source_digest(workspace, job):
    records={'facts':[e for e in workspace['profile'].get('entries',[]) if e.get('confirmed') and e.get('category')!='Preference'],
             'stories':[s for s in workspace['stories'] if s.get('confirmed')],
             'job':{k:job.get(k) for k in ('id','company','title','requirements','posting','sourceUrl')}}
    return hashlib.sha256(json.dumps(records,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

NUMBER = re.compile(r'(?<!\w)(?:[$£€]\s*)?\d[\d,]*(?:\.\d+)?(?:\s*(?:%|years?\b|months?\b|weeks?\b|patients?\b|beds?\b|hours?\b|million\b|thousand\b|[kmb]\b|x\b|percent\b))?(?!\w)', re.I)
CREDENTIALS = {'RN':r'\bRN\b|\bregistered nurse\b','BSN':r'\bBSN\b|\bbachelor(?:s|\x27s)? (?:degree )?(?:of science )?in nursing\b',
               'MSN':r'\bMSN\b','MBA':r'\bMBA\b|\bmaster(?:s|\x27s)? (?:of |in )business administration\b',
               'CCRN':r'\bCCRN\b','ACLS':r'\bACLS\b','BLS':r'\bBLS\b','CCRC':r'\bCCRC\b','CCRP':r'\bCCRP\b','PhD':r'\bPh\.?D\b'}
NEGATION = re.compile(r'\b(?:not|no|without|incomplete|unfinished|pursuing|coursework|expired|lapsed|in progress|working toward|plan to|intend to|need to|will pursue|considering)\b', re.I)


def numbers(text):
    return {re.sub(r'[\s,]+','',m.group().lower()) for m in NUMBER.finditer(text)}


def positive_credentials(text):
    found=set()
    for key, pattern in CREDENTIALS.items():
        for match in re.finditer(pattern,text,re.I):
            start=max(text.rfind('\n',0,match.start()), text.rfind('.',0,match.start()))+1
            end=text.find('\n',match.end()); end=len(text) if end<0 else end
            context=text[max(start,match.start()-65):min(end,match.end()+65)]
            if not NEGATION.search(context):
                found.add(key)
    return found


def audit_materials(workspace, job, text, digest=''):
    facts=[e['text'] for e in workspace['profile'].get('entries',[]) if e.get('confirmed') and e.get('category')!='Preference']
    stories=['\n'.join(s.get(k,'') for k in ('situation','action','outcome')) for s in workspace['stories'] if s.get('confirmed')]
    sources=facts+stories
    approved_numbers=set().union(*(numbers(s) for s in sources)) if sources else set()
    approved_credentials=set().union(*(positive_credentials(s) for s in sources)) if sources else set()
    issues=[]
    for item in sorted(numbers(text)-approved_numbers):
        issues.append({'kind':'Unsupported figure/date','detail':item,'action':'Confirm the specific claim in career memory, correct it, or remove it.'})
    for item in sorted(positive_credentials(text)-approved_credentials):
        issues.append({'kind':'Credential needs evidence','detail':item,'action':'Add a positive, current confirmed credential source; coursework or an expired credential is not completion.'})
    placeholders=list(dict.fromkeys(re.findall(r'\[[^\]\n]{1,300}\]',text)))
    for item in placeholders[:20]:
        issues.append({'kind':'Unfilled placeholder','detail':item,'action':'Replace with accurate information or remove before applying.'})
    changed=bool(digest and digest!=source_digest(workspace,job))
    if not digest and job.get('materials'):
        issues.append({'kind':'Source version not tracked','detail':'This saved draft predates source-version tracking.','action':'Rebuild or review it against current confirmed evidence.'})
    if changed:
        issues.append({'kind':'Sources changed','detail':'Your source library or requirement map changed after this draft was generated.','action':'Recheck the draft against current evidence.'})
    return {'issues':issues,'sourceChanged':changed,'checkedAtLabel':'Checked against current confirmed records',
            'limitations':'Heuristic review, not proof of accuracy. Reusing a known number in a different claim can still be wrong. Contact details may need confirmation. External licensure and employer facts are not verified.'}
