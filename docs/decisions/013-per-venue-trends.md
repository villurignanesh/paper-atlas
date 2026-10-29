# 013: Per-venue category trends (analytics.json, issue #4)

Date: 2026-10-29
Status: decided (denominator, category set, windows); thresholds PROPOSED, not adopted

## Context

The Analytics page shows one pooled chart of mega-category share by year. Issue #4 asks
for the same split by venue, so a reader can see whether, say, NeurIPS shifted
differently from ACL. `future_work.md` #4 warns to check sample sizes before cutting
three ways (year x venue x category): the pooled chart has 72 cells; a venue cut has
414 here (46 present venue-years x 9 categories), many sparse.

This stage adds data only (`venue_year_mega` in `analytics.json`) and an audit
(`report_cell_sizes.py`). It changes no page, and nothing in Phases 2-6. It needs no GPU.
Related: 003 (measure first, set the bar second), 001 (2026 stays excluded), 005 C
(manifest separates "absent by design" from "zero"), 011 (hierarchy, orphan rules),
012 (venue-siloed clusters, so venue differences in topic mix are large by construction).

## Decided

- **Denominator:** a venue-year's own labelled papers. Noise (`-1`) is dropped, then shares
  are renormalised, the same rule as the pooled chart so the two do not disagree
  methodologically. Noise rate is reported as its own column per venue-year, not only as
  the gap between totals. It ranges 9-17% (ICLR 13-17%, NAACL/ACL/EMNLP 9-12%).
- **Category set:** one fixed set for every venue, ranked by pooled labelled-paper count
  across all years (no per-year drift). Everything else goes to a plotted "Other", so
  shares sum to 100%.
- **N = 6.** Chosen from the N=5 vs N=6 comparison: "Other" is 18.2% of papers at N=5 and
  12.6% at N=6 (ICML 20.3% -> 10.7%). No category outside the top 6 reaches 10% of any
  venue, so the cutoff does not hide a venue-specific topic.
- **Windows:** counts are summed within a window, then divided (averaging per-year shares
  would weight a 50-paper year like a 900-paper year). Windows carry `n_years_present`
  so NAACL's biennial gaps (2020, 2023 did not run) are not read as a dip.
- **Binning is measured but not adopted for the chart.** Unbinned, ICLR/ICML/NeurIPS have
  0-9% of cells under 30 papers. 2-year windows barely help ACL/EMNLP/NAACL (see below).

## Options considered

- Per-year shares of the pooled corpus (rejected: the issue asks for within-venue shape).
- Per-venue top-N sets (rejected: panels become incomparable).
- 2-year windows by default (rejected: see above).
- Keeping noise in the denominator (rejected: inconsistent with the pooled chart).

## Measured (corpus: 70,861 papers; 2018-2025; 46 venue-years)

Structurally absent: NAACL 2020 and 2023 (did not run). Genuinely zero cells inside
present venue-years: 30 of 414 (all 9 categories, unbinned).

Cells under 30 papers, N=6:

| Venue | Unbinned | 2-year |
|---|---|---|
| ACL | 75.0% | 64.3% |
| EMNLP | 73.2% | 60.7% |
| NAACL | 83.3% | 78.6% |
| ICLR | 8.9% | 3.6% |
| ICML | 1.8% | 0.0% |
| NeurIPS | 0.0% | 0.0% |

Why: ACL, EMNLP and NAACL put 83-93% of their papers in one mega bucket (NLP & LLMs), so
the other categories have a few papers per venue-year. Mega-level trends for those venues
are close to flat by construction. This is a property of the category scheme, not of the
sample size, which is why binning does not fix it. The mega level has no decision log of
its own (011 records two levels); this log does not supply one.

## Thresholds: PROPOSED, provisional, open for the maintainer

Rules first suggested were inert on this data: "hide if labelled denominator < 30/50/100"
hides 0% of cells (the smallest venue-year has 284 labelled papers) and "grey if Wilson
95% half-width > 10 points" also hides 0% (widest interval is 5.3 points). Wilson in
points flatters tiny shares: 3 papers of 335 has a half-width of only 1.15 points.

Proposed instead, on the relative scale (half-width as a fraction of the cell's own
share; a zero cell is always hidden):

| Tier | Rule | Roughly | ACL / EMNLP / NAACL, unbinned | ICLR / ICML / NeurIPS, unbinned |
|---|---|---|---|---|
| Hide | half-width > 100% of share | fewer than ~5 papers | 30.4 / 28.6 / 47.6% | 1.8 / 0 / 0% |
| Grey | half-width > 50% of share | fewer than ~17 papers | 62.5 / 60.7 / 71.4% | 7.1 / 0 / 0% |

The paper-count equivalents are the smallest counts that survive in this data, not exact
conversions. No cutoff has been validated against how readers use the chart. These are
PROPOSED values; whether to adopt them, and whether the page hides or greys, is left to
the maintainer and to Stage 2 (the UI).

## What would make us revisit

- A finer category level (mid-level, 44 clusters) for the NLP venues.
- Grouping venues into NLP/ML families (see 012).
- Re-clustering: 011 reports seed ARI 0.57, so per-venue shares inherit that instability.
- A chosen threshold, once agreed.
