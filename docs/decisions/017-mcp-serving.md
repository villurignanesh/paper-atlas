# 017: Shared query core for MCP access (issue #3)

Date: 2026-11-11
Status: decided (serving architecture, first tool set, local SDK); distribution in 018

## Context

Paper Atlas currently serves a static site. The 70,861 normalized paper records live
in local Parquet files, with stable paper IDs, titles, abstracts, source links, and
venue/year metadata. The intended next product is an MCP that coding IDEs and language
models can use for grounded literature review, similar in integration shape to
alphaXiv's MCP. This is programmatic query access, beyond issue #3's original choice
between publishing data files and hosting a REST API.

## Options considered

- **Local stdio MCP only:** no server operations, but every user installs and updates
  a local corpus; browser-hosted clients need a bridge.
- **Hosted HTTP MCP only:** simple client connection, but adds uptime, bandwidth,
  deployment, and potentially authentication work to a static-site project.
- **Shared query core with both transports (chosen):** separate corpus loading and
  evidence-returning queries from MCP transport. Ship local stdio first, then add
  hosted HTTP over the same contracts. More structure up front, but preserves the
  static site and avoids two independent retrieval implementations.

## Why

The local-first path lets the evidence contract be tested against the existing corpus
before taking on hosting. A shared core keeps the eventual remote endpoint from
silently ranking or citing papers differently. The website remains static; the MCP
is a separate access path.

The current records support grounding in metadata and abstracts, with source URLs.
They do not contain extracted full-paper text or page locations. The first MCP must
label that limit plainly and must not present abstract-based evidence as PDF-level
verification. PDF reading and page citations are separate future work.

## First tool set (chosen 2026-11-12)

The maintainer chose search, paper details, and cluster-based related papers over
search/details alone or blocking the MCP on full-PDF extraction. Search starts with
lexical matches against the existing metadata and abstracts; it is not query-embedding
semantic search. Related papers share an existing leaf cluster, with that relationship
stated in the result. It does not imply citation, agreement, or direct support.

The shared query core was implemented first using existing dependencies. On
2026-11-12 the maintainer approved `mcp>=2,<3` for the local stdio adapter. The
official Python SDK is used for protocol handling, schema validation, structured
results, and recoverable tool errors; query behavior remains in the shared core.

## Still to decide

- Exact result schema, ranking, and query limits after measuring the first core.
- Eventual hosted transport/deployment details.

## What would make us revisit

- Local installation proves too cumbersome for the intended clients.
- Hosting and maintenance cost is low enough to make remote-first preferable.
- Full-text ingestion changes the evidence and index requirements materially.
