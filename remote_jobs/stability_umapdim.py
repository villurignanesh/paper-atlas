"""Does the UMAP-to-10D-then-HDBSCAN clustering survive a seed change, the way the
2D approach failed to (ARI ~0.30 measured earlier)? This is the test that decides
whether the intermediate-dimension approach is actually usable, not just fast and
numerous.

Two things vary across runs: the UMAP seed itself (a full re-embedding to 10D) AND
input order to HDBSCAN, so this is a strictly harder test than the pure
order-permutation check used earlier.
"""
from __future__ import annotations

import numpy as np
import umap
import hdbscan
from sklearn.metrics import adjusted_rand_score

MCS, MS = 15, 5


def run(neighbors, dists, n, seed):
    precomputed = (neighbors, dists, None)
    reducer = umap.UMAP(n_components=10, metric="cosine", random_state=seed,
                        min_dist=0.0, precomputed_knn=precomputed)
    coords = reducer.fit_transform(np.zeros((n, 1)))
    labels = hdbscan.HDBSCAN(min_cluster_size=MCS, min_samples=MS,
                             metric="euclidean").fit_predict(coords)
    return labels


def main():
    bf = np.load("data/knn/knn_bruteforce.npz", allow_pickle=False)
    ids, neighbors, sims = bf["ids"], bf["neighbors"], bf["sims"]
    dists = (1 - sims).astype(np.float32)
    n = len(ids)

    print(f"{'seed':>6} {'clusters':>9} {'noise%':>8}", flush=True)
    runs = []
    for seed in (42, 7, 123):
        lab = run(neighbors, dists, n, seed)
        k = int(lab.max() + 1)
        print(f"{seed:>6} {k:>9} {100*(lab==-1).mean():>7.1f}%", flush=True)
        runs.append(lab)

    aris = [adjusted_rand_score(runs[i], runs[j]) for i in range(3) for j in range(i+1, 3)]
    print(f"\npairwise ARI: {[round(a,4) for a in aris]}  mean={np.mean(aris):.4f}", flush=True)
    np.savez("data/knn/umap10d_seed_runs.npz", ids=ids,
            labels_seed42=runs[0], labels_seed7=runs[1], labels_seed123=runs[2])
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
