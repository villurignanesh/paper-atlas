# 011: Clustering (UMAP-to-10D then HDBSCAN, seed fixed)

Date: 2026-09-06
Status: decided

## Context

Charter flags "cluster in high-dim space or in the 2D projection" as a real decision,
"not as innocent as it looks." This turned into the most measurement-heavy phase so far:
four distinct approaches tried, each ruled out or validated by a specific number
rather than by argument.

## What was tried, in order

**1. Cluster directly on the 2D UMAP viz coordinates (min_dist=0.5, from 010).**
270 clusters, 47% noise. Noise-baseline check against random 2D points: real 46.8% vs
noise 51.1%, barely distinguishable. Seed stability (input-order permutation only):
ARI 0.9923, deceptively high. When directly compared against clustering in high-dim
space on the SAME papers: **ARI 0.0153, essentially zero agreement.** The 2D layout is
built for legibility (cosmetically tuned via min_dist) and does not preserve the
structure a clustering algorithm needs; "270 clusters" were largely projection
artifacts, not a rediscovery of real density structure.

**2. Cluster on the raw 4096-dim embedding directly.** HDBSCAN's BallTree does not
support cosine at all (`ValueError: Unrecognized metric 'cosine'`), switched to
euclidean, valid here since embeddings are unit-normalized (euclidean distance on unit
vectors is a monotonic function of cosine similarity, same neighbor ordering). Runtime:
one clustering call took **55+ minutes** and was killed. BallTree provides no effective
speedup at 4096 dimensions: the curse of dimensionality in its most literal,
measured form.

**3. PCA to 50-400 dims, then HDBSCAN.** Made clustering tractable (147s-2548s) but
never found more than 2-6 clusters at ANY dimensionality up to 400 (81% of variance
retained), ruling out "50 was just too aggressive a compression." Perfect seed
stability (ARI 1.0 at 50 dims) but useless granularity. Conclusion: PCA is linear and
cannot unfold the actual (presumably curved/nonlinear) shape of topic structure in this
embedding; it rotates and truncates, it does not do what UMAP does.

**4. UMAP to an intermediate dimension (5D, 10D) purely for clustering, separate from
the 2D used for display, the standard BERTopic-style two-reduction pattern, initially
missed.** Fast (UMAP ~45s, HDBSCAN 1-2s, versus 42 minutes for PCA-400) and finds
usable granularity: 883-920 clusters depending on seed, ~31% noise, consistent between
5D and 10D. Seed stability, tested properly this time (full UMAP re-fit per seed, not
just input-order permutation): **mean pairwise ARI 0.5669** across three seeds.

## Decision

**UMAP to 10 dimensions (metric=cosine, min_dist=0.0, using the exact kNN graph from
009 via precomputed_knn), then HDBSCAN (min_cluster_size=15, min_samples=5,
metric=euclidean) on that 10D output. Seed fixed at 42.**

Production result: 883 clusters, 31.0% noise, 70,861 papers.

## Why, honestly

This is not a fully solved problem. ARI 0.57 means roughly half the pairwise cluster
agreement survives a seed change and half does not: a real, disclosed limitation, not
a success. It is chosen because:

- It is dramatically more stable than clustering on 2D viz coords (0.57 vs 0.30 measured
  earlier on a 20k subset, and vs the 0D-agreement 0.0153 cross-check here).
- It has usable topic granularity, unlike the high-dim/PCA path's 2-6 clusters.
- The instability is a structural property of UMAP's own stochastic optimization
  propagating into wherever HDBSCAN draws density boundaries, not a hyperparameter
  miss to keep chasing. PCA's perfect stability came specifically from having NO
  randomness at all, at the cost of finding no real structure.

Fixing the seed guarantees THIS map is internally reproducible run to run. It does not
mean this is "the" correct clustering; a different seed produces a different, equally
defensible partition of the same data. This caveat should be stated plainly wherever
the map's clusters are presented, not hidden.

## What would make me revisit

- Consensus clustering across several seeds (keep only cluster co-assignments that
  agree across most seeds) turns out cheap enough to run as the real production
  method instead of a single fixed seed, deferred here for time, not ruled out.
- Phase 6 evaluation (trustworthiness/keyword-purity) on this specific 883-cluster
  output shows it performing worse in practice than the seed-agreement number alone
  would suggest.
- Cross-venue alignment (Phase 8) needs clusters more stable than 0.57 ARI to make
  reliable claims; may force a return to the consensus-clustering approach.

---

## Phase 6 addendum: cluster purity against ICLR keywords

Date: 2026-09-07

Evaluated the final production clustering (902 clusters, post NeurIPS-abstract-fix
re-run) against independent human ground truth: ICLR author-supplied keywords
(15,857 papers, the only free ground truth in the corpus; see 003).

Method: for each cluster, restrict to its ICLR-with-keywords papers, measure mean
pairwise keyword Jaccard within that group, compare against a size-matched random
baseline drawn from the full keyworded pool (controls for smaller groups trivially
showing higher overlap by chance).

    n_clusters_evaluated:            757 / 902 (145 excluded: <2 ICLR papers)
    mean within-cluster Jaccard:     0.0607
    mean size-matched random:        0.00279
    lift:                            21.79x
    median ICLR papers/cluster:      9

This is a different signal from the Phase 2 bake-off's kNN keyword agreement (which
tested nearest-neighbor agreement in raw embedding space, 22.0x for Qwen3-8B): this
tests the actual CLUSTERING OUTPUT that ships: the full UMAP-10D -> HDBSCAN pipeline,
not just the embedding it's built on. A comparable lift (21.8x vs 22.0x) is a good sign
that clustering is not meaningfully degrading the structure already present in the
embedding space.

Closes 003's cluster-purity success criterion against completely independent human
ground truth.

## Trustworthiness on final artifact

Date: 2026-09-07. Full 70,861-paper corpus, post NeurIPS-fix, Qwen3-8B embeddings,
min_dist=0.5 2D projection, n_neighbors=15, 5000-point subsample.

    trustworthiness: 0.8839

Consistent with the 0.92-vs-0.51-null result from the earlier 20k-paper spike (002/003
noise baseline), same order of magnitude, confirms the projection remains faithful on
the corrected, full-scale, Qwen3-embedded corpus. Phase 6 closed: trustworthiness,
seed stability (ARI 0.57, disclosed), and cluster purity (21.79x lift) all measured on
the final production artifact.

---

## Two-level hierarchy added

Date: 2026-09-07

Reused the SAME 10D UMAP coordinates (regenerated deterministically, seed=42, matching
the leaf-level input) and swept `min_cluster_size` upward: this cuts HDBSCAN's
underlying density tree at a higher point, which can only merge existing dense regions
or drop them to noise, never split a region the finer cut kept together. Measured, not
assumed: nesting held at 97-100% across every value tested (50 through 700), fully
validating this as a clean way to derive a coarser level from the existing leaf result.

    mcs   clusters   nesting
     50      322      1.000
     80      212      1.000
    120      143      1.000
    150      118      1.000
    250       72      1.000
    400       44      1.000
    700       29      1.000

Noise stayed stable at ~27% across the entire range (one outlier at mcs=400/ms=15,
34%), a real structural fact about this corpus: roughly a quarter of papers sit in
genuinely sparse regions at every resolution tested, not a tuning artifact.

**Decision: 2 levels, mcs=400 (44 top-level groups + 902 leaf clusters).**

Chosen by comparing against the reference implementation this project is modeled on
(jalammar.github.io/assets/neurips_2025.html), whose actual embedded data was decoded
and inspected directly: 11 top-level groups for 576 leaves (~52 leaves/group). At the
same ratio, our 902 leaves would suggest ~17 groups; mcs=400's 44 groups (~20
leaves/group) is closer to that browsing density than the coarser mcs=700 (~31/group).
Went with 2 levels rather than 3 despite the data supporting arbitrary granularity,
matching the reference's own design rather than adding structure it doesn't use.

Both levels labeled with the same c-TF-IDF + LLM pipeline (`remote_jobs/label_toplevel.py`
for the 44 groups, prompted explicitly as "broad groups" to avoid the model fixating on
one narrow keyword). All 44 labels came back distinct and legible on inspection:
Reinforcement Learning Methods and Policies, Vision-Language Foundation Models,
Molecular and Protein Design, Federated Learning, etc.

## What would make me revisit

- Wiring both label_layers into DataMapPlot (native multi-resolution support,
  `hierarchical_collision_priority`) surfaces a problem not visible from the label
  text alone; untested as of this entry.
- 3 levels turn out to be wanted after all once the 2-level UI is actually used.
  The data already supports it (see sweep table above), so adding a third level later
  costs only another labeling pass, not new clustering.
