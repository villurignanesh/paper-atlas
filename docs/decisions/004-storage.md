# 004: Storage (two-layer cache, Parquet partitioned by venue-year)

Date: 2026-08-27
Status: decided

## Context

Charter non-negotiable #1: every expensive step is cached and resumable; never re-embed
or re-fetch because a downstream step crashed. The biggest actual risk in Phase 1 is
designing the shared schema wrong across four heterogeneous sources, which is close to
certain, since OpenReview's 2019 records can't be anticipated before seeing them.

## Decision A: two layers, not one

**Layer 1: raw cache.** Whatever the source returned, verbatim, in the source's native
format. OpenReview JSON as JSON, Anthology XML as XML. Never parsed, never cleaned,
never overwritten. Keyed by source + venue + year.

**Layer 2: normalised records.** The shared schema, derived from layer 1 by a pure
function.

This makes schema mistakes cheap: fixing the schema re-runs a parser over local files
instead of re-fetching 70k papers and hoping the APIs still behave. It also isolates the
network-dependent, rate-limited step so it happens exactly once and is never invalidated
by anything downstream. Cost is a few hundred MB of disk. Irrelevant.

## Decision B: layer 2 format

Options: SQLite (stdlib, queryable, row-oriented, natural upserts); Parquet partitioned
by venue-year (columnar, compact, resumability from partitioning, direct path to
DuckDB-WASM); JSONL (trivial, git-diffable, degrades past ~70k rows).

**Chosen: Parquet, one file per venue-year** (`data/normalized/{venue}/{year}.parquet`).

Why: the partition is the natural unit of work, of caching, and of the DBLP recall check
; a partition either exists and is complete or it doesn't, so there is no partial-write
state to reason about. Re-running one venue-year rewrites exactly one file. Parquet's
immutability is the wanted property here, not a drawback.

The usual counter-argument for SQLite is "I want to query during development." It doesn't
apply: DuckDB reads Parquet directly with full SQL, so query ergonomics come for free
without making SQLite the storage engine.

## Dependency added

`pyarrow` (or `polars`, which bundles Arrow): Parquet I/O and the columnar in-memory
format every later phase reads from. `duckdb` deferred until SQL over the files is
actually wanted.

## Dedup / canonicalisation

Largely a non-issue at this scope, deliberately. Main-track-accepted-only means a paper
cannot appear at two of the six venues, and with no enrichment layer there are no
preprint/published duplicate pairs. The one real case is **OpenReview blind vs non-blind
submission pairs in early ICLR years**, an ICLR adapter concern, not a global dedup
strategy. Revisit if an enrichment layer is ever added.

## Sequencing

Phase 1 starts as a thin vertical slice: one year of ACL and one year of ICLR (~1,500
papers) before generalising. Deliberately hits the friendliest and the most hostile source
at once, so the shared schema is stress-tested against both before it hardens.

## What would make me revisit

- Partition rewrites become slow enough to notice (they won't at this scale).
- An enrichment layer arrives and row-level upserts start to matter → reconsider SQLite
  or DuckDB as storage of record.
