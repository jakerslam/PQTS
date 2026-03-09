#!/usr/bin/env python3
"""Send deterministic Telegram/Discord notifications for ops events."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if SRC.exists():
    src_str = str(SRC)
    if src_str not in sys.path:
        sys.path[:] = [src_str, *sys.path]
if str(ROOT) not in sys.path:
    sys.path[:] = [str(ROOT), *sys.path]

from analytics.notifications import (  # noqa: E402
    NotificationChannels,
    NotificationDispatcher,
    format_daily_pnl_message,
    format_incident_message,
    format_kill_switch_message,
)


def _load_json(path: str) -> Dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object payload")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["incident", "daily_pnl", "kill_switch", "raw"],
        default="raw",
    )
    parser.add_argument("--payload-json", default="", help="Path to JSON payload.")
    parser.add_argument("--message", default="", help="Raw message when mode=raw.")
    parser.add_argument("--event-key", default="", help="Idempotency key override.")
    parser.add_argument(
        "--discord-webhook-url",
        default=os.getenv("PQTS_DISCORD_WEBHOOK_URL", ""),
        help="Discord webhook URL.",
    )
    parser.add_argument(
        "--telegram-bot-token",
        default=os.getenv("PQTS_TELEGRAM_BOT_TOKEN", ""),
        help="Telegram bot token.",
    )
    parser.add_argument(
        "--telegram-chat-id",
        default=os.getenv("PQTS_TELEGRAM_CHAT_ID", ""),
        help="Telegram chat ID.",
    )
    parser.add_argument("--dedupe-ttl-seconds", type=int, default=3600)
    parser.add_argument("--min-interval-seconds", type=int, default=5)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload: Dict[str, Any] = {}
    if args.payload_json:
        payload = _load_json(str(args.payload_json))

    if args.mode == "incident":
        message = format_incident_message(payload)
        event_key = str(args.event_key).strip() or str(payload.get("incident_id", ""))
    elif args.mode == "daily_pnl":
        message = format_daily_pnl_message(payload)
        event_key = str(args.event_key).strip() or f"daily_pnl:{payload.get('date', '')}"
    elif args.mode == "kill_switch":
        message = format_kill_switch_message(payload)
        event_key = str(args.event_key).strip() or f"kill_switch:{payload.get('state', '')}"
    else:
        message = str(args.message).strip()
        if not message:
            raise ValueError("mode=raw requires --message")
        event_key = str(args.event_key).strip()

    dispatcher = NotificationDispatcher(
        channels=NotificationChannels(
            discord_webhook_url=str(args.discord_webhook_url),
            telegram_bot_token=str(args.telegram_bot_token),
            telegram_chat_id=str(args.telegram_chat_id),
        ),
        dedupe_ttl_seconds=int(args.dedupe_ttl_seconds),
        min_interval_seconds=int(args.min_interval_seconds),
    )
    result = dispatcher.dispatch(message, event_key=event_key)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
