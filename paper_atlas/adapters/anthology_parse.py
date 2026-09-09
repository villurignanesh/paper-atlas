"""ACL Anthology adapter, parse half. Raw XML -> normalised records -> Parquet.

Traps handled here, all of which fail silently if you don't (see 002/006):
  - 40% of titles contain inline markup, where `.text` returns None. Use itertext.
  - Non-papers (chairs' reports) sit inside main volumes with roman-numeral pages.
  - Volume ids mean different things in different years; `length` comes from config
    order, never from parsing the booktitle.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from paper_atlas.adapters.anthology import CollectionSpec
from paper_atlas.cache import RawCache

from paper_atlas.schema import SCHEMA


def _text(elem) -> str:
    """Flatten inline markup. `elem.text` returns None on 40% of Anthology titles."""
    return " ".join("".join(elem.itertext()).split()) if elem is not None else ""


def _is_paper(paper) -> bool:
    """Chairs' reports and front matter carry roman-numeral page ranges."""
    pages = paper.find("pages")
    return pages is not None and (pages.text or "").strip()[:1].isdigit()


def _length_for(spec: CollectionSpec, vol_id: str) -> str | None:
    if vol_id in ("long", "short"):
        return vol_id
    if len(spec.main_volumes) == 2:            # config declares order: long, then short
        return ("long", "short")[spec.main_volumes.index(vol_id)]
    return None                                 # merged or undifferentiated main volume


def parse(spec: CollectionSpec, cache: RawCache) -> list[dict]:
    root = ET.fromstring(cache.read(spec.key))
    by_id = {v.get("id"): v for v in root.findall("volume")}
    rows: list[dict] = []
    for vol_id in spec.main_volumes:
        length = _length_for(spec, vol_id)
        for p in by_id[vol_id].findall("paper"):
            if not _is_paper(p):
                continue
            url = p.find("url")
            anth_id = url.text if url is not None else f"{spec.collection}-{p.get('id')}"
            rows.append({
                "paper_id": f"{spec.venue}:{spec.year}:{anth_id}",
                "source_id": anth_id,
                "title": _text(p.find("title")),
                "abstract": _text(p.find("abstract")),
                "authors": [
                    {"name": " ".join(x for x in (_text(a.find("first")), _text(a.find("last"))) if x),
                     "source_author_id": a.get("id")}
                    for a in p.findall("author")
                ],
                "venue": spec.venue, "year": spec.year,
                "track": "main", "length": length,
                "source": "anthology",
                "source_url": f"https://aclanthology.org/{anth_id}/",
                "pdf_url": f"https://aclanthology.org/{anth_id}.pdf",
                "doi": (d.text if (d := p.find("doi")) is not None else None),
                "arxiv_id": None, "s2_corpus_id": None,
                "keywords": None, "primary_area": None,
            })
    return rows


def parse_all(specs: list[CollectionSpec], cache: RawCache,
              out_root: Path | str = "data/normalized") -> dict:
    out_root, report = Path(out_root), {}
    for spec in specs:
        rows = parse(spec, cache)
        # `expected` is self-consistency only (006): it catches parser bugs and source
        # drift, not under-collection by the Anthology itself.
        drift = len(rows) - spec.expected
        out = out_root / spec.venue / f"{spec.year}.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), out)
        report[f"{spec.venue}:{spec.year}"] = {"n": len(rows), "drift": drift}
    return report
