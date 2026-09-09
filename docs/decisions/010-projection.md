# 010: UMAP projection (exact kNN input, min_dist=0.5)

Date: 2026-09-04
Status: decided

## Context

Projection takes the kNN graph from 009 to 2D. Two choices: whether to feed UMAP our
own exact graph or let it build its own internally, and what min_dist to use.

## Graph source

Fed UMAP the exact brute-force kNN graph from 009 via `precomputed_knn`, rather than
letting UMAP build its own (internally approximate, NN-descent-based) graph. 009 showed
exact costs nothing extra at this corpus size (35.0s vs 34.1s, 0.9462 agreement):
no reason to accept approximation error when it is free to avoid.

## min_dist

Ran all three candidate values (0.0, 0.1, 0.5) on the full corpus, rendered side by
side colored by venue, chose by inspection rather than picking one blind.

**Chosen: 0.5.** Selected for legibility: less compressed than 0.0/0.1, which matters
once cluster labels are drawn on top in Phase 5/7. This is explicitly a cosmetic
choice: min_dist does not reflect anything true about the data, only how tightly
already-close points are allowed to visually pack.

## Timing

All three UMAP runs on the A6000 box: 37.9s, 33.2s, 33.3s. Fast enough that re-running
at a different min_dist later, or during Phase 4 iteration, costs nothing.

## What would make me revisit

- Cluster labels overlap illegibly at 0.5 once Phase 5 adds them: try a higher value.
- The final frontend rendering (Phase 7) reveals 0.5 reads as too sparse at certain
  zoom levels: this is worth an interactive check, not just a static image.
