"""Free, deterministic preparation tools. No model calls in this module."""
import re
import uuid

CATEGORIES = ('Experience', 'Education', 'Credential', 'Accomplishment', 'Preference', 'Skill')


def validate_workspace(data):
    if not isinstance(data, dict) or set(data) != {'profile', 'jobs', 'stories', 'sessions'}:
        return False
    def strings(obj, keys):
        return isinstance(obj, dict) and all(isinstance(obj.get(k), str) for k in keys)
    p = data['profile']
    if not strings(p, ('name', 'summary', 'facts')) or not isinstance(p.get('confirmed'), bool):
        return False
    entries = p.get('entries', [])
    if not isinstance(entries, list) or not all(strings(e, ('id', 'category', 'text', 'source', 'reviewedAt')) and e['category'] in CATEGORIES and isinstance(e.get('confirmed'), bool) for e in entries):
        return False
    required = {'jobs': ('id', 'company', 'title', 'stage', 'posting', 'notes'), 'stories': ('id', 'title', 'tags', 'situation', 'action', 'outcome'), 'sessions': ('id', 'jobId', 'mode', 'question', 'answer', 'date')}
    for key, fields in required.items():
        if not isinstance(data[key], list) or not all(strings(x, fields) for x in data[key]):
            return False
        ids = [x['id'] for x in data[key]]
        if len(ids) != len(set(ids)):
            return False
    for job in data['jobs']:
        reqs = job.get('requirements', [])
        if not isinstance(reqs, list) or not all(strings(r, ('id', 'text', 'kind', 'evidenceId', 'note')) and isinstance(r.get('reviewed'), bool) for r in reqs):
            return False
    for job in data['jobs']:
        messages = job.get('communications', [])
        if not isinstance(messages, list) or not all(strings(m, ('id', 'subject', 'from', 'body', 'receivedAt')) for m in messages):
            return False
        if not isinstance(job.get('replyDraft', ''), str):
            return False
    for key, fields in [('sources', ('id', 'name', 'url', 'query')), ('inbox', ('id', 'company', 'title', 'sourceUrl', 'posting'))]:
        items = p.get(key, [])
        if not isinstance(items, list) or not all(strings(x, fields) for x in items):
            return False
    return True


def analyze_posting(text):
    """Extract source passages for human review, never claim a definitive fit score."""
    requirements = []
    for line in re.split(r'[\n\r]+|(?<=[.;])\s+(?=[A-Z])', text):
        line = re.sub(r'^\s*[-•*\d.)]+\s*', '', line).strip()
        if len(line) < 20 or len(line) > 1200 or line.startswith(('http://', 'https://')):
            continue
        if re.search(r'prefer|desirable|nice.to.have', line, re.I):
            kind = 'Preferred'
        elif re.search(r'requir|must|minimum|degree|licens|certifi|years? of', line, re.I):
            kind = 'Requirement'
        elif re.search(r'review|process|communicat|document|prepare|responsib|maintain|manag|travel|onsite|remote|hybrid|salary|schedule', line, re.I):
            kind = 'Responsibility / logistics'
        else:
            continue
        if any(r['text'] == line for r in requirements):
            continue
        requirements.append({'id': str(uuid.uuid4()), 'text': line, 'kind': kind, 'reviewed': False, 'evidenceId': '', 'note': ''})
        if len(requirements) == 30:
            break
    return requirements


def guided_coach(payload):
    """Transparent question selection and checkpoints, not AI assessment."""
    mode = payload.get('mode', 'recruiter')
    turn = payload.get('turn', 0)
    answer = payload.get('answer', '').strip()
    job = payload.get('job') or {}
    reqs = [r for r in job.get('requirements', []) if r.get('reviewed')]
    focus = payload.get('focus', '') or (reqs[0]['text'] if reqs else '')
    role = job.get('title') or 'this role'
    company = job.get('company') or 'the organization'
    if mode == 'behavioral':
        sequence = [f'Tell me about a real experience that prepares you for {role}.', 'What did you personally do, and why?', 'What was the actual outcome, and what did you learn?']
    elif mode == 'negotiation':
        sequence = [f'{company} asks for your compensation expectations. How would you respond?', 'The offer is below your target. What would you ask about before deciding?', 'The recruiter requests an immediate decision. How would you respond?']
    elif mode == 'safety':
        sequence = ['A report describes a severe headache without a stated outcome. Does severe automatically mean serious?', 'The event timeline is missing. What information would you seek and how would you follow up?', 'A site has not responded and a deadline is approaching. What would you do?']
    else:
        sequence = [f'Tell me about yourself and why you are interested in {role} at {company}.', f'What draws you to the daily work of {role}?', 'How would you approach a responsibility you have not done before?', 'What questions would you ask the interviewer?']
    feedback = []
    if answer:
        words = len(answer.split())
        feedback.append(f'{words} words; approximately {round(words / 140 * 60)} seconds at 140 words per minute.')
        feedback.append('Try one specific example.' if words < 35 else 'Check that each sentence helps answer the question.')
        if mode == 'behavioral':
            feedback.append('Make your own actions explicit, then state only an outcome you can substantiate.')
        elif mode == 'safety':
            feedback.append(['Seriousness and intensity are separate. Seriousness depends on defined outcomes or medically important events.', 'Identify the missing facts, document uncertainty and follow-up, and follow the applicable reporting process.', 'Use the applicable timeline and escalate early. Do not invent a universal reporting deadline.'][min(max(turn - 1, 0), 2)])
        elif mode == 'negotiation':
            feedback.append('Use your real constraints and confirmed targets. Ask about the range and total package; no market salary is inferred here.')
        else:
            feedback.append('Connect your answer to the role, and separate transferable experience from areas you still need to learn.')
    next_question = sequence[turn % len(sequence)]
    if focus and mode in ('recruiter', 'behavioral') and turn == 1:
        next_question = f'The posting says: “{focus[:600]}”. What evidence from your experience would you discuss, and what would you need to learn?'
    elif answer and mode == 'behavioral' and turn == 2 and len(answer.split()) < 25:
        next_question = 'Can you make that more concrete? Describe one action you personally took and what happened next.'
    return {'engine': 'guided', 'question': next_question, 'feedback': feedback, 'label': 'Free guided coach · rules and prompts, not AI', 'complete': turn >= len(sequence)}
