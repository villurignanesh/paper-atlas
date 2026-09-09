# 006: Explicit venue-year → volume mapping for the Anthology

Date: 2026-08-27
Status: decided

## Context

Adapters must know which volumes in a collection are main track. The Anthology's naming
is not stable across years, surveyed directly:

  ACL main-track volume ids, 2018→2026:
    2018: ["1","2"]   2019: ["1"]   2020: ["main"]   2021-2026: ["long","short"]

Five consecutive years, four different conventions. Demos appear as `demo` or `demos`;
tutorials as `tutorial` or `tutorials`. Legacy collections (P/D/N + 2-digit year) use
numeric ids whose meaning is only recoverable from the free-text booktitle. Year-prefixed
files for 2018-19 (e.g. `2018.acl.xml`) exist and return HTTP 200 but are **event stubs
containing zero papers**; papers for those years live only under the legacy ids.

## Options considered

- **A. Infer from booktitle regex.** No config, adapts to new years automatically. But
  booktitle is free text with at least four observed shapes; a regex miss silently drops
  a whole volume (e.g. 164 short papers) with no signal.
- **B. Explicit hand-verified mapping table.** ~23 rows. Fails loudly on a missing entry.
  The table doubles as documentation of what was ingested.
- **C. Infer, then assert against expected counts.** Pays B's cost and adds a regex.

## Decision

**B.** `config/anthology.toml`, one entry per venue-year: collection id, main volume ids,
expected paper count, and a note where the year is odd.

Rationale: A's failure mode is silent under-collection, which is the exact bug class the
DBLP check exists to catch: better to make it impossible than to detect it later. At 23
rows the maintenance argument for A does not hold. C is the worst of both.

Accepted cost: the annual refresh is not fully automatic; adding ACL 2027 needs a human
to check the volume list and add a row. Given 005's manual re-run cadence, this costs
nothing real.

## Important caveat on `expected`

Those counts are read from the same XML the parser will read. They are a **self-consistency
check**; they catch parser bugs and future source drift. They are *not* independent
validation that the Anthology itself is complete. That remains the DBLP recall check (002).

## Result

23 venue-years, 19,971 main-track papers.

  acl    2018:381 2019:660 2020:778 2021:710 2022:700 2023:1075 2024:940 2025:1699 2026:2296
  emnlp  2018:549 2019:681 2020:751 2021:847 2022:828 2023:1047 2024:1268 2025:1809
  naacl  2018:330 2019:423 2021:477 2022:442 2024:562 2025:718

Absent by design: NAACL 2020 and 2023 (did not run); EMNLP/NAACL 2026 (not yet announced).
Industry, demo, SRW and tutorial volumes excluded per 001.

## What would make me revisit

- A venue reorganises volumes mid-series → add a row, do not generalise the parser.
- Scope widens to Findings or workshops → the table grows a `tracks` field rather than
  a second mechanism.
