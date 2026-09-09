"""Fill the gap between mcs=1500 (14 clusters) and mcs=2500 (5 clusters) to check
whether anything lands in the 6-10 target range, or whether HDBSCAN's merges really
do jump discretely past it.
"""
from __future__ import annotations

import time

import numpy as np
import hdbscan

COORDS_PATH = "data/knn/umap10d_coords.npz"
LEAF_LABELS_PATH = "data/knn/cluster_umap10d_mcs15_ms5.npz"


def nesting_score(coarse_labels, fine_labels):
    scores, weights = [], []
    for c in range(int(fine_labels.max()) + 1):
        idx = np.where(fine_labels == c)[0]
        if len(idx) == 0:
            continue
        _, counts = np.unique(coarse_labels[idx], return_counts=True)
        scores.append(counts.max() / len(idx))
        weights.append(len(idx))
    return float(np.average(scores, weights=weights))


def main():
    saved = np.load(COORDS_PATH, allow_pickle=False)
    ids, coords = saved["ids"], saved["coords"]
    leaf = np.load(LEAF_LABELS_PATH, allow_pickle=False)
    leaf_labels = leaf["labels"]
    assert (leaf["ids"] == ids).all()

    print(f"{'mcs':>6} {'clusters':>9} {'noise%':>8} {'nesting':>9} {'secs':>6}", flush=True)
    for mcs in (1600, 1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400):
        t0 = time.time()
        labels = hdbscan.HDBSCAN(min_cluster_size=mcs, min_samples=5,
                                 metric="euclidean").fit_predict(coords)
        dt = time.time() - t0
        k = int(labels.max() + 1)
        noise_pct = 100 * (labels == -1).mean()
        nest = nesting_score(labels, leaf_labels)
        print(f"{mcs:>6} {k:>9} {noise_pct:>7.1f}% {nest:>8.3f}  {dt:>5.1f}s", flush=True)
        np.savez(f"data/knn/megacat_mcs{mcs}_ms5.npz", ids=ids, labels=labels)

    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
