"""Label the 8 mega-categories (mcs=2000, docs/decisions/011-clustering.md third
addendum). Same c-TF-IDF + LLM pattern as label_toplevel.py and the SAME clustering
(this only ever changes the prompt, never the boundaries; the 8-cluster count was
already a measured, stable plateau, not the thing that needed fixing).

Originally prompted for plain, everyday language ("explain to a 5 year old",
future_work.md #2) on the theory that the top level should be layperson-accessible.
Reversed: compared against a real reference top-level taxonomy (jalammar's map) and
found the plain-language framing is exactly why this level didn't read as real AI/ML
categories to anyone who actually knows the field, while our OWN mid-level (44 topics,
label_toplevel.py, never told to avoid jargon) already reads close to that reference in
style. Reprompted to match: an area-chair, established-terminology framing instead of a
plain-English one, same 8 clusters, same c-TF-IDF/title inputs.
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

PROMPT_TEMPLATE = """You are an area chair defining the top-level research areas for a \
major AI/ML conference program, the kind of division used in NeurIPS/ICML primary-area \
listings (e.g. Reinforcement Learning, Generative Models, Optimization, Computer Vision, \
Natural Language Processing, Trustworthy ML, Graph Learning, AI for Science). You are \
naming ONE such area: broad enough to cover a large, diverse slice of the field, but \
named the way a researcher in that area would actually recognize it, not simplified for \
a general audience.

Distinguishing keywords for this category (from c-TF-IDF, most distinctive first):
{keywords}

Representative paper titles sampled across the category's full breadth:
{titles}

Write a short category name (2-6 words) using real, established AI/ML terminology \
(acronyms like "LLM", "RL", "NLP" are fine where they're the standard term researchers \
use). Name what actually unites this category's research content, not a generic or \
watered-down description. Do not use quotation marks. Respond with ONLY the name, \
nothing else."""


def load_corpus():
    files = sorted(glob.glob("data/normalized/**/*.parquet", recursive=True))
    return pa.concat_tables([pq.read_table(f) for f in files])


def main():
    t = load_corpus()
    ids = t.column("paper_id").to_pylist()
    titles = t.column("title").to_pylist()
    abstracts = t.column("abstract").to_pylist()
    texts = [f"{ti}. {ab}" for ti, ab in zip(titles, abstracts)]

    d = np.load("data/knn/megacat_mcs2000_ms5.npz", allow_pickle=False)
    cluster_ids, labels = d["ids"], d["labels"]
    pos = {pid: i for i, pid in enumerate(ids)}
    order = [pos[pid] for pid in cluster_ids]
    texts_aligned = [texts[i] for i in order]
    titles_aligned = [titles[i] for i in order]

    print("computing c-TF-IDF for mega-categories...", flush=True)
    ctfidf = build_ctfidf(texts_aligned, labels, top_k=15)
    sizes = {c: int((labels == c).sum()) for c in ctfidf}

    titles_by_cluster: dict[int, list[str]] = {}
    for c in ctfidf:
        idx = np.where(labels == c)[0]
        step = max(1, len(idx) // 12)
        titles_by_cluster[c] = [titles_aligned[i] for i in idx[::step][:12]]

    print(f"{len(ctfidf)} mega-categories, calling LLM...", flush=True)
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    out = {}
    for c in sorted(ctfidf, key=lambda c: -sizes[c]):
        kw = [w for w, _ in ctfidf[c]]
        prompt = PROMPT_TEMPLATE.format(
            keywords=", ".join(kw), titles="\n".join(f"- {ti}" for ti in titles_by_cluster[c]))
        resp = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=30)
        label = resp.choices[0].message.content.strip().strip('"')
        out[int(c)] = {"label": label, "size": sizes[c], "keywords": kw}
        print(f"  n={sizes[c]:>6}  {label}", flush=True)

    with open("data/knn/megacat_labels.json", "w") as f:
        json.dump(out, f, indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
