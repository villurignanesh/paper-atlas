"""Noise baseline for the mapping pipeline (003, criterion 1).

Question: how much of the structure in the real map is produced by the DATA, and how
much by UMAP+HDBSCAN, which manufacture convincing clusters from anything?

Three inputs, identical pipeline and seed:
  real      the bge-small embeddings
  gaussian  isotropic N(0,1), L2-normalised. The naive null.
  shuffled  each of the 384 columns independently permuted. Preserves every
            per-dimension marginal exactly; destroys only the correlations BETWEEN
            dimensions, i.e. keeps the statistics, removes the semantics. This is
            the null a referee would demand, and the one that matters.
"""
import numpy as np, umap, hdbscan, json, time
from sklearn.manifold import trustworthiness
from sklearn.metrics import adjusted_rand_score

RS, NN, MD, MCS, MS = 42, 15, 0.1, 25, 10
TW_SUB = 5000          # trustworthiness is O(n^2); subsample to fit in 8GB

real = np.load("data/embeddings/BAAI__bge-small-en-v1.5.npy")
rng = np.random.default_rng(RS)
n, d = real.shape

g = rng.standard_normal((n, d)).astype(np.float32)
gaussian = g / np.linalg.norm(g, axis=1, keepdims=True)      # match unit-norm real
shuffled = np.column_stack([rng.permutation(real[:, j]) for j in range(d)])

def run(name, X, seed=RS):
    t0 = time.time()
    coords = umap.UMAP(n_neighbors=NN, min_dist=MD, metric="cosine",
                       n_components=2, random_state=seed).fit_transform(X)
    lab = hdbscan.HDBSCAN(min_cluster_size=MCS, min_samples=MS).fit_predict(coords)
    k = int(lab.max() + 1)
    sizes = np.bincount(lab[lab >= 0]) if k else np.array([0])
    sub = rng.choice(n, TW_SUB, replace=False)
    tw = float(trustworthiness(X[sub], coords[sub], n_neighbors=NN, metric="cosine"))
    r = {"input": name, "seed": seed, "n_clusters": k,
         "noise_frac": float((lab == -1).mean()),
         "median_cluster": int(np.median(sizes)), "max_cluster": int(sizes.max()),
         "trustworthiness": tw, "secs": round(time.time() - t0, 1)}
    print(json.dumps(r), flush=True)
    np.save(f"data/nb_labels_{name}_{seed}.npy", lab)
    np.save(f"data/nb_coords_{name}_{seed}.npy", coords)
    return r

results = [run(nm, X) for nm, X in [("real", real), ("gaussian", gaussian), ("shuffled", shuffled)]]

# Seed stability: does the cluster structure survive changing the random seed?
for s in (7, 1234):
    results.append(run("real", real, seed=s))
labs = [np.load(f"data/nb_labels_real_{s}.npy") for s in (RS, 7, 1234)]
aris = [adjusted_rand_score(labs[i], labs[j]) for i, j in [(0,1),(0,2),(1,2)]]
print(json.dumps({"real_seed_ARI": [round(a,3) for a in aris]}), flush=True)
json.dump({"runs": results, "seed_ARI": aris}, open("data/noise_baseline.json","w"), indent=2)
print("WROTE data/noise_baseline.json")
