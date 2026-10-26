"""Reviewed application-preparation packets; no browser control or submission."""
import hashlib
import json
from intelligence import audit_materials, source_digest
from urllib.parse import urlsplit


def review_digest(workspace, job):
    materials = job.get('materials', {})
    facts = [[e['id'], e['text'], e['category'], e.get('source', '')] for e in workspace['profile'].get('entries', []) if e.get('confirmed') and e.get('category') != 'Preference']
    values = [workspace['profile']['name'], job.get('sourceUrl', ''), job['title'], job['company'], materials.get('resume', ''), materials.get('coverLetter', ''),
              job.get('applicationWorkflow', {}).get('screeningNotes', ''), facts, source_digest(workspace, job)]
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def preparation_packet(workspace, job_id):
    job = next((j for j in workspace['jobs'] if j['id'] == job_id), None)
    if job is None:
        raise ValueError('Choose an existing opportunity.')
    if job['stage'] != 'Exploring':
        raise ValueError('This opportunity is already applied, in progress, or closed. A second application is not authorized.')
    target = urlsplit(job.get('sourceUrl', ''))
    if target.scheme != 'https' or not target.hostname or target.username or target.password:
        raise ValueError('Add a valid HTTPS posting/application URL before preparing a browser handoff.')
    workflow = job.get('applicationWorkflow', {})
    if not workflow.get('reviewed') or workflow.get('reviewDigest') != review_digest(workspace, job):
        raise ValueError('Review the current materials, target role, and screening notes before exporting. Changes invalidate the previous review.')
    facts = [e for e in workspace['profile'].get('entries', []) if e.get('confirmed') and e.get('category') != 'Preference']
    if not facts or not job.get('materials', {}).get('resume', '').strip():
        raise ValueError('Add confirmed career facts and save a tailored resume first.')
    materials = job['materials']
    audit = audit_materials(workspace, job, materials.get('resume', '') + '\n' + materials.get('coverLetter', ''), materials.get('sourceDigest', ''))
    if audit['issues']:
        raise ValueError('Resolve the claims/placeholder/source checks in Tailored materials before approving an application packet.')
    return {'version': 1, 'job': {k: job.get(k, '') for k in ('id', 'company', 'title', 'sourceUrl')},
            'candidateName': workspace['profile']['name'], 'confirmedFacts': facts,
            'resumeText': materials['resume'], 'coverLetterText': materials.get('coverLetter', ''),
            'screeningNotes': workflow.get('screeningNotes', ''), 'reviewedAt': workflow.get('reviewedAt', ''),
            'reviewDigest': workflow['reviewDigest'], 'allowedActions': ['open-approved-role', 'prepare-reviewed-fields', 'prepare-reviewed-uploads'],
            'submissionAuthorized': False,
            'browserConnection': 'Required separately on the user computer. No browser connection is established by this packet.',
            'finalReview': 'Review the actual completed website form before authorizing submission. Applicant handles identity verification and legally binding attestations.'}
