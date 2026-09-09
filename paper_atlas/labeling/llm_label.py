"""LLM polish step: c-TF-IDF keywords + representative titles -> a clean human-readable
cluster name, via the Qwen3-80B server (OpenAI-compatible API).

Grounding the LLM in c-TF-IDF's actual distinguishing vocabulary (rather than just
handing it raw abstracts) keeps it honest about what makes this cluster different from
its neighbors, instead of trusting it to infer that from scratch.

temperature=0 for determinism: this directly serves the charter's "keep labels stable
across re-runs" concern. It does not fully solve it (the clusters themselves are only
ARI~0.57 stable across seeds, per 011), but it removes ONE source of instability: given
the same cluster contents, the same keywords, the same titles, this always returns the
same label.
"""
from __future__ import annotations

import os

from openai import OpenAI

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


def label_cluster(client: OpenAI, keywords: list[str], titles: list[str]) -> str:
    prompt = PROMPT_TEMPLATE.format(
        keywords=", ".join(keywords),
        titles="\n".join(f"- {t}" for t in titles),
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=40,
    )
    return resp.choices[0].message.content.strip().strip('"')


def label_all(ctfidf_results: dict[int, list[tuple[str, float]]],
             titles_by_cluster: dict[int, list[str]],
             sizes: dict[int, int]) -> dict[int, str]:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    out = {}
    for i, c in enumerate(sorted(ctfidf_results, key=lambda c: -sizes[c])):
        keywords = [w for w, _ in ctfidf_results[c]]
        titles = titles_by_cluster[c][:5]
        out[c] = label_cluster(client, keywords, titles)
        if i % 50 == 0:
            print(f"  {i}/{len(ctfidf_results)}", flush=True)
    return out
