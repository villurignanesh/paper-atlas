"""Shared normalised-record schema (docs/decisions/005-schema.md).

`source_id` is the source's own canonical key: an Anthology id like `2023.acl-long.1`,
an OpenReview note id like `HJz6tiCqYm`. `paper_id` is `{venue}:{year}:{source_id}`.
The venue/year prefix is redundant for Anthology ids, which are already globally unique,
but OpenReview ids are not self-describing, so the composite keeps one format across
every source (005, Decision A).
"""

import pyarrow as pa

SCHEMA = pa.schema([
    ("paper_id", pa.string()), ("source_id", pa.string()),
    ("title", pa.string()), ("abstract", pa.string()),
    ("authors", pa.list_(pa.struct([("name", pa.string()), ("source_author_id", pa.string())]))),
    ("venue", pa.string()), ("year", pa.int32()),
    ("track", pa.string()), ("length", pa.string()),
    ("source", pa.string()), ("source_url", pa.string()), ("pdf_url", pa.string()),
    ("doi", pa.string()), ("arxiv_id", pa.string()), ("s2_corpus_id", pa.string()),
    ("keywords", pa.list_(pa.string())), ("primary_area", pa.string()),
])
