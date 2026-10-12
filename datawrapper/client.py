"""Minimal Datawrapper API client (https://developer.datawrapper.de/docs).

The token is read from the DATAWRAPPER_API_TOKEN environment variable or, if unset, from a
`.env` file at the repo root (git-ignored). It is never printed or written anywhere else.

Usage:  python -m datawrapper.client --check      confirm the token works
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.datawrapper.de/v3"
TOKEN_VAR = "DATAWRAPPER_API_TOKEN"


class DatawrapperError(RuntimeError):
    pass


def token() -> str:
    value = os.environ.get(TOKEN_VAR, "").strip()
    env_file = ROOT / ".env"
    if not value and env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():  # -sig: tolerate a Notepad BOM
            key, sep, val = line.partition("=")
            if sep and key.strip() == TOKEN_VAR:
                value = val.strip("'\" \t")
    value = "".join(value.split())  # tokens never contain whitespace; drop stray spaces from copy-paste
    if not value:
        raise DatawrapperError(f"No token: set {TOKEN_VAR} or add it to {env_file.name} (see .env.example)")
    return value


def request(method: str, path: str, body: dict | str | None = None) -> dict | None:
    """Call the API. Dict bodies are sent as JSON, string bodies as CSV (chart data)."""
    headers = {"Authorization": f"Bearer {token()}"}
    data = None
    if isinstance(body, dict):
        data, headers["Content-Type"] = json.dumps(body).encode("utf-8"), "application/json"
    elif isinstance(body, str):
        data, headers["Content-Type"] = body.encode("utf-8"), "text/csv"
    req = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise DatawrapperError(f"{method} {path} -> HTTP {e.code}: {detail}") from None
    return json.loads(raw) if raw.strip() else None


def download(path: str) -> bytes:
    """GET a binary resource (e.g. a PNG export of a chart)."""
    req = urllib.request.Request(f"{API}{path}", headers={"Authorization": f"Bearer {token()}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise DatawrapperError(f"GET {path} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None


def check() -> str:
    """Return a short description of the account the token belongs to."""
    me = request("GET", "/me") or {}
    charts = request("GET", "/charts?limit=1") or {}
    return f"token OK: account id {me.get('id')}, role {me.get('role')}, {charts.get('total', '?')} charts"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="confirm the token works")
    args = parser.parse_args()
    if not args.check:
        parser.print_help(sys.stderr)
        return 2
    try:
        print(check())
    except DatawrapperError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
