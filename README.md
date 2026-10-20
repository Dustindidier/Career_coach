# Next Chapter

A single-user career workspace, initially focused on Dustin's Medpace Clinical Safety Nurse preparation.

## Run

Requires Python 3.10+; no third-party runtime dependencies.

```sh
cd /workspace/Career_coach
python server.py
```

Open port 8000 in your browser using your development environment's supported port access. The server binds to `127.0.0.1` by default. `HOST` and `PORT` override the binding; external hosting requires a CAREER_PASSWORD of at least 16 characters and HTTPS; see DEPLOY.md. If access requires `HOST=0.0.0.0`, use only a trusted, access-controlled development environment.

## Included

- Guided recruiter, behavioral, clinical safety, and negotiation exercises.
- Optional browser speech recognition (browser support varies; the provider may process audio).
- Clearly labeled rule-based structure coaching, saved answers, and real-story capture.
- Editable, explicitly confirmed career memory and opportunity records.
- Posting and interview notes, evidence worksheet export, JSON backup and restore.
- SQLite persistence in ignored `.data/career.sqlite3`; `CAREER_DB` overrides the location.

New databases start with an empty profile; your existing local database is preserved. Verify the actual job posting, interview date/time zone, compensation, and personal facts.

## Validation

```sh
python -m unittest discover -s tests -v
node --check static/app.js
```

## Scope and privacy

No LLM, live job search, scheduled sourcing, resume generation, or outbound messages are connected. Prompts are curated, follow-ups follow a fixed sequence, and feedback uses simple rules; it does not assess clinical correctness or hiring likelihood. Evidence worksheets assemble your own notes, not a tailored resume. Use approved sources and human review when extending these features.

Data is stored locally in plaintext. Do not enter patient-identifying details. Export sensitive backups carefully. Story and opportunity deletion and practice-history clearing are available in the UI. To delete the entire workspace, stop the server and remove the database; the next launch creates a fresh starter workspace. This is designed for one user and one editing tab; simultaneous edits use last-write-wins.

## Next development steps

1. Add a secure server-side AI provider integration with evidence-linked feedback and dynamic follow-ups.
2. Add requirement-to-evidence mapping and reviewable document generation.
3. Add permitted job-source connectors, fit comparisons, and scheduled discovery.
4. Replace single-user browser authentication with accounts before multi-user hosting.

## Deploy in the cloud

See [DEPLOY.md](DEPLOY.md). A Dockerfile and Render Blueprint configure a password-protected service with persistent storage. Hosting resources have not been provisioned.
