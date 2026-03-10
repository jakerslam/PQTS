"""Benchmark provenance standard for reproducible result bundles."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
from typing import Any, Dict, Iterable, List, Mapping


_MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


@dataclass(frozen=True)
class BenchmarkProvenanceRecord:
    """Canonical provenance record for one published benchmark bundle."""

    bundle_name: str
    bundle_path: str
    strategy_version: str
    dataset_version: str
    environment_hash: str
    run_timestamp: str
    generated_at: str
    scenario_count: int
    artifact_hashes: Dict[str, str]
    environment: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_json_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256_text(canonical)


def _find_latest_suite_file(bundle_dir: Path) -> Path | None:
    candidates = sorted(bundle_dir.glob("simulation_suite_*.json"))
    if not candidates:
        return None
    return candidates[-1]


def _load_json(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_git_sha(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        value = result.stdout.strip()
        return value if value else "unknown"
    except Exception:
        return "unknown"


def _discover_month_bundles(results_dir: Path, month: str) -> List[Path]:
    if not _MONTH_PATTERN.match(str(month)):
        raise ValueError(f"invalid month format: {month!r}; expected YYYY-MM")
    if not results_dir.exists():
        return []
    prefix = f"{month}-"
    bundles: List[Path] = []
    for child in sorted(results_dir.iterdir()):
        if child.is_dir() and child.name.startswith(prefix):
            bundles.append(child)
    return bundles


def _resolve_dataset_version(
    payload: Mapping[str, Any],
    bundle_name: str,
    fallback: str | None,
    bundle_dir: Path,
) -> str:
    if fallback:
        return str(fallback)
    manifest_path = bundle_dir / "dataset_manifest.json"
    if manifest_path.exists() and manifest_path.is_file():
        try:
            manifest = _load_json(manifest_path)
            token = manifest.get("dataset_version")
            if token:
                return str(token)
        except Exception:
            pass
    for key in ("dataset_version", "dataset_id", "dataset_manifest", "dataset"):
        value = payload.get(key)
        if value:
            return str(value)
    config_path = payload.get("config_path")
    if config_path:
        return f"config:{config_path}"
    return f"bundle:{bundle_name}"


def _resolve_run_timestamp(payload: Mapping[str, Any]) -> str:
    value = payload.get("created_at")
    if value:
        return str(value)
    return datetime.now(timezone.utc).isoformat()


def _build_artifact_hashes(bundle_dir: Path, payload: Mapping[str, Any], suite_file: Path) -> Dict[str, str]:
    hashes: Dict[str, str] = {
        suite_file.name: _sha256_file(suite_file),
    }

    leaderboard_path = payload.get("leaderboard_path")
    if leaderboard_path:
        leaderboard = Path(str(leaderboard_path))
        if not leaderboard.is_absolute():
            leaderboard = bundle_dir / leaderboard
        if leaderboard.exists() and leaderboard.is_file():
            hashes[leaderboard.name] = _sha256_file(leaderboard)

    for name in (
        "config_paper_snapshot.yaml",
        "dataset_manifest.json",
        "simulation_events.jsonl",
        "metrics_chart.svg",
        "quality_reject_chart.svg",
    ):
        candidate = bundle_dir / name
        if candidate.exists() and candidate.is_file():
            hashes[name] = _sha256_file(candidate)

    return dict(sorted(hashes.items()))


def _environment_metadata(bundle_name: str, artifact_hashes: Mapping[str, str]) -> Dict[str, Any]:
    return {
        "bundle_name": bundle_name,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "artifact_hash_fingerprint": _normalize_json_hash(dict(artifact_hashes)),
    }


def build_benchmark_provenance_record(
    *,
    bundle_dir: str | Path,
    strategy_version: str,
    dataset_version: str | None = None,
) -> BenchmarkProvenanceRecord | None:
    """Build one provenance record from a single result bundle directory."""
    path = Path(bundle_dir)
    suite_file = _find_latest_suite_file(path)
    if suite_file is None:
        return None

    payload = _load_json(suite_file)
    artifact_hashes = _build_artifact_hashes(path, payload, suite_file)
    environment = _environment_metadata(path.name, artifact_hashes)
    environment_hash = _normalize_json_hash(environment)

    scenario_count = 0
    results = payload.get("results")
    if isinstance(results, list):
        scenario_count = len(results)
    if scenario_count <= 0:
        leaderboard = payload.get("leaderboard")
        if isinstance(leaderboard, list):
            for row in leaderboard:
                if isinstance(row, Mapping):
                    scenario_count += max(1, int(_safe_float(row.get("runs", 1))))

    return BenchmarkProvenanceRecord(
        bundle_name=path.name,
        bundle_path=str(path),
        strategy_version=str(strategy_version),
        dataset_version=_resolve_dataset_version(payload, path.name, dataset_version, path),
        environment_hash=environment_hash,
        run_timestamp=_resolve_run_timestamp(payload),
        generated_at=datetime.now(timezone.utc).isoformat(),
        scenario_count=int(scenario_count),
        artifact_hashes=artifact_hashes,
        environment=environment,
    )


def collect_monthly_benchmark_provenance(
    *,
    results_dir: str | Path,
    month: str,
    strategy_version: str,
    dataset_version: str | None = None,
) -> List[BenchmarkProvenanceRecord]:
    """Collect provenance records for all bundle directories in a month."""
    root = Path(results_dir)
    records: List[BenchmarkProvenanceRecord] = []
    for bundle in _discover_month_bundles(root, month):
        record = build_benchmark_provenance_record(
            bundle_dir=bundle,
            strategy_version=strategy_version,
            dataset_version=dataset_version,
        )
        if record is not None:
            records.append(record)
    return records


def _record_key(payload: Mapping[str, Any]) -> str:
    bundle = str(payload.get("bundle_name", ""))
    run_ts = str(payload.get("run_timestamp", ""))
    strategy_version = str(payload.get("strategy_version", ""))
    return f"{bundle}|{run_ts}|{strategy_version}"


def merge_and_write_benchmark_provenance_log(
    *,
    records: Iterable[BenchmarkProvenanceRecord],
    output_path: str | Path,
) -> Path:
    """Merge records into a deduplicated JSONL provenance log."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    merged: Dict[str, Dict[str, Any]] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            merged[_record_key(payload)] = payload

    for record in records:
        payload = record.to_dict()
        merged[_record_key(payload)] = payload

    ordered = sorted(
        merged.values(),
        key=lambda row: (
            str(row.get("run_timestamp", "")),
            str(row.get("bundle_name", "")),
            str(row.get("strategy_version", "")),
        ),
    )

    output = "\n".join(json.dumps(row, sort_keys=True) for row in ordered)
    if output:
        output += "\n"
    path.write_text(output, encoding="utf-8")
    return path


def update_monthly_benchmark_provenance_log(
    *,
    results_dir: str | Path,
    month: str,
    output_path: str | Path,
    repo_root: str | Path,
    dataset_version: str | None = None,
) -> Path:
    """Collect month records and merge them into the canonical benchmark provenance log."""
    strategy_version = _resolve_git_sha(Path(repo_root))
    records = collect_monthly_benchmark_provenance(
        results_dir=results_dir,
        month=month,
        strategy_version=strategy_version,
        dataset_version=dataset_version,
    )
    return merge_and_write_benchmark_provenance_log(records=records, output_path=output_path)
