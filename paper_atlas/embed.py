"""Embedding step, keyed by paper_id and incremental.

An earlier version cached one bare .npy per model and returned it whenever the file
existed. Row i meant "row i of load_corpus() at the time of writing", so growing the
corpus from 20k to 70k silently invalidated the alignment without changing the file:
papers would have been paired with other papers' vectors. Vectors are now stored
alongside their paper_ids and looked up by key, never by position.

Only missing papers are embedded, so adding a venue costs only that venue.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


def load_corpus(root: Path | str = "data/normalized") -> pa.Table:
    files = sorted(Path(root).rglob("*.parquet"))
    return pa.concat_tables([pq.read_table(f) for f in files])


def build_text(table: pa.Table) -> list[str]:
    # JUDGMENT CALL: title + abstract, joined. What text goes in is a Phase 2 decision
    # point (title-only vs +abstract vs +keywords); this is the current default.
    titles = table.column("title").to_pylist()
    abstracts = table.column("abstract").to_pylist()
    return [f"{t}. {a}".strip() for t, a in zip(titles, abstracts)]


def _store_path(model_name: str, out_dir: Path | str) -> Path:
    return Path(out_dir) / f"{model_name.replace('/', '__')}.npz"


def load_store(model_name: str = DEFAULT_MODEL,
               out_dir: Path | str = "data/embeddings") -> dict[str, np.ndarray]:
    p = _store_path(model_name, out_dir)
    if not p.exists():
        return {}
    d = np.load(p, allow_pickle=False)
    return dict(zip(d["ids"].tolist(), d["vecs"]))


def _save_store(store: dict[str, np.ndarray], model_name: str, out_dir: Path | str) -> None:
    p = _store_path(model_name, out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    ids = np.array(list(store.keys()))
    vecs = np.stack([store[i] for i in ids]) if store else np.zeros((0, 0), np.float32)
    # np.savez appends ".npz" unless the name already ends in it, so name the temp
    # file accordingly rather than fighting it.
    tmp = p.with_name(p.stem + ".tmp.npz")
    np.savez(tmp, ids=ids, vecs=vecs)
    tmp.replace(p)


def embed_corpus(table: pa.Table, model_name: str = DEFAULT_MODEL,
                 out_dir: Path | str = "data/embeddings", batch_size: int = 64,
                 device: str = "mps") -> np.ndarray:
    """Return vectors aligned to `table`'s paper_id order, embedding only what's missing."""
    ids = table.column("paper_id").to_pylist()
    store = load_store(model_name, out_dir)
    missing_idx = [i for i, pid in enumerate(ids) if pid not in store]

    if missing_idx:
        from sentence_transformers import SentenceTransformer
        texts = build_text(table)
        todo = [texts[i] for i in missing_idx]
        print(f"embedding {len(todo)} new papers ({len(store)} cached)", flush=True)
        model = SentenceTransformer(model_name, device=device)
        t0 = time.time()
        # normalise -> cosine similarity becomes euclidean distance, which is what the
        # downstream UMAP metric assumes. Not cosmetic; it changes the geometry.
        vecs = model.encode(todo, batch_size=batch_size, normalize_embeddings=True,
                            show_progress_bar=True, convert_to_numpy=True)
        dt = time.time() - t0
        print(f"  {len(todo)} in {dt:.0f}s ({len(todo)/dt:.0f}/s), dim={vecs.shape[1]}", flush=True)
        for j, i in enumerate(missing_idx):
            store[ids[i]] = vecs[j]
        _save_store(store, model_name, out_dir)

    return np.stack([store[pid] for pid in ids])
