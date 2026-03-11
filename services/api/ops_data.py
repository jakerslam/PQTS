"""Operational data helpers for API-backed web diagnostics and bounded run tasks."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from execution.order_truth import load_pretrade_evidence_bundle, summarize_pretrade_evidence
except ModuleNotFoundError:  # pragma: no cover - local repo path fallback
    from src.execution.order_truth import load_pretrade_evidence_bundle, summarize_pretrade_evidence


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return fallback


def _reference_performance_path() -> Path:
    return _repo_root() / "results" / "reference_performance_latest.json"


def load_reference_performance() -> dict[str, Any]:
    payload = _read_json(
        _reference_performance_path(),
        {"generated_at": "", "bundle_count": 0, "bundles": []},
    )
    if not isinstance(payload, dict):
        return {"generated_at": "", "bundle_count": 0, "bundles": []}
    bundles = payload.get("bundles", [])
    payload["bundles"] = bundles if isinstance(bundles, list) else []
    return payload


def load_best_reference_bundle() -> dict[str, Any] | None:
    payload = load_reference_performance()
    bundles = payload.get("bundles", [])
    if not isinstance(bundles, list) or not bundles:
        return None

    def _score(bundle: dict[str, Any]) -> tuple[float, float]:
        summary = bundle.get("summary", {}) if isinstance(bundle, dict) else {}
        if not isinstance(summary, dict):
            summary = {}
        quality = float(summary.get("avg_quality_score", 0.0) or 0.0)
        fill = float(summary.get("avg_fill_rate", 0.0) or 0.0)
        return quality, fill

    ranked = sorted((b for b in bundles if isinstance(b, dict)), key=_score, reverse=True)
    return ranked[0] if ranked else None


def load_reference_provenance() -> dict[str, Any]:
    payload = load_reference_performance()
    best = load_best_reference_bundle()
    if best is None:
        return {
            "trust_label": "unverified",
            "generated_at": str(payload.get("generated_at", "")),
            "bundle": "",
            "report_path": "",
            "leaderboard_path": "",
            "source_path": "",
        }
    summary = best.get("summary", {}) if isinstance(best.get("summary"), dict) else {}
    quality = _parse_float(summary.get("avg_quality_score"))
    fill = _parse_float(summary.get("avg_fill_rate"))
    if quality >= 0.25 and fill > 0.0:
        trust_label = "reference"
    elif fill > 0.0:
        trust_label = "diagnostic_only"
    else:
        trust_label = "unverified"
    return {
        "trust_label": trust_label,
        "generated_at": str(payload.get("generated_at", "")),
        "bundle": str(best.get("bundle", "")),
        "report_path": str(best.get("report_path", "")),
        "leaderboard_path": str(best.get("leaderboard_path", "")),
        "source_path": str(best.get("path", "")),
    }


def _parse_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed == parsed else 0.0


def load_execution_quality_rows(limit: int = 500) -> list[dict[str, Any]]:
    best = load_best_reference_bundle()
    if best is None:
        return []

    report_path = str(best.get("report_path", "")).strip()
    if not report_path:
        return []

    report = _read_json(_repo_root() / report_path, {})
    if not isinstance(report, dict):
        return []
    results = report.get("results", [])
    if not isinstance(results, list) or not results:
        return []
    first = results[0] if isinstance(results[0], dict) else {}
    tca_path = str(first.get("tca_path", "")).strip()
    if not tca_path:
        return []

    tca_file = _repo_root() / tca_path
    if not tca_file.exists():
        return []

    rows: list[dict[str, Any]] = []
    with tca_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "trade_id": str(row.get("trade_id", "")),
                    "strategy_id": str(row.get("strategy_id", "")),
                    "symbol": str(row.get("symbol", "")),
                    "exchange": str(row.get("exchange", "")),
                    "side": str(row.get("side", "")),
                    "quantity": _parse_float(row.get("quantity")),
                    "price": _parse_float(row.get("price")),
                    "realized_slippage_bps": _parse_float(row.get("realized_slippage_bps")),
                    "predicted_slippage_bps": _parse_float(row.get("predicted_slippage_bps")),
                    "realized_net_alpha_usd": _parse_float(row.get("realized_net_alpha_usd")),
                    "timestamp": str(row.get("timestamp", "")),
                }
            )
            if len(rows) >= max(1, int(limit)):
                break
    return rows


def summarize_execution_quality(limit: int = 200) -> dict[str, Any]:
    rows = load_execution_quality_rows(limit)

    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    realized = [_parse_float(row.get("realized_slippage_bps")) for row in rows]
    predicted = [_parse_float(row.get("predicted_slippage_bps")) for row in rows]
    alpha = [_parse_float(row.get("realized_net_alpha_usd")) for row in rows]

    return {
        "summary": {
            "rows": len(rows),
            "avg_realized_slippage_bps": _mean(realized),
            "avg_predicted_slippage_bps": _mean(predicted),
            "avg_realized_net_alpha_usd": _mean(alpha),
            "total_realized_net_alpha_usd": sum(alpha),
        },
        "rows": rows,
    }


def load_replay_events(limit: int = 100) -> list[dict[str, Any]]:
    best = load_best_reference_bundle()
    if best is None:
        return []
    bundle_path = str(best.get("path", "")).strip()
    if not bundle_path:
        return []
    events_path = _repo_root() / bundle_path / "simulation_events.jsonl"
    if not events_path.exists():
        return []

    events: list[dict[str, Any]] = []
    with events_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except Exception:  # noqa: BLE001
                parsed = {}
            if isinstance(parsed, dict):
                events.append(parsed)
            if len(events) >= max(1, int(limit)):
                break
    return events


def replay_hash(events: list[dict[str, Any]]) -> str:
    canonical = json.dumps(events, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def summarize_replay(limit: int = 120) -> dict[str, Any]:
    events = load_replay_events(limit)
    counter: dict[str, int] = {}
    for event in events:
        token = str(event.get("event_type", "unknown")).strip() or "unknown"
        counter[token] = counter.get(token, 0) + 1
    event_types = [
        {"event_type": event_type, "count": count}
        for event_type, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {
        "hash": replay_hash(events),
        "count": len(events),
        "event_types": event_types,
        "events": events,
    }


def build_order_truth(order_id: str | None = None) -> dict[str, Any]:
    rows = load_execution_quality_rows(limit=300)
    evidence_path = _repo_root() / "data" / "reports" / "order_truth" / "event_intel_latest.json"
    evidence_summary = summarize_pretrade_evidence(load_pretrade_evidence_bundle(evidence_path))
    selected = None
    if order_id:
        selected = next((row for row in rows if str(row.get("trade_id", "")) == order_id), None)
    if selected is None and rows:
        selected = rows[0]

    if selected is None:
        explanation = ["No execution rows found in latest reference bundle."]
    else:
        predicted = _parse_float(selected.get("predicted_slippage_bps"))
        realized = _parse_float(selected.get("realized_slippage_bps"))
        alpha = _parse_float(selected.get("realized_net_alpha_usd"))
        explanation = [
            f"Signal: {selected.get('strategy_id', '')} emitted {selected.get('side', '')} for {selected.get('symbol', '')}.",
            f"Risk: expected slippage budget {predicted:.2f} bps.",
            f"Execution: realized slippage {realized:.2f} bps on {selected.get('exchange', '')}.",
            f"Attribution: realized_net_alpha_usd={alpha:.4f}.",
        ]
    if evidence_summary is not None:
        explanation.append(
            "Event-intel evidence bundle: "
            f"trust={evidence_summary.get('trust_label', 'unverified')} "
            f"sources={evidence_summary.get('source_count', 0)} "
            f"gate={evidence_summary.get('risk_gate_decision', '')}"
        )
    return {
        "selected": selected,
        "rows": rows,
        "explanation": explanation,
        "evidence_bundle": evidence_summary,
    }


def list_template_run_artifacts(mode: str | None = None, limit: int = 40) -> list[dict[str, Any]]:
    reports_root = _repo_root() / "data" / "reports"
    if not reports_root.exists():
        return []

    if mode:
        modes = [mode]
    else:
        modes = sorted([item.name for item in reports_root.iterdir() if item.is_dir()])

    results: list[dict[str, Any]] = []
    for current_mode in modes:
        mode_dir = reports_root / current_mode
        if not mode_dir.exists() or not mode_dir.is_dir():
            continue
        manifests = sorted(
            [item for item in mode_dir.iterdir() if item.is_file() and item.name.startswith("template_run_") and item.suffix == ".json"],
            reverse=True,
        )
        for manifest in manifests:
            payload = _read_json(manifest, {})
            if not isinstance(payload, dict):
                payload = {}
            stamp = manifest.name.removeprefix("template_run_").removesuffix(".json")
            diff = mode_dir / f"template_run_diff_{stamp}.diff"
            results.append(
                {
                    "mode": current_mode,
                    "generated_at": str(payload.get("generated_at", "")),
                    "template": str(payload.get("template", "unknown")),
                    "resolved_strategy": str(payload.get("resolved_strategy", "unknown")),
                    "config_path": str(payload.get("config_path", "")),
                    "command": [str(token) for token in payload.get("command", [])] if isinstance(payload.get("command"), list) else [],
                    "artifact_path": str(manifest.relative_to(_repo_root())).replace("\\", "/"),
                    "diff_path": str(diff.relative_to(_repo_root())).replace("\\", "/") if diff.exists() else "",
                    "config_sha256": str(payload.get("config_sha256", "")),
                }
            )
            if len(results) >= max(1, int(limit)):
                return results
    return results


def data_seed_presets() -> list[dict[str, Any]]:
    return [
        {
            "label": "Crypto 1h (Q1 sample)",
            "venue": "binance",
            "interval": "1h",
            "start": "2026-01-01",
            "end": "2026-03-01",
        },
        {
            "label": "Cross-venue 1h (Q1 sample)",
            "venue": "all",
            "interval": "1h",
            "start": "2026-01-01",
            "end": "2026-03-01",
        },
    ]


def build_data_seed_command(payload: dict[str, Any]) -> list[str]:
    venue = str(payload.get("venue", "all"))
    if venue not in {"binance", "coinbase", "all"}:
        venue = "all"
    interval = str(payload.get("interval", "1h"))
    start = str(payload.get("start", "2026-01-01"))
    end = str(payload.get("end", "2026-03-01"))
    file_format = str(payload.get("format", "csv"))
    if file_format not in {"csv", "parquet"}:
        file_format = "csv"
    cache_mode = str(payload.get("cache_mode", "use"))
    if cache_mode not in {"use", "refresh"}:
        cache_mode = "use"
    retries = payload.get("max_retries", 3)
    try:
        max_retries = max(1, int(retries))
    except (TypeError, ValueError):
        max_retries = 3

    return [
        "scripts/download_historical_data.py",
        "--venue",
        venue,
        "--interval",
        interval,
        "--start",
        start,
        "--end",
        end,
        "--format",
        file_format,
        "--cache-mode",
        cache_mode,
        "--max-retries",
        str(max_retries),
    ]


def build_notify_command(payload: dict[str, Any]) -> list[str]:
    channel = str(payload.get("channel", "stdout"))
    if channel not in {"stdout", "telegram", "discord"}:
        channel = "stdout"
    message = str(payload.get("message", "[PQTS TEST] Notifications channel check from API."))

    command = [
        "main.py",
        "notify",
        "test",
        "--channel",
        channel,
        "--message",
        message,
        "--output",
        "json",
    ]
    if channel == "telegram":
        command.extend(
            [
                "--telegram-token",
                str(payload.get("telegram_token", "")),
                "--telegram-chat-id",
                str(payload.get("telegram_chat_id", "")),
            ]
        )
    elif channel == "discord":
        command.extend(["--discord-webhook", str(payload.get("discord_webhook", ""))])
    return command


def parse_last_json_line(stdout: str) -> dict[str, Any] | None:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            parsed = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def run_python_command(command: list[str], *, timeout_seconds: int) -> dict[str, Any]:
    start = time.perf_counter()
    resolved = [sys.executable, *command]
    try:
        completed = subprocess.run(  # noqa: S603
            resolved,
            cwd=str(_repo_root()),
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_seconds)),
            check=False,
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return {
            "succeeded": completed.returncode == 0,
            "returncode": int(completed.returncode),
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration_ms,
            "command": resolved,
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "succeeded": False,
            "returncode": -1,
            "stdout": exc.stdout or "",
            "stderr": f"command timed out after {timeout_seconds}s",
            "duration_ms": duration_ms,
            "command": resolved,
        }
