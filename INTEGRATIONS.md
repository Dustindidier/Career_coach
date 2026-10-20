# Free-first integrations

## Gmail

A Gmail plugin connection in ChatGPT can help review relevant recruiter conversations and draft replies in chat. It does not automatically provide OAuth credentials or scheduled access to the separately hosted Next Chapter app.

Hosted sync needs a Google Cloud OAuth app, enabled Gmail API, and user consent. Start with read access to relevant recruiter threads and draft creation; keep send approval explicit. Search by opportunity/company and allow the user to review proposed matches, extracted interview dates/time zones, stage updates, and negotiation details. Retain only relevant context. Do not silently ingest the entire mailbox.

Google API access is generally quota-based rather than a paid plugin, but OAuth configuration/verification and personal testing restrictions apply. No Gmail credentials or scheduler are configured in the hosted app yet. The current free alternative is manual message import and local reply drafts in Email & sourcing.

## Job sourcing

LinkedIn, Indeed, Glassdoor, and ZipRecruiter links and job-alert workflows are supported as bookmarks. There is no direct account scraping or claimed access to their APIs.

On-demand employer feeds are implemented for:

- Greenhouse: a public board at `https://boards.greenhouse.io/BOARD` or `https://job-boards.greenhouse.io/BOARD`; enter `BOARD` as the slug.
- Lever: a public board at `https://jobs.lever.co/BOARD`; enter `BOARD` as the slug.

Save the source with its provider, board slug, and optional keywords, then Fetch listings. Every keyword must occur in the title, description, or location (case-insensitive). Review candidates in the inbox and add selected roles. Fetches use fixed provider API hosts, preserve TLS verification, and never submit applications.

Scheduled sourcing remains next work. Free options include approved job-alert email ingestion and a quota-limited scheduler. No always-on worker or paid job-data API is enabled. A sleeping free Render service alone cannot guarantee scheduled work. An external scheduler requires separate configuration and secret management; do not expose a public unauthenticated trigger.

## Future implementation order

1. Complete Gmail consent and verify mailbox access in chat.
2. Configure hosted OAuth and store refresh credentials server-side, separate from exported career data.
3. Add reviewed email-to-opportunity suggestions and draft creation.
4. Add free scheduled alert/feed checks with deduplication, logs, and retry limits.
5. Add notifications and wider sources only through supported access methods.
