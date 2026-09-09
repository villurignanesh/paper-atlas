# 008: Phase 2, embedding bake-off design

Date: 2026-08-27
Status: decided (models / input / metrics); `adapters` dependency pending approval

## The axis that matters

Not model size. What "similar" was trained to mean:

- **Citation-trained** (SPECTER / SPECTER2 / SciNCL): triplet loss where the positive is
  a *cited* paper. Learns "similar = likely to cite each other".
- **Semantics-trained** (bge / e5 / gte): contrastive on paraphrase, QA, NLI pairs.
  Learns "similar = means the same thing".

**The hypothesis this project must test:** citation-training encodes *community
structure*, not only topic. Two papers doing the same thing in communities that do not
cite each other land far apart. Since the charter's most interesting phase is detecting
that "a NeurIPS cluster and an EMNLP cluster are the same research thread", the
field-standard choice for scientific papers may be actively wrong here.

## Decisions

**Models:** bge-small-en-v1.5 (baseline, already computed) + SPECTER2 + one 7B
(gte-Qwen2-7B class). bge-large omitted: the size axis within general embedders is less
informative than the citation axis, and the 7B already covers scale.

**Input:** title + abstract, **all models truncated to 512 tokens.** bge and SPECTER2 cap
at 512 while a 7B handles 8k+, so uncapped comparison would confound embedding quality
with context length: a 7B win would be unattributable. ~3% of abstracts are clipped.

Keywords deliberately EXCLUDED from input despite being available. They exist for ICLR
only (22% of corpus), so including them would make ICLR papers cluster better for reasons
unrelated to the model, contaminating the venue comparison below. They remain
evaluation-only ground truth (003).

**Per-model formatting, content held constant.** SPECTER/SPECTER2 are trained on
`title [SEP] abstract`; bge on plain text. Feeding SPECTER a `". "` join is off-
distribution and would handicap it for reasons unrelated to citation-training. Same
content, model-native separators.

**Metrics:**
1. **Cluster purity against ICLR author keywords**: 15,857 human-labelled papers.
   Caveat: ICLR-only, so models are compared on a subset.
2. **Venue predictability**: logistic regression predicting venue from the embedding.
   A direct test of the hypothesis: if citation-training bakes in community structure,
   venue is more predictable from SPECTER2 vectors than from bge's. High venue
   predictability is a *warning sign* for cross-venue alignment, not a quality score.

Deferred: known-item retrieval (003's probe file does not exist yet); trustworthiness and
seed stability per model (worth running once the top two models are known).

## Dependency

`adapters` (AdapterHub), required to load SPECTER2's proximity adapter. `specter2_base`
alone is NOT SPECTER2; the adapter is what makes it a similarity model, and benchmarking
the bare base would misrepresent it.

## Compute

bge-small measured at 50/s on M2 MPS (70,861 papers in 1021s). SPECTER2 at 110M params
fits in 8 GB and can run locally. The 7B needs ~15.2 GB fp16 and **cannot** run on the
M2; it requires the A6000 box, which needs a human-opened SSH tunnel (docs/compute.md).

Storage per model: 109 MB (384d) / 218 MB (768d) / ~1 GB (3584d).

## What would make me revisit

- SPECTER2 shows both higher keyword purity AND higher venue predictability → the two
  metrics disagree and the choice becomes a genuine trade-off to reason about, not a
  ranking.
- The 7B wins by a wide margin → re-examine whether the 512 cap distorted the comparison.

---

## Results: bge-small vs SPECTER2

Measured 2026-09-04. Full corpus, 70,861 papers. Metrics as designed above.

| metric | bge-small-en-v1.5 | SPECTER2 (base+proximity) |
|---|---|---|
| dim | 384 | 768 |
| kNN keyword Jaccard lift | 19.55x | 17.83x |
| kNN "any shared keyword" | 29.0% (vs 1.9% random) | 26.5% (vs 1.9% random) |
| venue accuracy | 63.5% | 63.9% |
| venue macro F1 | 0.482 | 0.481 |

(majority-class baseline for venue: 30.8%)

## Reading it

**The citation-community hypothesis is not supported by these two numbers.** SPECTER2's
venue accuracy (63.9%) is statistically indistinguishable from bge-small's (63.5%),
well within noise for a 30k-sample logistic regression probe. If citation-training were
encoding community structure beyond topic, SPECTER2 should separate venues more sharply
than a model with no citation signal at all. It does not, on this measure.

**SPECTER2 is also not better on keyword agreement**: it is slightly *worse* (17.8x vs
19.6x lift, 26.5% vs 29.0% any-shared-keyword). That is the more surprising result: the
field-standard scientific-paper embedder underperforms a small general-purpose model on
the one piece of ground truth this project has.

Two competing readings, neither settled by this data alone:

1. SPECTER2's citation objective is measuring something real about scientific
   documents but that signal happens not to show up in ICLR author keywords: keywords
   are self-reported and coarse, and citation similarity may capture a kind of relatedness
   keywords don't.
2. bge-small's general contrastive training is simply a better fit for "papers that
   mean the same thing" on this specific task, and the citation-community concern in 008
   was well-motivated in theory but the base SPECTER2 encoder (110M, 2020-era pretraining)
   is not a strong enough model to show it.

Qwen3-Embedding-8B is the tiebreaker for reading (2): a much larger, much more recent
general embedder. If it clearly beats both on keyword agreement without inflating venue
accuracy, that favours "bigger/better general embedder" over "citation training matters."
If Qwen3 also lands near bge-small on venue accuracy, the community-structure concern
looks unfounded across the board, independent of scale.

## What would make me revisit this section

- Qwen3-8B results change the picture (see above).
- The keyword-agreement gap (bge > SPECTER2) turns out to be an artifact of using the
  base SPECTER2 encoder without a stronger adapter, rather than a real quality difference.
  Worth checking if `allenai/specter2` ships alternate adapters for different tasks.

---

## Results: three-way, decision made

Measured 2026-09-04. Full corpus, 70,861 papers, all three models.

| metric | bge-small-en-v1.5 | SPECTER2 (base+proximity) | Qwen3-Embedding-8B |
|---|---|---|---|
| dim | 384 | 768 | 4096 |
| kNN keyword Jaccard lift | 19.55x | 17.83x | **21.97x** |
| kNN "any shared keyword" | 29.0% | 26.5% | **32.4%** |
| venue accuracy | 63.5% | 63.9% | 66.2% |
| venue macro F1 | 0.482 | 0.481 | 0.504 |

(random keyword baseline: 1.9%; venue majority-class baseline: 30.8%)

## Decision: Qwen3-Embedding-8B

Wins cleanly on the metric that matters most (keyword agreement, the only ground truth
in the project) and does not show disproportionate venue separation for it: keyword
lift rose 12% over bge-small while venue accuracy rose only 4%, the opposite ratio from
what a "picking up superficial venue style" concern would predict.

**The citation-training hypothesis (008's original motivation) is not supported.**
SPECTER2 (the citation-trained model) showed no elevated venue predictability
relative to bge-small (63.9% vs 63.5%, within noise for a 30k-sample probe) and was
*worse* on keyword agreement. Venue predictability tracked with general embedding
quality (bigger, more recent, more capable model), not with whether the model saw a
citation objective. This reframes the axis that matters for this project: model
capability, not citation-vs-semantics training.

## Cost of the choice, going forward

4096-dim vectors for 70,861 papers is 1.17 GB and materially heavier for downstream
kNN/UMAP construction than 384-dim was on the 8 GB M2. Phase 3 (kNN-graph, projection)
should be evaluated for whether it needs to run on your-gpu-host rather than locally,
particularly the from-scratch kNN construction, which is O(n^2) before any
approximation is applied.

## What would make me revisit this

- Phase 3/4 prove genuinely impractical at 4096-dim on available hardware and a
  lower-dimensional model becomes the pragmatic choice.
- A cross-venue alignment result later suggests SPECTER2's citation signal would have
  helped despite this probe: keyword agreement is not the same thing as cross-venue
  thread identity, and 008 always flagged this metric as ICLR-only, a caveat worth
  remembering here.
