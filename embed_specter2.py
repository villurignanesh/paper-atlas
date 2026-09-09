"""SPECTER2 embedding, run in an isolated env.

`adapters` pins transformers~=4.57 while sentence-transformers 6.0 needs 5.x, so this
cannot share the project venv. Run with:

    uv run --isolated --no-project --python 3.13 \
        --with adapters==1.3.0 --with torch --with numpy --with pyarrow \
        python embed_specter2.py

Writes into the same paper_id-keyed npz store the main pipeline reads (see embed.py).
"""
import sys, time, warnings, glob
warnings.filterwarnings("ignore")
import numpy as np, torch, pyarrow.parquet as pq, pyarrow as pa
from transformers import AutoTokenizer
from adapters import AutoAdapterModel

OUT = "data/embeddings/allenai__specter2.npz"
MAXLEN, BATCH = 512, 32          # 512 cap for all models, per 008

tok = AutoTokenizer.from_pretrained("allenai/specter2_base")
model = AutoAdapterModel.from_pretrained("allenai/specter2_base")
model.load_adapter("allenai/specter2", source="hf", load_as="proximity", set_active=True)
dev = "mps" if torch.backends.mps.is_available() else "cpu"
model.to(dev).eval()

def encode(texts):
    b = tok(texts, padding=True, truncation=True, max_length=MAXLEN, return_tensors="pt").to(dev)
    with torch.no_grad():
        v = model(**b).last_hidden_state[:, 0, :]      # CLS pooling, as SPECTER2 specifies
    v = torch.nn.functional.normalize(v, dim=1)        # match bge: unit-norm
    return v.cpu().numpy().astype(np.float32)

# Sanity check: does the adapter actually change the forward pass?
probe = ["Attention Is All You Need" + tok.sep_token + "We propose the Transformer."]
with_adapter = encode(probe)
model.set_active_adapters(None)
without = encode(probe)
model.set_active_adapters("proximity")
delta = float(np.abs(with_adapter - without).mean())
print(f"adapter sanity: mean|with - without| = {delta:.6f}", flush=True)
if delta < 1e-6:
    sys.exit("ABORT: adapter is not affecting the forward pass; this would not be SPECTER2")

# Corpus
files = sorted(glob.glob("data/normalized/**/*.parquet", recursive=True))
t = pa.concat_tables([pq.read_table(f) for f in files])
ids = t.column("paper_id").to_pylist()
titles = t.column("title").to_pylist()
abstracts = t.column("abstract").to_pylist()
# SPECTER2's training format. A ". " join (what bge gets) is off-distribution here and
# would handicap the model for reasons unrelated to citation-training (008).
texts = [f"{ti}{tok.sep_token}{ab}" for ti, ab in zip(titles, abstracts)]
print(f"corpus {len(ids)} papers on {dev}", flush=True)

store = {}
try:
    d = np.load(OUT, allow_pickle=False)
    store = dict(zip(d["ids"].tolist(), d["vecs"]))
    print(f"resuming: {len(store)} already embedded", flush=True)
except Exception:
    pass

todo = [i for i, p in enumerate(ids) if p not in store]
t0 = time.time()
for s in range(0, len(todo), BATCH):
    idx = todo[s:s + BATCH]
    for j, v in zip(idx, encode([texts[j] for j in idx])):
        store[ids[j]] = v
    if (s // BATCH) % 50 == 0:
        done = s + len(idx)
        rate = done / max(time.time() - t0, 1e-9)
        print(f"  {done}/{len(todo)}  {rate:.0f}/s  eta {(len(todo)-done)/max(rate,1e-9)/60:.0f}m", flush=True)
    if (s // BATCH) % 500 == 0 and s:                  # checkpoint so a crash costs little
        k = np.array(list(store)); np.savez(OUT.replace(".npz", ".tmp.npz"), ids=k, vecs=np.stack([store[i] for i in k]))
        import os; os.replace(OUT.replace(".npz", ".tmp.npz"), OUT)

k = np.array(list(store))
np.savez(OUT.replace(".npz", ".tmp.npz"), ids=k, vecs=np.stack([store[i] for i in k]))
import os; os.replace(OUT.replace(".npz", ".tmp.npz"), OUT)
print(f"DONE {len(store)} vectors in {time.time()-t0:.0f}s -> {OUT}", flush=True)
