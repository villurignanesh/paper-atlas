# 005: Shared schema and paper identity

Date: 2026-08-27
Status: decided

## Core record

paper_id, title, abstract, authors, venue, year, track, source, source_url, pdf_url,
source_fetched_at; nullable enrichment placeholders doi / arxiv_id / s2_corpus_id;
nullable ICLR eval side-channel keywords / primary_area.

## Decision A: paper_id is a source-native composite key

Charter requires reproducibility from a seed and a config, so a fresh clone plus a full
run must produce identical IDs. That rules out sequential surrogates and UUIDs: the ID
must be a deterministic function of the data.

Two candidates remained:

- **Source-native composite key**: `iclr:2019:HJz6tiCqYm`, `acl:2023:2023.acl-long.1`.
- **Content hash**: SHA of normalised title + first author + year.

**Chosen: source-native composite key.**

Content hashing is source-independent, which is its one real advantage. But it makes the
ID mutate whenever the content does: a source fixing a title typo silently turns one
paper into a different paper, orphaning anything keyed to it. That is precisely the
failure a stable ID exists to prevent, and it is far harder to detect than the composite
key's failure mode. Switching a venue's source is rare, deliberate, and absorbable with
an alias table.

Secondary benefit: composite keys are debuggable. Paste one into a URL and find the paper.

## Decision B: authors as list<struct{name, source_author_id}>

Costs nothing extra now and captures something unreconstructable later without
re-parsing: OpenReview profile IDs and Anthology author IDs are real disambiguation keys,
and author name strings are not. No author-level features are planned for v1; this is a
free-now/expensive-later field.

## Decision C: separate venue_year manifest table

One row per venue-year: source, fetch timestamp, raw record count, normalised count,
DBLP count, computed recall, completeness flag. 54 rows.

Makes two things first-class rather than tribal knowledge. The DBLP recall check from 002
becomes an inspectable table rather than a script someone ran once. And 001's ragged-2026
problem gets an explicit representation, so the frontend can grey out incomplete
venue-years instead of silently misleading.

## What would make me revisit

- Author-level features arrive → promote authors to a normalised table.
- A venue's source has to change → add an alias table mapping old IDs to new, do not
  regenerate IDs in place.
