"""Evidence-based tailoring and free search plans. No invented candidate claims."""
from urllib.parse import urlencode
from intelligence import source_digest

DEFAULT_ROLES = ['Clinical Safety Nurse', 'Utilization Review Nurse', 'Clinical Documentation Specialist',
                 'Quality Improvement Nurse', 'Clinical Research Nurse', 'Clinical Informatics Nurse']


def search_plan(preferences):
    roles = preferences.get('roles') or DEFAULT_ROLES
    location = preferences.get('location', '').strip()
    remote = preferences.get('remote', 'any')
    result = []
    for role in roles[:12]:
        if not isinstance(role, str) or not role.strip():
            continue
        keywords = role.strip() + (' remote' if remote == 'only' else '')
        linkedin = {'keywords': role.strip()}
        if location:
            linkedin['location'] = location
        if remote == 'only':
            linkedin['f_WT'] = '2'
        indeed = {'q': keywords, 'l': 'Remote' if remote == 'only' else location}
        lower = role.lower()
        if 'safety' in lower or 'pharmacovigilance' in lower:
            reason = 'Explore clinical review, safety narratives, and follow-up work.'
            checks = 'Verify entry-level research training, onsite expectations, and case-processing duties.'
        elif 'utilization' in lower:
            reason = 'Explore chart review and medical-necessity workflows.'
            checks = 'Verify payer experience requirements, productivity expectations, licensure, and schedule.'
        elif 'documentation' in lower:
            reason = 'Explore documentation quality and clinical clarification work.'
            checks = 'Verify CDI/coding experience requirements and whether certification is required or preferred.'
        elif 'informatics' in lower:
            reason = 'Explore clinical workflows, systems, and implementation work.'
            checks = 'Verify technical expectations, project experience, on-call coverage, and travel.'
        elif 'research' in lower:
            reason = 'Explore trial coordination and research nursing.'
            checks = 'Check whether the role includes direct patient care, research experience requirements, and travel.'
        else:
            reason = 'Compare the actual responsibilities with your confirmed experience and interests.'
            checks = 'Verify credentials, training, compensation, schedule, location, and travel.'
        result.append({'role': role, 'reason': reason, 'checks': checks,
            'linkedin': 'https://www.linkedin.com/jobs/search/?' + urlencode(linkedin),
            'indeed': 'https://www.indeed.com/jobs?' + urlencode(indeed)})
    return {'searches': result, 'preferences': preferences,
        'limitations': 'These are search routes, not live vacancies or a qualification ranking. Salaries and requirements must be verified in each posting.'}


def tailor(workspace, job_id):
    job = next((j for j in workspace['jobs'] if j['id'] == job_id), None)
    if job is None:
        raise ValueError('Choose an existing opportunity.')
    profile = workspace['profile']
    facts = {e['id']: e for e in profile.get('entries', []) if e.get('confirmed')}
    stories = {s['id']: s for s in workspace['stories']}
    supported, gaps, evidence = [], [], {}
    for requirement in job.get('requirements', []):
        if not requirement.get('reviewed'):
            continue
        key = requirement.get('evidenceId', '')
        source = None
        if key.startswith('fact:'):
            fact = facts.get(key[5:])
            if fact and fact.get('category') != 'Preference':
                source = {'id': key, 'label': fact['text'], 'text': fact['text'], 'source': fact.get('source') or 'Your confirmed account', 'type': 'fact'}
        elif key.startswith('story:'):
            story = stories.get(key[6:])
            if story and story.get('confirmed') is True:
                source = {'id': key, 'label': story['title'], 'text': 'Actions: ' + story['action'] + '\nOutcome: ' + story['outcome'], 'source': 'Your saved story — review before use', 'type': 'story'}
        row = {'requirement': requirement['text'], 'note': requirement.get('note', '')}
        if source:
            evidence[key] = source
            supported.append({**row, 'evidence': source})
        else:
            if key.startswith('story:') and key[6:] in stories and not stories[key[6:]].get('confirmed'):
                row['note'] = 'Linked story needs factual review and confirmation in the story bank. ' + row['note']
            gaps.append(row)
    relevant = list(evidence.values())
    name = profile['name']
    resume = [name, '[Contact information]', '', 'TARGET ROLE', job['title'] + ' — ' + job['company'], '',
        'SUMMARY', '[Write your motivation for this role using the verified evidence below.]', '', 'ROLE-RELEVANT EVIDENCE']
    resume += ['- ' + e['text'] for e in relevant] or ['[Map confirmed facts or stories to reviewed requirements first.]']
    resume += ['', 'EDUCATION & CREDENTIALS']
    resume += ['- ' + e['text'] for e in facts.values() if e.get('category') in ('Education', 'Credential')] or ['[Add confirmed education and credentials.]']
    resume += ['', 'EMPLOYMENT HISTORY', '[Add verified employers, role titles, and dates. No employment dates are inferred.]']
    intro = f'Dear Hiring Team,\n\nI am interested in the {job["title"]} opportunity at {job["company"]}. [Add your specific, researched reason for applying.]'
    proof = '\n\nRelevant experience I would welcome discussing:\n' + '\n'.join('- ' + e['text'] for e in relevant) if relevant else '\n\n[Add a confirmed example that addresses a reviewed requirement.]'
    closing = '\n\n[Explain how this evidence connects to the role, and acknowledge any training needs.]\n\nThank you for your consideration.\n\n' + name
    return {'sourceDigest': source_digest(workspace, job), 'jobId': job_id, 'title': job['title'], 'company': job['company'], 'supported': supported, 'gaps': gaps,
        'evidence': relevant, 'resume': '\n'.join(resume), 'coverLetter': intro + proof + closing,
        'questions': ['Could you clarify: ' + r['requirement'] for r in gaps[:5]],
        'label': 'Free evidence-based drafts · review all placeholders and claims',
        'limitations': 'Evidence links reflect your assessment, not proof of qualification. No company research, market salary, or ATS score is inferred.'}
