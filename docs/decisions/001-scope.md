# 001: Scope (venues, years, inclusion)

Date: 2026-08-27
Status: decided

## Context

v1 needs a corpus boundary before any ingestion code exists. Three sub-decisions:
which venues, which years, and what counts as a paper. All three trade corpus size
and adapter effort against how interesting the cross-venue phase (Phase 8) can be.

## Options considered

**Venues.** ML core only (NeurIPS/ICML/ICLR): cheapest, but one community with heavy
overlap makes cross-venue alignment trivial and Phase 8 pointless. NLP only, cheapest
data path of all (one XML parser), but forecloses cross-venue work. Three communities
(+CVPR/ICCV): richest structure, but CVF scraping is per-year brittle and adds ~40%
corpus. ML core + NLP: two genuinely different vocabularies, and ACL Anthology is the
cheapest community to add.

**Years.** 2013→ (full ICLR era, best for topic evolution, worst adapter tail).
2020→ (comfortable OpenReview coverage, likely too short to see topics move).
2024→ (fast, matches existing hobby projects, useless for change over time).
2018→ (starts at the BERT inflection point).

**Inclusion.** Main only / +Findings +D&B / +workshops / +ICLR rejects.

## Decision

- **Venues:** NeurIPS, ICML, ICLR, ACL, EMNLP, NAACL
- **Years:** 2018 → present
- **Inclusion:** main track only

Estimated corpus ~60–75k papers (order of magnitude only; not verified).

## Why

Two communities is the minimum that keeps Phase 8 meaningful, and NLP is the cheapest
possible second community because ACL Anthology ships clean XML with abstracts and
explicit track separation. 2018 starts at BERT, capturing the pre-scaling → LLM-era
transition where topic movement should be most visible, while avoiding the pre-OpenReview
adapter pain of the early 2010s. Main-track-only is the cleanest defensible claim about
what the map represents; the schema carries a `track` field from day one so widening
later is a filter change, not a re-ingest.

## Known consequence: 2026 is ragged

As of 2026-08-27, ICLR/ICML/ACL/NAACL 2026 have happened; NeurIPS 2026 and EMNLP 2026
have not announced. The most recent year is structurally incomplete in a venue-dependent
way. Ingestion must record per-venue-year completeness and the frontend must not present
a partial year as if it were whole. A year filter on "2026" with half the venues missing
produces exactly the wrong visual conclusion.

## What would make me revisit

- Phase 8 turns out to be trivial anyway → add CV as a third community.
- Corpus turns out too small to produce interesting structure → add Findings and D&B.
- ~70k turns out to be painful on 8GB → cut years before cutting venues (venues are the
  point; years are depth).
