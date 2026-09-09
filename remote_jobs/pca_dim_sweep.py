"""Is 50-dim PCA throwing away the fine structure, or is 4096-dim Qwen3-8B genuinely
this coarse? Test higher PCA dimensionalities with a fixed, reasonable HDBSCAN config,
rather than assume 50 dims was the right compression level.
"""
from __future__ import annotations

import time

import numpy as np
import hdbscan
from sklearn.decomposition import PCA

MIN_CLUSTER_SIZE, MIN_SAMPLES = 15, 5   # picked from the mcs sweep as a reasonable middle


def cluster(X, seed=42):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(X))
    inv = np.argsort(perm)
    labels = hdbscan.HDBSCAN(min_cluster_size=MIN_CLUSTER_SIZE, min_samples=MIN_SAMPLES,
                             metric="euclidean").fit_predict(X[perm])
    return labels[inv]


def main():
    emb = np.load("data/embeddings/qwen3_embedding_8b.npz", allow_pickle=False)
    ids_e, V_full = emb["ids"], emb["vecs"].astype(np.float32)

    print(f"{'pca_dim':>8} {'expl_var':>9} {'pca_secs':>9} {'clusters':>9} {'noise%':>8} {'cluster_secs':>13}", flush=True)
    results = {}
    for dim in (50, 100, 200, 400):
        t0 = time.time()
        pca = PCA(n_components=dim, random_state=0)
        V = pca.fit_transform(V_full).astype(np.float32)
        pca_secs = time.time() - t0
        ev = pca.explained_variance_ratio_.sum()

        t0 = time.time()
        lab = cluster(V)
        cluster_secs = time.time() - t0
        k = int(lab.max() + 1)
        noise_pct = 100 * (lab == -1).mean()
        print(f"{dim:>8} {ev:>9.3f} {pca_secs:>8.1f}s {k:>9} {noise_pct:>7.1f}% {cluster_secs:>12.1f}s", flush=True)
        results[dim] = lab

    np.savez("data/knn/pca_dim_sweep.npz", ids=ids_e,
            **{f"labels_pca{d}": lab for d, lab in results.items()})
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
