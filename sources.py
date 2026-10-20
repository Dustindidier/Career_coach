"""Public employer feeds only. No login, scraping, or paid job-data service."""
import json
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import quote

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]
    def handle_data(self, data):
        self.parts.append(data)

def plain(value):
    parser=PlainText(); parser.feed(value or '')
    return ' '.join(' '.join(parser.parts).split())

def fetch_jobs(provider, board, query=''):
    if provider not in ('greenhouse','lever') or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', board):
        raise ValueError('Choose a supported provider and a valid board slug.')
    base = ('https://boards-api.greenhouse.io/v1/boards/' + quote(board) + '/jobs?content=true' if provider=='greenhouse'
            else 'https://api.lever.co/v0/postings/' + quote(board) + '?mode=json')
    request=urllib.request.Request(base,headers={'Accept':'application/json','User-Agent':'NextChapter/2.0'})
    with urllib.request.urlopen(request,timeout=25) as response:
        raw=response.read(5_000_001)
    if len(raw)>5_000_000:
        raise ValueError('Feed too large. Use a narrower employer source.')
    data=json.loads(raw)
    jobs=data.get('jobs',[]) if provider=='greenhouse' else data
    result=[]
    terms=[x.lower() for x in query.split() if x.strip()]
    for item in jobs:
        title=item.get('title','') if provider=='greenhouse' else item.get('text','')
        description=plain(item.get('content','') if provider=='greenhouse' else item.get('descriptionPlain',item.get('description','')))
        location=item.get('location',{}).get('name','') if provider=='greenhouse' else item.get('categories',{}).get('location','')
        if terms and not all(word in (title+' '+description+' '+location).lower() for word in terms):
            continue
        result.append({'id':provider+':'+board+':'+str(item['id']), 'company':board, 'title':title,
                       'sourceUrl':item.get('absolute_url','') if provider=='greenhouse' else item.get('hostedUrl',''),
                       'posting':description[:40000], 'location':location, 'provider':provider})
        if len(result)>=100:break
    return result
