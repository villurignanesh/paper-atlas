"""ICML adapter (PMLR). Volume listing gives titles/authors/links; abstracts are one
request per paper, same shape as NeurIPS.

PMLR abstracts contain raw LaTeX (`$k$`, `\\ldots`). That is left intact here: how to
handle maths in embedding input is a Phase 2 decision, and destroying it at ingest would
remove the option.
"""

from __future__ import annotations

import html
import re
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import requests

from paper_atlas.cache import CacheKey, RawCache
from paper_atlas.schema import SCHEMA

BASE = "https://proceedings.mlr.press"
UA = "paper-atlas/0.1 (research literature map)"
ENTRY_RE = re.compile(
    r'<div class="paper">\s*<p class="title">(?P<title>.*?)</p>.*?'
    r'<span class="authors">(?P<authors>.*?)</span>.*?'
    r'\[<a href="(?P<abs>[^"]+?)">abs</a>\]', re.S)
ABSTRACT_RE = re.compile(r'<div[^>]*id="abstract"[^>]*>(.*?)</div>', re.S)
PDF_RE = re.compile(r'href="([^"]+\.pdf)"')


@dataclass(frozen=True)
class IcmlYear:
    year: int
    volume: str
    expected: int


def load_years(path: Path | str = "config/icml.toml") -> list[IcmlYear]:
    raw = tomllib.loads(Path(path).read_text())
    return [IcmlYear(c["year"], c["volume"], c["expected"]) for c in raw["collection"]]


def _clean(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", s or "")).split())


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    return s


def fetch_listing(y: IcmlYear, cache: RawCache, s: requests.Session) -> bytes:
    key = CacheKey(source="pmlr", venue="icml", year=y.year, ext="html", part="listing")
    if cache.exists(key):
        return cache.read(key)
    url = f"{BASE}/{y.volume}/"
    r = s.get(url, timeout=120)
    r.raise_for_status()
    cache.write(key, r.content, meta={"url": url, "volume": y.volume})
    return r.content


def parse_listing(page: bytes) -> list[dict]:
    out = []
    for m in ENTRY_RE.finditer(page.decode("utf-8", "replace")):
        abs_url = m["abs"]
        slug = abs_url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".html")
        out.append({"slug": slug, "abs_url": abs_url,
                    "title": _clean(m["title"]),
                    "authors": [a.strip() for a in _clean(m["authors"]).split(",") if a.strip()]})
    return out


def _paper_key(y: IcmlYear, slug: str) -> CacheKey:
    return CacheKey(source="pmlr", venue="icml", year=y.year, ext="html", part=slug)


def crawl_year(y: IcmlYear, cache: RawCache, workers: int = 4) -> dict:
    entries = parse_listing(fetch_listing(y, cache, _session()))
    todo = [e for e in entries if not cache.exists(_paper_key(y, e["slug"]))]
    done, miss, lock, local = len(entries) - len(todo), 0, threading.Lock(), threading.local()

    def one(e):
        nonlocal done, miss
        if not hasattr(local, "s"):
            local.s = _session()
        try:
            r = local.s.get(e["abs_url"], timeout=120)
            r.raise_for_status()
            cache.write(_paper_key(y, e["slug"]), r.content, meta={"url": e["abs_url"]})
            ok = True
        except Exception:
            ok = False
        with lock:
            done, miss = (done + 1, miss) if ok else (done, miss + 1)
            if (done + miss) % 250 == 0:
                print(f"    icml {y.year}: {done + miss}/{len(entries)}", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, todo))
    return {"year": y.year, "entries": len(entries), "fetched": done, "failed": miss}


def parse_year(y: IcmlYear, cache: RawCache) -> list[dict]:
    rows = []
    for e in parse_listing(fetch_listing(y, cache, _session())):
        key = _paper_key(y, e["slug"])
        abstract, pdf = "", None
        if cache.exists(key):
            page = cache.read(key).decode("utf-8", "replace")
            if m := ABSTRACT_RE.search(page):
                abstract = _clean(m.group(1))
            if p := PDF_RE.search(page):
                pdf = p.group(1)
        rows.append({
            "paper_id": f"icml:{y.year}:{e['slug']}", "source_id": e["slug"],
            "title": e["title"], "abstract": abstract,
            "authors": [{"name": a, "source_author_id": None} for a in e["authors"]],
            "venue": "icml", "year": y.year, "track": "main", "length": None,
            "source": "pmlr", "source_url": e["abs_url"], "pdf_url": pdf,
            "doi": None, "arxiv_id": None, "s2_corpus_id": None,
            "keywords": None, "primary_area": None,
        })
    return rows


def parse_all(cache: RawCache, out_root: Path | str = "data/normalized") -> dict:
    out_root, rep = Path(out_root), {}
    for y in load_years():
        rows = parse_year(y, cache)
        n_abs = sum(1 for r in rows if r["abstract"])
        p = out_root / "icml" / f"{y.year}.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), p)
        rep[y.year] = {"n": len(rows), "expected": y.expected, "with_abstract": n_abs}
        print(f"  icml {y.year} ({y.volume}): n={len(rows):>5} expected={y.expected:>5} "
              f"abstracts={n_abs:>5} ({n_abs/max(len(rows),1):.1%})", flush=True)
    return rep
