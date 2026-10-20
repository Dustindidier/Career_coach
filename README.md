# Next Chapter

A personal career workspace for exploring opportunities beyond bedside nursing, preparing interviews, and keeping reusable career evidence.

Live service: https://next-chapter-uqr1.onrender.com (password protected).

## Run locally

Python 3.10+, no third-party runtime dependencies:

```sh
python server.py
```

Uses local SQLite in ignored `.data/career.sqlite3` unless `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set. `CAREER_DB`, `HOST`, and `PORT` are configurable. External binding requires a `CAREER_PASSWORD` of at least 16 characters. Use HTTPS and trusted hosting. Browser Basic authentication is single-user access, not a multi-user account system.

## Included

- Revision-checked cloud and local saves: stale device writes receive 409, never silently overwrite newer data.
- Browser-local recovery for unsubmitted forms, current interview sessions, and unsaved workspace changes. A recovered conflicting copy can be exported before loading the latest server copy.
- Editable/searchable story bank; structured career facts with category, source, confirmation, and review date; legacy notes preserved.
- Resume text / .txt / .md import with candidate selection and per-fact review. No PDF/DOCX parser yet.
- Opportunity tracking, source passages extracted by free rules, manually reviewed requirements, and evidence mapping to stories or confirmed facts. Text matches are suggestions, not fit scores.
- Role- and requirement-specific free guided coaching, coaching/simulation formats, optional browser dictation, saved answers, and reflections. Guided feedback is rule-based, not AI assessment.
- Optional Gemini integration: only configured and explicitly selected AI mode makes provider calls. Free quota is provider-dependent; leave billing disabled for free-only use. Guided mode needs no key and is the fallback on AI errors.
- Manual recruiter email context, editable reply templates, and saved reply drafts. No messages sent; hosted Gmail OAuth is available after setup, while always-on scheduled sync remains unconfigured.
- Source watchlist, public Greenhouse/Lever employer-feed import with keyword filtering and a deduplicated sourcing inbox. Imports are on demand; no scraping or automatic applications. Job-board alert emails are the planned route for LinkedIn/Indeed coverage.
- Evidence worksheet and JSON backup exports, restore with revision checks, and device-draft cleanup.

## Validate

```sh
python -m unittest discover -s tests -v
node --check static/app.js
# Optional browser checks (isolated temporary server/database):
npm ci
npm run test:browser
```

Browser checks need Chromium at `/usr/bin/chromium` or `CHROMIUM_PATH`. Node/Playwright are development-only dependencies, not required to run the app.

Tests use isolated storage and do not write to the production workspace. They cover concurrent save conflicts, authentication, invalid imports, coach fallback, requirement extraction, and supported feed normalization.

## Costs and AI

Default workflows have no AI or paid-plugin charges. Hosting is on the existing Render and Supabase free tiers, subject to their limits and sleep/pause behavior. No always-on or paid plan is enabled.

For optional AI: set `GEMINI_API_KEY` in Render only, optionally `GEMINI_MODEL` (default `gemini-2.5-flash-lite`), redeploy, then explicitly select AI mode. Confirm current model availability and free quotas at https://ai.google.dev/gemini-api/docs/pricing and review provider data terms. Model support changes; no AI request has been verified without a configured key. Paid API capacity is optional; guided coaching is the free alternative. For voice, browser dictation remains the free alternative to paid realtime voice.

## Privacy and data

Submitted records use the shared server database. Drafts and current session progress are stored in plaintext localStorage on the current device; they are not automatically available on another device. Clear drafts on shared devices. Do not enter patient-identifying information. AI mode sends the selected role (including imported emails), confirmed structured facts, story library, and interview context to the provider after confirmation. No AI calls occur in guided mode.

Exports contain private notes. Keep backups secure. Revision checks prevent silent overwrites but do not merge edits; export a conflicting copy, load current data, and reapply desired changes. Data is still one workspace document; normalized per-record tables and account sign-in remain future upgrades. Automated cloud backups and full history are not included.

See [DEPLOY.md](DEPLOY.md) and [INTEGRATIONS.md](INTEGRATIONS.md).

## Gmail, search planning, and tailoring

See [GMAIL_SETUP.md](GMAIL_SETUP.md) for the free Google OAuth setup. The hosted app now supports consent, chosen-search previews, reviewed context imports, LinkedIn/Indeed alert-link intake, and explicitly confirmed unsent Gmail drafts. Tokens use Supabase Vault (`gmail.sql`), separate from exports. Google credentials and real consent are required before mailbox access can be verified.

Email & sourcing generates LinkedIn/Indeed search packs from editable preferences. Tailored materials generates free evidence-based working drafts with editable placeholders and gap questions. No model or paid job-data service is needed.

[Career Ops review](docs/CAREER_OPS_REVIEW.md) evaluates selective upstream reuse; no upstream code has been copied.
