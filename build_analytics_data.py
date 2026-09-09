"""Analytics data prep: venue/year counts (from the manifest) + mega-category share of
corpus over time. Pure aggregation of data already computed by build_frontend.py's
loading logic: no new clustering, no LLM calls, no GPU.
"""
import json
import numpy as np
import pandas as pd
from paper_atlas.embed import load_corpus

t = load_corpus()
ids = t.column("paper_id").to_pylist()
years = t.column("year").to_pylist()
venues = t.column("venue").to_pylist()

# Same alignment pattern as build_frontend.py
mega = np.load("data/knn/megacat_mcs2000_ms5.npz", allow_pickle=False)
top = np.load("data/knn/midlevel_mcs400_ms5.npz", allow_pickle=False)
clust = np.load("data/knn/cluster_umap10d_mcs15_ms5.npz", allow_pickle=False)
megacat_labels_json = json.load(open("data/knn/megacat_labels.json"))

pos = {p: i for i, p in enumerate(ids)}
order = [pos[p] for p in mega["ids"]]
years_o = [years[i] for i in order]
venues_o = [venues[i] for i in order]

labels, top_labels, mega_labels = clust["labels"], top["labels"].copy(), mega["labels"].copy()

# Same orphan-handling as build_frontend.py, needed for consistent totals
for leaf_id in range(int(labels.max()) + 1):
    idx = np.where(labels == leaf_id)[0]
    if len(idx) == 0:
        continue
    if (top_labels[idx] >= 0).sum() == 0:
        top_labels[idx] = -2
for group_val in np.unique(top_labels):
    idx = np.where(top_labels == group_val)[0]
    if (mega_labels[idx] >= 0).sum() == 0:
        mega_labels[idx] = -3

mega_names = {int(k): v["label"] for k, v in megacat_labels_json.items()}
mega_names[-3] = "Cross-Cutting & Specialized Research"
mega_names[-1] = "Unclustered"

df = pd.DataFrame({"year": years_o, "venue": venues_o, "mega": mega_labels})

# 2026 excluded: structurally partial for most venues (001-scope.md), would misleadingly
# read as a collapse in every trend line rather than "the year isn't over yet".
df = df[df["year"] <= 2025]

# Mega-category share of corpus, by year. "Unclustered" (-1, genuine HDBSCAN noise at
# this clustering resolution, not a research area) dropped from THIS chart specifically:
# it sits flat around ~13% every year, so it's not a trend, just clustering noise
# competing for attention against the 8 real lines. Still shown as-is on the map and
# Browse table, where per-paper transparency matters more than trend legibility.
# "Cross-Cutting & Specialized Research" (-3) is kept: unlike noise, those points DO have
# a real mid-level topic, they just don't fit one of the 8 broad areas, which is a
# genuine (if imprecise) research-content signal, not an algorithm artifact.
# Denominator recomputed on the filtered rows so the remaining 9 lines still sum to 100%
# instead of silently topping out around 87%.
df = df[df["mega"] != -1]
share = (df.groupby(["year", "mega"]).size().unstack(fill_value=0))
share_pct = share.div(share.sum(axis=1), axis=0) * 100
share_pct.columns = [mega_names.get(c, str(c)) for c in share_pct.columns]
share_pct = share_pct.round(2)

# Venue paper counts, by year, from the manifest (has the completeness flag).
# 2026 excluded here too, same reasoning as the mega-share filter above: structurally
# partial for most venues, not enough data yet to show as its own column.
manifest = pd.read_parquet("data/manifest.parquet")
manifest = manifest[["venue", "year", "n_papers", "complete"]]
manifest = manifest[manifest["year"] <= 2025]

out = {
    "mega_share_by_year": {
        "years": share_pct.index.tolist(),
        "series": {col: share_pct[col].tolist() for col in share_pct.columns},
    },
    "venue_counts_by_year": manifest.to_dict(orient="records"),
}
json.dump(out, open("data/analytics.json", "w"), indent=2)
print(f"mega categories: {len(share_pct.columns)}")
print(f"years: {share_pct.index.tolist()}")
print(f"venue-year rows: {len(manifest)}")
print("wrote data/analytics.json")
