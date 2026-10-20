# Free-first integrations

## Gmail

A Gmail plugin connection in ChatGPT can help review relevant recruiter conversations and draft replies in chat. It does not automatically provide OAuth credentials or scheduled access to the separately hosted Next Chapter app.

Hosted Gmail authorization is implemented; activation needs a Google Cloud OAuth app, enabled Gmail API, and user consent. See GMAIL_SETUP.md. Start with read access to relevant recruiter threads and draft creation; keep send approval explicit. Search by opportunity/company and allow the user to review proposed matches, extracted interview dates/time zones, stage updates, and negotiation details. Retain only relevant context. Do not silently ingest the entire mailbox.

Google API access is generally quota-based rather than a paid plugin, but OAuth configuration/verification and personal testing restrictions apply. The connector is available once Google credentials and consent are supplied; no always-on scheduler is configured. Manual message import and workspace reply drafts remain available without connecting Google.

## Job sourcing

LinkedIn, Indeed, Glassdoor, and ZipRecruiter links and job-alert workflows are supported as bookmarks. There is no direct account scraping or claimed access to their APIs.

On-demand employer feeds are implemented for:

- Greenhouse: a public board at `https://boards.greenhouse.io/BOARD` or `https://job-boards.greenhouse.io/BOARD`; enter `BOARD` as the slug.
- Lever: a public board at `https://jobs.lever.co/BOARD`; enter `BOARD` as the slug.
- Ashby: a public board at `https://jobs.ashbyhq.com/BOARD`; enter `BOARD` as the slug.
- SmartRecruiters: enter the employer company slug. The list API may omit full descriptions.
- Workday: enter the full employer careers URL, for example `https://company.wd5.myworkdayjobs.com/External`. Up to three 20-item pages per check, using the vendor's keyword search.
- iCIMS: enter the full public portal URL, for example `https://careers-company.icims.com`. Up to three public listing pages; access-denial or unrecognized markup is reported as unknown coverage, not zero jobs.

These URLs illustrate formats, not verified employers. Workday/iCIMS/SmartRecruiters summaries need the full original posting before tailoring. Scans disclose caps, failures, matched counts and partial coverage. HTTPS redirects are not followed; no login, CAPTCHA bypass or authenticated account scraping is attempted.

Save the source with its provider, board slug, and optional keywords, then Fetch listings. For feeds/local portal filtering, every keyword must occur in the available title, description, or location (case-insensitive); Workday uses its own search endpoint. Review candidates in the inbox and add selected roles. Fetches use fixed provider API hosts, preserve TLS verification, and never submit applications.

Scheduled sourcing remains next work. Free options include approved job-alert email ingestion and a quota-limited scheduler. No always-on worker or paid job-data API is enabled. A sleeping free Render service alone cannot guarantee scheduled work. An external scheduler requires separate configuration and secret management; do not expose a public unauthenticated trigger.

## Activation and next steps

1. Supply the Google OAuth client credentials in Render and complete consent in the app (see GMAIL_SETUP.md).
2. Use the implemented reviewed email-to-opportunity imports, alert-link intake and unsent Gmail draft creation.
3. Enable the optional on-open search check if desired; it is not an always-on scheduler.
4. Add a free external scheduler with deduplication, logs and retry limits after the mailbox search and source coverage are validated.
5. Expand sources only through supported public endpoints or authorized APIs.

Exact canonical posting URLs consolidate observations without overwriting role notes or approved material. Similar titles/descriptions remain separate and are marked for review. A missing role in a query-limited scan does not establish closure.
