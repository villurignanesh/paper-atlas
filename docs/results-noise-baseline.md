# Noise baseline + stability audit: results

Run 2026-08-27. Corpus: 19,970 ACL/EMNLP/NAACL main-track papers, 2018-2026.
Pipeline: bge-small-en-v1.5 (384d, unit-norm) -> UMAP(n_neighbors=15, min_dist=0.1,
cosine, 2d) -> HDBSCAN(min_cluster_size=25, min_samples=10), clustering on the 2D coords.
Trustworthiness: sklearn, k=15, on a 5,000-point subsample (O(n^2) memory at 8GB).

## Nulls

- **gaussian**: isotropic N(0,1), L2-normalised. The naive null.
- **shuffled**: each of the 384 columns independently permuted. Preserves every
  per-dimension marginal exactly; destroys only cross-dimension correlation. Keeps the
  statistics, removes the semantics. The null a referee would ask for.

## Results

| input | seed | clusters | noise | median | max | trustworthiness |
|---|---|---|---|---|---|---|
| real | 42 | 143 | 27.3% | 67 | 747 | **0.921** |
| gaussian | 42 | 121 | 62.3% | 51 | 240 | 0.506 |
| shuffled | 42 | 2 | 6.6% | 9327 | 18628 | 0.505 |
| real | 7 | 163 | 29.9% | 62 | 472 | 0.922 |
| real | 1234 | 158 | 30.3% | 63 | 534 | 0.924 |

Seed stability, real data, ARI between seeds {42,7,1234}: **0.278, 0.322, 0.311**

Vocabulary coherence (mean pairwise Jaccard of title content words within cluster,
vs size-matched random groupings):

| labels | within-cluster | size-matched random | lift |
|---|---|---|---|
| real | 0.0681 | 0.0050 | **13.56x** |
| gaussian | 0.0053 | 0.0050 | 1.05x |
| shuffled | 0.0055 | 0.0053 | 1.06x |

## Findings

**1. The map is not an artifact.** Trustworthiness 0.92 vs 0.51 at the null, and cluster
vocabulary coherence 13.6x chance vs 1.05x. Both nulls are at chance on both metrics.

**2. Trustworthiness discriminates sharply, contrary to the prediction made before the
run.** The prior expectation was that UMAP would faithfully preserve even a meaningless
kNN graph, scoring high on noise. It does not. In isotropic high-dimensional noise the
kNN graph is not merely meaningless but *unstable*, so there is no consistent
neighbourhood structure to preserve in 2D either.

**3. The choice of null changes the conclusion.** Gaussian fragments into 121 clusters
with 62% noise: UMAP visibly manufacturing structure from nothing. Column-shuffled
collapses to a single blob of 18,628 with 6.6% noise. Same "no structure" premise,
opposite failure signatures. A study reporting only one null would characterise
"what noise looks like" incorrectly.

**4. The headline negative result: global metrics are stable, cluster identity is not.**
Across three seeds on identical data and hyperparameters, trustworthiness moves 0.921 ->
0.924 while ARI between cluster assignments is ~0.30 and cluster count swings 143/163/158.
Roughly 70% of pairwise co-clustering structure changes when nothing but the seed does.

The clusters are the object that gets labelled, counted, turned into a topic hierarchy
and cited. The metric that would normally be reported is precisely the one that hides
their instability.

## Consequences for this project

- 003 criterion 1 (above noise floor): **passed**, decisively.
- 003 criterion 2 (seed agreement above noise): **fails as currently framed.** ARI 0.30
  is above a null but nowhere near usable for a stable topic hierarchy.
- Phase 4 must treat cluster stability as a design constraint, not a post-hoc check.
  Candidate mitigations: consensus clustering over seeds, clustering in high-dim rather
  than on the 2D coords, HDBSCAN's condensed tree rather than a flat cut.
- Phase 5 label stability across re-runs is now a known-hard problem with a number
  attached, not a vague worry.

## Reproduce

    uv run python noise_baseline.py     # -> data/noise_baseline.json
    uv run python vocab_coherence.py    # -> data/vocab_coherence.json
