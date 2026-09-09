# Compute available

Reference for design decisions. Updated 2026-08-27.

**No credentials in this file.** Password auth is required for the SSH hops below; the
password is not recorded here and must not be committed. Use an SSH key or a local
password manager.

---

## Local: Apple M2

| | |
|---|---|
| Chip | Apple M2, 8 CPU cores, 10 GPU cores |
| Memory | **8 GB unified** (shared CPU/GPU) |
| Accel | PyTorch MPS backend, available and working |
| Python | 3.13.7, `uv`-managed venv |

**Measured**: `BAAI/bge-small-en-v1.5` (33M params, 384-dim) over 19,970 abstracts
(median ~250 tokens) ran at **~55 texts/sec**, batch size 64. Extrapolates to ~21 min
for a 70k corpus.

**The binding constraint is memory, not throughput.** 8 GB unified rules out large
embedders locally: a 7B model needs ~14 GB in fp16 and will not load. Models up to
roughly BERT-base scale (110M, e.g. SPECTER2) are comfortable.

---

## Remote: (university lab), `your-gpu-host`

Reached via a jump host; a local port is forwarded to an LLM server on the box.

```
ssh -J <user>@your-jump-host.example.edu \
    -L 8000:127.0.0.1:8000 \
    <user>@your-gpu-host.example.edu
```

Password is prompted twice (once per hop) and is not echoed. Keep the session open while
the tunnel is in use.

| | |
|---|---|
| OS | Ubuntu 22.04.5 LTS |
| GPUs | **4 × NVIDIA RTX A6000**, 48 GB VRAM each (~196 GB total) |
| Driver / CUDA | 570.207 / CUDA 12.8 |
| Disk | 590 GB, ~50% used |
| Observed load | Essentially idle (one small ComfyUI process on GPU 0) |
| Extra | An LLM server reachable at `127.0.0.1:8000` once tunnelled |

---

## What this changes, per phase

**Phase 2, embeddings.** The 8 GB ceiling disappears. 48 GB per card fits 7B-class
embedders (e5-mistral, gte-Qwen2, NV-Embed) in fp16 with room to spare, and four cards
means four models can be baked off in parallel rather than serially. This turns the
model comparison from a two-model gesture into a real one.

**Phase 3, projection.** GPU UMAP via RAPIDS cuML becomes viable, which matters at 70k+
points and matters a great deal if projection hyperparameters get swept rather than
guessed.

**Phase 5, labeling.** The LLM server on port 8000 means cluster labeling can run
locally: no per-call cost, no rate limit, and no abstracts leaving the network. Directly
relevant to the charter's "every API call that costs money gets logged" requirement:
this path costs nothing. **Unverified: which model the server actually serves, and
whether it exposes an OpenAI-compatible API.** Check before designing Phase 5 around it.

## Friction to plan around

- Password auth on two hops; no key configured yet. Automating anything means fixing this.
- Data has to move: ~14 MB of Parquet is trivial, embeddings for 70k papers at 4096-dim
  fp32 would be ~1.1 GB. Plan transfers, or generate on the box and bring back only
  what is needed.
- It is a shared university machine. Idle now is not idle always; do not assume
  exclusive access, and check `nvidia-smi` before launching long jobs.
- Sessions are interactive over SSH. Long runs want `tmux` or `nohup` so a dropped
  connection does not kill them.
