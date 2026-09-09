"""Mid/macro-level clustering: reuse the SAME 10D UMAP coords (regenerated
deterministically, same seed as production) and sweep larger min_cluster_size values.

Larger min_cluster_size cuts HDBSCAN's underlying density tree at a higher point, which
can only MERGE existing dense regions or drop them to noise, never split a region the
finer cut kept together. So a coarser cut is mathematically expected to nest inside the
existing 902-cluster (mcs=15) result. This measures whether that holds in practice, not
just in theory: min_samples changes the core-distance calculation itself, which can
shift the tree, not just where it's cut.
"""
from __future__ import annotations

import time

import numpy as np
import umap
import hdbscan

LEAF_LABELS_PATH = "data/knn/cluster_umap10d_mcs15_ms5.npz"


def nesting_score(coarse_labels: np.ndarray, fine_labels: np.ndarray) -> float:
    """For each fine (leaf) cluster, what fraction of its points share the SAME coarse
    label (majority vote)? Averaged across fine clusters, weighted by fine-cluster size.
    1.0 = perfect nesting; lower = the coarser cut is splitting leaf clusters apart.
    """
    scores, weights = [], []
    for c in range(int(fine_labels.max()) + 1):
        idx = np.where(fine_labels == c)[0]
        if len(idx) == 0:
            continue
        coarse_here = coarse_labels[idx]
        _, counts = np.unique(coarse_here, return_counts=True)
        scores.append(counts.max() / len(idx))
        weights.append(len(idx))
    return float(np.average(scores, weights=weights))


def main():
    bf = np.load("data/knn/knn_bruteforce.npz", allow_pickle=False)
    ids, neighbors, sims = bf["ids"], bf["neighbors"], bf["sims"]
    dists = (1 - sims).astype(np.float32)
    precomputed = (neighbors, dists, None)

    leaf = np.load(LEAF_LABELS_PATH, allow_pickle=False)
    leaf_ids, leaf_labels = leaf["ids"], leaf["labels"]
    assert (leaf_ids == ids).all(), "id order mismatch vs leaf clustering"
    print(f"leaf clustering: {int(leaf_labels.max())+1} clusters (reference)", flush=True)

    print("regenerating 10D UMAP (same seed=42 as production)...", flush=True)
    t0 = time.time()
    reducer = umap.UMAP(n_components=10, metric="cosine", random_state=42,
                        min_dist=0.0, precomputed_knn=precomputed)
    coords = reducer.fit_transform(np.zeros((len(ids), 1)))
    print(f"  done in {time.time()-t0:.1f}s", flush=True)
    np.savez("data/knn/umap10d_coords.npz", ids=ids, coords=coords)  # save this time

    print(f"\n{'mcs':>5} {'ms':>4} {'clusters':>9} {'noise%':>8} {'nesting':>9} {'secs':>6}", flush=True)
    for mcs in (50, 80, 120, 150, 250, 400, 700):
        for ms in (5, 15):
            t0 = time.time()
            labels = hdbscan.HDBSCAN(min_cluster_size=mcs, min_samples=ms,
                                     metric="euclidean").fit_predict(coords)
            dt = time.time() - t0
            k = int(labels.max() + 1)
            noise_pct = 100 * (labels == -1).mean()
            nest = nesting_score(labels, leaf_labels)
            print(f"{mcs:>5} {ms:>4} {k:>9} {noise_pct:>7.1f}% {nest:>8.3f}  {dt:>5.1f}s", flush=True)
            np.savez(f"data/knn/midlevel_mcs{mcs}_ms{ms}.npz", ids=ids, labels=labels)

    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
