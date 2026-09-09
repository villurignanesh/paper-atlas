"""Layer 1 of the two-layer store (docs/decisions/004-storage.md).

Holds exactly what a source returned, byte for byte, so that changing the
normalised schema never means re-fetching. Deliberately ignorant of format:
it stores bytes plus a provenance sidecar and lets adapters decide what the
bytes mean.

Layout: data/raw/{source}/{venue}/{year}/{part}.{ext}

The `part` exists for paginated sources. OpenReview hands back a venue-year in
pages; caching per page means a failure on page 7 of 12 does not throw away the
first six.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class CacheKey:
    source: str
    venue: str
    year: int
    ext: str          # the source's native format ("json", "xml"), not ours
    part: str = "all"


class RawCache:
    def __init__(self, root: Path | str = "data/raw"):
        self.root = Path(root)

    def path(self, key: CacheKey) -> Path:
        return self.root / key.source / key.venue / str(key.year) / f"{key.part}.{key.ext}"

    def _meta_path(self, key: CacheKey) -> Path:
        p = self.path(key)
        return p.with_suffix(p.suffix + ".meta.json")

    def exists(self, key: CacheKey) -> bool:
        # Both files must be present. A crash between the data write and the
        # meta write therefore reads as absent rather than as a truncated hit,
        # which is the whole point of having a resumable cache.
        return self.path(key).exists() and self._meta_path(key).exists()

    def read(self, key: CacheKey) -> bytes:
        return self.path(key).read_bytes()

    def read_meta(self, key: CacheKey) -> dict:
        return json.loads(self._meta_path(key).read_text())

    def write(self, key: CacheKey, data: bytes, meta: dict | None = None) -> None:
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        full = {
            "source": key.source,
            "venue": key.venue,
            "year": key.year,
            "part": key.part,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "bytes": len(data),
            # Lets a later refetch detect that the source itself changed under us,
            # which is otherwise invisible and quietly poisons temporal claims.
            "sha256": hashlib.sha256(data).hexdigest(),
            **(meta or {}),
        }
        self._atomic_write(path, data)
        self._atomic_write(self._meta_path(key), json.dumps(full, indent=2).encode())

    def parts(self, source: str, venue: str, year: int) -> list[Path]:
        d = self.root / source / venue / str(year)
        if not d.is_dir():
            return []
        return sorted(p for p in d.iterdir() if not p.name.endswith(".meta.json"))

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)   # atomic on POSIX; no half-written file is ever visible
