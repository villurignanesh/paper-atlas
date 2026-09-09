"""DBLP client. Accept-list authority and recall validator, never a content source.

DBLP has no abstracts (002), but it has the cleanest accept lists in CS and models
conference tracks correctly.

**Uses the static per-volume XML, not the search API.** The search API is paginated,
silently caps results below the requested `h`, rate-limits aggressively, and eventually
resets connections outright: all hit during development. The static endpoint returns a
whole TOC in one request, gives an exact count, and separates the proceedings
front-matter row into its own <proceedings> element, so no title heuristic is needed to
exclude it.

Titles still need `itertext()`: DBLP marks up sub/sup inline and `.text` truncates them,
the same trap as the ACL Anthology (002).
"""

from __future__ import annotations

import html
import re
import time
import unicodedata
import xml.etree.ElementTree as ET

import requests

from paper_atlas.cache import CacheKey, RawCache

TOC_XML = "https://dblp.org/db/conf/{conf}/{conf}{year}.xml"
UA = "paper-atlas/0.1 (research literature map)"
POLITE_DELAY = 2.0


def normalise_title(t: str) -> str:
    """Aggressive normalisation for cross-source title matching.

    Unescapes twice: DBLP double-escapes some entities, so a single pass leaves
    `&apos;` as the literal text "apos" and manufactures false mismatches.
    """
    t = html.unescape(html.unescape(t or ""))
    t = unicodedata.normalize("NFKD", t).lower().replace("’", "'")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def toc_titles(conf: str, year: int, cache: RawCache | None = None,
               stem: str | None = None) -> list[str]:
    """Titles of every paper in a DBLP proceedings TOC.

    Front matter is excluded structurally: it is a <proceedings> element, papers are
    <inproceedings>.
    """
    cache = cache or RawCache("data/raw")
    stem = stem or conf
    key = CacheKey(source="dblp", venue=stem, year=year, ext="xml")
    if cache.exists(key):
        data = cache.read(key)
    else:
        url = f"https://dblp.org/db/conf/{conf}/{stem}{year}.xml"
        s = requests.Session()
        s.headers["User-Agent"] = UA
        data = None
        for attempt in range(4):
            try:
                r = s.get(url, timeout=90)
            except requests.ConnectionError:
                time.sleep(POLITE_DELAY * 2 ** attempt)
                continue
            if r.status_code == 404:
                return []                       # venue did not run that year
            if r.status_code == 429 or r.status_code >= 500:
                # DBLP throttles with BOTH 429 and 503; treat any 5xx as backpressure
                # rather than a hard failure, since it is the same underlying signal.
                time.sleep(float(r.headers.get("Retry-After", 5 * 2 ** attempt)))
                continue
            r.raise_for_status()
            data = r.content
            break
        if data is None:
            raise RuntimeError(f"DBLP unreachable after retries: {url}")
        cache.write(key, data, meta={"url": url, "conf": conf})
        time.sleep(POLITE_DELAY)

    root = ET.fromstring(data)
    out = []
    for p in root.findall(".//inproceedings"):
        t = p.find("title")
        if t is not None:
            out.append(" ".join("".join(t.itertext()).split()).rstrip("."))
    return out


def accepted_index(conf: str, year: int, cache: RawCache | None = None,
                   stem: str | None = None) -> set[str]:
    """Normalised titles of everything DBLP lists as published at conf/year."""
    return {normalise_title(t) for t in toc_titles(conf, year, cache, stem)}
