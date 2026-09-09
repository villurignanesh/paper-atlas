# 003: What "done" means for v1

Date: 2026-08-27
Status: decided

## Context

The initial criterion was "papers on a topic are near each other, and search takes me to
that cluster." Rejected as unfalsifiable: **UMAP produces convincing, well-separated
clusters from pure Gaussian noise.** There is no version of the map, including a broken
one, that fails a look-at-it-and-judge test. A criterion with no failing case is not a
criterion.

No pre-existing ground truth was available. Resolution: ground truth is made or extracted,
not found.

## Options considered for ground truth

1. **Hand-built topic probes**: 20 topics, 10–15 papers each. Uses real expertise; limited
   by recall and biased toward what's already been read.
2. **Known-item retrieval**: papers described in own words, measure retrieval rank. Tests
   the actual workflow; tests retrieval more than layout.
3. **Borrowed metadata labels**: ICLR OpenReview author keywords + primary area. Free,
   thousands of human labels, already in the data. ICLR-only; self-reported and needs
   normalisation ("LLM" / "large language model" / "language models").
4. **Citation-based**: free at scale, but reintroduces the S2 dependency and citation is
   not topical similarity.

Chosen: **3 (scale, free) + 2 (the actual workflow)**. 4 rejected for v1 on dependency
cost. 1 subsumed by 2.

## Decision: v1 is done when

1. Projection scores meaningfully above the **noise-baseline floor** on trustworthiness
   and continuity.
2. Cluster assignments agree across seeds meaningfully above the noise baseline.
3. Cluster purity against ICLR author keywords is meaningfully above chance.
4. On a known-item set of ≥30 papers described in my own words **before seeing the map**,
   the correct paper appears in the top 10 and clicking it lands in a cluster whose
   neighbours I judge related, at least 70% of the time.

1–3 require no manual labelling. 4 requires a text file and a habit.

## The noise baseline

Run the exact pipeline (same dimensionality, count, UMAP and HDBSCAN settings) on random
vectors. It will produce a beautiful map with crisp islands. Whatever trustworthiness,
cluster count and noise fraction that produces is the floor: the score obtainable from
nothing. Real results not clearly above that floor are not results.

## Thresholds are provisional

The 70% and the top-10 are placeholders. Achievable ranges are unknown. **Measure first,
set the bar second.** Setting thresholds before knowing the achievable range produces
either premature victory or an unwinnable grind.

## Standing action

Known-item file starts now, appended to while reading normally between now and Phase 6.
Two lines per paper: title, and a one-sentence description in own words, not the
abstract's words. Written before the map exists, which is what makes it honest; it
physically cannot be fitted to a map that does not yet exist.

## What would make me revisit

- ICLR keyword normalisation turns out to dominate the signal → drop criterion 3, lean on 4.
- Known-item set stalls below 30 by Phase 6 → weaken 4 to a qualitative audit and say so.
- Measured ranges make 70%/top-10 obviously wrong in either direction → reset, and record
  the reset here rather than quietly moving the goalposts.

---

## Amended 2026-08-27: criterion 3 covers ICLR only

ACL Anthology XML turned out to carry no track/area field (see 002), so the only free
ground-truth labels in the corpus are OpenReview author keywords, which exist for ICLR
alone, roughly 15k of ~70k papers, one venue, one community.

**The NLP half of the corpus therefore has no free ground truth at all**, and it is the
half that makes Phase 8 interesting. As it stands, criterion 3 would evaluate cluster
quality on ML papers and then assert, unevaluated, that NLP clusters are equally good.

Not blocking Phase 1. Must be resolved before Phase 6. Options, unranked:
- Check whether ARR/OpenReview carries submission tracks for recent *ACL years (EMNLP
  moved to ARR). Cleanest fix if it exists.
- arXiv `cs.CL` subcategories: almost certainly too coarse to separate topics *within* NLP.
- Hand-label a small NLP probe set.
- Accept ICLR-only coverage and state the limitation explicitly in Phase 6.

Decide with better information at Phase 6, not now.
