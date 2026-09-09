"""Data prep for the paper table: every paper with title, venue, year, url, and all
three hierarchy levels. Pure aggregation of data already computed: same alignment
pattern as build_frontend.py and build_analytics_data.py.
"""
import json
import numpy as np
from paper_atlas.embed import load_corpus

t = load_corpus()
ids = t.column("paper_id").to_pylist()
titles = t.column("title").to_pylist()
venues = t.column("venue").to_pylist()
years = t.column("year").to_pylist()
urls = t.column("source_url").to_pylist()

clust = np.load("data/knn/cluster_umap10d_mcs15_ms5.npz", allow_pickle=False)
top = np.load("data/knn/midlevel_mcs400_ms5.npz", allow_pickle=False)
mega = np.load("data/knn/megacat_mcs2000_ms5.npz", allow_pickle=False)
cluster_labels = json.load(open("data/knn/cluster_labels.json"))
toplevel_labels = json.load(open("data/knn/toplevel_labels.json"))
megacat_labels = json.load(open("data/knn/megacat_labels.json"))

pos = {p: i for i, p in enumerate(ids)}
order = [pos[p] for p in clust["ids"]]
labels, top_labels, mega_labels = clust["labels"].copy(), top["labels"].copy(), mega["labels"].copy()

# Same orphan-handling as build_frontend.py: keeps the table's category labels
# consistent with what the map itself shows for the same papers.
for leaf_id in range(int(labels.max()) + 1):
    idx = np.where(labels == leaf_id)[0]
    if len(idx) and (top_labels[idx] >= 0).sum() == 0:
        top_labels[idx] = -2
for group_val in np.unique(top_labels):
    idx = np.where(top_labels == group_val)[0]
    if (mega_labels[idx] >= 0).sum() == 0:
        mega_labels[idx] = -3

def leaf_name(l): return cluster_labels.get(str(l), {}).get("label", "Unclustered") if l >= 0 else "Unclustered"
def top_name(l):
    if l >= 0: return toplevel_labels.get(str(l), {}).get("label", "Unclustered")
    return "Specialized / Niche Topics" if l == -2 else "Unclustered"
def mega_name(l):
    if l >= 0: return megacat_labels.get(str(l), {}).get("label", "Unclustered")
    return "Cross-Cutting & Specialized Research" if l == -3 else "Unclustered"

rows = []
for j, i in enumerate(order):
    rows.append({
        "t": titles[i], "v": venues[i], "y": years[i], "u": urls[i],
        "mega": mega_name(mega_labels[j]), "topic": top_name(top_labels[j]),
        "leaf": leaf_name(labels[j]),
    })

json.dump(rows, open("data/table_data.json", "w"))
venues_u = sorted(set(r["v"] for r in rows))
years_u = sorted(set(r["y"] for r in rows))
mega_u = sorted(set(r["mega"] for r in rows))
print(f"{len(rows)} rows, {len(venues_u)} venues, {len(years_u)} years, {len(mega_u)} mega-categories")
print(f"data/table_data.json size: {__import__('os').path.getsize('data/table_data.json')/1e6:.1f} MB")
