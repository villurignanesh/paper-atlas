# Paper Atlas

**[villurignanesh.github.io/paper-atlas](https://villurignanesh.github.io/paper-atlas/)**

An interactive semantic map of 70,861 accepted papers from six top AI/ML venues
(NeurIPS, ICML, ICLR, ACL, EMNLP, NAACL, 2018-2026). Papers are embedded, projected
to 2D, clustered into a three-level topic hierarchy, and labeled, so the actual
shape of the field, not a hand-built taxonomy, is what you're looking at.

## What's here

- **[Map](https://villurignanesh.github.io/paper-atlas/)**: the interactive
  semantic map. Zoom, search, and browse a topic tree spanning 902 fine-grained
  clusters, 44 mid-level topics, and 8 top-level research areas.
- **[Browse](https://villurignanesh.github.io/paper-atlas/table.html)**: every
  paper as a searchable, filterable, sortable table.
- **[Analytics](https://villurignanesh.github.io/paper-atlas/analytics.html)**:
  how the field's attention has shifted across topics and venues since 2018.

No backend, no database, no API calls at view time. Everything is a static site;
the heavy compute (embedding, projection, clustering, labeling) happens once,
offline, and the result ships as a self-contained page.

## How it's built

1. **Ingest**: per-venue adapters normalize each source (OpenReview, PMLR, ACL
   Anthology, NeurIPS proceedings) into one shared schema.
2. **Embed**: title + abstract through `Qwen3-Embedding-8B` (4096-dim), chosen
   over citation-trained alternatives (SPECTER2) after a measured bake-off, see
   [`docs/decisions/008-embeddings.md`](docs/decisions/008-embeddings.md).
3. **Project**: UMAP to 2D for display, and separately to 10D purely for
   clustering, the standard two-reduction pattern.
4. **Cluster**: HDBSCAN on the 10D embedding, with the three hierarchy levels
   derived from the *same* embedding by sweeping `min_cluster_size`, not three
   independent, potentially-inconsistent runs. Nesting between levels validated
   at 97-100%, not assumed, see
   [`docs/decisions/011-clustering.md`](docs/decisions/011-clustering.md).
5. **Label**: c-TF-IDF keywords + representative titles through an LLM, prompted
   for the precise, established terminology a researcher in that area would
   actually use.
6. **Evaluate**: trustworthiness, seed-stability, and cluster purity against
   independent human ground truth (ICLR's own author-supplied keywords), all
   measured against a noise baseline rather than eyeballed. See
   [`docs/decisions/`](docs/decisions/) for the full trail.

Every non-trivial choice along the way, including the ones that got tried and
rejected, is written up in [`docs/decisions/`](docs/decisions/): what was
considered, what was picked, why, and what would change it.

## Running it yourself

```bash
uv sync
```

Data (`data/`) is gitignored and not checked in. You'll need to run the
ingestion adapters yourself to build a local corpus; see
[`docs/REPRODUCE.md`](docs/REPRODUCE.md) for the full pipeline, and
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the remote-GPU push/run/pull pattern
the embedding and clustering steps use.

Once you have the processed data, each page is a single script:

```bash
uv run python build_frontend.py        # -> index.html (the map)
uv run python build_table_page.py      # -> table.html (browse)
uv run python build_analytics_page.py  # -> analytics.html
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for how this repo works, and
[`future_work.md`](future_work.md) for scoped-out tasks, including good first
issues and the larger Paper-Copilot-inspired features (institution rankings,
submission/acceptance rates, review analytics) that are real, substantial
undertakings rather than quick add-ons.

## License

Code is [MIT licensed](LICENSE). The bundled fonts (Valley Sans, Instrument
Serif) are separately licensed under the SIL Open Font License; see the
`*_OFL.txt` files alongside them in [`fonts/`](fonts/). Paper titles, abstracts,
and other metadata are drawn from publicly available sources (OpenReview, ACL
Anthology, conference proceedings) and remain the property of their original
authors and venues; this project doesn't claim any rights over that content.
