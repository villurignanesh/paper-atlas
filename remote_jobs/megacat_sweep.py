"""Mega-category sweep: push min_cluster_size well past the mid-level sweep's range
(50-700) to find a genuinely small, layperson-scannable top layer (~6-10 categories),
completing a 3-level hierarchy: mega-category -> topic (44, mcs=400) -> sub-topic (902).

Reuses the SAME 10D UMAP coordinates saved by midlevel_sweep.py: same underlying
density tree, same nesting guarantee already validated at 97-100% through mcs=700.
"""
from __future__ import annotations

import numpy as np
import hdbscan

COORDS_PATH = "data/knn/umap10d_coords.npz"
LEAF_LABELS_PATH = "data/knn/cluster_umap10d_mcs15_ms5.npz"


def nesting_score(coarse_labels: np.ndarray, fine_labels: np.ndarray) -> float:
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
    print(f"loaded saved 10D coords: {len(ids)} points (skipped UMAP regen)", flush=True)

    leaf = np.load(LEAF_LABELS_PATH, allow_pickle=False)
    leaf_ids, leaf_labels = leaf["ids"], leaf["labels"]
    assert (leaf_ids == ids).all(), "id order mismatch vs leaf clustering"

    print(f"\n{'mcs':>6} {'ms':>4} {'clusters':>9} {'noise%':>8} {'nesting':>9} {'secs':>6}", flush=True)
    import time
    for mcs in (1000, 1500, 2500, 4000, 6000, 9000, 15000):
        for ms in (5,):
            t0 = time.time()
            labels = hdbscan.HDBSCAN(min_cluster_size=mcs, min_samples=ms,
                                     metric="euclidean").fit_predict(coords)
            dt = time.time() - t0
            k = int(labels.max() + 1)
            noise_pct = 100 * (labels == -1).mean()
            nest = nesting_score(labels, leaf_labels)
            print(f"{mcs:>6} {ms:>4} {k:>9} {noise_pct:>7.1f}% {nest:>8.3f}  {dt:>5.1f}s", flush=True)
            np.savez(f"data/knn/megacat_mcs{mcs}_ms{ms}.npz", ids=ids, labels=labels)
            if k <= 1:
                print("hit 1 cluster or fewer, stopping sweep early", flush=True)
                break

    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
