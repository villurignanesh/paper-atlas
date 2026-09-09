# Running Qwen3-Embedding-8B on your-gpu-host

## 1. Push code + corpus (run on the Mac)

```bash
rsync -av /path/to/paper-atlas/remote_jobs/ \
  youruser@your-gpu-host.example.edu:~/paper_atlas/ \
  -e "ssh -J youruser@your-jump-host.example.edu"

rsync -av /path/to/paper-atlas/data/normalized/ \
  youruser@your-gpu-host.example.edu:~/paper_atlas/data/normalized/ \
  -e "ssh -J youruser@your-jump-host.example.edu"
```

Corpus is ~59MB, near-instant. Two passwords each (jump host, then target) unless
you set up SSH `ControlMaster` or key-based auth for the two hops.

## 2. Open the shell (run on the Mac, keep this terminal open)

```bash
ssh -J youruser@your-jump-host.example.edu youruser@your-gpu-host.example.edu
```

## 3. One-time environment setup (on your-gpu-host, inside the ssh session)

Shell there is **tcsh**: no inline `VAR=x cmd`, use `setenv`. No `cmd > out 2>&1`,
use `cmd >& out`. Don't paste multi-line `python3 -c "..."`.

```tcsh
cd ~/paper_atlas
python3 -m venv venv
source venv/bin/activate.csh
pip install torch transformers pyarrow numpy accelerate
```

`transformers>=4.51` is required for Qwen3 support; pip will resolve a recent
enough version in a fresh venv. If `AutoModel.from_pretrained` errors on an
unrecognized model type, that is the symptom: `pip install -U transformers` fixes it.

## 4. Run it (on your-gpu-host, in tmux so it survives a dropped connection)

```tcsh
tmux new-session -s qwen3embed
cd ~/paper_atlas
source venv/bin/activate.csh
setenv CUDA_VISIBLE_DEVICES 1
python3 embed_qwen3.py --gpu 0 --batch-size 16 >& qwen3.log &
```

(`--gpu 0` here refers to the *visible* device index after `CUDA_VISIBLE_DEVICES=1`
restricts the process to physical GPU 1: inside that restriction it is the only
card the process can see, so it's index 0 to it.)

Detach with `Ctrl-b d`. Reattach any time with `tmux attach -t qwen3embed`.

Check progress without attaching:

```tcsh
tail -20 ~/paper_atlas/qwen3.log
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv
```

Expect ~16GB VRAM on GPU 1 once the model loads. 70,861 papers at whatever rate the
log reports; unknown ahead of time, this is the first run (charter rule 6: measure,
don't guess).

## 5. Pull results back (run on the Mac, once the log shows `DONE`)

```bash
rsync -av \
  youruser@your-gpu-host.example.edu:~/paper_atlas/data/embeddings/qwen3_embedding_8b.npz \
  /path/to/paper-atlas/data/embeddings/ \
  -e "ssh -J youruser@your-jump-host.example.edu"
```

Drops straight into the local `data/embeddings/` directory in the same paper_id-keyed
format the local store uses; no conversion needed.
