"""Qwen3-Embedding-8B embedding, run on a remote GPU host reached via SSH (see remote_jobs/RUN.md).

Reads the corpus Parquet, embeds title+abstract, writes a paper_id-keyed .npz in the
same format paper_atlas/embed.py uses locally; pull it back and it merges in with no
conversion step.

Self-contained: no dependency on the paper_atlas package (that would mean rsyncing the
whole repo and matching its exact venv). Just needs the normalized Parquet files and a
standard ML stack. Point --corpus at wherever those Parquet files land after rsync.
"""
from __future__ import annotations

import argparse
import glob
import os
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import torch
from transformers import AutoModel, AutoTokenizer

MODEL = "Qwen/Qwen3-Embedding-8B"
MAXLEN = 512          # 512 cap for all models in the bake-off, per 008, keeps the
                       # comparison fair rather than letting the 8B win on context length


def last_token_pool(hidden, mask):
    """Qwen3-Embedding uses last-token pooling, not CLS or mean (unlike SPECTER2/bge)."""
    left_padded = mask[:, -1].sum() == mask.shape[0]
    if left_padded:
        return hidden[:, -1]
    lengths = mask.sum(dim=1) - 1
    return hidden[torch.arange(hidden.shape[0]), lengths]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/normalized")
    ap.add_argument("--out", default="data/embeddings/qwen3_embedding_8b.npz")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--gpu", type=int, default=1)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    dev = f"cuda:{args.gpu}" if torch.cuda.is_available() else "cpu"
    print(f"device: {dev}", flush=True)

    tok = AutoTokenizer.from_pretrained(MODEL, padding_side="left")
    model = AutoModel.from_pretrained(MODEL, dtype=torch.bfloat16).to(dev).eval()
    print(f"model loaded: {sum(p.numel() for p in model.parameters())/1e9:.1f}B params", flush=True)

    files = sorted(glob.glob(os.path.join(args.corpus, "**", "*.parquet"), recursive=True))
    t = pa.concat_tables([pq.read_table(f) for f in files])
    ids = t.column("paper_id").to_pylist()
    titles = t.column("title").to_pylist()
    abstracts = t.column("abstract").to_pylist()
    # No instruction prefix: Qwen3-Embedding's asymmetric instruction format is for
    # QUERY-side retrieval. This is symmetric document-to-document similarity, so
    # documents go in bare on both sides of every comparison, same as bge/SPECTER2.
    texts = [f"{ti}. {ab}".strip() for ti, ab in zip(titles, abstracts)]
    print(f"corpus: {len(ids)} papers", flush=True)

    store = {}
    if os.path.exists(args.out):
        d = np.load(args.out, allow_pickle=False)
        store = dict(zip(d["ids"].tolist(), d["vecs"]))
        print(f"resuming: {len(store)} already embedded", flush=True)

    todo = [i for i, p in enumerate(ids) if p not in store]
    t0 = time.time()
    for s in range(0, len(todo), args.batch_size):
        idx = todo[s:s + args.batch_size]
        batch = [texts[j] for j in idx]
        enc = tok(batch, padding=True, truncation=True, max_length=MAXLEN,
                 return_tensors="pt").to(dev)
        with torch.no_grad():
            hidden = model(**enc).last_hidden_state
            v = last_token_pool(hidden, enc["attention_mask"])
            v = torch.nn.functional.normalize(v, dim=1)   # unit-norm, matches bge/SPECTER2
        v = v.to(torch.float32).cpu().numpy()
        for j, vec in zip(idx, v):
            store[ids[j]] = vec

        done = s + len(idx)
        if (s // args.batch_size) % 25 == 0:
            rate = done / max(time.time() - t0, 1e-9)
            print(f"  {done}/{len(todo)}  {rate:.1f}/s  eta {(len(todo)-done)/max(rate,1e-9)/60:.1f}m", flush=True)
        if (s // args.batch_size) % 200 == 0 and s:      # checkpoint periodically
            k = np.array(list(store))
            tmp = args.out + ".tmp.npz"
            np.savez(tmp, ids=k, vecs=np.stack([store[i] for i in k]))
            os.replace(tmp, args.out)

    k = np.array(list(store))
    tmp = args.out + ".tmp.npz"
    np.savez(tmp, ids=k, vecs=np.stack([store[i] for i in k]))
    os.replace(tmp, args.out)
    print(f"DONE {len(store)} vectors in {time.time()-t0:.0f}s -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
