# Reviewed application workflow and Windows browser connection

## What is available now

Next Chapter has an Application queue that stores reviewed screening notes and exports a preparation packet for an approved role. It checks current confirmed facts, saved materials, source versions, and the role URL. Changes invalidate the review. Applied/in-progress/closed opportunities cannot export a second application packet.

This is a handoff, not an automatic application submission service. The hosted app and this cloud chat have no connection to your personal computer. Gmail OAuth permits the implemented email actions, not desktop/browser control.

## Free local browser route: Windows + ChatGPT web

1. Install Node.js LTS from https://nodejs.org/en/download if needed, or run `winget install --id OpenJS.NodeJS.LTS --exact --source winget`. If winget is unavailable, use the official LTS Windows installer.
2. Close all PowerShell/Windows Terminal windows and reopen from Start so the new PATH is loaded. Check `node --version` and `npm.cmd --version`; both must print version numbers before continuing. Errors that npm is not recognized mean this prerequisite is not ready.
3. Open normal PowerShell (administrator access is not required) and run:

```powershell
npm.cmd install -g @openai/codex
codex.cmd login
codex.cmd mcp add playwright -- cmd /c npx -y @playwright/mcp@latest --browser msedge
codex.cmd
```

Sign into the existing ChatGPT account. Playwright MCP is free/open source; Codex usage follows the account's existing entitlement and limits. Do not enable new API billing for this workflow. If Codex is unavailable on the plan, manual use of the preparation packet remains free; another local client with a suitable free model quota is an alternative to evaluate separately.

If npm succeeds but `codex.cmd` is not found, reopen PowerShell. You can also invoke it directly with:

```powershell
$codexExe = Join-Path (npm.cmd prefix -g) 'codex.cmd'
& $codexExe login
& $codexExe mcp add playwright -- cmd /c npx -y @playwright/mcp@latest --browser msedge
& $codexExe
```

The local agent gets browser tools on that Windows machine. This does not transfer this cloud conversation's tool connection or automatically authorize another application. By default the server uses a separate browser session. Sign into career portals yourself in the controlled window. To attach existing Chrome/Edge tabs, follow Microsoft's official Playwright MCP extension setup; that requires its browser extension and deliberate attachment.

Official instructions: https://github.com/microsoft/playwright-mcp

## Use a reviewed packet

1. Confirm your career facts and current credentials, add your resume, and save role-specific materials.
2. Record actual screening questions and truthful answers in Application queue. Do not infer dates, eligibility, work authorization or demographic responses.
3. Review the target, materials and answers; save the preparation review, then export its packet. Unfilled placeholders, unsupported claims or changed source versions need resolution first.
4. Give that file to the local agent with this instruction:

> Use this packet only for its specified job. Open the approved URL and let me sign in. Prepare fields and uploads using reviewed information; list any missing or ambiguous answers. Show me the completed website form for final review before submission. Do not submit another application for a role already applied to. I will handle account verification and applicant/legal attestations.

The packet explicitly sets `submissionAuthorized: false` because approving a preparation packet cannot approve website questions that have not yet been seen. Final submission requires approval of the actual completed form in the local session. The applicant handles identity verification, CAPTCHA/MFA and legally binding attestations/signatures. Passwords and authentication codes should not be placed in exported packets or chat.

## Existing applications

For an already-applied role, use the role-specific interview plan, debrief, materials and communications. Do not resubmit simply to test automation. The application queue prevents that action in its packet workflow.
