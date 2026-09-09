"""Standard practice (BERTopic-style): a SEPARATE UMAP reduction to a modest
intermediate dimension (5-10), used only for clustering: distinct from the 2D
reduction used only for the visualization.

Why this differs from what was already tried:
  - 2D viz coords: heavily compressed, cosmetically tuned (min_dist), optimized to
    look good rather than preserve density structure.
  - Raw/PCA high-dim: PCA is linear and cannot unfold nonlinear topic structure; this
    is why it hit the curse of dimensionality regardless of how many dims were kept.
  - UMAP to 5-10 dims: nonlinear, explicitly designed to preserve local neighborhood
    structure at whatever output size you ask for, enough room to keep real
    distinctions, without HDBSCAN drowning in high-dimensional noise.
"""
from __future__ import annotations

import time

import numpy as np
import umap
import hdbscan


def main():
    bf = np.load("data/knn/knn_bruteforce.npz", allow_pickle=False)
    ids, neighbors, sims = bf["ids"], bf["neighbors"], bf["sims"]
    dists = (1 - sims).astype(np.float32)
    precomputed = (neighbors, dists, None)

    for n_dim in (5, 10):
        print(f"\n=== UMAP -> {n_dim}D (for clustering) ===", flush=True)
        t0 = time.time()
        reducer = umap.UMAP(n_components=n_dim, metric="cosine", random_state=42,
                            min_dist=0.0, precomputed_knn=precomputed)
        coords = reducer.fit_transform(np.zeros((len(ids), 1)))
        print(f"  UMAP done in {time.time()-t0:.1f}s", flush=True)

        for mcs, ms in ((15, 5), (30, 10)):
            t0 = time.time()
            labels = hdbscan.HDBSCAN(min_cluster_size=mcs, min_samples=ms,
                                     metric="euclidean").fit_predict(coords)
            dt = time.time() - t0
            k = int(labels.max() + 1)
            print(f"  mcs={mcs} ms={ms}: {k} clusters, "
                  f"{100*(labels==-1).mean():.1f}% noise ({dt:.1f}s)", flush=True)
            np.savez(f"data/knn/cluster_umap{n_dim}d_mcs{mcs}_ms{ms}.npz",
                    ids=ids, labels=labels)

    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
