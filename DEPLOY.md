# Free-tier cloud deployment

GitHub stores the code. Render runs the Python server. Supabase stores the workspace in Postgres so Render restarts do not delete your records. GitHub Pages cannot run this backend.

## Setup

1. Create a free Supabase project. In its SQL Editor, run `supabase.sql` from this repository. The table has row-level security with no public policies; anonymous/client access is revoked.
2. Find the project URL and legacy `service_role` API key in Supabase settings. Keep that key private: it bypasses RLS. It belongs only in Render's server environment, never in browser code, GitHub, or chat.
3. Connect your GitHub account to Render. Create a Blueprint from this repository (`main`). `render.yaml` selects the free plan, with no paid disk.
4. In Render's secure environment settings enter:
   - `SUPABASE_URL`: your HTTPS project URL.
   - `SUPABASE_SERVICE_ROLE_KEY`: the service-role key.
   - `CAREER_PASSWORD`: a unique password of at least 16 characters.
   - `CAREER_USER`: defaults to `owner`.
5. Deploy. Open Render's HTTPS URL on desktop or mobile and sign in with the username/password. Always use HTTPS.
6. Verify: unauthenticated access requires login; add a test story, reload on another device, then redeploy and verify it survives. Confirm both Supabase variables are configured: without them, local SQLite is used and Render's free ephemeral disk will lose records.
7. To migrate the prepared Medpace workspace, export it from the existing app and restore the JSON backup through Career memory. The repository intentionally contains no personal database or profile facts.

Free-tier limits and availability are controlled by the providers; review their current terms. Render may sleep after inactivity and Supabase free projects may pause; first access can require a wake-up. No paid resources are declared here. The existing service is deployed at https://next-chapter-uqr1.onrender.com; this file also documents reproducing the setup.

This remains a single-user prototype using browser Basic authentication. Saves now require a matching revision; stale edits are rejected and can be exported for manual reconciliation. Export JSON backups regularly. A shared cloud database is persistence, not a backup strategy. Multi-user accounts and automatic conflict merging remain future work. Optional Gemini AI is opt-in; the guided default is free.

## Local development / other hosts

`python server.py` uses local SQLite by default. A Dockerfile is included. External binds require a long `CAREER_PASSWORD`. With local SQLite on another host, attach persistent storage at `/data`; never rely on ephemeral disk. Do not horizontally scale the SQLite configuration.

## Existing-database upgrade

Before deploying this release over v1, run the additive `revision` column statement in `supabase.sql`. It preserves existing workspace JSON. Back up the workspace privately first. Old open browser tabs must reload: saves without `If-Match` now receive 428. New GET responses include an ETag and successful saves increment it atomically.
