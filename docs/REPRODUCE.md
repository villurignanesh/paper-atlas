# Reproducing / refreshing Paper Atlas

Full pipeline, in order. Ingestion + eval run locally; embedding + heavy
clustering/projection run on your-gpu-host (GPU) via the push/run/pull pattern
established across this project (see docs/compute.md and remote_jobs/RUN.md).

## 1. Ingest (local, ~30 min incl. network)

    uv run python -m paper_atlas.adapters.anthology_parse    # ACL/EMNLP/NAACL
    uv run python -m paper_atlas.adapters.iclr_parse          # ICLR (+ DBLP accept-list check)
    uv run python -m paper_atlas.adapters.neurips_parse        # NeurIPS
    uv run python -m paper_atlas.adapters.icml                 # ICML

Validates against DBLP automatically for scraped sources (002).

## 2. Embed (remote, GPU, ~24 min for full corpus)

    rsync data/normalized/ + remote_jobs/ -> your-gpu-host:~/paper_atlas/
    ssh your-gpu-host, activate venv, setenv CUDA_VISIBLE_DEVICES <idle GPU>
    python3 embed_qwen3.py --batch-size 16
    rsync qwen3_embedding_8b.npz back

Incremental: only embeds paper_ids missing from the store (embed.py). Adding one
year's papers next cycle re-embeds only those, not the full corpus.

## 3. kNN graph + projection + clustering (remote, GPU, ~3 min total)

    python3 knn_graph.py           # exact brute-force (009: free at this scale)
    python3 project.py             # UMAP 2D, min_dist=0.5 (010)
    python3 umap_for_clustering.py # UMAP 10D -> HDBSCAN, seed=42 (011)
    rsync data/knn/ back

## 4. Label (remote, needs the Qwen3-80B server up)

    curl 127.0.0.1:8000/v1/models -H "Authorization: Bearer $LLM_API_KEY"
    # if down: tmux new -s qwen80b ~/start_qwen.sh
    python3 label_clusters.py
    rsync cluster_labels.json back

## 5. Evaluate (local, fast)

    uv run python -c "from paper_atlas.eval.clustering import cluster_keyword_purity; ..."
    # trustworthiness re-check, cross_venue_analysis.py

## 6. Build + ship (local)

    uv run python build_frontend.py   # -> paper_atlas_map.html, self-contained
    # host: GitHub Pages, or any static file server. No backend, no GPU at
    # view-time; see conversation notes: build offline, serve static forever.

## Refresh cadence

Manual, on demand (005 Q5: "re-run when we want"). Adding a year: re-run step 1 for
that venue-year only, step 2 picks up only new paper_ids automatically, steps 3-6
re-run in full (projection/clustering are not currently incremental: a new paper
changes the whole map's layout, 005's known consequence of full-refit).

## Known manual friction (honest, not automated away)

- SSH key auth to your-gpu-host never got working (jump host rejects it even with
  correct permissions); every remote step needs a live password-authenticated
  tunnel/session, run by a human, not by CI.
- GPU contention: check `nvidia-smi` before launching (qwen80b server occupies
  GPUs 0-1; use 2 or 3, see docs/compute.md).
- No single script chains all of this yet: each step above is a separate command,
  run in the sequence above.
