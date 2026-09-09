"""OpenReview authentication with an on-disk token cache.

Two facts drive this design, both learned the hard way:

1. OpenReview's public API now sits behind a bot challenge. Anonymous requests to
   either api.openreview.net or api2.openreview.net return ChallengeRequiredError,
   including through the official client. Authentication clears it.
2. **Login is rate-limited to 3 requests per window.** Logging in once per run is
   enough to lock yourself out during development, so the token is cached on disk
   and reused until it stops working.

Credentials come from .env (gitignored) and are never logged.
"""

from __future__ import annotations

import json
import os
import pathlib
import time

import requests

ENV_PATH = pathlib.Path(".env")
TOKEN_PATH = pathlib.Path(".or_token.json")
API1, API2 = "https://api.openreview.net", "https://api2.openreview.net"
UA = "paper-atlas/0.1 (research literature map)"


def load_env(path: pathlib.Path = ENV_PATH) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing - see docs; never commit it")
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _login(base: str) -> str:
    load_env()
    r = requests.post(f"{base}/login", json={
        "id": os.environ["OPENREVIEW_USERNAME"],
        "password": os.environ["OPENREVIEW_PASSWORD"],
    }, headers={"User-Agent": UA}, timeout=60)
    if r.status_code == 429:
        raise RuntimeError(
            "OpenReview login rate-limited (3/window). Wait, then reuse the cached "
            "token rather than logging in again."
        )
    r.raise_for_status()
    return r.json()["token"]


def get_token(base: str = API2, force: bool = False) -> str:
    """Return a bearer token, trusting the cache.

    Deliberately does NOT probe the token before use. An earlier version validated it
    with a test request and treated any failure as a dead token, so a single 429
    triggered a re-login, burning the 3-per-window budget and locking us out. The
    token is now trusted until a real request returns 401/403 (see `session`).
    """
    cache = json.loads(TOKEN_PATH.read_text()) if TOKEN_PATH.exists() else {}
    if not force and (tok := cache.get(base)):
        return tok
    tok = _login(base)
    cache[base] = tok
    TOKEN_PATH.write_text(json.dumps(cache))
    TOKEN_PATH.chmod(0o600)
    return tok


def session(base: str = API2) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {get_token(base)}", "User-Agent": UA})
    return s


def get_json(s: requests.Session, base: str, path: str, delay: float = 0.4, **params) -> dict:
    r = s.get(f"{base}{path}", params=params, timeout=60)
    if r.status_code == 429:                       # be a good guest, then retry once
        time.sleep(float(r.headers.get("Retry-After", 30)))
        r = s.get(f"{base}{path}", params=params, timeout=60)
    if r.status_code in (401, 403):                # only NOW is a re-login justified
        s.headers["Authorization"] = f"Bearer {get_token(base, force=True)}"
        r = s.get(f"{base}{path}", params=params, timeout=60)
    r.raise_for_status()
    time.sleep(delay)
    return r.json()
