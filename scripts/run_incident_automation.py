#!/usr/bin/env python3
"""Generate incidents from recent ops events using deterministic thresholds."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if SRC.exists():
    src_str = str(SRC)
    if src_str not in sys.path:
        sys.path[:] = [src_str, *sys.path]
if str(ROOT) not in sys.path:
    sys.path[:] = [str(ROOT), *sys.path]

from analytics.incident_automation import IncidentAutomation, IncidentThresholds  # noqa: E402
from analytics.notifications import (  # noqa: E402
    NotificationChannels,
    NotificationDispatcher,
    format_incident_message,
)
from analytics.ops_observability import OpsEventStore  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ops-events", default="data/analytics/ops_events.jsonl")
    parser.add_argument("--incident-log", default="data/analytics/incidents.jsonl")
    parser.add_argument("--since-minutes", type=int, default=60)
    parser.add_argument("--max-reject-rate", type=float, default=0.25)
    parser.add_argument("--max-slippage-mape-pct", type=float, default=35.0)
    parser.add_argument(
        "--discord-webhook-url",
        default=os.getenv("PQTS_DISCORD_WEBHOOK_URL", ""),
        help="Discord webhook URL for incident notifications.",
    )
    parser.add_argument(
        "--telegram-bot-token",
        default=os.getenv("PQTS_TELEGRAM_BOT_TOKEN", ""),
        help="Telegram bot token for incident notifications.",
    )
    parser.add_argument(
        "--telegram-chat-id",
        default=os.getenv("PQTS_TELEGRAM_CHAT_ID", ""),
        help="Telegram chat ID for incident notifications.",
    )
    parser.add_argument("--notify-dedupe-ttl-seconds", type=int, default=3600)
    parser.add_argument("--notify-min-interval-seconds", type=int, default=5)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    store = OpsEventStore(path=str(args.ops_events))
    automation = IncidentAutomation(incident_log_path=str(args.incident_log))
    payload = automation.run_from_store(
        store=store,
        since_minutes=int(args.since_minutes),
        thresholds=IncidentThresholds(
            max_reject_rate=float(args.max_reject_rate),
            max_slippage_mape_pct=float(args.max_slippage_mape_pct),
        ),
    )

    channels = NotificationChannels(
        discord_webhook_url=str(args.discord_webhook_url),
        telegram_bot_token=str(args.telegram_bot_token),
        telegram_chat_id=str(args.telegram_chat_id),
    )
    dispatcher = NotificationDispatcher(
        channels=channels,
        dedupe_ttl_seconds=int(args.notify_dedupe_ttl_seconds),
        min_interval_seconds=int(args.notify_min_interval_seconds),
    )

    notifications: list[dict[str, object]] = []
    for row in payload.get("incidents", []):
        if not isinstance(row, dict):
            continue
        message = format_incident_message(row)
        result = dispatcher.dispatch(message, event_key=str(row.get("incident_id", "")))
        notifications.append(
            {
                "incident_id": str(row.get("incident_id", "")),
                "result": result,
            }
        )
    payload["notifications"] = notifications

    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
