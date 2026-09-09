"""THROWAWAY SPIKE (see conversation 2026-08-27). Delete after Phases 2-6 do this properly.

Every parameter below is a Phase 3/4 decision point taken on defaults. The output will
look authoritative and is not evidence of anything.
"""
import re, numpy as np, umap, hdbscan
from collections import Counter
import datamapplot
from paper_atlas.embed import load_corpus, build_text, embed

STOP = set("""a an the of and or for to in on with by from as at is are be we our this that
these those using use used via towards toward new novel approach method model models
learning based can it its into more than not do does can't dont paper study analysis
task tasks data llm llms large language""".split())

table = load_corpus()
vecs = embed(build_text(table))
titles = table.column("title").to_pylist()
venues = table.column("venue").to_pylist()
years  = table.column("year").to_pylist()
print(f"{len(titles)} papers, embeddings {vecs.shape}")

# Projection
# n_neighbors/min_dist are pure defaults. min_dist in particular is cosmetic: lower it
# and ANY dataset looks more clustered. This is the hyperparameter-artifact problem.
coords = umap.UMAP(n_neighbors=15, min_dist=0.1, metric="cosine",
                   n_components=2, random_state=42, verbose=True).fit_transform(vecs)

# Clustering
# JUDGMENT CALL, and the charter flags it as "not as innocent as it looks": clustering
# on the 2D coords, not in high-dim. It makes the visual blobs and the labels agree,
# which is what a *viewer* needs, and it inflates apparent structure, because UMAP
# already exaggerated the separation. Phase 4 must revisit this properly.
labels = hdbscan.HDBSCAN(min_cluster_size=25, min_samples=10).fit_predict(coords)
n_clusters = labels.max() + 1
print(f"{n_clusters} clusters, {(labels==-1).mean():.1%} noise")

# Labels
# PLACEHOLDER, deliberately crude: raw title-term frequency. This is NOT c-TF-IDF;
# that is on the "I write this myself" list. It exists so the real c-TF-IDF has a
# baseline to beat.
def top_terms(idx, k=3):
    c = Counter(w for i in idx for w in re.findall(r"[a-z][a-z-]{2,}", titles[i].lower())
                if w not in STOP)
    return " / ".join(w for w, _ in c.most_common(k)) or "Unlabelled"

names = {c: top_terms(np.where(labels == c)[0]) for c in range(n_clusters)}
label_strings = np.array([names.get(l, "Unlabelled") for l in labels])

hover = [f"{t}\n[{v.upper()} {y}]" for t, v, y in zip(titles, venues, years)]
datamapplot.create_interactive_plot(
    coords, label_strings,
    hover_text=hover,
    title="ACL / EMNLP / NAACL main track, 2018-2026",
    sub_title=f"{len(titles):,} papers - SPIKE, unvalidated - bge-small + UMAP + HDBSCAN defaults",
    noise_label="Unlabelled", enable_search=True, inline_data=True, darkmode=True,
).save("spike_map.html")
np.save("data/spike_coords.npy", coords); np.save("data/spike_labels.npy", labels)
print("wrote spike_map.html")
