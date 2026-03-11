#!/usr/bin/env python3
"""Run proof artifact publication when schedule cadence is due."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/moat/proof_schedule.json")
    parser.add_argument("--out", default="data/reports/proof/proof_manifest.json")
    return parser


def main() -> int:
    from moat.proof_pipeline import ProofArtifactPipeline
    from moat.proof_schedule import ProofSchedulePolicy, schedule_due

    args = build_arg_parser().parse_args()
    cfg_path = Path(args.config)
    config = json.loads(cfg_path.read_text(encoding="utf-8"))

    cadence_hours = int(config.get("cadence_hours", 24))
    last_run_at = config.get("last_run_at")
    policy = ProofSchedulePolicy(cadence_hours=cadence_hours)
    now = datetime.now(timezone.utc)

    due = schedule_due(last_run_at=last_run_at, now=now, policy=policy)
    if not due:
        print(json.dumps({"due": False, "published": False}, sort_keys=True))
        return 0

    pipeline = ProofArtifactPipeline()
    artifact = pipeline.publish(
        artifact_id=str(config.get("artifact_id", "weekly_benchmark")),
        artifact_type=str(config.get("artifact_type", "benchmark")),
        result_class=str(config.get("result_class", "reference")),
        command=str(config.get("reproducible_command", "make sim-suite")),
        provenance_ref=str(
            config.get("provenance_ref", "data/reports/provenance/benchmark_provenance.jsonl")
        ),
    )

    manifest_path = pipeline.write_manifest(args.out)
    config["last_run_at"] = artifact.created_at
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "due": True,
                "published": True,
                "manifest": str(manifest_path),
                "artifact_id": artifact.artifact_id,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
