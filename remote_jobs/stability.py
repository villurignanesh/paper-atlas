"""Cluster stability + noise baseline on the real Qwen3-8B / min_dist=0.5 projection.

Two questions, measured not assumed (charter rule 6):
  1. Is the map real, or could HDBSCAN find "clusters" in pure noise? (noise baseline)
  2. Do cluster assignments survive a change of random seed? (stability)

Clusters on the 2D UMAP coords (the choice flagged in the charter as "not as innocent
as it looks"): this run measures the cost of that choice rather than assuming it away.
"""
from __future__ import annotations

import numpy as np
import hdbscan
from sklearn.metrics import adjusted_rand_score

MIN_CLUSTER_SIZE = 30
MIN_SAMPLES = 10


def cluster(coords, seed):
    # HDBSCAN itself has no seed parameter (it's deterministic given input order), so
    # "seed" here perturbs input order (shuffle-then-unshuffle) to test whether
    # cluster identity is sensitive to something that SHOULD be irrelevant.
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(coords))
    inv = np.argsort(perm)
    labels = hdbscan.HDBSCAN(min_cluster_size=MIN_CLUSTER_SIZE,
                             min_samples=MIN_SAMPLES).fit_predict(coords[perm])
    return labels[inv]


def main():
    d = np.load("data/knn/umap_mindist0.5.npz", allow_pickle=False)
    ids, coords = d["ids"], d["coords"]
    print(f"n={len(ids)}", flush=True)

    print("\n=== noise baseline ===", flush=True)
    rng = np.random.default_rng(0)
    noise_coords = rng.uniform(coords.min(0), coords.max(0), size=coords.shape).astype(np.float32)
    real_labels = cluster(coords, seed=42)
    noise_labels = cluster(noise_coords, seed=42)
    for name, lab in (("real", real_labels), ("noise", noise_labels)):
        k = int(lab.max() + 1)
        print(f"  {name}: {k} clusters, {100*(lab==-1).mean():.1f}% noise-labelled", flush=True)

    print("\n=== seed stability (real data, order-permutation) ===", flush=True)
    runs = [cluster(coords, seed=s) for s in (1, 2, 3)]
    for i in range(3):
        k = int(runs[i].max() + 1)
        print(f"  run seed={i+1}: {k} clusters, {100*(runs[i]==-1).mean():.1f}% noise", flush=True)
    aris = [adjusted_rand_score(runs[i], runs[j]) for i in range(3) for j in range(i+1, 3)]
    print(f"  pairwise ARI: {[round(a,4) for a in aris]}  mean={np.mean(aris):.4f}", flush=True)

    np.savez("data/knn/cluster_real.npz", ids=ids, labels=real_labels)
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
