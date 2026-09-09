"""ACL Anthology adapter, fetch half (docs/decisions/006-anthology-map.md).

Pulls one XML collection per venue-year into the raw cache. Which volumes inside
a collection count as main track is config, not inference; see 006 for why.
"""

from __future__ import annotations

import time
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import requests

from paper_atlas.cache import CacheKey, RawCache

XML_BASE = "https://raw.githubusercontent.com/acl-org/acl-anthology/master/data/xml"
UA = "paper-atlas/0.1 (research literature map; contact via repo)"


@dataclass(frozen=True)
class CollectionSpec:
    venue: str
    year: int
    collection: str
    main_volumes: tuple[str, ...]
    expected: int
    note: str = ""

    @property
    def key(self) -> CacheKey:
        return CacheKey(source="anthology", venue=self.venue, year=self.year, ext="xml")

    @property
    def url(self) -> str:
        return f"{XML_BASE}/{self.collection}.xml"


def load_specs(path: Path | str = "config/anthology.toml") -> list[CollectionSpec]:
    raw = tomllib.loads(Path(path).read_text())
    return [
        CollectionSpec(
            venue=c["venue"], year=c["year"], collection=c["collection"],
            main_volumes=tuple(c["main_volumes"]), expected=c["expected"],
            note=c.get("note", ""),
        )
        for c in raw["collection"]
    ]


def _assert_right_document(spec: CollectionSpec, data: bytes) -> None:
    """Guard against caching the wrong resource.

    `2018.acl.xml` returns HTTP 200 with valid XML but is an *event stub* holding
    zero papers (006). A 200 is therefore not evidence that we fetched the right
    document, so confirm the declared main volumes are actually present before this
    enters the cache. This checks resource identity only: interpreting the content
    is the parser's job, and the bytes are still stored verbatim.
    """
    root = ET.fromstring(data)
    present = {v.get("id") for v in root.findall("volume")}
    missing = [v for v in spec.main_volumes if v not in present]
    if missing:
        raise ValueError(
            f"{spec.collection}.xml is missing main volumes {missing} "
            f"(found: {sorted(present) or 'none, likely an event stub'})"
        )


def fetch_one(spec: CollectionSpec, cache: RawCache, session: requests.Session,
              force: bool = False) -> bool:
    """Return True if a network fetch happened, False if the cache already had it."""
    if cache.exists(spec.key) and not force:
        return False
    resp = session.get(spec.url, timeout=60)
    resp.raise_for_status()          # a 404 is a config bug; never swallow it
    _assert_right_document(spec, resp.content)
    cache.write(spec.key, resp.content, meta={
        "url": spec.url, "collection": spec.collection,
        "main_volumes": list(spec.main_volumes), "expected": spec.expected,
    })
    return True


def fetch_all(specs: list[CollectionSpec], cache: RawCache, force: bool = False,
              delay: float = 0.5) -> dict[str, int]:
    session = requests.Session()
    session.headers["User-Agent"] = UA
    counts = {"fetched": 0, "cached": 0}
    for spec in specs:
        if fetch_one(spec, cache, session, force):
            counts["fetched"] += 1
            time.sleep(delay)        # 23 requests; be a polite guest
        else:
            counts["cached"] += 1
    return counts
