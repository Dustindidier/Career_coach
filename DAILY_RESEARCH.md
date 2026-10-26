# Scheduled opportunity research

A cloud-scheduled research task reads the current app brief, researches current employer postings, and imports qualifying records through the authenticated app. The scheduler is outside the Render web process, so web server sleep/restarts do not themselves trigger a new search. This does not connect arbitrary project chats automatically or submit applications.

`research_sync.py` is the authenticated handoff. It never writes the database directly, stores credentials on disk, or commits candidate records. Read AGENTS.md, RESEARCH_FEEDBACK.md and the application-assistant skill first. Keep working data in `.career-private/` or `work/`.

## Read before researching

With configured `NEXT_CHAPTER_URL`, `CAREER_USER`, `CAREER_PASSWORD`:

```
python research_sync.py read
```

If the hosted hostname is unavailable in an otherwise authorized managed environment, an explicit `--render-service-id` can run the same app server on loopback using its configured shared storage. This requires already-configured Render access. Server credentials remain inside the app; the client uses normal user authentication and revision-checked saves. Never print or persist secrets, bypass network policy, or replace this with administrative SQL writes. Do not enable new billing or services.

Read `.career-private/daily-research-brief.json` and `.career-private/daily-research-workspace.json`. The latter contains private data. Do not send the entire workspace to job websites. Use current preferences, active feedback, reviewed facts and all existing jobs/Discover decisions. Proposed assistant suggestions are not facts.

## Research and import

Use current employer sources and the existing research skill. Include pay evidence, requirements, travel/schedule/location, why the role supports the target career, a conditional `careerPath`, and `applicationDeadline`. Confirm the specific vacancy; do not pad results with expired roles, reposts, talent pools, major credential gaps or pay incompatible with the minimum. A zero-result day is valid. Be explicit when employer pay/location/travel remain unknown; do not pretend the role meets constraints.

Save a JSON array of zero to ten reviewed Discover-format records privately, then:

```
python research_sync.py import .career-private/daily-batch.json
```

The importer uses the current New York calendar date for an idempotent daily run ID, deduplicates canonical URLs and employer/title/location identities across tracked jobs and all Discover decisions, preserves every existing job/stage/material, and retries revision conflicts against a fresh workspace. Researchers must also catch semantic duplicates across syndicated URLs. Each imported record stays pending; no materials or applications are generated. A successful import records last-run status even for zero results. Access or search failures must be reported as failures, not successful zero-result days.

## Scheduler status

After the scheduler confirms an enabled task, save its returned ID/timezone/schedule in a private metadata JSON and use `research_sync.py schedule <file>`. The app displays that schedule and the last completed import. This metadata does not itself create, pause or change a scheduler task. Use the actual scheduler for those actions, then sync its confirmed status. No search is claimed complete before its imported records are read back.
