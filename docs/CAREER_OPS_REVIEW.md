# Career Ops integration review

Reviewed `career-ops-hq/career-ops` at commit `ca5e70b9321daf4765f5143a4aa4d2d135f0d397`, package version 1.37.0. Read-only inspection: no upstream setup scripts, dependencies, agents, or scan commands were run. The initial review did not copy code or create a fork. Subsequent work adapted the conservative URL canonicalization design with attribution in THIRD_PARTY_NOTICES.md; no upstream CLI or web app is bundled.

## Recommendation

Keep Next Chapter's cloud/mobile interface and Supabase persistence. Selectively adapt useful algorithms and provider contracts, with upstream license attribution if copying code. A full fork is a different product architecture, not a drop-in plugin.

The root MIT license permits reuse, modification, and redistribution with its copyright and permission notice retained. Keep Next Chapter branding. Review licenses of fonts/assets and any external community plugin separately.

## Best candidates, in priority order

| Priority | Upstream code / design | Benefit for Next Chapter | Integration work / limits |
| --- | --- | --- | --- |
| 1 | `providers/workday.mjs`, `providers/icims.mjs`, `providers/ashby.mjs`, `providers/smartrecruiters.mjs`, `providers/_types.js` | Expand employer sourcing beyond Greenhouse/Lever; normalize company, location, source, dates and description | Start with healthcare employers you choose. Adapt parsers and test fixtures to our backend or isolate a Node worker. Public endpoints can change or deny access. Do not call an empty/blocked response an empty job market. |
| 2 | `url-key.mjs`, `jd-similarity.mjs`, repost logic | Consolidate email alerts and employer feeds; flag likely reposts while keeping distinct positions separate | Preserve functional job identifiers; remove only known tracking parameters. Require review of fuzzy matches rather than silently merging opportunities. |
| 3 | `verify-cv-facts.mjs`, `story-provenance-check.mjs`, `DATA_CONTRACT.md` | Prevent generated materials from promoting unconfirmed claims, credentials, dates or numbers | Their verifier is large and coupled to local source files. Port focused checks and provenance states to our confirmed facts and stories; add nursing-specific fixtures. Heuristics are not a complete truth guarantee. |
| 4 | `match-star.mjs`, `lib/story-bank.mjs` | Suggest the right story for a question using tags, theme, action and result without an LLM | Adapt to existing structured stories, retain source labels, and make it a suggestion the user chooses. |
| 5 | `liveness-api.mjs`, `liveness-core.mjs`, archived-posting design | Avoid tailoring closed jobs and preserve the original posting | Prefer supported APIs first. Treat access failures as unknown, not closed. Browser fallback adds runtime weight and maintenance. |
| 6 | `modes/oferta.md` evidence table and explicit-vs-inferred importance | Explain why a role may fit, where evidence is missing, and which constraints are real blockers | Tailor for a bedside-to-research transition. Do not inherit a universal 4/5 application cutoff or treat preferred qualifications as mandatory. |
| 7 | PDF/cover-letter templates and document validation | Better application exports and consistent formatting | Root PDF generation uses Playwright and many local helpers. A print stylesheet/browser Save as PDF is a lighter free first step. Review individual asset licenses. |

## Gmail / LinkedIn / Indeed

The project documents optional keyed plugins, not an automatic transfer of OAuth authorization. `docs/PLUGINS.md` links a separate community `career-ops-plugin-linkedin-alerts` repository, which parses Gmail alerts and normalizes job links. That external plugin was not reviewed here and must be inspected separately before reuse.

Our current implementation follows the same useful pattern independently: Google consent, a chosen Gmail search, reviewed email imports, and canonical direct LinkedIn/Indeed links. A ChatGPT Gmail connector does not supply tokens to the hosted web app. OAuth setup remains necessary.

The reviewed built-in provider catalog does not establish direct authenticated LinkedIn/Indeed search support. Do not advertise those connections as available simply because the project mentions LinkedIn.

## Cost assessment

- Public provider scans, matching, canonicalization and deterministic fact checks do not consume LLM tokens.
- The repository's AI modes still depend on a chosen CLI/model/provider. Free models have availability/usage limits; the software's MIT license does not make every dependency/service free.
- Ollama avoids API charges but needs suitable local hardware. Running useful local models on the existing small free cloud service is not a realistic default.
- Browser scanning/rendering and a second Node/Next service increase deployment complexity and resource use even where software licenses are free.
- The optional alpha web UI is local-first and uses loopback/host guards rather than a cloud account system; our authentication and shared-database model should remain in place.

## Suggested adoption sequence

1. Keep the current Gmail/search/tailoring release independent.
2. Add focused canonicalization and story selection, with tests and attribution for any copied code.
3. Pilot one additional provider against a chosen healthcare employer, then expand based on verified results.
4. Add posting freshness and snapshot storage.
5. Improve fact checking and application export before considering any larger worker/service integration.

A full upstream fork is useful only if we decide to maintain its CLI as a separate optional research worker. It is not needed to reuse MIT-licensed portions.

## Sources

- https://github.com/career-ops-hq/career-ops/blob/ca5e70b9321daf4765f5143a4aa4d2d135f0d397/LICENSE
- https://github.com/career-ops-hq/career-ops/tree/ca5e70b9321daf4765f5143a4aa4d2d135f0d397/providers
- https://github.com/career-ops-hq/career-ops/blob/ca5e70b9321daf4765f5143a4aa4d2d135f0d397/docs/PLUGINS.md
- https://github.com/career-ops-hq/career-ops/blob/ca5e70b9321daf4765f5143a4aa4d2d135f0d397/web/README.md
