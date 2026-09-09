"""UMAP projection to 2D, seeded from our own precomputed exact kNN graph rather than
letting UMAP build its own (internally approximate) graph: 009 showed exact is free
at this corpus size, so there's no reason to accept approximation error here.

Uses UMAP's `precomputed_knn` parameter (indices + distances), which exists exactly to
skip UMAP's internal neighbor search and feed it a graph computed elsewhere.

Runs at three min_dist values so the "how tightly do points pack" cosmetic choice is
made by comparing real output, not guessed.
"""
from __future__ import annotations

import time

import numpy as np
import umap


def main():
    bf = np.load("data/knn/knn_bruteforce.npz", allow_pickle=False)
    ids, neighbors, sims = bf["ids"], bf["neighbors"], bf["sims"]
    print(f"n={len(ids)}  k={neighbors.shape[1]}", flush=True)

    # UMAP wants distances, not similarities: cosine distance = 1 - cosine similarity
    dists = (1 - sims).astype(np.float32)
    precomputed = (neighbors, dists, None)   # (indices, distances, search_index=None)

    for min_dist in (0.0, 0.1, 0.5):
        print(f"\n=== UMAP min_dist={min_dist} ===", flush=True)
        t0 = time.time()
        reducer = umap.UMAP(n_components=2, metric="cosine", random_state=42,
                            min_dist=min_dist, precomputed_knn=precomputed)
        coords = reducer.fit_transform(np.zeros((len(ids), 1)))  # X unused when
                                                                  # precomputed_knn is set,
                                                                  # but UMAP still requires
                                                                  # an X of the right length
        dt = time.time() - t0
        print(f"done in {dt:.1f}s", flush=True)
        np.savez(f"data/knn/umap_mindist{min_dist}.npz", ids=ids, coords=coords)

    print("\nDONE all min_dist values saved", flush=True)


if __name__ == "__main__":
    main()
