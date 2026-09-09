"""Full Phase 5 labeling, self-contained for your-gpu-host: c-TF-IDF distinguishing
vocabulary -> Qwen3-80B polish into a clean human-readable label per cluster.

Run on your-gpu-host directly (not through the SSH tunnel) since port 8000 is native here.
"""
from __future__ import annotations

import glob
import json

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import os

from openai import OpenAI

from ctfidf import build_ctfidf

BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = os.environ.get("LLM_API_KEY", "changeme")  # set your GPU server's token here
MODEL = "Qwen/Qwen3-Next-80B-A3B-Instruct-FP8"

PROMPT_TEMPLATE = """You are labeling a cluster of AI research papers with a short, precise topic name.

Distinguishing keywords for this cluster (from c-TF-IDF, most distinctive first):
{keywords}

A few representative paper titles from this cluster:
{titles}

Write a single short topic label (4-8 words) that captures what unites these papers. \
Be specific and technical, not generic. Do not use quotation marks. Respond with ONLY \
the label, nothing else."""


def load_corpus():
    files = sorted(glob.glob("data/normalized/**/*.parquet", recursive=True))
    return pa.concat_tables([pq.read_table(f) for f in files])


def main():
    t = load_corpus()
    ids = t.column("paper_id").to_pylist()
    titles = t.column("title").to_pylist()
    abstracts = t.column("abstract").to_pylist()
    texts = [f"{ti}. {ab}" for ti, ab in zip(titles, abstracts)]

    d = np.load("data/knn/cluster_umap10d_mcs15_ms5.npz", allow_pickle=False)
    cluster_ids, labels = d["ids"], d["labels"]
    pos = {pid: i for i, pid in enumerate(ids)}
    order = [pos[pid] for pid in cluster_ids]
    texts_aligned = [texts[i] for i in order]
    titles_aligned = [titles[i] for i in order]

    print("computing c-TF-IDF...", flush=True)
    ctfidf = build_ctfidf(texts_aligned, labels, top_k=8)
    sizes = {c: int((labels == c).sum()) for c in ctfidf}

    titles_by_cluster: dict[int, list[str]] = {c: [] for c in ctfidf}
    for i, c in enumerate(labels):
        if c >= 0 and len(titles_by_cluster[c]) < 5:
            titles_by_cluster[c].append(titles_aligned[i])

    print(f"{len(ctfidf)} clusters, calling LLM...", flush=True)
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    out = {}
    order_by_size = sorted(ctfidf, key=lambda c: -sizes[c])
    for i, c in enumerate(order_by_size):
        kw = [w for w, _ in ctfidf[c]]
        prompt = PROMPT_TEMPLATE.format(
            keywords=", ".join(kw), titles="\n".join(f"- {ti}" for ti in titles_by_cluster[c]))
        resp = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=40)
        label = resp.choices[0].message.content.strip().strip('"')
        out[int(c)] = {"label": label, "size": sizes[c], "keywords": kw,
                       "sample_titles": titles_by_cluster[c]}
        if i % 50 == 0:
            print(f"  {i}/{len(order_by_size)}  latest: {label}", flush=True)

    with open("data/knn/cluster_labels.json", "w") as f:
        json.dump(out, f, indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
