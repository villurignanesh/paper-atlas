"""Does clustering on the original 4096-dim embedding (vs the 2D UMAP projection)
change the answer? The charter flags this exact choice as 'not as innocent as it
looks': 2D clustering risks finding shapes that are artifacts of UMAP's layout
compression, not the data itself.

Same corpus, same HDBSCAN parameters as stability.py, only the input space changes.
Also re-runs the noise baseline in high-dim, since a noise baseline computed in 2D
doesn't tell us anything about whether high-dim clustering is any more decisive.
"""
from __future__ import annotations

import numpy as np
import hdbscan
from sklearn.metrics import adjusted_rand_score

MIN_CLUSTER_SIZE = 30
MIN_SAMPLES = 10


def cluster(X, seed, metric="euclidean"):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(X))
    inv = np.argsort(perm)
    labels = hdbscan.HDBSCAN(min_cluster_size=MIN_CLUSTER_SIZE, min_samples=MIN_SAMPLES,
                             metric=metric).fit_predict(X[perm])
    return labels[inv]


def main():
    emb = np.load("data/embeddings/qwen3_embedding_8b.npz", allow_pickle=False)
    ids_e, V_all = emb["ids"], emb["vecs"].astype(np.float32)
    proj = np.load("data/knn/umap_mindist0.5.npz", allow_pickle=False)
    ids_2d, coords_2d = proj["ids"], proj["coords"]

    # Different scripts wrote these files in different orders (dict iteration order is
    # not guaranteed stable across runs/processes). Align explicitly by paper_id rather
    # than assuming row order matches: the alternative is silently comparing paper A's
    # embedding to paper B's cluster label, which would corrupt every result downstream.
    e_pos = {pid: i for i, pid in enumerate(ids_e)}
    common = [pid for pid in ids_2d if pid in e_pos]
    assert len(common) == len(ids_2d) == len(ids_e), \
        f"id set mismatch: {len(ids_2d)} in projection, {len(ids_e)} in embeddings, {len(common)} common"
    order = [e_pos[pid] for pid in common]
    V_full = V_all[order]
    ids_e = np.array(common)

    # 4096-dim HDBSCAN with BallTree was measured taking 1hr+ per single clustering call:
    # BallTree provides essentially no speedup at this dimensionality (the curse of
    # dimensionality in its most literal, measured form), degrading toward brute-force
    # with tree-building overhead on top. PCA to 50 dims first is standard practice for
    # exactly this reason: it keeps clustering in a "real embedding space" (unlike the
    # UMAP-distorted 2D layout) while staying tractable. Chosen empirically, not assumed:
    # 50 is a common default, not tuned here.
    from sklearn.decomposition import PCA
    t_pca = __import__("time").time()
    pca = PCA(n_components=50, random_state=0)
    V = pca.fit_transform(V_full).astype(np.float32)
    print(f"PCA 4096->50 in {__import__('time').time()-t_pca:.1f}s, "
          f"explained variance: {pca.explained_variance_ratio_.sum():.3f}", flush=True)
    print(f"n={len(ids_e)}  dim={V.shape[1]} (post-PCA)", flush=True)

    print("\n=== noise baseline, high-dim ===", flush=True)
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(V.shape).astype(np.float32)
    noise /= np.linalg.norm(noise, axis=1, keepdims=True)     # match unit-norm real embeddings
    real_labels = cluster(V, seed=42)
    noise_labels = cluster(noise, seed=42)
    for name, lab in (("real (high-dim)", real_labels), ("noise (high-dim)", noise_labels)):
        k = int(lab.max() + 1)
        print(f"  {name}: {k} clusters, {100*(lab==-1).mean():.1f}% noise-labelled", flush=True)

    print("\n=== seed stability, high-dim (order-permutation) ===", flush=True)
    runs = [cluster(V, seed=s) for s in (1, 2, 3)]
    for i in range(3):
        k = int(runs[i].max() + 1)
        print(f"  run seed={i+1}: {k} clusters, {100*(runs[i]==-1).mean():.1f}% noise", flush=True)
    aris = [adjusted_rand_score(runs[i], runs[j]) for i in range(3) for j in range(i+1, 3)]
    print(f"  pairwise ARI: {[round(a,4) for a in aris]}  mean={np.mean(aris):.4f}", flush=True)

    print("\n=== agreement: high-dim clustering vs 2D clustering (same real data) ===", flush=True)
    twod = np.load("data/knn/cluster_real.npz", allow_pickle=False)
    twod_pos = {pid: i for i, pid in enumerate(twod["ids"])}
    twod_labels = twod["labels"][[twod_pos[pid] for pid in ids_e]]   # same realignment
    agr = adjusted_rand_score(real_labels, twod_labels)
    print(f"  ARI(high-dim, 2D): {agr:.4f}", flush=True)

    np.savez("data/knn/cluster_highdim.npz", ids=ids_e, labels=real_labels)
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
