"""Is 4 clusters a real property of the data, or an artifact of min_cluster_size=30
being tuned for the 2D case? Sweep it on the same PCA-50 space and measure, rather
than assume either 'high-dim is too coarse' or 'just needs a smaller number'.
"""
from __future__ import annotations

import time

import numpy as np
import hdbscan
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score


def cluster(X, min_cluster_size, min_samples, seed=42):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(X))
    inv = np.argsort(perm)
    labels = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples,
                             metric="euclidean").fit_predict(X[perm])
    return labels[inv]


def main():
    emb = np.load("data/embeddings/qwen3_embedding_8b.npz", allow_pickle=False)
    ids_e, V_full = emb["ids"], emb["vecs"].astype(np.float32)

    pca = PCA(n_components=50, random_state=0)
    V = pca.fit_transform(V_full).astype(np.float32)
    print(f"PCA 4096->50, explained variance: {pca.explained_variance_ratio_.sum():.3f}", flush=True)

    print(f"\n{'min_cluster_size':>16} {'min_samples':>12} {'n_clusters':>11} {'noise%':>8} {'secs':>6}", flush=True)
    results = {}
    for mcs in (5, 10, 15, 30):
        for ms in (5, 10):
            if ms > mcs:
                continue
            t0 = time.time()
            lab = cluster(V, mcs, ms)
            dt = time.time() - t0
            k = int(lab.max() + 1)
            noise_pct = 100 * (lab == -1).mean()
            print(f"{mcs:>16} {ms:>12} {k:>11} {noise_pct:>7.1f}% {dt:>5.1f}s", flush=True)
            results[(mcs, ms)] = lab

    np.savez("data/knn/highdim_sweep.npz",
            ids=ids_e,
            **{f"labels_mcs{mcs}_ms{ms}": lab for (mcs, ms), lab in results.items()})
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
