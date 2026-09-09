"""Phase 8: cross-venue alignment. Because embedding used one shared space across all
six venues (not per-venue spaces aligned afterward), a cluster containing papers from
multiple venues already IS the cross-venue alignment signal: the pipeline detects
"same research thread across venues" by construction, as a side effect of clustering
in a unified space.

This measures: which clusters genuinely span venues, how much, and whether it lines up
with what should be true of the field (e.g. LLM/alignment topics spanning ML+NLP venues,
vs venue-specific methodology topics staying siloed).
"""
import json
import numpy as np
from collections import Counter
from paper_atlas.embed import load_corpus

NLP = {"acl", "emnlp", "naacl"}
ML = {"neurips", "icml", "iclr"}

t = load_corpus()
ids = t.column("paper_id").to_pylist()
venues = t.column("venue").to_pylist()

clust = np.load("data/knn/cluster_umap10d_mcs15_ms5.npz", allow_pickle=False)
clust_ids, labels = clust["ids"], clust["labels"]
cluster_labels = json.load(open("data/knn/cluster_labels.json"))

pos = {p: i for i, p in enumerate(ids)}
venues_o = [venues[pos[p]] for p in clust_ids]

rows = []
for c in range(int(labels.max()) + 1):
    idx = np.where(labels == c)[0]
    vc = Counter(venues_o[i] for i in idx)
    n = len(idx)
    nlp_frac = sum(vc.get(v, 0) for v in NLP) / n
    ml_frac = sum(vc.get(v, 0) for v in ML) / n
    # cross-venue index: how far from "single venue family dominates"
    cross_index = min(nlp_frac, ml_frac) * 2   # 1.0 = perfect 50/50 ML/NLP split
    rows.append({
        "cluster": c, "label": cluster_labels.get(str(c), {}).get("label", "?"),
        "n": n, "nlp_frac": round(nlp_frac, 3), "ml_frac": round(ml_frac, 3),
        "cross_index": round(cross_index, 3),
        "venue_breakdown": dict(vc.most_common()),
    })

rows.sort(key=lambda r: -r["cross_index"])
json.dump(rows, open("docs/eval/cross_venue_clusters.json", "w"), indent=2)

print(f"{'cross_idx':>9} {'n':>5}  label")
print("=== TOP 15 most cross-venue (ML+NLP genuinely mixed) ===")
for r in rows[:15]:
    print(f"{r['cross_index']:>9.3f} {r['n']:>5}  {r['label']}  {r['venue_breakdown']}")

siloed = [r for r in rows if r["cross_index"] < 0.05]
print(f"\n=== venue-siloed clusters (cross_index < 0.05): {len(siloed)} / {len(rows)} ===")
for r in siloed[:5]:
    print(f"  {r['n']:>5}  {r['label']}  {r['venue_breakdown']}")

mixed = [r for r in rows if r["cross_index"] >= 0.3]
print(f"\n=== substantially mixed clusters (cross_index >= 0.3): {len(mixed)} / {len(rows)} ===")
