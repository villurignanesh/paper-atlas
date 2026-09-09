# Future Work

Tasks below are scoped for someone who does **not** have the context of building this
project. Each includes what exists today, what "done" looks like, a suggested
approach, and open questions you'll need to resolve yourself. See `CONTRIBUTING.md`
for how this repo works (decision logs, the GPU/remote-job pattern, etc.) before
starting.

Difficulty is relative to this codebase, not absolute: "good first issue" assumes you've
read `docs/decisions/` for the phase you're touching.

**Long-term direction**: [papercopilot.com](https://papercopilot.com) is the closest
thing to a scale/scope reference for where this project could grow. It tracks
submission/acceptance statistics, reviewer score dynamics, and institution rankings
across a similarly-sized corpus (70,000+ papers, seven venues), live-updated. It does
**not** have a semantic content map, and that's this project's actual differentiator,
not something to give up chasing their feature set. Several tasks below explicitly work
toward closing the gap on their side without losing ours. Tasks 6-8 are the direct
Paper-Copilot-inspired additions; each needs data this project does not currently
collect, so read the "why this is hard" section before starting.

---

## 1. Automatic ingestion as new conferences release

**Difficulty:** Advanced. Touches most of the pipeline, and intersects an unsolved
problem (see below). Don't take this on as a first task.

**Current state.** Ingestion is entirely manual (`docs/decisions/005-schema.md`, Q5:
"re-run when we want"). Four per-venue adapters (`paper_atlas/adapters/`) each read a
config file (`config/*.toml`) that hardcodes venue-year to source mapping: which
PMLR volume is ICML 2024, which ACL Anthology collection ID is EMNLP 2023. Adding a new
year today means adding a row to the config, running the adapter, running the embedder
(`remote_jobs/embed_qwen3.py`, already incremental, only embeds new `paper_id`s), then
re-running the full projection/clustering/labeling chain.

**What "done" looks like.** At minimum: a scheduled job (GitHub Actions cron is
sufficient) that checks each source for new venue-years (a new PMLR volume, a new ACL
Anthology collection, a new NeurIPS proceedings year) and opens a PR adding the config
row when it finds one. Stretch goal: the PR also triggers ingestion + embedding
automatically. These two steps are structurally safe to automate; they're idempotent
and additive, per the two-layer cache design in `paper_atlas/cache.py`.

**What's genuinely hard, and why this isn't a bigger job than "hook up a cron":**
projection and clustering are **not incremental**. Every full refit reshuffles the
entire 2D layout and produces different cluster boundaries (`docs/decisions/011-clustering.md`
measured this precisely: ARI ≈0.57 between two runs on *identical* data, different seed
only). Adding one year's papers is likely to move *every* paper on the map, not just the
new ones. Automating re-labeling on top of that means labels silently changing meaning
underneath users who bookmarked a cluster. Don't attempt full end-to-end automation
without first reading 011 and deciding how to handle this. A reasonable scope-down is
automating ingestion + embedding only, and leaving projection/clustering/labeling as an
explicit manual step with a changelog.

**Paper Copilot comparison**: they run this live via cron jobs against a MySQL backend
(per their arXiv writeup, arxiv.org/abs/2510.13201), proof this is achievable at this
scale, not just a nice idea. Their architecture is a real backend (LAMP stack); this
project's static-site design means the automation target is narrower (ingest + embed,
not live serving), which is a smaller and more tractable version of the same problem.

**Where to start:** one adapter, one source freshness-check, opening a PR. Prove that
narrow slice before automating the rest.

---

## 2. Richer hover metadata: "explain it like I'm five"

**Difficulty:** Good first issue. Self-contained, reuses existing infrastructure.

**Current state.** Hovering a point shows title, venue/year, and a ~220-character
abstract snippet (`build_frontend.py`, the `snippet()` function and
`hover_text_html_template`). That's the raw academic abstract, truncated, not
simplified.

**What "done" looks like.** An additional line in the hover card: a one-sentence,
genuinely plain-language explanation of the paper, written at a level a non-expert (the
"explain to a 5 year old" framing) could follow. Not a truncation of the abstract, an
actual rewrite.

**Suggested approach.** You already have exactly the infrastructure this needs:
`remote_jobs/label_clusters.py` shows the pattern (OpenAI-compatible client to your GPU
box's Qwen server, one call per item, cached to JSON). Do the same per-paper instead of
per-cluster: one LLM call per paper generating the plain-language line, cached as
`data/knn/plain_summaries.json` keyed by `paper_id`, merged into `extra_point_data` in
`build_frontend.py` the same way `snippet` is today. At 70,861 papers this is the
expensive part: batch it, checkpoint it (see how `embed_qwen3.py` checkpoints every
500 batches so a crash doesn't lose progress), and expect it to take real wall-clock
time even on a fast local model.

**A free field you're not using yet:** ICLR submissions on OpenReview carry an
author-written `TL;DR` field (confirmed present in the raw fetched data, see
`paper_atlas/adapters/iclr_parse.py`, which currently does *not* capture it). For the
~16k ICLR papers, that's a free, human-written one-liner you could surface immediately
without any LLM call at all, before or alongside the generated summaries for other
venues. Cheap partial win, worth doing first.

**Open question for you to decide:** one unified "simple explanation" field, or show
the author's own TL;DR when available and fall back to a generated one otherwise? The
two will read differently (one is what the authors chose to emphasize, the other is
what a model thinks is simple), worth being honest about the distinction in whatever
label you put on the field.

---

## 3. Programmatic API access

**Difficulty:** Medium. Mostly an architecture decision, not hard engineering.

**Current state.** Pure static site: `index.html` is self-contained, no backend, no
API, by design (see the "GPU only needed to build the map, never to serve it"
reasoning in the project history). This was flagged as an open decision point in the
original project charter under "Serving": static tiles vs. a query backend.

**Two real options, not one obvious answer:**

- **Zero-infrastructure: publish the data, not an API.** The underlying
  `data/normalized/*.parquet` (per-venue-year, ~60MB total), the cluster assignments
  and labels (`data/knn/cluster_umap10d_mcs15_ms5.npz`, `cluster_labels.json`), and the
  2D coordinates are already clean, documented, columnar data. Publish them as GitHub
  Release assets or similar, and "the API" becomes "point DuckDB or pandas at this
  Parquet file." No server to run, no uptime to maintain, and it's arguably more useful
  to a researcher than a bespoke REST API would be. This is the option most consistent
  with how the rest of this project is built.
- **An actual REST API**, if programmatic *querying* (not just bulk download) is the
  real goal, e.g. "give me all papers within this cluster" or "search by embedding
  similarity" as an HTTP call. This needs a real host (the static site currently has
  none), and reintroduces the ops burden the static-site design deliberately avoided.
  FastAPI over the same Parquet files, deployed wherever, is the obvious shape. Paper
  Copilot exposes something similar via linked OpenReview APIs plus their own JSON
  exports on GitHub; worth looking at their export format as a reference before
  inventing your own.

**What "done" looks like:** depends entirely on which option. Decide first, document
the decision (see `CONTRIBUTING.md` on decision logs), then build.

---

## 4. Dashboard: accepted-paper trends by venue and year

**Difficulty:** Good first issue, **partially done.** `analytics.html` already covers
venue paper-count history and mega-category share-of-corpus trends 2018-2025 (see
`build_analytics_data.py`, `build_analytics_page.py`). Remaining scope below.

**What's left:** the mega-category trend chart currently pools all six venues together.
Splitting it by venue (e.g. "has NeurIPS's topic mix shifted differently than ACL's?")
is a natural extension using data already computed: no new clustering, just an
additional groupby dimension. Worth checking sample sizes hold up before committing to
a three-way cut (year × venue × mega-category) rather than assuming they do.

---

## 5. A proper analytics dashboard

**Difficulty:** Advanced, and deliberately open-ended. Treat this as a project, not a
single task. Break it into smaller PRs.

**Current state.** `analytics.html` covers two views (see task 4). A lot of additional
*content* already exists, scattered across `docs/eval/*.json` and `docs/decisions/*.md`.
It's just never been made interactive.

**Concrete ideas, roughly in order of how much new work they need:**

- **Ship the existing eval numbers as an interactive page**, not a static markdown
  table: trustworthiness, seed-stability ARI, cluster purity vs. ICLR keywords,
  the noise-baseline comparison. All the numbers exist in `docs/eval/`; this is
  presentation work, not new analysis.
- **Cross-venue index over time** (`docs/decisions/012-cross-venue.md` computed this as
  a single snapshot: 231/902 clusters "substantially cross-venue", and extending it to a
  time series shows whether the ML/NLP boundary is blurring or hardening year over
  year). Note: this was scoped and deliberately deferred during initial development.
  Early years have far fewer papers than recent ones (3,226 in 2018 vs 16,545 in 2025),
  so a per-cluster-per-year cut risks reading as a trend when it's actually a
  sample-size artifact. If you take this on, address that statistical concern directly
  (e.g. only compute it at the mega-category level, which has enough volume per year to
  trust, following the same reasoning `analytics.html`'s mega-category chart already
  uses) rather than the raw 902-cluster level.
- **Embedding-model comparison, made interactive**: the Phase 2 bake-off
  (`docs/decisions/008-embeddings.md`) compared three models on two metrics; if someone
  adds a fourth model later, this should be a page that updates, not a table someone
  edits by hand.

**Open question:** does this live as more static pages (consistent with the rest of the
site, no backend) or does "proper dashboard" imply something with live filtering/
querying that needs task #3's API decision resolved first? Worth deciding before
picking which sub-task to start with.

---

## 6. Institution and author rankings (Paper Copilot-inspired)

**Difficulty:** Advanced. Needs a schema change before any ranking work can start.

**Current state.** Author records are `list<struct{name, source_author_id}>` (see
`docs/decisions/005-schema.md`). **No affiliation field is captured at all**, from any
source. This is the actual blocker, not the ranking/display logic.

**What "done" looks like**, matching Paper Copilot's institution-hierarchy feature
(department → lab → institution → region, tracked over time): a browsable ranking of
institutions/authors by paper count, filterable by venue/year/topic.

**Why this is genuinely hard, not just a missing field:**

1. **Source coverage is uneven.** ACL Anthology XML sometimes includes `<affiliation>`
   per author (confirmed present in some records during Phase 1 development), but this
   was never systematically checked across all years, and OpenReview/PMLR/NeurIPS
   proceedings metadata may not carry it consistently or at all. Audit each source
   before assuming this is a uniform re-parse.
2. **Institution name normalization is a real, hard problem**, not a lookup table you
   write once. "MIT", "Massachusetts Institute of Technology", and "M.I.T." are the
   same entity; department-level affiliations ("MIT CSAIL" vs "MIT") complicate the
   department to institution rollup Paper Copilot's hierarchy implies. This is the part
   of the task that will actually take the time; budget for it accordingly.
3. Once affiliation data exists and is normalized, the ranking/display logic itself is
   comparatively easy: a groupby and a table, similar in spirit to `table.html`.

**Where to start:** an audit, not code. For each of the four adapters, determine
whether affiliation is available in the raw source data at all, and for how many years.
That answer determines whether this is a one-adapter task or a four-adapter one.

---

## 7. Submission-vs-acceptance rates (Paper Copilot-inspired)

**Difficulty:** Medium engineering, but gated on a real scope decision first. Read
`docs/decisions/001-scope.md` before starting.

**Current state.** This project deliberately ingests **accepted papers only**
(001-scope.md's "main track only" decision). We have no rejected-submission data for
five of six venues, and even for ICLR, the one venue where OpenReview technically
exposes rejected submissions, 007's design (`docs/decisions/007-iclr-acquisition.md`)
filters down to the DBLP-confirmed accept list, discarding rejects along the way.

**What "done" looks like**, matching Paper Copilot's acceptance-rate tracking: a
chart/table showing submissions, acceptances, and rate, per venue per year.

**Two paths, genuinely different in cost:**

- **Aggregate-only**: most venues publish a single reported number ("X submissions, Y
  accepted") in a press release, keynote slides, or an official post. No need to
  ingest individual rejected papers, just capture that one aggregate stat per
  venue-year. Cheap, but you're trusting self-reported numbers with no way to verify
  them independently.
- **Full submission records**: for ICLR specifically, OpenReview's rejected
  submissions are actually accessible (007 chose to filter them out, not that they're
  unavailable). Re-including them would let this venue support real submission-level
  analysis (e.g. score distributions of rejected vs. accepted), matching Paper Copilot's
  depth for at least one venue. This is a genuine scope expansion: more storage, a new
  `decision` field in the schema, and a re-audit of 007's whole DBLP-filtering approach,
  which was specifically designed around NOT keeping rejects.

**Open question for you to decide:** is aggregate-only acceptance-rate tracking enough,
or is the point of this task specifically to get ICLR's rejected-submission depth?
They're very different scopes wearing the same feature name. Decide which one you're
building before starting, and log the decision.

---

## 8. Review and rebuttal analytics (Paper Copilot-inspired)

**Difficulty:** Advanced, effectively a new project phase, not an addition to this one.
This is Paper Copilot's most distinctive feature and also their most data-intensive.

**Current state.** Nothing. This project has never ingested review threads, reviewer
scores, or rebuttal text, only final accepted-paper metadata (title, abstract, authors,
venue, year). This is a fundamentally different data source than anything currently in
`paper_atlas/adapters/`.

**What "done" looks like**, matching their score-footprint and rebuttal-dynamics
features: for OpenReview venues (ICLR, and NeurIPS/ICML for the years they're on
OpenReview, see `docs/decisions/002-sources.md` on per-venue-year OpenReview
coverage), pull the full review thread per paper: individual reviewer scores,
confidence, review text, rebuttal responses, and how scores changed over the discussion
period, not just the final decision.

**Why this is a new phase, not a task:**

1. **Different API surface.** Reviews live under different OpenReview invitations than
   the submission content this project currently fetches (`paper_atlas/adapters/iclr.py`
   / `iclr_parse.py` only ever requested submission notes, never review or rebuttal
   notes). This needs new fetch logic, not a parameter change to existing adapters.
2. **Needs timestamped snapshots, not a single fetch.** Paper Copilot's key
   differentiator, reconstructing how scores changed over the rebuttal period, requires
   capturing review state *over time*, which their architecture handles via scheduled
   re-fetches (per their arXiv paper). A one-time fetch after the fact only gets you the
   final state, missing the actual dynamics.
3. **Venue coverage is inherently partial.** This only works for venues on OpenReview
   with public reviews (ICLR is the strong case here); EMNLP/ACL (ARR-based),
   PMLR/ICML, and NeurIPS's non-OpenReview years have no equivalent public review data
   to pull at all. Any version of this feature will be ICLR-heavy by necessity, not a
   gap in the implementation.

**Where to start, if you take this on:** ICLR only, one recent year, a read-only
exploration of what OpenReview's review-note structure actually looks like (mirroring
how this project's own Phase 1 began with raw-XML inspection before writing any adapter
code, see the early `docs/decisions/002-sources.md` entries for that pattern). Don't
design the timestamped-snapshot architecture before you've seen one real review thread.
