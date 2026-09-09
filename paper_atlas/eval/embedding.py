"""Phase 2 bake-off metrics (008). Both compare embedding SPACES, not pipelines.

Deliberately no clustering. Cluster purity would fold UMAP and HDBSCAN hyperparameters
into a number meant to describe the embedding, and given the measured ARI 0.30 seed
instability that noise would swamp the signal we are trying to read.
"""

from __future__ import annotations

import numpy as np


def _norm_kw(kws) -> set[str]:
    return {" ".join(str(k).lower().split()) for k in (kws or []) if str(k).strip()}


def knn_keyword_agreement(vecs: np.ndarray, keywords: list, k: int = 10,
                          seed: int = 0, block: int = 2048) -> dict:
    """Do a paper's nearest neighbours share its author-assigned keywords?

    Measures the embedding directly: if the space is good, neighbours in it should be
    papers humans tagged alike. Restricted to papers that HAVE keywords (ICLR only),
    and compared against a random-pair baseline so the number means something.
    """
    keep = [i for i, kw in enumerate(keywords) if _norm_kw(kw)]
    V = vecs[keep].astype(np.float32)
    K = [_norm_kw(keywords[i]) for i in keep]
    n = len(keep)
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-12

    jac, hit = [], []
    for s in range(0, n, block):
        sims = V[s:s + block] @ V.T                    # cosine, vectors unit-norm
        for r in range(sims.shape[0]):
            i = s + r
            sims[r, i] = -np.inf                       # exclude self
            nb = np.argpartition(-sims[r], k)[:k]
            for j in nb:
                inter = len(K[i] & K[j]); union = len(K[i] | K[j])
                jac.append(inter / union if union else 0.0)
                hit.append(1.0 if inter else 0.0)

    rng = np.random.default_rng(seed)
    a, b = rng.integers(0, n, len(jac)), rng.integers(0, n, len(jac))
    rj = [len(K[x] & K[y]) / max(len(K[x] | K[y]), 1) for x, y in zip(a, b)]
    rh = [1.0 if K[x] & K[y] else 0.0 for x, y in zip(a, b)]

    return {"n_labelled": n, "k": k,
            "knn_jaccard": float(np.mean(jac)), "random_jaccard": float(np.mean(rj)),
            "jaccard_lift": float(np.mean(jac) / max(np.mean(rj), 1e-9)),
            "knn_any_shared": float(np.mean(hit)), "random_any_shared": float(np.mean(rh))}


def venue_predictability(vecs: np.ndarray, venues: list[str], seed: int = 0,
                         sample: int = 30000) -> dict:
    """How much venue identity is baked into the embedding space?

    Tests 008's hypothesis. Citation-trained models learn "similar = cites each other",
    and citation is strongly within-community, so venue should be MORE predictable from
    SPECTER2 than from a semantics-trained model.

    High accuracy is a WARNING for cross-venue alignment, not a quality score: it means
    the space separates communities even when they work on the same topic.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score

    rng = np.random.default_rng(seed)
    idx = rng.choice(len(venues), min(sample, len(venues)), replace=False)
    X, y = vecs[idx], np.array(venues)[idx]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=seed)
    clf = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
    pred = clf.predict(Xte)
    _, counts = np.unique(yte, return_counts=True)
    return {"n": len(idx), "accuracy": float(accuracy_score(yte, pred)),
            "macro_f1": float(f1_score(yte, pred, average="macro")),
            "majority_baseline": float(counts.max() / counts.sum())}
