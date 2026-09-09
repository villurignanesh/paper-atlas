"""Remove NeurIPS entries from the embedding store so the next run re-embeds them
with corrected (decontaminated) text, while keeping the other 48,983 untouched papers'
embeddings: no need to redo work that was never wrong.
"""
import numpy as np

path = "data/embeddings/qwen3_embedding_8b.npz"
d = np.load(path, allow_pickle=False)
ids, vecs = d["ids"], d["vecs"]

keep = np.array([not pid.startswith("neurips:") for pid in ids])
print(f"before: {len(ids)} total")
print(f"removing: {(~keep).sum()} neurips entries")
print(f"keeping: {keep.sum()} non-neurips entries")

np.savez(path, ids=ids[keep], vecs=vecs[keep])
print(f"DONE -> {path}")
