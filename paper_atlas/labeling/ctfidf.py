"""c-TF-IDF: cluster-level distinguishing vocabulary (charter: user writes this one,
but build-fast mode is active, built here, explained inline for review).

Concept: normal TF-IDF scores a word's importance to ONE document against a corpus of
many documents. c-TF-IDF (BERTopic's term) treats each CLUSTER as one big concatenated
document, so it scores a word's importance to a whole topic-group against all other
topic-groups. A word scores high if it is frequent within this cluster's combined text
AND rare in the combined text of every other cluster, which is exactly what makes it
distinguishing rather than just common (words like "model", "learning", "neural" are
frequent everywhere and score low almost everywhere, which is the point).
"""
from __future__ import annotations

import re
from collections import Counter

import numpy as np

STOPWORDS = set("""
a an the of and or for to in on with by from as at is are be we our this that
these those using use used via towards toward new novel approach method model models
learning based can it its into more than not do does paper study analysis task tasks
data results propose present show demonstrate also however between which
""".split())


def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z][a-z0-9-]{2,}", text.lower()) if w not in STOPWORDS]


def build_ctfidf(texts: list[str], labels: np.ndarray, top_k: int = 10) -> dict[int, list[tuple[str, float]]]:
    """texts[i] is paper i's title+abstract; labels[i] its cluster id (-1 = noise, skipped).

    Returns {cluster_id: [(word, score), ...]} sorted by score, top_k per cluster.
    """
    cluster_ids = sorted(set(labels[labels >= 0].tolist()))

    # Per-cluster raw term counts, and a global document-frequency count (in how many
    # of the K clusters does this word appear at all, not per-paper, per-cluster).
    cluster_counts: dict[int, Counter] = {c: Counter() for c in cluster_ids}
    for text, c in zip(texts, labels):
        if c < 0:
            continue
        cluster_counts[c].update(tokenize(text))

    doc_freq = Counter()
    for c in cluster_ids:
        doc_freq.update(cluster_counts[c].keys())   # each word counted once per cluster it's in

    n_clusters = len(cluster_ids)
    cluster_sizes = {c: sum(cluster_counts[c].values()) for c in cluster_ids}

    results = {}
    for c in cluster_ids:
        counts = cluster_counts[c]
        size = cluster_sizes[c] or 1
        scores = {}
        for word, count in counts.items():
            # tf: term's share of this cluster's total word count.
            tf = count / size
            # idf: rarer across clusters -> higher. +1 smoothing avoids log(0)/div0 for
            # a word that appears in every single cluster (score -> near 0, correctly).
            idf = np.log(1 + n_clusters / doc_freq[word])
            scores[word] = tf * idf
        top = sorted(scores.items(), key=lambda kv: -kv[1])[:top_k]
        results[c] = top
    return results
