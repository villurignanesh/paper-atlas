"""NeurIPS adapter (papers.nips.cc).

Structure, established by inspection:
  - One listing page per year gives every paper's title, authors, hash, and track.
    Track is explicit: <li class="conference"> vs <li class="datasets_and_benchmarks">,
    so main-track filtering needs no string heuristics (contrast 006).
  - Abstracts live only on the per-paper page, in <p class="paper-abstract">. That is
    one request per paper, roughly 22k for 2018-2025, so per-paper caching is what
    makes the crawl resumable rather than a single 2-hour all-or-nothing job.
"""

from __future__ import annotations

import html
import re
import time

import requests

from paper_atlas.cache import CacheKey, RawCache

BASE = "https://papers.nips.cc"
UA = "paper-atlas/0.1 (research literature map)"
# Track comes from `data-track`, NOT the class attribute. The class is inconsistent
# across years: absent in 2018-2021, "datasets_and_benchmarks" in 2023,
# "datasets_and_benchmarks_track" in 2024, while data-track is present throughout.
# 2018-2021 predate the D&B track entirely and carry data-track="none"; everything
# there is main track.
LISTING_RE = re.compile(
    r'<li[^>]*data-track="(?P<track>[a-z_]+)"[^>]*>.*?'
    r'href="(?P<href>/paper_files/paper/(?P<year>\d{4})/hash/(?P<hash>[0-9a-f]+)-Abstract[^"]*)"[^>]*>'
    r'(?P<title>.*?)</a>.*?<span class="paper-authors">(?P<authors>.*?)</span>',
    re.S)
MAIN_TRACKS = {"conference", "none"}      # "none" = pre-2022, before D&B existed
# Two HTML shapes coexist, even within the same year: confirmed by inspecting raw
# cached pages, not assumed:
#   nested:    <p class="paper-abstract"><p>TEXT</p> ... (page chrome incl. a leaked
#              "Name Change Policy" modal) ... </p></div>
#   unnested:  <p class="paper-abstract">TEXT</p></section>
# A single non-greedy `<p class="paper-abstract">(.*?)</p>\s*</div>` (the original)
# overshoots on the nested shape: it skips the inner </p> (whitespace before </div>
# doesn't immediately follow it) and matches the OUTER wrapper's much later </p></div>,
# swallowing the leaked modal along the way. That contamination was caught by c-TF-IDF
# surfacing "name" / "dropdown-menu" as top terms across unrelated clusters.
# Try nested first (stops at the inner </p>, skipping the modal); fall back to the
# first </p> when there is no nested tag.
ABSTRACT_RE_NESTED = re.compile(r'<p class="paper-abstract">\s*<p>(.*?)</p>', re.S)
ABSTRACT_RE_PLAIN = re.compile(r'<p class="paper-abstract">(.*?)</p>', re.S)


class _AbstractMatcher:
    def search(self, text):
        return ABSTRACT_RE_NESTED.search(text) or ABSTRACT_RE_PLAIN.search(text)


ABSTRACT_RE = _AbstractMatcher()


def _clean(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", s or "")).split())


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    return s


VOLUME_RE = re.compile(r'href="(/paper_files/paper/\d{4}/vol[^"]*main[^"]*)"')


def fetch_listing(year: int, cache: RawCache, s: requests.Session,
                  force: bool = False, path: str | None = None) -> bytes:
    part = "listing" if path is None else "listing-" + path.rstrip("/").rsplit("/", 1)[-1]
    key = CacheKey(source="nips", venue="neurips", year=year, ext="html", part=part)
    if cache.exists(key) and not force:
        page = cache.read(key)
    else:
        url = f"{BASE}{path}" if path else f"{BASE}/paper_files/paper/{year}"
        r = s.get(url, timeout=90)
        r.raise_for_status()
        page = r.content
        cache.write(key, page, meta={"url": url})
    # From 2025 the proceedings are split into volumes: the year page lists only side
    # tracks (creative AI etc.) plus a pointer to the main-conference volume. Follow it
    # when no MAIN_TRACK entries are present: checking "no entries at all" is not
    # enough, because the side-track entries do match.
    text = page.decode("utf-8", "replace")
    if path is None and not any(m["track"] in MAIN_TRACKS for m in LISTING_RE.finditer(text)):
        if m := VOLUME_RE.search(text):
            return fetch_listing(year, cache, s, force, path=m.group(1))
    return page


def parse_listing(page: bytes, main_only: bool = True) -> list[dict]:
    out = []
    for m in LISTING_RE.finditer(page.decode("utf-8", "replace")):
        if main_only and m["track"] not in MAIN_TRACKS:
            continue
        out.append({"hash": m["hash"], "href": m["href"], "year": int(m["year"]),
                    "track": m["track"], "title": _clean(m["title"]),
                    "authors": [a.strip() for a in _clean(m["authors"]).split(",") if a.strip()]})
    return out


def fetch_abstract(entry: dict, cache: RawCache, s: requests.Session,
                   delay: float = 0.3, force: bool = False) -> str | None:
    """One request per paper, cached by hash so a crash costs only the current page."""
    key = CacheKey(source="nips", venue="neurips", year=entry["year"], ext="html",
                   part=entry["hash"])
    if cache.exists(key) and not force:
        page = cache.read(key)
    else:
        r = s.get(f"{BASE}{entry['href']}", timeout=90)
        r.raise_for_status()
        page = r.content
        cache.write(key, page, meta={"url": f"{BASE}{entry['href']}", "hash": entry["hash"]})
        time.sleep(delay)
    m = ABSTRACT_RE.search(page.decode("utf-8", "replace"))
    return _clean(m.group(1)) if m else None
