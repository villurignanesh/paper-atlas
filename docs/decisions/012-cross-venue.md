# 012: Cross-venue alignment (shared-space clustering as the detection mechanism)

Date: 2026-09-07
Status: decided

## Context

Charter's "interesting one": one shared embedding space vs per-venue spaces aligned
afterward, and how to detect that a NeurIPS cluster and an EMNLP cluster are the same
research thread.

## Decision (retroactively confirmed)

**One shared embedding space** was already the design from Phase 2: all six venues
embedded together with Qwen3-Embedding-8B, no per-venue spaces. This makes cross-venue
detection a natural consequence of clustering rather than a separate alignment step: if
two venues' papers on the same topic land in the same cluster, that IS the alignment
signal, measured directly from venue composition per cluster.

## Method

Cross-venue index per cluster: `2 * min(NLP_fraction, ML_fraction)`, where NLP =
{acl, emnlp, naacl}, ML = {neurips, icml, iclr}. 1.0 = perfect 50/50 split between the
two venue families; 0.0 = entirely one family.

## Result

    479 / 902 clusters (53%) venue-siloed (cross_index < 0.05)
    231 / 902 clusters (26%) substantially cross-venue (cross_index >= 0.3)

Top cross-venue clusters (near-perfect ML/NLP balance): Uncertainty Quantification in
LLMs, Code Generation with LLMs, Knowledge Editing in LLMs, Red-teaming for LLM Safety,
LLM-as-Judge Evaluation, Self-Verification and Reflection in LLMs.

Top venue-siloed clusters: EEG/BCI Representation Learning, Genome/DNA Sequence
Understanding (both ML-only), Multimodal Machine Translation, Biomedical Entity
Linking, Keyphrase Generation (all NLP-only).

## Reading

The siloed/mixed split is not noise: it lines up with what should be true of the
field. Topics requiring venue-specific infrastructure or community conventions (EEG
signal processing, MT-specific architectures) stay siloed; topics that are genuinely
LLM-era, community-agnostic concerns (safety, evaluation methodology, code generation)
span venues. This is falsifiable evidence for the cross-venue thesis this project was
scoped around, not an assumption.

## What would make me revisit

- A siloed cluster turns out siloed only because one venue's papers on that topic
  didn't survive Phase 1 ingestion, not because the field itself doesn't discuss it there.
- Cross-venue index doesn't distinguish "many small threads coincidentally in one
  cluster" from "one genuine shared thread": worth a qualitative spot-check pass if
  this becomes a claim used publicly.
