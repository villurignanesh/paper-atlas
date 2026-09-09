"""NeurIPS crawl + parse. Abstracts are one request per paper, so the crawl is separated
from the parse: the network step is resumable and idempotent, the parse step is local.
"""

from __future__ import annotations

import re
import threading
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from paper_atlas.adapters import neurips as N
from paper_atlas.cache import CacheKey, RawCache
from paper_atlas.schema import SCHEMA

PDF_RE = re.compile(r'href="(/paper_files/paper/\d{4}/file/[^"]+\.pdf)"')


def load_years(path: Path | str = "config/neurips.toml") -> list[tuple[int, int]]:
    raw = tomllib.loads(Path(path).read_text())
    return [(c["year"], c["expected"]) for c in raw["collection"]]


def crawl_year(year: int, cache: RawCache, s, delay: float = 0.0,
               workers: int = 4) -> dict:
    """Fetch every main-track abstract page for a year.

    Serial fetching measured ~1.6s per paper (latency-bound, not delay-bound), which
    is ~10h for the full corpus. Four workers against a static file server is a normal,
    polite crawl rate and brings it to a few hours. Each worker gets its own Session
    (requests.Session is not thread-safe); the cache makes re-runs free.
    """
    entries = N.parse_listing(N.fetch_listing(year, cache, s))
    todo = [e for e in entries
            if not cache.exists(CacheKey(source="nips", venue="neurips", year=year,
                                         ext="html", part=e["hash"]))]
    done, miss, lock = len(entries) - len(todo), 0, threading.Lock()
    local = threading.local()

    def one(e):
        nonlocal done, miss
        if not hasattr(local, "s"):
            local.s = N._session()
        try:
            N.fetch_abstract(e, cache, local.s, delay=delay)
            ok = True
        except Exception:
            ok = False
        with lock:
            if ok:
                done += 1
            else:
                miss += 1
            if (done + miss) % 250 == 0:
                print(f"    {year}: {done + miss}/{len(entries)}", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, todo))
    return {"year": year, "entries": len(entries), "fetched": done, "failed": miss}


def parse_year(year: int, cache: RawCache) -> list[dict]:
    rows = []
    for e in N.parse_listing(N.fetch_listing(year, cache, N._session())):
        key = CacheKey(source="nips", venue="neurips", year=year, ext="html", part=e["hash"])
        abstract, pdf = "", None
        if cache.exists(key):
            page = cache.read(key).decode("utf-8", "replace")
            m = N.ABSTRACT_RE.search(page)
            abstract = N._clean(m.group(1)) if m else ""
            if p := PDF_RE.search(page):
                pdf = f"{N.BASE}{p.group(1)}"
        rows.append({
            "paper_id": f"neurips:{year}:{e['hash']}", "source_id": e["hash"],
            "title": e["title"], "abstract": abstract,
            "authors": [{"name": a, "source_author_id": None} for a in e["authors"]],
            "venue": "neurips", "year": year, "track": "main", "length": None,
            "source": "nips", "source_url": f"{N.BASE}{e['href']}", "pdf_url": pdf,
            "doi": None, "arxiv_id": None, "s2_corpus_id": None,
            "keywords": None, "primary_area": None,
        })
    return rows


def parse_all(cache: RawCache, out_root: Path | str = "data/normalized") -> dict:
    out_root, rep = Path(out_root), {}
    for year, expected in load_years():
        rows = parse_year(year, cache)
        n_abs = sum(1 for r in rows if r["abstract"])
        p = out_root / "neurips" / f"{year}.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), p)
        rep[year] = {"n": len(rows), "expected": expected, "with_abstract": n_abs}
        print(f"  neurips {year}: n={len(rows):>5} expected={expected:>5} "
              f"abstracts={n_abs:>5} ({n_abs/max(len(rows),1):.1%})", flush=True)
    return rep
