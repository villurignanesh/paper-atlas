# 009: kNN-graph construction (exact, not approximate)

Date: 2026-09-04
Status: decided

## Context

Phase 3 (projection) needs a kNN graph as its input: this is what UMAP builds
internally before ever touching 2D layout. Charter requires a from-scratch
implementation of this step specifically so the machinery isn't a black box before
`umap.fit_transform` gets called on it.

Two implementations were built and measured against each other on the real corpus,
rather than assuming the textbook tradeoff (charter rule 6):

- **Brute-force**: exact cosine similarity via chunked matmul (V @ V.T), O(n^2).
- **NN-descent** (pynndescent, the same algorithm UMAP uses internally): approximate,
  starts from random neighbor guesses and iteratively refines via neighbors-of-neighbors,
  nominally O(n log n).

## Measured, on the full corpus (70,861 papers, Qwen3-Embedding-8B, 4096-dim, k=15)

    brute-force: 35.0s
    nn-descent:  34.1s   (1.0x speedup)
    neighbor-set agreement: 0.9462

## Decision

**Use exact brute-force kNN for this corpus size**, not the approximate method.

## Why

The textbook expectation was that NN-descent would be meaningfully faster. It was not:
at 70,861 points, one large BLAS-optimized matmul is cheap enough that the
approximate method's iterative overhead cancels out its algorithmic advantage entirely.
This is a fact about this problem size on this hardware, not a universal claim: at
millions of points the outcome would very likely flip. It is exactly the kind of gap
between expected and measured behaviour the charter flags as worth capturing.

Given no speed cost, exactness is free. NN-descent's ~5.4% neighbor disagreement
(1 - 0.9462) is the price of a shortcut that, here, buys nothing.

## What would make me revisit

- Corpus size grows an order of magnitude (annual refresh accumulating years, or scope
  widening to more venues): re-measure; brute-force's O(n^2) will eventually lose.
- Embedding dimensionality changes (a different Phase 2 model): the crossover point
  depends on both n and dimensionality, not n alone.
