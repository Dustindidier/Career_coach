# Connect Gmail — free personal setup

This connects Gmail to the hosted Next Chapter app. A Gmail connector in ChatGPT is separate and cannot supply this app's OAuth credentials.

## One-time Google setup

1. Open https://console.cloud.google.com/ and create/select a project. No billing account is required for this Gmail workflow.
2. Enable **Gmail API** in APIs & Services → Library.
3. Open **Google Auth Platform**. Configure Branding (Next Chapter, your support/contact email), Audience → External, and add your own Gmail account under Test users.
4. Under Data Access add these scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.compose`
5. Under Clients create a **Web application** OAuth client.
6. Add this exact Authorized redirect URI:
   `https://next-chapter-uqr1.onrender.com/oauth/gmail/callback`
7. In Render's secure environment settings add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. If `RENDER_EXTERNAL_URL` is unavailable, also set `PUBLIC_BASE_URL=https://next-chapter-uqr1.onrender.com`. Save and redeploy. Never put the client secret in GitHub or chat.

## Authorize in the app

1. Refresh Next Chapter → Email & sourcing → Refresh status → Connect Gmail.
2. Sign into the Google test-user account and grant both permissions. The app returns to Email & sourcing with the connected address.
3. Choose a narrow search, for example `label:career-search newer_than:30d` or `newer_than:30d (Medpace OR recruiter OR interview)`.
4. Preview up to ten messages. Review the proposed role and the original date/time zone, then import selected messages.
5. For job alerts, review direct LinkedIn/Indeed links and add them to the sourcing inbox. Titles, employers and full postings still need verification.
6. Edit a reply, supply its recipient and subject, and confirm **Create unsent Gmail draft**. The draft is saved in Gmail; the app never sends it.

## Limits and privacy

- Google testing-mode grants for these scopes may expire after seven days; reconnect when needed. Public production distribution can require Google verification, so this setup is intended for your personal test account.
- Gmail scopes permit mailbox reading and composing (Google's compose scope also permits sending); the app implements only selected-search reads and draft creation. There is no send endpoint.
- OAuth uses state validation, PKCE and an HttpOnly/Secure cookie. Tokens are encrypted in Supabase Vault, accessible only through server-only RPC functions; they never appear in workspace exports or API status responses.
- No attachments are fetched. Imported emails become career data only after review. The original Gmail date header is retained; dates and time zones are not guessed.
- Optional on-open checks run only when you visit Email & sourcing, at most hourly per device. This is not a guaranteed background scheduler.
- Disconnect removes stored credentials and attempts to revoke Google's grant. Imported messages remain until you delete them. If revocation fails, remove access in your Google Account's third-party connections.

## Hosting preparation

Apply `gmail.sql` once through the Supabase SQL Editor or Management API. It creates a Vault-backed token store and grants its RPC functions only to service_role. It does not change the career workspace or enable billing.

## Search and tailoring

Set role titles, location, remote preference and constraints in Email & sourcing. Search packs open LinkedIn and Indeed without scraping or paid APIs. Enable job alerts on those sites to receive their own latest results.

In Opportunities paste the actual posting, review requirements and map evidence. Tailored materials produces editable resume/cover-letter working drafts and gap questions using only confirmed linked facts and saved stories. It does not invent employment dates, qualifications, compensation data or employer research.
