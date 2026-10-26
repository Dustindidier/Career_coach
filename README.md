# Next Chapter

A personal career workspace for exploring opportunities beyond bedside nursing, preparing interviews, and keeping reusable career evidence.

Live service: https://next-chapter-uqr1.onrender.com (password protected).

## Run locally

Python 3.10+. Install the PDF renderer, then start the app:

```sh
python -m pip install -r requirements.txt
python server.py
```

Uses local SQLite in ignored `.data/career.sqlite3` unless `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set. `CAREER_DB`, `HOST`, and `PORT` are configurable. External binding requires a `CAREER_PASSWORD` of at least 16 characters. Use HTTPS and trusted hosting. Browser Basic authentication is single-user access, not a multi-user account system.

## Included

- Revision-checked cloud and local saves: stale device writes receive 409, never silently overwrite newer data.
- Browser-local recovery for unsubmitted forms, current interview sessions, and unsaved workspace changes. A recovered conflicting copy can be exported before loading the latest server copy.
- Editable/searchable story bank; structured career facts with category, source, confirmation, and review date; legacy notes preserved.
- Resume text / .txt / .md import with candidate selection and per-fact review. Private DOCX originals and extraction are supported in the source library; PDF extraction is not included.
- Opportunity tracking, source passages extracted by free rules, manually reviewed requirements, and evidence mapping to stories or confirmed facts. Text matches are suggestions, not fit scores.
- Role- and requirement-specific free guided coaching, coaching/simulation formats, optional browser dictation, saved answers, and reflections. Guided feedback is rule-based, not AI assessment.
- Optional Gemini integration: only configured and explicitly selected AI mode makes provider calls. Free quota is provider-dependent; leave billing disabled for free-only use. Guided mode needs no key and is the fallback on AI errors.
- Manual recruiter email context, editable reply templates, and saved reply drafts. No messages sent; hosted Gmail OAuth is available after setup, while always-on scheduled sync remains unconfigured.
- Source watchlist, public Greenhouse/Lever/Ashby/SmartRecruiters feeds and bounded Workday/iCIMS portal import with keyword filtering and a deduplicated sourcing inbox. Imports are on demand; no scraping or automatic applications. Job-board alert emails are the planned route for LinkedIn/Indeed coverage.
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

[Career Ops review](docs/CAREER_OPS_REVIEW.md) evaluates selective upstream reuse; the canonicalization design has since been adapted with attribution in THIRD_PARTY_NOTICES.md.

## Source quality and evidence review

The free sourcing workflow now includes canonical URL deduplication, possible-duplicate flags (never automatic fuzzy merges), source refresh history, coverage/error diagnostics, and last-seen feed observations. Only known tracking parameters are removed; functional posting IDs are preserved. Public providers can change or block access; a failed/partial scan never marks an opportunity closed.

Stories have an explicit factual-review checkbox. Editing story details or confirmed facts clears their confirmation until reviewed again. Existing stories remain intact and need confirmation before supplying facts/figures to tailoring or AI practice.

Before exporting tailored materials, run **Check claims & placeholders**. This flags unfilled fields, figures/dates absent from approved sources, unsupported credentials (unfinished coursework is not a degree), and changes in source versions. It is a heuristic aid, not full fact verification or a licensure check. You can still export an explicitly reviewed working draft with warnings. Story suggestions use explained keyword overlap and no AI service.

## Role-specific preparation and application handoff

Opportunities can carry a reviewed preparation plan: source status, role-specific question banks, focus areas, fit checks and next steps. Guided practice uses that selected role's questions and labels provisional plans. Closing an opportunity preserves history; the dashboard defaults to an open role on reload.

Application queue records reviewed screening notes and exports preparation packets after evidence and source-version checks. These are not automated submissions. Existing applied/in-progress/closed jobs are protected from duplicate packet creation. See [APPLICATION_AUTOMATION.md](APPLICATION_AUTOMATION.md) for the free Windows/local-browser connection route and its remaining setup requirements. No personal browser connection is created by the cloud app.

## Baseline document library

Career memory preserves original resume/cover-letter DOCX files in the private `career-documents` Supabase Storage bucket (or local development storage), with their checksums, extracted text and drafting defaults in the database. Originals are not placed in GitHub. Upload/import treats document contents as data, not agent instructions.

Imported resume facts start unconfirmed. Source review confirms the associated facts after the user checks dates, figures and current credential status. Drafting can use a user-approved reference while application-packet export still requires source/claim review. New role drafts preserve career history and replace the previous role's target wording; they do not invent research, supervisory or degree credentials. Basic DOCX and text exports are free and leave the originals intact.

## Research feedback loop

Opportunities and Email & sourcing share a sourced feedback ledger and a downloadable research brief. Import conversation feedback for review, activate guidance, record reasons for Discover decisions, and carry an updated brief into the next conversation. See [RESEARCH_FEEDBACK.md](RESEARCH_FEEDBACK.md) and [AGENTS.md](AGENTS.md). Chats do not sync automatically; research callers receive the same context through `/api/research-context` and `/api/search-plan`.
