#!/usr/bin/env python3
"""Validate required public documentation URLs and package metadata links."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Callable, Iterable
from urllib import error as urllib_error
from urllib import request as urllib_request


URLChecker = Callable[[str, float], tuple[bool, int, str]]


def load_project_urls(pyproject_path: str | Path) -> list[str]:
    """Read project URL values from pyproject metadata."""
    path = Path(pyproject_path)
    if not path.exists():
        return []

    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    project = payload.get("project", {})
    if not isinstance(project, dict):
        return []
    urls = project.get("urls", {})
    if not isinstance(urls, dict):
        return []
    return [str(value).strip() for value in urls.values() if str(value).strip()]


def load_required_urls(path: str | Path) -> list[str]:
    """Load newline-delimited URL list, ignoring comments/empty lines."""
    target = Path(path)
    if not target.exists():
        return []

    urls: list[str] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        token = line.strip()
        if not token or token.startswith("#"):
            continue
        urls.append(token)
    return urls


def _http_request(url: str, method: str, timeout: float) -> urllib_request.addinfourl:
    req = urllib_request.Request(url=url, method=method)
    return urllib_request.urlopen(req, timeout=timeout)  # noqa: S310


def default_checker(url: str, timeout: float) -> tuple[bool, int, str]:
    """Check URL reachability with HEAD fallback to GET."""
    methods = ("HEAD", "GET")
    last_status = 0
    last_reason = "no_response"

    for method in methods:
        try:
            with _http_request(url, method, timeout) as response:
                status = int(getattr(response, "status", 0) or 0)
                ok = 200 <= status < 400
                reason = "ok" if ok else f"http_{status}"
                return ok, status, reason
        except urllib_error.HTTPError as exc:
            last_status = int(getattr(exc, "code", 0) or 0)
            last_reason = f"http_{last_status}"
            if method == "HEAD" and last_status in (403, 405):
                continue
        except urllib_error.URLError as exc:
            last_reason = str(exc.reason)
            if method == "HEAD":
                continue
        except TimeoutError:
            last_reason = "timeout"
            if method == "HEAD":
                continue
        break

    return False, last_status, last_reason


def dedupe_urls(urls: Iterable[str]) -> list[str]:
    """Preserve order while dropping duplicates."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in urls:
        token = str(raw).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def evaluate_urls(
    urls: Iterable[str],
    *,
    timeout: float = 10.0,
    checker: URLChecker = default_checker,
) -> tuple[list[tuple[str, int, str]], list[tuple[str, int, str]]]:
    """Return (passes, failures) URL checks."""
    passes: list[tuple[str, int, str]] = []
    failures: list[tuple[str, int, str]] = []

    for url in dedupe_urls(urls):
        ok, status, reason = checker(url, timeout)
        row = (url, int(status), reason)
        if ok:
            passes.append(row)
        else:
            failures.append(row)
    return passes, failures


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument("--required", default="docs/required_public_links.txt")
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    urls = dedupe_urls(
        [
            *load_project_urls(args.pyproject),
            *load_required_urls(args.required),
        ]
    )
    if not urls:
        print("No public URLs found to check.")
        return 1

    passes, failures = evaluate_urls(urls, timeout=float(args.timeout))
    for url, status, reason in passes:
        print(f"PASS {status:>3} {url} ({reason})")
    for url, status, reason in failures:
        print(f"FAIL {status:>3} {url} ({reason})")

    print(f"Checked {len(urls)} URLs: {len(passes)} passed, {len(failures)} failed")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
