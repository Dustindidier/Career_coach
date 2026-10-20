"""User-authorized Gmail reads and draft creation. No send endpoint."""
import base64
import hashlib
import hmac
import json
import re
import secrets
import time
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser
from sources import plain

SCOPES = 'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose'


def encode(value):
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


def decode(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def start_oauth(client_id, redirect_uri, signing_key):
    nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    payload = encode(json.dumps({'state': nonce, 'verifier': verifier, 'expires': int(time.time()) + 600}).encode())
    cookie = payload + '.' + encode(hmac.digest(signing_key.encode(), payload.encode(), 'sha256'))
    query = urllib.parse.urlencode({'client_id': client_id, 'redirect_uri': redirect_uri, 'response_type': 'code',
        'scope': SCOPES, 'access_type': 'offline', 'prompt': 'consent', 'state': nonce,
        'code_challenge': encode(hashlib.sha256(verifier.encode()).digest()), 'code_challenge_method': 'S256'})
    return 'https://accounts.google.com/o/oauth2/v2/auth?' + query, cookie


def verify_oauth(cookie, state, signing_key):
    try:
        payload, signature = cookie.split('.')
        expected = encode(hmac.digest(signing_key.encode(), payload.encode(), 'sha256'))
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        data = json.loads(decode(payload))
        if data['expires'] < time.time() or not hmac.compare_digest(data['state'], state):
            raise ValueError()
        return data['verifier']
    except Exception:
        raise ValueError('Authorization expired or state did not match. Start again.') from None


def google_token(values):
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=urllib.parse.urlencode(values).encode(),
        headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            value=dict(attrs).get('href','')
            if value.startswith(('https://','http://')):
                self.urls.append(value)


def message_text(payload):
    """Skip attachments and prefer plain text over HTML alternatives."""
    if payload.get('filename'):
        return ''
    children = payload.get('parts', [])
    if children:
        preferred = [p for p in children if p.get('mimeType') == 'text/plain']
        return '\n'.join(message_text(p) for p in (preferred or children))[:40000]
    raw = payload.get('body', {}).get('data', '')
    try:
        text = decode(raw).decode('utf-8', errors='replace')
    except Exception:
        return ''
    if payload.get('mimeType') == 'text/html':
        links=Links();links.feed(text)
        return (plain(text) + '\n' + '\n'.join(links.urls))[:40000]
    return text[:40000]


def normalize_message(message):
    headers = {h['name'].lower(): h['value'] for h in message.get('payload', {}).get('headers', [])}
    return {'id': message['id'], 'threadId': message.get('threadId', ''), 'from': headers.get('from', ''),
        'subject': headers.get('subject', '(No subject)'), 'receivedAt': headers.get('date', ''),
        'body': message_text(message.get('payload', {})) or message.get('snippet', ''), 'source': 'gmail'}


def alert_links(message):
    result, seen = [], set()
    # Gmail text parts frequently include link URLs; no external pages are fetched.
    for value in re.findall(r'https?://[^\s<>"\]]+', unescape(message.get('body', ''))):
        value = value.rstrip(').,;')
        parsed = urllib.parse.urlsplit(value)
        host = (parsed.hostname or '').lower()
        url = identifier = provider = ''
        if host == 'linkedin.com' or host.endswith('.linkedin.com'):
            match = re.search(r'/jobs/view/(?:[^/]*-)?(\d+)', parsed.path)
            if match:
                provider, identifier = 'LinkedIn', match[1]
                url = 'https://www.linkedin.com/jobs/view/' + identifier
        elif host == 'indeed.com' or host.endswith('.indeed.com'):
            identifier = urllib.parse.parse_qs(parsed.query).get('jk', [''])[0]
            if re.fullmatch(r'[a-zA-Z0-9_-]+', identifier):
                provider = 'Indeed'
                url = 'https://www.indeed.com/viewjob?jk=' + identifier
        if url and url not in seen:
            seen.add(url)
            result.append({'id': 'alert:' + provider.lower() + ':' + identifier, 'company': 'Employer not verified',
                'title': provider + ' alert listing — review original', 'sourceUrl': url,
                'posting': 'Imported link only; paste the actual posting before tailoring.\nAlert: ' + message.get('subject', ''),
                'location': '', 'provider': provider, 'emailId': message['id']})
    return result


def context_hints(message, jobs):
    text = (message.get('subject', '') + ' ' + message.get('body', '')).lower()
    matches = [j['id'] for j in jobs if len(j.get('company', '').strip()) >= 3 and j['company'].lower() in text]
    stage = 'Offer / negotiation' if re.search(r'\boffer\b|compensation|salary', text) else 'Interview' if 'interview' in text else 'Review needed'
    return {'jobIds': matches, 'stageHint': stage, 'reviewRequired': True}


class Gmail:
    def __init__(self, read, write, delete, client_id, client_secret, redirect_uri):
        self.read, self.write, self.delete = read, write, delete
        self.client_id, self.client_secret, self.redirect_uri = client_id, client_secret, redirect_uri

    def request(self, path, tokens, body=None):
        req = urllib.request.Request('https://gmail.googleapis.com/gmail/v1/users/me/' + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization': 'Bearer ' + tokens['access_token'], 'Content-Type': 'application/json'},
            method='POST' if body is not None else 'GET')
        with urllib.request.urlopen(req, timeout=25) as response:
            return json.load(response)

    def authorize(self, code, verifier):
        tokens = google_token({'client_id': self.client_id, 'client_secret': self.client_secret,
            'code': code, 'code_verifier': verifier, 'redirect_uri': self.redirect_uri, 'grant_type': 'authorization_code'})
        if not tokens.get('refresh_token'):
            raise ValueError('Offline access was not granted. Reconnect and grant consent.')
        granted=set(tokens.get('scope','').split())
        if not set(SCOPES.split()).issubset(granted):
            raise ValueError('Both requested Gmail permissions are required. Reconnect and grant them.')
        tokens['expires_at'] = time.time() + tokens.get('expires_in', 3600)
        profile = self.request('profile', tokens)
        tokens['email'] = profile.get('emailAddress', '')
        self.write(tokens)
        return tokens['email']

    def access(self):
        tokens = self.read()
        if not tokens:
            raise ValueError('Gmail is not connected.')
        if tokens.get('expires_at', 0) < time.time() + 60:
            refreshed = google_token({'client_id': self.client_id, 'client_secret': self.client_secret,
                'refresh_token': tokens['refresh_token'], 'grant_type': 'refresh_token'})
            tokens.update(refreshed)
            tokens['expires_at'] = time.time() + refreshed.get('expires_in', 3600)
            self.write(tokens)
        return tokens

    def preview(self, query, limit=10):
        if not query.strip() or len(query)>500:
            raise ValueError('Choose a search query of 1–500 characters.')
        tokens = self.access()
        listing = self.request('messages?' + urllib.parse.urlencode({'q': query, 'maxResults': min(max(limit, 1), 10)}), tokens)
        # At most ten messages, no attachments, no whole-mailbox import.
        return [normalize_message(self.request('messages/' + item['id'] + '?format=full', tokens)) for item in listing.get('messages', [])]

    def create_draft(self, to, subject, body, thread_id=''):
        from email.message import EmailMessage
        if not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', to) or any(c in subject for c in '\r\n'):
            raise ValueError('Enter one valid recipient and a single-line subject.')
        message = EmailMessage()
        message['To'], message['Subject'] = to, subject
        message.set_content(body)
        payload = {'message': {'raw': encode(message.as_bytes())}}
        # Do not attach a draft to a thread without verified RFC Message-ID headers.
        result = self.request('drafts', self.access(), payload)
        return {'id': result['id'], 'saved': True, 'sent': False}
