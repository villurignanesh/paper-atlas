"""venue_year manifest (005, Decision C). One row per venue-year.

Exists so two things are inspectable facts rather than tribal knowledge:
  - the DBLP recall check (002) is a table you can look at, not a script someone ran once
  - 001's ragged 2026 has an explicit representation, so the frontend can grey out
    incomplete venue-years instead of implying a partial year is whole

`complete` is False where the conference had not concluded (or proceedings were not
published) as of the ingestion date.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# Venue-years absent from the corpus by design, and why. Kept explicit so a missing
# partition is never silently read as "we failed to ingest it".
NOT_HELD = {
    ("naacl", 2020): "conference did not run",
    ("naacl", 2023): "conference did not run",
}
NOT_YET = {
    ("neurips", 2026): "conference is December 2026",
    ("emnlp", 2026): "conference is November 2026",
    ("naacl", 2026): "not published at ingestion",
    ("icml", 2026): "held July 2026; PMLR volume not published at ingestion",
}


def build(root: Path | str = "data/normalized",
          out: Path | str = "data/manifest.parquet") -> pa.Table:
    rows = []
    for f in sorted(Path(root).rglob("*.parquet")):
        t = pq.read_table(f, columns=["paper_id", "abstract", "keywords", "source"])
        venue, year = f.parent.name, int(f.stem)
        abstracts = t.column("abstract").to_pylist()
        rows.append({
            "venue": venue, "year": year, "n_papers": t.num_rows,
            "n_with_abstract": sum(1 for a in abstracts if a and a.strip()),
            "n_with_keywords": sum(1 for k in t.column("keywords").to_pylist() if k),
            "source": t.column("source").to_pylist()[0] if t.num_rows else None,
            "complete": True, "note": None,
        })
    have = {(r["venue"], r["year"]) for r in rows}
    for (v, y), why in {**NOT_HELD, **NOT_YET}.items():
        if (v, y) not in have:
            rows.append({"venue": v, "year": y, "n_papers": 0, "n_with_abstract": 0,
                         "n_with_keywords": 0, "source": None,
                         "complete": False, "note": why})
    rows.sort(key=lambda r: (r["venue"], r["year"]))
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, out)
    return table
