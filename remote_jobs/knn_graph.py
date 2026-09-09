"""From-scratch kNN-graph construction over the Qwen3-8B corpus embeddings.

Two implementations, same interface, so their outputs and timings are directly
comparable:

  brute_force_knn: exact, O(n^2) cosine similarity via a single matmul, chunked
                        so the full n x n similarity matrix never has to fit in memory
                        at once (70,861^2 floats would be ~20GB in fp32).
  nndescent_knn: approximate, via pynndescent (the same NN-descent algorithm
                        UMAP uses internally). Starts from random neighbor guesses and
                        iteratively improves them by exploring neighbors-of-neighbors,
                        which converges near-exact in roughly O(n log n) instead of O(n^2).

The point of running both is to measure, not assume, the accuracy/speed tradeoff on
THIS corpus at THIS k, rather than trusting the textbook claim (charter rule 6).
"""
from __future__ import annotations

import argparse
import glob
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def load_embeddings(npz_path: str, corpus_glob: str):
    """Return (paper_ids, vectors) in a fixed, reproducible order (sorted by paper_id)."""
    d = np.load(npz_path, allow_pickle=False)
    store = dict(zip(d["ids"].tolist(), d["vecs"]))
    files = sorted(glob.glob(corpus_glob, recursive=True))
    t = pa.concat_tables([pq.read_table(f, columns=["paper_id"]) for f in files])
    ids = sorted(t.column("paper_id").to_pylist())          # fixed order, not file order
    ids = [i for i in ids if i in store]
    V = np.stack([store[i] for i in ids]).astype(np.float32)
    return ids, V


def brute_force_knn(V: np.ndarray, k: int, chunk: int = 2000):
    """Exact kNN by cosine similarity. V is assumed unit-norm, so cosine sim = dot
    product: a single matmul per chunk, no separate normalization step needed.
    """
    n = V.shape[0]
    neighbors = np.empty((n, k), dtype=np.int64)
    sims = np.empty((n, k), dtype=np.float32)
    for s in range(0, n, chunk):
        e = min(s + chunk, n)
        block = V[s:e] @ V.T                      # (chunk, n) similarity block
        for r in range(e - s):
            block[r, s + r] = -np.inf              # exclude self
        idx = np.argpartition(-block, k, axis=1)[:, :k]
        for r in range(e - s):
            order = idx[r][np.argsort(-block[r, idx[r]])]
            neighbors[s + r] = order
            sims[s + r] = block[r, order]
    return neighbors, sims


def nndescent_knn(V: np.ndarray, k: int, seed: int = 42):
    from pynndescent import NNDescent
    index = NNDescent(V, n_neighbors=k + 1, metric="cosine", random_state=seed)
    neighbors, dists = index.neighbor_graph
    # NNDescent includes self as neighbor 0 (distance 0); drop it to match brute_force's
    # self-exclusion so the two methods are compared on the same definition of "neighbor"
    return neighbors[:, 1:k + 1], (1 - dists[:, 1:k + 1])   # cosine sim = 1 - cosine dist


def agreement(a_idx: np.ndarray, b_idx: np.ndarray) -> float:
    """Fraction of neighbor-set overlap between two kNN results, averaged over points."""
    return float(np.mean([len(set(a_idx[i]) & set(b_idx[i])) / a_idx.shape[1]
                          for i in range(a_idx.shape[0])]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--embeddings", default="data/embeddings/qwen3_embedding_8b.npz")
    ap.add_argument("--corpus", default="data/normalized/**/*.parquet")
    ap.add_argument("--k", type=int, default=15)
    ap.add_argument("--out", default="data/knn")
    args = ap.parse_args()

    print("loading...", flush=True)
    ids, V = load_embeddings(args.embeddings, args.corpus)
    print(f"n={len(ids)} dim={V.shape[1]}", flush=True)

    print(f"\n=== brute-force exact kNN, k={args.k} ===", flush=True)
    t0 = time.time()
    bf_nb, bf_sim = brute_force_knn(V, args.k)
    bf_time = time.time() - t0
    print(f"done in {bf_time:.1f}s", flush=True)

    print(f"\n=== NN-descent approximate kNN, k={args.k} ===", flush=True)
    t0 = time.time()
    nd_nb, nd_sim = nndescent_knn(V, args.k)
    nd_time = time.time() - t0
    print(f"done in {nd_time:.1f}s", flush=True)

    agr = agreement(bf_nb, nd_nb)
    print(f"\n=== comparison ===", flush=True)
    print(f"brute-force: {bf_time:.1f}s", flush=True)
    print(f"nn-descent:  {nd_time:.1f}s  ({bf_time/max(nd_time,1e-9):.1f}x speedup)", flush=True)
    print(f"neighbor-set agreement: {agr:.4f}", flush=True)

    import os
    os.makedirs(args.out, exist_ok=True)
    np.savez(f"{args.out}/knn_bruteforce.npz", ids=np.array(ids), neighbors=bf_nb, sims=bf_sim)
    np.savez(f"{args.out}/knn_nndescent.npz", ids=np.array(ids), neighbors=nd_nb, sims=nd_sim)
    print(f"\nsaved to {args.out}/", flush=True)


if __name__ == "__main__":
    main()
