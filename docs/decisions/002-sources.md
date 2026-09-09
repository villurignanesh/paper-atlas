# 002: Data acquisition (one authority source per venue)

Date: 2026-08-27
Status: **accepted by non-objection: confirm before Phase 1 code**

## Context

Sources split into two kinds. *Authority* sources answer "what was accepted at venue V in
year Y, in which track" (per-venue proceedings, DBLP, OpenReview). *Enrichment* sources
answer "given this paper, what's its abstract / DOI / citations / precomputed embedding"
(Semantic Scholar, OpenAlex, arXiv). Enrichment sources cannot reliably separate main
track from workshops from arXiv preprints, so a corpus claiming "accepted main-track
papers" cannot be built from them alone, and the contamination is silent.

## Options considered

- **A. Single enrichment source** (query S2/OpenAlex by venue). Fastest; accepts unknown
  workshop/preprint contamination and no track separation.
- **B. DBLP spine + enrichment backfill.** One parser, uniform schema, correct tracks,
  scales to new venues nearly free. But DBLP has no abstracts, so the cross-source join
  becomes the centre of Phase 1.
- **C. Per-venue authority adapters.** Most correct, most work, most brittle year to year.
- **D. Hybrid by venue.** Pragmatic, least conceptually clean.

## Decision

Option C, four adapters:

| Venue | Source | Abstracts |
|---|---|---|
| ACL, EMNLP, NAACL | ACL Anthology XML | yes |
| ICLR | OpenReview | yes |
| ICML | PMLR volumes | yes |
| NeurIPS | papers.nips.cc | yes |

No enrichment layer in v1. Schema carries nullable `doi` / `arxiv_id` / `s2_corpus_id`.

Plus two additions:
- **DBLP as validator, not spine.** Diff per-venue-year paper counts against DBLP.
  Per-venue-year recall is the Phase 1 acceptance test: 54 rows, each explained.
- **OpenReview ICLR keywords + primary area pulled as an eval-only side channel**
  (see 003).

## Why

For this specific scope, all four authority sources already ship abstracts. That means
the enrichment join is not on the critical path at all: a materially different Phase 1
than the generic advice would suggest. Track separation comes free (Anthology volume IDs,
PMLR volume structure, nips.cc D&B split), which is what makes "main track only" an
enforceable claim rather than an aspiration.

One source per venue **for all years** is deliberate. PMLR over OpenReview for ICML and
nips.cc over OpenReview for NeurIPS both give up richer recent metadata to avoid mixing
sources within a venue across time; otherwise any temporal claim ("this topic grew") is
confounded with a change in source coverage.

Deferring Semantic Scholar also sidesteps its abstract-redistribution restrictions
entirely, which matters given 004's decision to display abstracts.

## Cost accepted

ICLR carries the OpenReview tax: API v1/v2 split, venue-string parsing for
accept/reject/withdrawn, blind-submission duplicates in early years. One venue's worth
of pain rather than four.

## Open / unverified

- PMLR-over-OpenReview for ICML is the weakest call here. It trades away author-supplied
  keywords, which are the best free evaluation signal available. Partly mitigated by
  pulling ICLR keywords separately, but ICML keywords stay lost.
- Whether ACL Anthology XML carries submission track (area): would be a significant free
  label source for the NLP half. Unverified; check in Phase 1.
- Exact OpenReview per-venue first-year coverage. Verify empirically, do not trust recall.

## What would make me revisit

- DBLP diff shows large unexplained gaps in a venue → reconsider that venue's source.
- Phase 6 starves for labels → pull arXiv primary categories, accepting the matching cost.
- Citation-based features become desirable → add S2 as a genuine enrichment layer.

---

## Resolved 2026-08-27: ACL Anthology carries NO track/area field

Inspected `2023.acl.xml` directly. Per-paper tag census across 911 long papers:
`author, title, pages, abstract, url, bibkey, doi, video, award, revision`.
Volume meta: `booktitle, editor, publisher, address, month, year, venue`.
There is no submission track or area anywhere in the XML. The open question from the
original entry is answered, negatively. Consequence recorded in 003.

Confirmed good: abstract coverage 100%, DOI coverage 100%, and track separation via
volume id works as assumed (`long` + `short` = 1,075 main-track papers for ACL 2023).

Two parsing hazards found, both silent:
- **Inline markup.** 40% of titles and 19% of abstracts contain child elements
  (`fixed-case`, `url`, `tex-math`, `i`, `b`). `elem.text` returns `None` on these.
  Adapters must use `''.join(elem.itertext())`.
- **Non-papers inside main volumes.** The ACL 2023 Program Chairs' Report sits in the
  `long` volume as a regular `<paper>`, distinguishable only by its roman-numeral page
  range. `<frontmatter>` is a sibling element and excluded for free; this is not.

Author source ids are present on only 38% of Anthology author elements.
