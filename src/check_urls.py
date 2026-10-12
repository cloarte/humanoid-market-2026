"""Check that every source_url in data/ still answers. Not run in CI (network is flaky).

Usage:  python -m src.check_urls          prints one line per URL, exit 1 if any is unreachable

Many publishers answer 403 to scripts while serving readers normally, so refused requests are
retried once with a browser User-Agent; pages that still refuse are reported as `blocked`, not broken. Only 404/410,
DNS failures and timeouts count as failures.
"""

from __future__ import annotations

import csv
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect() -> dict[str, list[str]]:
    urls: dict[str, list[str]] = {}
    for path in sorted((ROOT / "data").glob("*.csv")):
        if path.name == "fx_rates.csv":
            continue
        with path.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                urls.setdefault(r["source_url"], []).append(path.stem)
    return urls


# Hosts that refuse, throttle or drop scripted requests but were read by hand (browser or a single
# direct request) on the given date. Re-check by hand and update the date when re-verifying.
MANUALLY_VERIFIED = {
    "pitchbook.com": "2026-10-12",
    "www.businesswire.com": "2026-10-12",
    "www.sec.gov": "2026-10-12",
    "forgeglobal.com": "2026-10-12",
    "push2his.eastmoney.com": "2026-10-12",
    "www.sz.gov.cn": "2026-10-12",
}

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def probe(url: str) -> tuple[str, str]:
    """Plain request first; if refused or timed out, retry once with a browser User-Agent."""
    code, final = _get(url, None)
    if code in ("401", "403", "429", "ERR"):
        code2, final2 = _get(url, BROWSER_UA)
        if code2.startswith(("2", "3")):
            return code2, final2 or "(needs browser UA)"
    return code, final


def _get(url: str, ua: str | None) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": ua} if ua else {})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            final = resp.geturl()
            return str(resp.status), "" if final == url else final
    except urllib.error.HTTPError as e:
        return str(e.code), ""
    except Exception as e:  # DNS, TLS, timeout
        return "ERR", type(e).__name__


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    urls = collect()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(zip(urls, pool.map(probe, urls), strict=True))
    failed = 0
    for url, (code, final) in sorted(results.items(), key=lambda kv: kv[1][0]):
        host = urllib.parse.urlsplit(url).hostname or ""
        if code.startswith(("2", "3")):
            verdict = "ok"
        elif host in MANUALLY_VERIFIED:
            verdict, final = "manual", f"(scripts refused; read by hand {MANUALLY_VERIFIED[host]})"
        elif code in ("401", "403", "429", "451"):
            verdict = "blocked"
        else:
            verdict = "FAIL"
        failed += verdict == "FAIL"
        tables = ",".join(sorted(set(urls[url])))
        print(f"{verdict:<8}{code:<5}{url}  [{tables}]" + (f"  -> {final}" if final else ""))
    print(f"\n{len(urls)} URLs, {failed} failing")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
