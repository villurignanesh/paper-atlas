"""Label the 44 top-level groups (mcs=400, docs/decisions/011-clustering.md addendum),
same c-TF-IDF + LLM approach as label_clusters.py for the 902 leaves. Separate script
rather than generalizing label_clusters.py under time pressure: avoids risk to the
already-validated leaf-labeling path for a one-off second run.
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from openai import OpenAI

from ctfidf import build_ctfidf

BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = os.environ.get("LLM_API_KEY", "changeme")
MODEL = "Qwen/Qwen3-Next-80B-A3B-Instruct-FP8"

# Same prompt shape as label_clusters.py, but told explicitly that these are BROAD
# groups covering many sub-topics, not narrow ones, otherwise the model tends to
# describe only the single most frequent keyword rather than the group as a whole.
PROMPT_TEMPLATE = """You are labeling a BROAD top-level group of AI research papers. \
Each group contains many distinct sub-topics, so the label should name the overarching \
theme that unites them, not just the single most common keyword.

Distinguishing keywords for this group (from c-TF-IDF, most distinctive first):
{keywords}

A few representative paper titles, sampled across the group's breadth:
{titles}

Write a single broad topic label (4-10 words) that captures the overarching theme. \
Do not use quotation marks. Respond with ONLY the label, nothing else."""


def load_corpus():
    files = sorted(glob.glob("data/normalized/**/*.parquet", recursive=True))
    return pa.concat_tables([pq.read_table(f) for f in files])


def main():
    t = load_corpus()
    ids = t.column("paper_id").to_pylist()
    titles = t.column("title").to_pylist()
    abstracts = t.column("abstract").to_pylist()
    texts = [f"{ti}. {ab}" for ti, ab in zip(titles, abstracts)]

    d = np.load("data/knn/midlevel_mcs400_ms5.npz", allow_pickle=False)
    cluster_ids, labels = d["ids"], d["labels"]
    pos = {pid: i for i, pid in enumerate(ids)}
    order = [pos[pid] for pid in cluster_ids]
    texts_aligned = [texts[i] for i in order]
    titles_aligned = [titles[i] for i in order]

    print("computing c-TF-IDF for top-level groups...", flush=True)
    ctfidf = build_ctfidf(texts_aligned, labels, top_k=12)  # more keywords: broader groups
    sizes = {c: int((labels == c).sum()) for c in ctfidf}

    # Sample titles spread across the group (every Nth), not just the first 5:
    # a broad group's first 5 papers by index are not representative of its breadth.
    titles_by_cluster: dict[int, list[str]] = {}
    for c in ctfidf:
        idx = np.where(labels == c)[0]
        step = max(1, len(idx) // 8)
        titles_by_cluster[c] = [titles_aligned[i] for i in idx[::step][:8]]

    print(f"{len(ctfidf)} groups, calling LLM...", flush=True)
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    out = {}
    for c in sorted(ctfidf, key=lambda c: -sizes[c]):
        kw = [w for w, _ in ctfidf[c]]
        prompt = PROMPT_TEMPLATE.format(
            keywords=", ".join(kw), titles="\n".join(f"- {ti}" for ti in titles_by_cluster[c]))
        resp = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=50)
        label = resp.choices[0].message.content.strip().strip('"')
        out[int(c)] = {"label": label, "size": sizes[c], "keywords": kw}
        print(f"  n={sizes[c]:>5}  {label}", flush=True)

    with open("data/knn/toplevel_labels.json", "w") as f:
        json.dump(out, f, indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
