#!/usr/bin/env python3
"""Validate official integration index freshness and schema."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

URLChecker = Callable[[str, float], tuple[bool, int, str]]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ALLOWED_STATUS = {"active", "beta", "certified", "deprecated", "experimental"}
_ALLOWED_SURFACE = {"sdk", "cli", "examples", "contracts", "api", "docs"}
_REQUIRED_STAGE_KEYS = ("paper_p95_ms", "canary_p95_ms", "live_p95_ms")
_REQUIRED_STATUS_BY_STAGE = ("paper", "canary", "live")


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def load_integration_index(path: str | Path) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("integration index must be a JSON array")
    rows: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            raise ValueError("integration entries must be JSON objects")
        rows.append(dict(row))
    return rows


def _is_github_repo_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.lower() != "github.com":
        return False
    parts = [p for p in parsed.path.split("/") if p]
    return len(parts) >= 2


def _parse_date(value: str) -> date | None:
    token = str(value).strip()
    if not _DATE_RE.match(token):
        return None
    try:
        return date.fromisoformat(token)
    except ValueError:
        return None


def evaluate_integrations(
    rows: Iterable[dict[str, Any]],
    *,
    requirements: dict[str, Any] | None = None,
    max_age_days: int = 45,
    today: date | None = None,
    check_urls: bool = False,
    timeout: float = 10.0,
    checker: URLChecker | None = None,
) -> list[str]:
    rows = list(rows)
    errors: list[str] = []
    today = today or _utc_today()
    checker = checker or _default_url_checker
    requirements = dict(requirements or {})
    required_providers: set[str] = set()
    providers_cfg = requirements.get("providers", {})
    if isinstance(providers_cfg, dict):
        required_providers = {str(key).strip().lower() for key in providers_cfg if str(key).strip()}
    observed_providers: set[str] = set()

    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        prefix = f"entry[{idx}]"
        integration_id = str(row.get("id", "")).strip()
        provider = str(row.get("provider", "")).strip()
        repo_url = str(row.get("repo_url", "")).strip()
        owner = str(row.get("owner", "")).strip()
        status = str(row.get("status", "")).strip().lower()
        surface = str(row.get("surface", "")).strip().lower()
        last_reviewed = str(row.get("last_reviewed", "")).strip()

        if not integration_id:
            errors.append(f"{prefix}: missing id")
        elif integration_id in seen_ids:
            errors.append(f"{prefix}: duplicate id '{integration_id}'")
        else:
            seen_ids.add(integration_id)

        if not provider:
            errors.append(f"{prefix}: missing provider")
        else:
            observed_providers.add(provider.lower())
        if not owner:
            errors.append(f"{prefix}: missing owner")

        if not repo_url:
            errors.append(f"{prefix}: missing repo_url")
        elif not _is_github_repo_url(repo_url):
            errors.append(f"{prefix}: repo_url must target github repo: {repo_url}")
        elif repo_url in seen_urls:
            errors.append(f"{prefix}: duplicate repo_url '{repo_url}'")
        else:
            seen_urls.add(repo_url)

        if status not in _ALLOWED_STATUS:
            errors.append(
                f"{prefix}: invalid status '{status}' (allowed: {sorted(_ALLOWED_STATUS)})"
            )
        if surface not in _ALLOWED_SURFACE:
            errors.append(
                f"{prefix}: invalid surface '{surface}' (allowed: {sorted(_ALLOWED_SURFACE)})"
            )
        readiness = row.get("readiness", {})
        if not isinstance(readiness, dict):
            errors.append(f"{prefix}: missing readiness object")
            readiness = {}
        paper_ok = readiness.get("paper_ok")
        if not isinstance(paper_ok, bool):
            errors.append(f"{prefix}: readiness.paper_ok must be boolean")
        latency_budget = readiness.get("latency_budget")
        if not isinstance(latency_budget, dict):
            errors.append(f"{prefix}: readiness.latency_budget must be object")
            latency_budget = {}
        for key in _REQUIRED_STAGE_KEYS:
            value = latency_budget.get(key)
            if not isinstance(value, (int, float)) or float(value) <= 0:
                errors.append(f"{prefix}: readiness.latency_budget.{key} must be positive number")
        reliability_budget = readiness.get("reliability_budget")
        if not isinstance(reliability_budget, dict):
            errors.append(f"{prefix}: readiness.reliability_budget must be object")
            reliability_budget = {}
        uptime = reliability_budget.get("min_uptime_pct")
        incidents = reliability_budget.get("max_incidents_30d")
        if not isinstance(uptime, (int, float)) or float(uptime) <= 0 or float(uptime) > 100:
            errors.append(f"{prefix}: readiness.reliability_budget.min_uptime_pct must be in (0, 100]")
        if not isinstance(incidents, int) or incidents < 0:
            errors.append(f"{prefix}: readiness.reliability_budget.max_incidents_30d must be non-negative integer")
        incident_profile = readiness.get("incident_profile")
        if not isinstance(incident_profile, dict):
            errors.append(f"{prefix}: readiness.incident_profile must be object")

        reviewed_on = _parse_date(last_reviewed)
        if reviewed_on is None:
            errors.append(
                f"{prefix}: invalid last_reviewed '{last_reviewed}' (expected YYYY-MM-DD)"
            )
        else:
            age_days = (today - reviewed_on).days
            if age_days < 0:
                errors.append(f"{prefix}: last_reviewed is in the future ({last_reviewed})")
            elif age_days > int(max_age_days):
                errors.append(
                    f"{prefix}: stale last_reviewed ({last_reviewed}, {age_days} days old)"
                )

        if check_urls and repo_url:
            ok, status_code, reason = checker(repo_url, float(timeout))
            if not ok:
                errors.append(
                    f"{prefix}: repo_url check failed ({status_code}, {reason}) for {repo_url}"
                )

    missing_providers = sorted(required_providers - observed_providers)
    if missing_providers:
        errors.append(f"missing providers declared in requirements: {missing_providers}")

    return errors


def _default_url_checker(url: str, timeout: float) -> tuple[bool, int, str]:
    from tools.check_public_links import default_checker

    return default_checker(url, timeout)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index",
        default="config/integrations/official_integrations.json",
        help="Path to integration index JSON file.",
    )
    parser.add_argument(
        "--requirements",
        default="config/integrations/official_integration_requirements.json",
        help="Path to integration requirements JSON file.",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=45,
        help="Maximum allowed age in days for `last_reviewed` entries.",
    )
    parser.add_argument(
        "--check-urls",
        action="store_true",
        help="Also perform HTTP checks against repo URLs.",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    rows = load_integration_index(args.index)
    requirements_path = Path(args.requirements)
    requirements_payload: dict[str, Any] = {}
    if requirements_path.exists():
        loaded = json.loads(requirements_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            requirements_payload = loaded
    errors = evaluate_integrations(
        rows,
        requirements=requirements_payload,
        max_age_days=int(args.max_age_days),
        check_urls=bool(args.check_urls),
        timeout=float(args.timeout),
    )
    if errors:
        for item in errors:
            print(f"FAIL {item}")
        print(
            f"Checked {len(rows)} integration entries: {len(errors)} violations found."
        )
        return 2
    print(
        f"PASS integration index valid: {len(rows)} entries (max_age_days={int(args.max_age_days)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
