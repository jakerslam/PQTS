#!/usr/bin/env python3
"""Validate release-readiness gates across beta proof, integrations, and benchmark truth."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_RELEASE_WINDOW_RE = re.compile(
    r"^\s*[-*]?\s*`?release_window\s*:\s*([0-9]{4}-[0-9]{2})`?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

_STATUS_SCORE = {
    "experimental": 0,
    "beta": 1,
    "active": 2,
    "certified": 3,
    "deprecated": -1,
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_release_window(user_research_text: str) -> str:
    match = _RELEASE_WINDOW_RE.search(user_research_text)
    return str(match.group(1)).strip() if match else ""


def _status_at_least(actual: str, minimum: str) -> bool:
    actual_score = _STATUS_SCORE.get(str(actual).strip().lower(), -99)
    min_score = _STATUS_SCORE.get(str(minimum).strip().lower(), -99)
    return actual_score >= min_score


def _evaluate_external_beta(policy: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    registry_path = Path(str(policy.get("registry", "")))
    user_research_path = Path(str(policy.get("user_research", "")))
    payload = _load_json(registry_path)
    if not isinstance(payload, dict):
        errors.append(f"external_beta registry must be JSON object: {registry_path}")
        return {}
    cohorts = payload.get("cohorts", [])
    if not isinstance(cohorts, list):
        errors.append("external_beta registry `cohorts` must be an array")
        return {}
    user_research = _read_text(user_research_path)
    release_window = _extract_release_window(user_research)
    if not release_window:
        errors.append("external_beta: missing release_window in user research document")
        return {}

    required_statuses = {str(token).strip().lower() for token in list(policy.get("required_statuses") or []) if str(token).strip()}
    require_current_window = bool(policy.get("require_current_release_window", True))
    min_beginner = int(policy.get("min_external_beginner_participants", 0) or 0)
    min_pro = int(policy.get("min_external_pro_participants", 0) or 0)

    current_row: dict[str, Any] | None = None
    for row in cohorts:
        if not isinstance(row, dict):
            continue
        if str(row.get("release_window", "")).strip() == release_window:
            current_row = row
            break

    if current_row is None:
        if require_current_window:
            errors.append(f"external_beta: missing cohort row for current release_window={release_window}")
        return {"release_window": release_window, "cohort_found": False}

    status = str(current_row.get("status", "")).strip().lower()
    beginner = int(current_row.get("external_beginner_participants", 0) or 0)
    pro = int(current_row.get("external_pro_participants", 0) or 0)
    if required_statuses and status not in required_statuses:
        errors.append(
            "external_beta: cohort status gate failed "
            f"(release_window={release_window}, status={status}, allowed={sorted(required_statuses)})"
        )
    if beginner < min_beginner:
        errors.append(
            "external_beta: beginner participant gate failed "
            f"(actual={beginner}, required={min_beginner})"
        )
    if pro < min_pro:
        errors.append(
            "external_beta: professional participant gate failed "
            f"(actual={pro}, required={min_pro})"
        )
    return {
        "release_window": release_window,
        "cohort_found": True,
        "status": status,
        "external_beginner_participants": beginner,
        "external_pro_participants": pro,
    }


def _evaluate_integrations(policy: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    index_path = Path(str(policy.get("index", "")))
    report_path = Path(str(policy.get("certification_report", "")))
    requirements_path = Path(str(policy.get("requirements", "")))
    required_venues = [str(token).strip().lower() for token in list(policy.get("required_venues") or []) if str(token).strip()]
    required_market_classes = {str(token).strip().lower() for token in list(policy.get("required_market_classes") or []) if str(token).strip()}
    min_status = str(policy.get("min_status", "beta")).strip().lower()
    required_stage = str(policy.get("required_stage", "paper")).strip().lower()

    index_payload = _load_json(index_path)
    if not isinstance(index_payload, list):
        errors.append(f"integrations index must be JSON array: {index_path}")
        return {}
    rows = [row for row in index_payload if isinstance(row, dict)]
    by_provider: dict[str, dict[str, Any]] = {}
    market_classes: set[str] = set()
    for row in rows:
        provider = str(row.get("provider", "")).strip().lower()
        if provider:
            by_provider[provider] = row
        for token in list(row.get("market_classes") or []):
            value = str(token).strip().lower()
            if value:
                market_classes.add(value)

    missing_classes = sorted(required_market_classes - market_classes)
    if missing_classes:
        errors.append(f"integrations: missing required market classes: {missing_classes}")

    for venue in required_venues:
        row = by_provider.get(venue)
        if row is None:
            errors.append(f"integrations: missing required venue in index: {venue}")
            continue
        status = str(row.get("status", "")).strip().lower()
        if not _status_at_least(status, min_status):
            errors.append(
                "integrations: venue maturity gate failed "
                f"(venue={venue}, status={status}, required_min={min_status})"
            )
        readiness = row.get("readiness", {})
        if not isinstance(readiness, dict):
            errors.append(f"integrations: readiness object missing for venue={venue}")
            continue
        if not isinstance(readiness.get("paper_ok"), bool):
            errors.append(f"integrations: readiness.paper_ok missing/invalid for venue={venue}")
        latency_budget = readiness.get("latency_budget")
        if not isinstance(latency_budget, dict):
            errors.append(f"integrations: readiness.latency_budget missing for venue={venue}")
        reliability_budget = readiness.get("reliability_budget")
        if not isinstance(reliability_budget, dict):
            errors.append(f"integrations: readiness.reliability_budget missing for venue={venue}")
        incident_profile = readiness.get("incident_profile")
        if not isinstance(incident_profile, dict):
            errors.append(f"integrations: readiness.incident_profile missing for venue={venue}")
        if required_stage == "paper" and not bool(readiness.get("paper_ok", False)):
            errors.append(f"integrations: readiness.paper_ok gate failed for venue={venue}")

    requirements_payload: dict[str, Any] = {}
    provider_requirements: dict[str, Any] = {}
    defaults: dict[str, Any] = {}
    if requirements_path.exists():
        loaded = _load_json(requirements_path)
        if not isinstance(loaded, dict):
            errors.append(f"integrations: requirements must be JSON object: {requirements_path}")
        else:
            requirements_payload = loaded
            defaults = dict(loaded.get("defaults") or {})
            raw_provider_requirements = loaded.get("providers") or {}
            if isinstance(raw_provider_requirements, dict):
                provider_requirements = {
                    str(key).strip().lower(): value
                    for key, value in raw_provider_requirements.items()
                    if str(key).strip()
                }
    for venue in required_venues:
        row = by_provider.get(venue)
        if row is None:
            continue
        readiness = row.get("readiness", {})
        if not isinstance(readiness, dict):
            continue
        cfg = provider_requirements.get(venue, {})
        if not isinstance(cfg, dict):
            cfg = {}
        required_status_by_stage = cfg.get("required_status_by_stage", defaults.get("required_status_by_stage", {}))
        if not isinstance(required_status_by_stage, dict):
            required_status_by_stage = {}
        required_status = str(required_status_by_stage.get(required_stage, min_status)).strip().lower()
        status = str(row.get("status", "")).strip().lower()
        if required_status and not _status_at_least(status, required_status):
            errors.append(
                "integrations: stage requirement gate failed "
                f"(venue={venue}, stage={required_stage}, status={status}, required={required_status})"
            )

    if not report_path.exists():
        errors.append(f"integrations: certification report missing: {report_path}")
        return {
            "required_venues": required_venues,
            "required_market_classes": sorted(required_market_classes),
            "min_status": min_status,
            "required_stage": required_stage,
            "requirements_loaded": bool(requirements_payload),
        }

    report_payload = _load_json(report_path)
    if not isinstance(report_payload, dict):
        errors.append(f"integrations: certification report must be JSON object: {report_path}")
        return {"required_venues": required_venues}
    if not bool(report_payload.get("all_passed", False)):
        errors.append("integrations: certification report indicates failures (all_passed=false)")
    result_rows = report_payload.get("results", [])
    if not isinstance(result_rows, list):
        result_rows = []
    cert_by_venue: dict[str, dict[str, Any]] = {}
    for row in result_rows:
        if not isinstance(row, dict):
            continue
        venue = str(row.get("venue", "")).strip().lower()
        if venue:
            cert_by_venue[venue] = row
    for venue in required_venues:
        cert = cert_by_venue.get(venue)
        if cert is None:
            errors.append(f"integrations: certification report missing venue={venue}")
            continue
        if not bool(cert.get("passed", False)):
            errors.append(f"integrations: venue certification failed (venue={venue})")
    return {
        "required_venues": required_venues,
        "required_market_classes": sorted(required_market_classes),
        "min_status": min_status,
        "required_stage": required_stage,
        "requirements_loaded": bool(requirements_payload),
    }


def _evaluate_benchmark(policy: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    path = Path(str(policy.get("reference_performance", "")))
    payload = _load_json(path)
    if not isinstance(payload, dict):
        errors.append(f"benchmark payload must be JSON object: {path}")
        return {}
    min_bundles = int(policy.get("min_reference_bundle_count", 1) or 1)
    required_top_level_trust = str(policy.get("required_top_level_trust_label", "")).strip().lower()
    required_bundle_trust = str(policy.get("required_bundle_trust_label", "")).strip().lower()

    top_level_trust = str(payload.get("trust_label", "")).strip().lower()
    if required_top_level_trust and top_level_trust != required_top_level_trust:
        errors.append(
            "benchmark: top-level trust gate failed "
            f"(actual={top_level_trust}, required={required_top_level_trust})"
        )
    bundles = payload.get("bundles", [])
    if not isinstance(bundles, list):
        errors.append("benchmark: bundles must be an array")
        bundles = []
    bundle_count = int(payload.get("bundle_count", 0) or 0)
    if bundle_count < min_bundles:
        errors.append(f"benchmark: reference bundle count gate failed (actual={bundle_count}, required={min_bundles})")
    if required_bundle_trust:
        for idx, row in enumerate(bundles, start=1):
            if not isinstance(row, dict):
                continue
            trust = str(row.get("trust_label", "")).strip().lower()
            if trust != required_bundle_trust:
                errors.append(
                    "benchmark: bundle trust gate failed "
                    f"(bundle_index={idx}, actual={trust}, required={required_bundle_trust})"
                )
    return {
        "bundle_count": bundle_count,
        "generated_at": str(payload.get("generated_at", "")).strip(),
        "trust_label": top_level_trust,
    }


def _evaluate_docs(policy: dict[str, Any], benchmark_summary: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    benchmarks_doc = Path(str(policy.get("benchmarks_doc", "")))
    issue_backlog = Path(str(policy.get("issue_backlog", "")))
    benchmark_text = _read_text(benchmarks_doc)
    backlog_text = _read_text(issue_backlog)

    generated_at = str(benchmark_summary.get("generated_at", "")).strip()
    generated_date = generated_at[:10] if generated_at else ""
    if generated_date and generated_date not in benchmark_text:
        errors.append(
            "docs: BENCHMARKS.md must include latest reference artifact date "
            f"(missing {generated_date})"
        )

    required_marker = str(policy.get("require_issue_backlog_archive_marker", "")).strip()
    if required_marker and required_marker not in backlog_text:
        errors.append("docs: ISSUE_BACKLOG archive marker missing required text")

    return {"benchmarks_doc": str(benchmarks_doc), "issue_backlog": str(issue_backlog)}


def evaluate_release_readiness(policy_path: Path) -> tuple[list[str], dict[str, Any]]:
    policy = _load_json(policy_path)
    if not isinstance(policy, dict):
        return [f"policy must be a JSON object: {policy_path}"], {}

    errors: list[str] = []
    summary: dict[str, Any] = {
        "policy": str(policy_path),
        "schema_version": str(policy.get("schema_version", "")),
    }
    try:
        summary["external_beta"] = _evaluate_external_beta(dict(policy.get("external_beta") or {}), errors)
    except Exception as exc:  # pragma: no cover - defensive path
        errors.append(f"external_beta: evaluation error: {exc}")
        summary["external_beta"] = {}
    try:
        summary["integrations"] = _evaluate_integrations(dict(policy.get("integrations") or {}), errors)
    except Exception as exc:  # pragma: no cover - defensive path
        errors.append(f"integrations: evaluation error: {exc}")
        summary["integrations"] = {}
    try:
        benchmark_summary = _evaluate_benchmark(dict(policy.get("benchmark") or {}), errors)
    except Exception as exc:  # pragma: no cover - defensive path
        errors.append(f"benchmark: evaluation error: {exc}")
        benchmark_summary = {}
    summary["benchmark"] = benchmark_summary
    try:
        summary["docs"] = _evaluate_docs(dict(policy.get("docs") or {}), benchmark_summary, errors)
    except Exception as exc:  # pragma: no cover - defensive path
        errors.append(f"docs: evaluation error: {exc}")
        summary["docs"] = {}
    summary["passed"] = len(errors) == 0
    summary["error_count"] = len(errors)
    return errors, summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="config/release/release_readiness_policy.json")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    errors, summary = evaluate_release_readiness(Path(args.policy))
    if errors:
        for item in errors:
            print(f"FAIL {item}")
        print(json.dumps(summary, sort_keys=True))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
