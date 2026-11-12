# 018: Versioned corpus releases for the local MCP

Date: 2026-11-12
Status: decided

## Context

The local stdio MCP needs normalized paper metadata, leaf-cluster assignments, and
labels. Before this decision, every user had to reproduce the full ingestion and
clustering pipeline to use it. The required artifacts are about 70 MB uncompressed.

## Options considered

- **Versioned GitHub Release download (chosen):** publish a compact, immutable
  snapshot with a manifest and checksums. Users can start the MCP without rerunning
  the pipeline, while the server remains local and requires no uptime budget.
- **Rebuild instructions only:** no data hosting, but costly and impractical for
  most IDE users.
- **Hosted HTTP MCP now:** simplest connection, but adds hosting and operations
  before local use has been evaluated.

## Why and how

The maintainer chose the release snapshot. `corpus-v1` contains only the 48
normalized Parquet files and the two cluster files the query core reads. The
builder validates paper/cluster ID consistency, writes per-file SHA-256 hashes in
`manifest.json`, and publishes an archive SHA-256 sidecar. Archive ordering and
timestamps are fixed so the same inputs reproduce the same bytes. The release
stays separate from the source repository; `data/` remains gitignored.

## What would make us revisit

- Frequent corpus refreshes make manual downloads cumbersome.
- Hosted use becomes a clear requirement for clients that cannot run local stdio.
- The corpus grows enough that a full download is no longer practical.
