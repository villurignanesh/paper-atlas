"""Phase 6: does the final clustering (902 clusters, 011) agree with independent human
ground truth? Uses ICLR author-supplied keywords (15,857 papers, the only free ground
truth in the corpus, 003).

Different question from the Phase 2 bake-off's kNN keyword agreement (which tested
nearest-neighbor agreement in raw embedding space): this tests whether the actual
CLUSTERS, the output of the full UMAP-10D -> HDBSCAN pipeline, are coherent, which
is what actually ships.
"""
from __future__ import annotations

import numpy as np


def _norm_kw(kws) -> set[str]:
    return {" ".join(str(k).lower().split()) for k in (kws or []) if str(k).strip()}


def cluster_keyword_purity(labels: np.ndarray, keywords: list, seed: int = 0,
                           max_pairs_per_cluster: int = 200) -> dict:
    """For each cluster, restrict to its papers that HAVE keywords (ICLR only), then
    measure mean pairwise Jaccard overlap within that cluster. Compare against a
    size-matched random baseline (same-size group, drawn from the full keyworded pool):
    controls for the fact that smaller groups trivially show higher overlap by chance.
    """
    kw_sets = [_norm_kw(k) for k in keywords]
    has_kw = np.array([len(k) > 0 for k in kw_sets])
    kw_idx_pool = np.where(has_kw)[0]
    rng = np.random.default_rng(seed)

    def mean_jaccard(idx_list, pairs):
        if len(idx_list) < 2:
            return None
        a = rng.choice(idx_list, min(pairs, len(idx_list) ** 2)); b = rng.choice(idx_list, min(pairs, len(idx_list) ** 2))
        keep = a != b
        a, b = a[keep], b[keep]
        if len(a) == 0:
            return None
        out = []
        for i, j in zip(a, b):
            u = len(kw_sets[i] | kw_sets[j])
            out.append(len(kw_sets[i] & kw_sets[j]) / u if u else 0.0)
        return float(np.mean(out))

    real_scores, random_scores, sizes = [], [], []
    for c in range(int(labels.max()) + 1):
        idx = np.where((labels == c) & has_kw)[0]
        if len(idx) < 2:
            continue
        r = mean_jaccard(idx, max_pairs_per_cluster)
        rand_idx = rng.choice(kw_idx_pool, len(idx), replace=False)
        n = mean_jaccard(rand_idx, max_pairs_per_cluster)
        # Both r and n can independently return None for very small clusters (an
        # unlucky draw of all-matching pairs is rare but not impossible across ~900
        # trials). Skip the cluster entirely rather than let a None poison the mean.
        if r is None or n is None:
            continue
        real_scores.append(r); random_scores.append(n); sizes.append(len(idx))

    real_mean, rand_mean = float(np.mean(real_scores)), float(np.mean(random_scores))
    return {
        "n_clusters_evaluated": len(real_scores),
        "n_iclr_papers_with_keywords_used": int(has_kw.sum()),
        "mean_within_cluster_jaccard": real_mean,
        "mean_size_matched_random_jaccard": rand_mean,
        "lift": round(real_mean / rand_mean, 2) if rand_mean else None,
        "median_iclr_papers_per_evaluated_cluster": int(np.median(sizes)),
    }
