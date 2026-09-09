"""ICLR adapter, parse half (007).

api1 pages contain every submission including rejects, so acceptance comes from DBLP's
TOC by normalised title. api2 pages are already accept-only. The per-year match rate is
reported, not assumed: 007 validated 99.6-99.85% on two years, and a drop below that is
the signal that a year needs its own handling.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from paper_atlas.adapters.iclr import IclrYear, _key, load_years
from paper_atlas.cache import RawCache
from paper_atlas.dblp import accepted_index, normalise_title
from paper_atlas.schema import SCHEMA


def _val(content: dict, key: str):
    """api2 wraps every field as {"value": x}; api1 stores it bare."""
    v = content.get(key)
    return v.get("value") if isinstance(v, dict) else v


def _notes(y: IclrYear, cache: RawCache) -> list[dict]:
    out, page = [], 0
    while True:
        k = _key(y, page)
        if not cache.exists(k):
            break
        out += json.loads(cache.read(k))["notes"]
        page += 1
    return out


def _record(note: dict, year: int) -> dict:
    c = note["content"]
    nid = note["id"]
    names = _val(c, "authors") or []
    ids = _val(c, "authorids") or []
    return {
        "paper_id": f"iclr:{year}:{nid}", "source_id": nid,
        "title": " ".join(str(_val(c, "title") or "").split()),
        "abstract": " ".join(str(_val(c, "abstract") or "").split()),
        "authors": [{"name": n,
                     # OpenReview profile ids look like ~Jane_Doe1; raw emails appear for
                     # unregistered authors, so keep only the profile form.
                     "source_author_id": (ids[i] if i < len(ids) and str(ids[i]).startswith("~") else None)}
                    for i, n in enumerate(names)],
        "venue": "iclr", "year": year,
        "track": "main", "length": None,
        "source": "openreview",
        "source_url": f"https://openreview.net/forum?id={nid}",
        "pdf_url": f"https://openreview.net/pdf?id={nid}",
        "doi": None, "arxiv_id": None, "s2_corpus_id": None,
        "keywords": _val(c, "keywords") or None,
        "primary_area": _val(c, "primary_area"),
    }


def parse_year(y: IclrYear, cache: RawCache) -> tuple[list[dict], dict]:
    notes = _notes(y, cache)
    if y.api == "v2":
        rows = [_record(n, y.year) for n in notes]
        report = {"submissions": len(notes), "accepted": len(rows), "method": "venueid",
                  "expected": y.expected, "recall": None}
    else:
        idx = accepted_index("iclr", y.year)
        rows = [_record(n, y.year) for n in notes
                if normalise_title(_val(n["content"], "title")) in idx]
        report = {"submissions": len(notes), "accepted": len(rows), "method": "dblp",
                  "expected": y.expected,
                  "recall": round(len(rows) / y.expected, 4) if y.expected else None}
    return rows, report


def parse_all(cache: RawCache, out_root: Path | str = "data/normalized") -> dict:
    out_root, rep = Path(out_root), {}
    for y in load_years():
        rows, r = parse_year(y, cache)
        p = out_root / "iclr" / f"{y.year}.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), p)
        rep[y.year] = r
        print(f"  iclr {y.year} [{r['method']:<7}] subs={r['submissions']:>5} "
              f"accepted={r['accepted']:>5} expected={str(r['expected']):>5} "
              f"recall={r['recall']}", flush=True)
    return rep
