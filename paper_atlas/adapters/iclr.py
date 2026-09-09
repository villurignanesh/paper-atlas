"""ICLR adapter, fetch half (docs/decisions/007-iclr-acquisition.md).

Two paths. api1 years (2018-2023) return every submission including rejects, so the
accept filter is applied later from DBLP. api2 years (2024-2026) are already accept-only
because `content.venueid` excludes rejected papers.

Pages are cached individually: a failure on page 7 of 12 keeps the first six. The API
rate-limits, and refetching 2,000 rejected ICLR papers to recover from a timeout is
exactly the waste the cache exists to prevent.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from paper_atlas.cache import CacheKey, RawCache
from paper_atlas.openreview_auth import API1, API2, get_json, session

PAGE = 1000


@dataclass(frozen=True)
class IclrYear:
    year: int
    api: str                      # "v1" | "v2"
    expected: int | None = None
    note: str = ""

    @property
    def base(self) -> str:
        return API1 if self.api == "v1" else API2

    @property
    def query(self) -> dict:
        if self.api == "v1":
            return {"invitation": f"ICLR.cc/{self.year}/Conference/-/Blind_Submission"}
        return {"content.venueid": f"ICLR.cc/{self.year}/Conference"}


def load_years(path: Path | str = "config/iclr.toml") -> list[IclrYear]:
    raw = tomllib.loads(Path(path).read_text())
    return [IclrYear(year=c["year"], api=c["api"],
                     expected=c.get("expected"), note=c.get("note", ""))
            for c in raw["collection"]]


def _key(y: IclrYear, page: int) -> CacheKey:
    return CacheKey(source="openreview", venue="iclr", year=y.year, ext="json",
                    part=f"page{page:03d}")


def fetch_year(y: IclrYear, cache: RawCache, force: bool = False) -> dict:
    """Page through a year's notes into the cache. Returns counts."""
    s = session(y.base)
    page, total, fetched = 0, 0, 0
    while True:
        key = _key(y, page)
        if cache.exists(key) and not force:
            notes = json.loads(cache.read(key))["notes"]
        else:
            d = get_json(s, y.base, "/notes", limit=PAGE, offset=page * PAGE, **y.query)
            notes = d.get("notes", [])
            # Cache even an empty terminal page: it records that pagination ended here,
            # so a resumed run does not re-issue the request to rediscover the end.
            cache.write(key, json.dumps({"notes": notes}).encode(),
                        meta={"api": y.api, "offset": page * PAGE, "n": len(notes),
                              **{k: str(v) for k, v in y.query.items()}})
            fetched += 1
        total += len(notes)
        page += 1
        if len(notes) < PAGE:
            break
    return {"year": y.year, "api": y.api, "notes": total,
            "pages_fetched": fetched, "expected_accepted": y.expected}


def fetch_all(cache: RawCache, years: list[IclrYear] | None = None,
              force: bool = False) -> list[dict]:
    out = []
    for y in (years or load_years()):
        r = fetch_year(y, cache, force)
        print(f"  iclr {r['year']} ({r['api']}): {r['notes']:>5} notes  "
              f"({r['pages_fetched']} pages fetched)", flush=True)
        out.append(r)
    return out
