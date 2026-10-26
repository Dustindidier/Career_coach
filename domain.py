"""Free, deterministic preparation tools. No model calls in this module."""
import re
import uuid
from feedback import valid_feedback

CATEGORIES = ('Experience', 'Education', 'Credential', 'Accomplishment', 'Preference', 'Skill')


def valid_application_deadline(value):
    from datetime import date
    if not isinstance(value, dict) or value.get('status') not in ('published', 'anticipated', 'rolling', 'not_published', 'unverified'):
        return False
    if not all(isinstance(value.get(k), str) and len(value[k]) <= limit for k, limit in [('date',10),('sourceUrl',3000),('checkedAt',100),('note',4000),('timeZone',200)]):
        return False
    if value['sourceUrl'] and not value['sourceUrl'].startswith(('https://','http://')):
        return False
    if value['status'] in ('published','anticipated'):
        try:
            return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',value['date'])) and bool(date.fromisoformat(value['date'])) and bool(value['sourceUrl']) and bool(value['checkedAt'])
        except ValueError:
            return False
    return value['date'] == ''


def valid_career_path(path):
    if not isinstance(path, dict) or path.get('schemaVersion') != 1:
        return False
    for key in ('summary', 'bedsideFit', 'industryBridge', 'entryFit', 'assumptions', 'updatedAt'):
        if not isinstance(path.get(key), str) or len(path[key]) > 12000:
            return False
    for key in ('milestones', 'gaps', 'questions'):
        if not isinstance(path.get(key), list) or len(path[key]) > 20 or not all(isinstance(x, str) and len(x) <= 4000 for x in path[key]):
            return False
    if not isinstance(path.get('steps'), list) or not 1 <= len(path['steps']) <= 8:
        return False
    for step in path['steps']:
        if not isinstance(step, dict) or not all(isinstance(step.get(k), str) and len(step[k]) <= 6000 for k in ('timeframe', 'role', 'salary', 'basis', 'experience', 'gate')):
            return False
    if not isinstance(path.get('sources'), list) or len(path['sources']) > 12:
        return False
    return all(isinstance(x, dict) and all(isinstance(x.get(k), str) and len(x[k]) <= 3000 for k in ('label', 'url', 'note')) and x['url'].startswith(('https://', 'http://')) for x in path['sources'])


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
    if not all(isinstance(story.get('confirmed', False), bool) for story in data['stories']):
        return False
    for job in data['jobs']:
        reqs = job.get('requirements', [])
        if not isinstance(reqs, list) or not all(strings(r, ('id', 'text', 'kind', 'evidenceId', 'note')) and isinstance(r.get('reviewed'), bool) for r in reqs):
            return False
    for job in data['jobs']:
        preparation = job.get('preparation')
        if preparation is not None:
            if not isinstance(preparation, dict) or not isinstance(preparation.get('sourceNote', ''), str) or preparation.get('status') not in ('posting_verified', 'provisional') or not isinstance(preparation.get('scenarioCheckpoint', ''), str):
                return False
            questions = preparation.get('questions', {})
            if not isinstance(questions, dict) or not all(isinstance(v, list) and all(isinstance(q, str) for q in v) for v in questions.values()):
                return False
            for key in ('focusAreas', 'fitChecks', 'nextActions'):
                if not isinstance(preparation.get(key, []), list) or not all(isinstance(x, str) for x in preparation.get(key, [])):
                    return False
        messages = job.get('communications', [])
        if not isinstance(messages, list) or not all(strings(m, ('id', 'subject', 'from', 'body', 'receivedAt')) for m in messages):
            return False
        if not isinstance(job.get('replyDraft', ''), str):
            return False
    documents = p.get('referenceDocuments', [])
    if not isinstance(documents, list) or not all(strings(d, ('id','kind','filename','sha256','extractedText','storagePath','mimeType','createdAt')) and d['kind'] in ('resume','coverLetter') and isinstance(d.get('approvedForDrafting'), bool) and isinstance(d.get('reviewedForApplications'), bool) for d in documents):
        return False
    if not valid_feedback(p.get('researchFeedback', [])):
        return False
    preferences = p.get('searchPreferences', {})
    discovery=p.get('discovery',[])
    if not isinstance(discovery,list) or len(discovery)>500:
        return False
    for item in discovery:
        if not strings(item,('id','company','title','sourceUrl','posting')) or item.get('decision','pending') not in ('pending','accepted','rejected'):
            return False
        for key in ('fitReasons','concerns'):
            if not isinstance(item.get(key),list) or not all(isinstance(x,str) for x in item[key]):
                return False
        if not all(isinstance(item.get(k,''),str) for k in ('location','schedule','salary','verifiedAt','availabilityEvidence','jobId','decisionReason','decidedAt')):
            return False
    if not isinstance(preferences, dict) or not all(isinstance(preferences.get(k, ''), str) for k in ('location', 'remote', 'compensation', 'constraints')):
        return False
    if not isinstance(preferences.get('roles', []), list) or not all(isinstance(x, str) for x in preferences.get('roles', [])):
        return False
    if not isinstance(p.get('gmailQuery', ''), str) or not isinstance(p.get('gmailAutoCheck', False), bool):
        return False
    for job in data['jobs']:
        workflow = job.get('applicationWorkflow', {})
        if not isinstance(workflow, dict) or not isinstance(workflow.get('reviewed', False), bool) or not all(isinstance(workflow.get(k, ''), str) for k in ('screeningNotes', 'reviewDigest', 'reviewedAt')):
            return False
        materials = job.get('materials', {})
        if not isinstance(materials, dict) or not all(isinstance(materials.get(k, ''), str) for k in ('resume', 'coverLetter')):
            return False
    for key, fields in [('sources', ('id', 'name', 'url', 'query')), ('inbox', ('id', 'company', 'title', 'sourceUrl', 'posting'))]:
        items = p.get(key, [])
        if not isinstance(items, list) or not all(strings(x, fields) for x in items):
            return False
    for source in p.get('sources', []):
        runs = source.get('runs', [])
        last = source.get('lastRun')
        if not isinstance(runs, list) or not all(strings(r, ('status', 'checkedAt')) for r in runs):
            return False
        if last is not None and (not strings(last, ('status', 'checkedAt')) or not isinstance(last.get('warnings', []), list) or not all(isinstance(w, str) for w in last.get('warnings', []))):
            return False
    for record in data['jobs'] + discovery:
        if 'applicationDeadline' in record and not valid_application_deadline(record['applicationDeadline']):
            return False
        if 'careerPath' in record and not valid_career_path(record['careerPath']):
            return False
    for record in data['jobs'] + p.get('inbox', []):
        observations = record.get('observations', [])
        if not isinstance(observations, list) or not all(strings(o, ('source', 'url', 'checkedAt')) for o in observations):
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
    prep = job.get('preparation', {})
    custom = prep.get('questions', {}).get(mode, []) if isinstance(prep, dict) else []
    custom = [q for q in custom if isinstance(q, str) and q.strip()]
    if custom:
        sequence = custom[:12]
        if answer and mode == 'safety':
            feedback[-1] = prep.get('scenarioCheckpoint', 'Use the role’s actual scope, procedures, and escalation channels. This is a rehearsal checkpoint, not a verification of professional competence.')
    next_question = sequence[turn % len(sequence)]
    if focus and mode in ('recruiter', 'behavioral') and turn == 1:
        next_question = f'The posting says: “{focus[:600]}”. What evidence from your experience would you discuss, and what would you need to learn?'
    elif not custom and answer and mode == 'behavioral' and turn == 2 and len(answer.split()) < 25:
        next_question = 'Can you make that more concrete? Describe one action you personally took and what happened next.'
    return {'engine': 'guided', 'question': next_question, 'feedback': feedback, 'label': ('Role-specific guided practice · ' + ('posting verification pending' if prep.get('status') != 'posting_verified' else 'reviewed role plan')) if custom else 'Free guided coach · rules and prompts, not AI', 'complete': turn >= len(sequence)}
