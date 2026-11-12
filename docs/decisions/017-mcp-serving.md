# 017: Shared query core for MCP access (issue #3)

Date: 2026-11-11
Status: decided (serving architecture); tool and retrieval contracts open

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

## Still to decide

- Initial tools and result schema, including how evidence and provenance appear.
- Retrieval method: lexical, cluster-assisted, semantic, or a staged combination.
- How a user obtains and refreshes the local corpus snapshot.
- MCP SDK dependency and the eventual hosted transport/deployment details.

## What would make us revisit

- Local installation proves too cumbersome for the intended clients.
- Hosting and maintenance cost is low enough to make remote-first preferable.
- Full-text ingestion changes the evidence and index requirements materially.
