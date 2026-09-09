"""Complement to the noise baseline: can the clusters be told apart from the null by a
signal the pipeline never saw?

The noise baseline can only show a map is not PURE artifact. It cannot show the map is
good. This can: cluster assignments come from the embedding geometry, but title
vocabulary is independent of it, so vocabulary agreement within clusters is
non-circular evidence that the geometry found something semantic.

Metric: mean pairwise Jaccard overlap of title content-words within a cluster, compared
against size-matched random groupings of the same corpus (which controls for the fact
that bigger groups trivially overlap less).
"""
import numpy as np, re, json
from collections import Counter

from paper_atlas.embed import load_corpus

STOP = set("""a an the of and or for to in on with by from as at is are be we our this that
these those using use used via towards toward new novel approach method model models
learning based can it its into more than not do does paper study analysis task tasks
data llm llms large language a an""".split())

titles = load_corpus().column("title").to_pylist()
toks = [set(w for w in re.findall(r"[a-z][a-z-]{2,}", t.lower()) if w not in STOP) for t in titles]
rng = np.random.default_rng(0)

def mean_jaccard(idx, pairs=400):
    if len(idx) < 2: return np.nan
    a = rng.choice(idx, pairs); b = rng.choice(idx, pairs)
    keep = a != b
    a, b = a[keep], b[keep]
    out = []
    for i, j in zip(a, b):
        u = len(toks[i] | toks[j])
        out.append(len(toks[i] & toks[j]) / u if u else 0.0)
    return float(np.mean(out))

def score(labels, name):
    real_s, null_s, sizes = [], [], []
    for c in range(int(labels.max()) + 1):
        idx = np.where(labels == c)[0]
        if len(idx) < 5: continue
        real_s.append(mean_jaccard(idx))
        null_s.append(mean_jaccard(rng.choice(len(titles), len(idx), replace=False)))
        sizes.append(len(idx))
    r, n = float(np.nanmean(real_s)), float(np.nanmean(null_s))
    res = {"labels": name, "n_clusters": len(sizes),
           "within_cluster_jaccard": round(r, 4),
           "size_matched_random_jaccard": round(n, 4),
           "lift": round(r / n, 2) if n else None}
    print(json.dumps(res), flush=True)
    return res

out = []
for nm, path in [("real", "data/nb_labels_real_42.npy"),
                 ("gaussian", "data/nb_labels_gaussian_42.npy"),
                 ("shuffled", "data/nb_labels_shuffled_42.npy")]:
    try: out.append(score(np.load(path), nm))
    except FileNotFoundError: print(f"skip {nm} (not ready)", flush=True)
json.dump(out, open("data/vocab_coherence.json", "w"), indent=2)
print("WROTE data/vocab_coherence.json")
