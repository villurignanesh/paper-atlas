# 007: ICLR acquisition (OpenReview content, DBLP accept list)

Date: 2026-08-27
Status: decided

## What changed since 002

**OpenReview's public API is now behind a bot challenge.** Anonymous requests to both
api.openreview.net and api2.openreview.net return `ChallengeRequiredError`, including
through the official `openreview-py` client. 002 assumed anonymous access.

**Authenticating clears it.** Credentials live in `.env` (gitignored). Crucially,
`keywords` and `primary_area` come back. After 002's finding that the ACL Anthology has
no track field, ICLR keywords are the *only* free ground truth in the project, so losing
OpenReview would have left 003 criterion 3 unevaluable.

**Login is rate-limited to 3 requests per window.** The token must be cached on disk and
reused. An early version of `openreview_auth.py` validated the cached token with a probe
request and treated any failure, including a 429, as a dead token, triggering a
re-login and locking us out. It now trusts the cache and re-authenticates only on a
genuine 401/403.

## The problem

Acceptance detection changes shape five times across 2018-2026:

| years | api | how acceptance is signalled |
|---|---|---|
| 2018 | v1 | `Acceptance_Decision` notes: Accept (Poster/Oral) / Reject / Invite to Workshop |
| 2019 | v1 | decisions only in ~1,500 per-paper `Paper{n}/Meta_Review` invitations |
| 2020 | v1 | no decision invitation at the Conference level at all |
| 2021 | v1 | `venue` field present only when accepted |
| 2022 | v1 | rejected reads `ICLR 2022 Submitted` |
| 2023 | v1 | rejected reads `Submitted to ICLR 2023` |
| 2024-26 | v2 | querying `content.venueid` already excludes rejects |

Note also the case inconsistency across api2 years: `ICLR 2024 poster` vs `ICLR 2025 Poster`.

## Options considered

- **A. Full archaeology**: per-year decision logic, including a per-paper crawl for
  2019/2020. Most correct; thousands of extra requests against an aggressively
  rate-limited API, for two years of data.
- **B. DBLP supplies the accept list; OpenReview supplies the content.**
- **C. Drop ICLR 2018-2020** (~1,500 of ~70k papers). Silently degrades scope.

## Decision: B, generalised to all api1 years

- **2018-2023**: fetch all `Blind_Submission` notes from api1 for content; keep those
  whose normalised title matches DBLP's accepted list for that year.
- **2024-2026**: api2 `content.venueid=ICLR.cc/{year}/Conference`, which is already
  accept-only. DBLP has not indexed ICLR 2026 at all, so this path is mandatory there,
  not merely preferable.

Generalising B across all six api1 years (rather than only 2019-2020) replaces five
different acceptance mechanisms with one validated mechanism. Where a native `venue`
field also exists (2021-2023) it is retained as a **cross-check**, not as the primary
signal.

## Validation

Measured before committing to the approach:

| year | DBLP accepted | OR submissions | matched | recall |
|---|---|---|---|---|
| 2019 | 503 | 1,419 | 501 | 99.60% |
| 2020 | 688 | 2,213 | 687 | 99.85% |

Both shortfalls are explained. Each year's DBLP list contains a **proceedings
front-matter entry** ("7th International Conference on Learning Representations, ICLR
2019...") which is not a paper and correctly fails to match, the same contamination
class as the ACL Chairs' Report (002). Excluding it: 501/502 and 687/687.

The one genuine 2019 miss is a title changed between submission and camera-ready.

## Matching hazards found

- **DBLP double-escapes HTML entities.** `&amp;apos;` survives one `html.unescape` and
  manufactures fake mismatches. Unescape twice.
- **DBLP's search API caps results well below the requested `h`.** Paginate with `f`
  against `@total`, or silently receive 100 of 688 rows.
- DBLP rate-limits hard; 3s between requests.

## DBLP ICLR totals (includes 1 front-matter row per year)

2018:337 2019:503 2020:688 2021:861 2022:1095 2023:1574 2024:2261 2025:3705 2026:**0**

## What would make me revisit

- Match recall for any year drops below ~99% → fall back to per-year native logic there.
- DBLP indexes ICLR 2026 → optional cross-check, but api2 stays primary.
- OpenReview removes the challenge → nothing changes; auth still works.
