"""Local product packaging CLI for localhost launch + setup artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.local_product import (  # noqa: E402
    ServiceSpec,
    build_bundle_manifest,
    build_support_bundle,
    evaluate_localhost_launch,
    generate_first_run_config,
    write_runtime_status_artifact,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    launch = sub.add_parser("launch", help="Evaluate launch readiness and emit status artifact")
    launch.add_argument("--status-artifact", default="data/runtime/local_status.json")
    launch.add_argument("--redis-ok", action="store_true")
    launch.add_argument("--api-ok", action="store_true")
    launch.add_argument("--web-ok", action="store_true")
    launch.add_argument("--occupied-port", action="append", default=[])

    wizard = sub.add_parser("wizard", help="Create first-run safe config artifact")
    wizard.add_argument("--mode", default="paper")
    wizard.add_argument("--risk-profile", default="safe")
    wizard.add_argument("--workspace", default=".")
    wizard.add_argument("--out", default="config/local/first_run.json")

    bundle = sub.add_parser("bundle", help="Create distributable bundle manifest")
    bundle.add_argument("--bundle-id", required=True)
    bundle.add_argument("--version", required=True)
    bundle.add_argument("--os", required=True)
    bundle.add_argument("--arch", required=True)
    bundle.add_argument("--hash", required=True)
    bundle.add_argument("--signed", action="store_true")
    bundle.add_argument("--component", action="append", default=[])
    bundle.add_argument("--out", default="data/release/local_bundle_manifest.json")

    support = sub.add_parser("support", help="Emit support bundle with redacted config")
    support.add_argument("--out", default="data/support/latest_support_bundle.json")
    support.add_argument("--version", default="unknown")
    support.add_argument("--health-json", default="{}")
    support.add_argument("--config-json", default="{}")
    support.add_argument("--logs-json", default="{}")

    return parser


def _run_launch(args: argparse.Namespace) -> int:
    services = [
        ServiceSpec(
            name="api",
            command="uvicorn services.api.main:app --host 127.0.0.1 --port 8100",
            health_url="http://127.0.0.1:8100/health",
            url="http://127.0.0.1:8100",
            required_dependency="redis",
            required_port=8100,
        ),
        ServiceSpec(
            name="web",
            command="npm --prefix apps/web run dev -- --port 3000",
            health_url="http://127.0.0.1:3000/api/health",
            url="http://127.0.0.1:3000",
            required_dependency="node",
            required_port=3000,
        ),
    ]
    summary = evaluate_localhost_launch(
        services=services,
        available_dependencies={
            "redis": bool(args.redis_ok),
            "node": True,
        },
        occupied_ports=[int(item) for item in args.occupied_port],
        health_by_service={
            "api": bool(args.api_ok),
            "web": bool(args.web_ok),
        },
    )
    artifact = write_runtime_status_artifact(
        path=args.status_artifact,
        state="ready" if summary.ready else "degraded",
        summary=summary,
    )
    print(json.dumps({"ready": summary.ready, "artifact": str(artifact), "urls": summary.urls}, sort_keys=True))
    return 0 if summary.ready else 1


def _run_wizard(args: argparse.Namespace) -> int:
    config = generate_first_run_config(
        mode=args.mode,
        risk_profile=args.risk_profile,
        workspace_path=args.workspace,
        credentials={},
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config.__dict__, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "mode": config.mode, "risk_profile": config.risk_profile}, sort_keys=True))
    return 0


def _run_bundle(args: argparse.Namespace) -> int:
    manifest = build_bundle_manifest(
        bundle_id=args.bundle_id,
        version=args.version,
        os=args.os,
        arch=args.arch,
        included_components=list(args.component),
        verification_hash=args.hash,
        signed=bool(args.signed),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest.__dict__, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "signed": manifest.signed}, sort_keys=True))
    return 0


def _run_support(args: argparse.Namespace) -> int:
    bundle = build_support_bundle(
        output_path=args.out,
        logs=json.loads(args.logs_json),
        config=json.loads(args.config_json),
        health=json.loads(args.health_json),
        version=args.version,
    )
    print(json.dumps({"output": str(bundle)}, sort_keys=True))
    return 0


def main() -> int:
    args = _build_parser().parse_args()
    if args.command == "launch":
        return _run_launch(args)
    if args.command == "wizard":
        return _run_wizard(args)
    if args.command == "bundle":
        return _run_bundle(args)
    if args.command == "support":
        return _run_support(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
