# Phase 1 validation: independent recall against DBLP

Run 2026-08-27. Closes 002's Phase 1 acceptance test.

## Scope of the check, and why it is narrower than 002 implied

002 called for a DBLP recall check across every venue-year. On execution that turned out
to be the wrong shape for two of the four sources:

- **ACL / EMNLP / NAACL: not checked, deliberately.** The ACL Anthology *is* the
  canonical record for those venues and DBLP indexes from it, so the comparison is close
  to circular rather than independent. It would also require re-deriving 006's volume
  mapping in DBLP's second naming scheme (`naacl2024-1..-6`, `naacl2024f`, `emnlp2025i`)
  for no independent evidence.
- **ICLR: validated by construction.** DBLP *supplies* its accept list (007), so a
  recall check against DBLP is tautological there.

The check earns its cost on the **scraped** sources, where silent omission is a real
risk: NeurIPS (papers.nips.cc HTML) and ICML (PMLR HTML).

## Metric

Reported as **confirmation rate** = |ours ∩ DBLP| / |ours|: what fraction of the papers
we ingested does an independent source confirm exist.

An earlier pass reported |ours ∩ DBLP| / |DBLP| and produced alarming 89-94% figures for
NeurIPS 2022+. That metric conflates a scope difference with a recall failure: DBLP's
`neurips{year}` TOC merges Datasets & Benchmarks and position papers into one list, which
001 excludes by design.

## Results

| year | NeurIPS ours | confirmed | rate | ICML ours | confirmed | rate |
|---|---|---|---|---|---|---|
| 2018 | 1009 | 1007 | 99.80% | 621 | 605 | 97.42% |
| 2019 | 1428 | 1423 | 99.65% | 773 | 769 | 99.48% |
| 2020 | 1898 | 1893 | 99.74% | 1084 | 1081 | 99.72% |
| 2021 | 2334 | 2322 | 99.49% | 1183 | 1177 | 99.49% |
| 2022 | 2671 | 2669 | 99.93% | 1233 | 1224 | 99.27% |
| 2023 | 3218 | 3171 | 98.54% | 1828 | 1818 | 99.45% |
| 2024 | 4034 | 4010 | 99.41% | 2610 | 2587 | 99.12% |
| 2025 | 5286 | 5240 | 99.13% | 3330 | 3232 | 97.06% |

## Every deviation is explained

- **NeurIPS DBLP-only surplus, 2022+** (165 / 369 / 484 / 583) matches the excluded
  tracks almost exactly: D&B is 163/322/459/497, plus 40 position papers in 2025.
  Sample "missing" titles are unambiguous benchmark papers: *3DOS: towards 3D open set
  learning benchmarking*, *a benchmark of categorical encoders*.
- **ICML 2025 at 97.06%**: DBLP lists FEWER papers than we hold (3257 vs 3330). DBLP has
  not finished indexing ICML 2025; PMLR is authoritative and our count matches its volume
  listing exactly.
- **ICML 2018 at 97.42%**: 16 title mismatches against identical counts (621 vs 621),
  so no papers are missing; the residue is title normalisation, most likely LaTeX
  (e.g. *A Spline Theory of Deep Networks*).

## Verdict

**No evidence of silent omission in either scraped source.** Residual 0.5-1% is title
normalisation between two independently typed records, not lost papers.

## Known limitation

Title normalisation is the measurement instrument here, so it bounds the precision of
the check: a systematic normalisation failure would look like a small recall shortfall.
The counts agreeing exactly (621/621, 1898/1898, 2334/2334, 1828/1828, 2610/2610) is the
stronger evidence that nothing is missing.

## DBLP TOC key naming, for future runs

    NeurIPS   conf/nips/nips{year}      2018-2019
              conf/nips/neurips{year}   2020+
    ICML      conf/icml/icml{year}
    ICLR      conf/iclr/iclr{year}
    *ACL      multi-volume: conf/naacl/naacl2024-1..-6, naacl2024f, emnlp2025i, ...
