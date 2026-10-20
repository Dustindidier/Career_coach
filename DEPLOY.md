# Cloud deployment

GitHub stores the code. Render (or another container host with persistent storage) runs the server and database. GitHub Pages cannot run this Python backend.

## Render

1. Connect your GitHub account to Render and create a Blueprint from this repository. `render.yaml` defines a paid Starter web service and 1 GB persistent disk. Review current pricing before creating resources.
2. Set `CAREER_PASSWORD` to a unique password of at least 16 characters in Render's secure environment settings. The login username defaults to `owner` (`CAREER_USER`). Do not put passwords in GitHub.
3. Deploy and open Render's HTTPS service URL on desktop or mobile. Browser authentication protects both the UI and the API. Always use HTTPS. The app refuses an external bind without a long password.
4. Confirm login is required, save a test story, reload on another device, then redeploy and verify the story survives. The persistent disk must be mounted at `/data` and `CAREER_DB` must reference it.
5. Restore a JSON backup from Career memory if migrating an existing workspace. The repository intentionally includes no personal profile, notes, or database.

The same URL and login access the same single-user database on every device. Avoid editing the same workspace simultaneously: the current save model is last-write-wins. This deployment is a personal prototype with browser Basic authentication, not a multi-user account system. Password rotation is through the hosting settings. Use workspace exports as backups; a persistent disk alone is not a backup strategy.

## Other hosts

Build the Dockerfile, supply `CAREER_PASSWORD`, terminate HTTPS at the host, and attach a persistent volume at `/data`. Do not deploy SQLite on an ephemeral filesystem or horizontally scale this version. Review costs before provisioning. No hosting resources are created by adding these files.
