# Paper Atlas: a map of 70,861 AI papers

Six months ago I started a literature review and had no good way to see the shape
of the field. Google Scholar returns a ranked list. arXiv returns a stream of new
papers. Neither shows where the clusters are, which ones are growing, or where a
given paper sits relative to the rest of the field.

I built [Paper Atlas](https://villurignanesh.github.io/paper-atlas/) to answer
that question directly. It is an interactive map of every accepted paper from six
AI/ML venues, NeurIPS, ICML, ICLR, ACL, EMNLP, and NAACL, from 2018 through 2026.
The corpus is 70,861 papers. Each paper is embedded, projected to two dimensions,
clustered into a three-level topic hierarchy, and placed on one map you pan and
zoom like a piece of geography.

The site is free and static: no backend, no sign-up, no server costs at view
time. The code is [open source](https://github.com/villurignanesh/paper-atlas).

## Why not Paper Copilot

[Paper Copilot](https://papercopilot.com) already tracks this venue set well. It
reports submission counts, acceptance rates, and reviewer dynamics. What it does
not have is a semantic map: it shows how many papers a venue accepted, not what
those papers were about, or how that mix shifted over time.

[Jay Alammar's Illustrated NeurIPS 2025](https://newsletter.languagemodels.co/p/the-illustrated-neurips-2025-a-visual)
is closer to what I mean. It clusters and labels one conference's accepted papers
on an interactive map. Reading it helped convince me this was worth building at
full scale. Paper Atlas extends the same idea to six venues instead of one, eight
years instead of one, and a three-level hierarchy (902 fine-grained clusters, 44
mid-level topics, 8 top-level research areas) instead of a flat one. You can zoom
from the whole field down to a single narrow sub-problem without losing the
surrounding context.

## How it works

Title and abstract text for each paper goes through Qwen3-Embedding-8B, an
embedding model, to produce a vector. UMAP projects that vector to two dimensions
for display, and separately to ten dimensions for clustering. HDBSCAN clusters
the ten-dimensional vectors. An LLM names each cluster from its most distinctive
keywords and a sample of its titles.

Three of these choices are worth explaining, because the results were not what I
expected going in.

**Embedding model.** The standard choice for scientific papers is a
citation-trained model like SPECTER2, trained so that papers citing each other
sit close together in the embedding space. I compared SPECTER2 against a
general-purpose text embedder and against Qwen3-8B, scoring each against ICLR's
own author-supplied keywords, the one piece of independent ground truth in this
corpus. SPECTER2 scored worse on keyword agreement than the general-purpose
embedder. It also showed no advantage on a separate check for the opposite
failure mode: whether an embedding groups papers by venue instead of by topic. I
used Qwen3-8B for the full corpus.

**Hierarchy construction.** All three levels of the topic hierarchy come from the
same clustering, read at three resolutions of one density tree, not from three
independent clustering runs that could disagree with each other. I validated
that a fine-grained cluster sits inside the coarse cluster the map claims it
does. Nesting held at 97% to 100% across every resolution I tested.

**Seed stability.** Cluster assignment is not identical across random seeds. Two
HDBSCAN runs from different seeds agree at an adjusted Rand index of about 0.57.
Every non-trivial decision in the pipeline, including the ones that did not
work, is documented in the repo's
[decision log](https://github.com/villurignanesh/paper-atlas/tree/master/docs/decisions).

## What the map shows

Venue growth is uneven. ICLR accepted 336 papers in 2018 and 3,703 in 2025, an
11x increase. NeurIPS and ICML each grew about 5x over the same period. ACL,
EMNLP, and NAACL grew more slowly.

The NLP and LLMs research area held a stable share of the corpus: about 45% to
46% every year from 2018 to 2025. This area did not take over the corpus in the
last two years, contrary to what recent coverage of LLMs might suggest.

Optimization and Federated Learning moved the most. Its share of the corpus fell
from 15.5% in 2018 to 6.4% in 2025, a drop of 9.1 percentage points, the largest
single change on the map. Multimodal Understanding, 3D Generation, and Graph
Neural Networks and Molecular AI each roughly doubled or more than doubled their
share over the same period.

The [analytics page](https://villurignanesh.github.io/paper-atlas/analytics.html)
plots both trends directly, using the same clustering as the map.

## Using it

The [Browse page](https://villurignanesh.github.io/paper-atlas/table.html) is a
searchable, filterable table of every paper, for scanning rather than exploring
spatially. On the [main map](https://villurignanesh.github.io/paper-atlas/),
hover any point to see its authors, topic, and abstract; search to highlight
matches; use the histogram at the bottom to filter by year.

The project is open source. The
[contributing guide](https://github.com/villurignanesh/paper-atlas/blob/master/CONTRIBUTING.md)
and [open issues](https://github.com/villurignanesh/paper-atlas/issues) list the
current backlog: richer per-paper summaries, institution-level rankings,
submission and acceptance rate tracking, and a few harder problems scoped
honestly as such.

If you build something on the data, or find something in the map worth
reporting, I want to hear about it.
