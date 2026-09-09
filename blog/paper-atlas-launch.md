# Paper Atlas: mapping 70,861 AI papers so you can actually see the field

Six months ago I needed to do a literature review and realized I had no good way to
see the shape of a field with tens of thousands of papers in it. Google Scholar gives
you a ranked list. arXiv gives you a firehose. Neither tells you where the clusters
are, which ones are growing, or where your own reading sits relative to everything
else.

So I built [Paper Atlas](https://villurignanesh.github.io/paper-atlas/): an
interactive semantic map of every accepted paper from six major AI/ML venues,
NeurIPS, ICML, ICLR, ACL, EMNLP, and NAACL, 2018 through 2026. 70,861 papers,
embedded, projected, clustered into a three-level topic hierarchy, and dropped onto
one map you can pan and zoom like a piece of geography.

It's free, it's a static site (no backend, nothing to sign up for), and the code is
[open source](https://github.com/villurignanesh/paper-atlas).

## Why not just use Paper Copilot

[Paper Copilot](https://papercopilot.com) already does something like this well; it
tracks submission stats, acceptance rates, and reviewer dynamics across the same kind
of venue set, and it's genuinely useful. What it doesn't have is a semantic map. You
can see *how many* papers a venue accepted, but not *what they were about* or how
that's shifted.

[Jay Alammar's Illustrated NeurIPS 2025](https://newsletter.languagemodels.co/p/the-illustrated-neurips-2025-a-visual)
is closer to what I mean, an interactive map of one conference's accepted papers,
clustered and labeled. It's a great piece of work, and it's part of what convinced me
this was worth building properly. Paper Atlas is the same idea taken further: six
venues instead of one, eight years instead of one, and a three-level topic hierarchy
(902 fine-grained clusters, 44 mid-level topics, 8 top-level research areas) instead
of a flat one, so you can zoom from "the whole field" down to "this one narrow
sub-problem" without losing context.

## How it actually works

The short version: title and abstract go through `Qwen3-Embedding-8B`, get projected
to 2D with UMAP for display and separately to 10D purely for clustering, get grouped
with HDBSCAN, and get named by an LLM reading each cluster's most distinctive
keywords and a sample of its titles.

The longer version is that almost every step in that pipeline was a measured decision,
not a default. A few examples, because I think the "how" is more interesting than the
one-line summary:

- **Citation-trained vs. semantics-trained embeddings.** The obvious choice for
  scientific papers is something like SPECTER2, trained on citation graphs. I ran a
  three-way bake-off (SPECTER2, a general embedder, and Qwen3-8B) against the one
  piece of independent ground truth in the corpus, ICLR's own author-supplied
  keywords, and the citation-trained model came in *worse* on keyword agreement than
  a general-purpose one, with no compensating advantage on the "does it separate
  venues too aggressively" check I ran to test the opposite failure mode. That result
  surprised me enough that it's its own writeup in the repo.
- **All three hierarchy levels come from the same clustering**, at three different
  resolutions of the same underlying density tree, not three independent runs that
  might disagree with each other. I validated the nesting (does every fine-grained
  cluster actually sit inside the coarse cluster the map says it does) at 97-100%
  across every resolution I tested, rather than assuming a coarser cut of the same
  tree would nest cleanly.
- **The clustering isn't perfectly stable across random seeds** (a measured ARI of
  about 0.57 between runs), and I'd rather say that plainly than pretend the map is
  more deterministic than it is. Every non-trivial choice like this is written up in
  the repo's [decision log](https://github.com/villurignanesh/paper-atlas/tree/master/docs/decisions),
  including the ones that didn't work.

## What the map actually shows

A few things I only noticed once the whole corpus was on one screen:

**ICLR grew 11x since 2018** (336 accepted papers to 3,703), by far the fastest of the
six venues. NeurIPS and ICML both grew about 5x over the same period; ACL, EMNLP, and
NAACL grew more slowly.

**"NLP and LLMs" has held a remarkably stable ~45% share of the whole corpus since
2018**, not the runaway takeover the last two years of hype might suggest. What
*did* move a lot: Optimization & Federated Learning dropped from 15.5% of the corpus
to 6.4% (the single biggest swing on the map), while Multimodal Understanding, 3D
Generation, and Graph Neural Networks & Molecular AI each roughly doubled or better
their share.

You can see both of those directly on the [analytics page](https://villurignanesh.github.io/paper-atlas/analytics.html),
which turns the same clustering into trend lines instead of a spatial map.

## What's next

The [Browse](https://villurignanesh.github.io/paper-atlas/table.html) page is a
searchable, filterable table of every paper if you'd rather scan than explore
spatially. The [main map](https://villurignanesh.github.io/paper-atlas/) is where the
clustering actually earns its keep, hover anything to see its authors, topic, and
abstract; search to highlight matches; the histogram at the bottom brushes by year.

It's open source, and the [contributing guide](https://github.com/villurignanesh/paper-atlas/blob/master/CONTRIBUTING.md)
and [open issues](https://github.com/villurignanesh/paper-atlas/issues) have a real
backlog: richer per-paper summaries, institution-level rankings, submission/acceptance
rate tracking, and a few things that are genuinely hard and honestly scoped as such,
not quick wins dressed up as easy.

If you build something on top of the data or find something interesting in the map
that I haven't, I'd like to hear about it.
