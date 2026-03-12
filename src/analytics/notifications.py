"""Notification dispatch helpers for Telegram and Discord channels."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping

import requests

from execution.distributed_ops_state import DistributedOpsState, DistributedStateConfig


@dataclass(frozen=True)
class NotificationChannels:
    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    slack_webhook_url: str = ""
    email_webhook_url: str = ""
    sms_webhook_url: str = ""


def _now_ts() -> float:
    return float(time.time())


def _short_hash(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:20]


def format_incident_message(row: Mapping[str, Any]) -> str:
    incident_id = str(row.get("incident_id", "unknown"))
    severity = str(row.get("severity", "unknown")).upper()
    category = str(row.get("category", "unknown"))
    reason = str(row.get("reason", "unspecified"))
    message = str(row.get("message", "")).strip()
    runbook = str(row.get("runbook_action", "review_ops_event_context"))
    return (
        f"[PQTS INCIDENT] {severity} | {category}\n"
        f"id={incident_id}\n"
        f"reason={reason}\n"
        f"message={message}\n"
        f"runbook={runbook}"
    )


def format_daily_pnl_message(payload: Mapping[str, Any]) -> str:
    date_label = str(payload.get("date", "today"))
    pnl = float(payload.get("net_pnl_usd", 0.0))
    filled = int(payload.get("filled", 0))
    rejected = int(payload.get("rejected", 0))
    reject_rate = float(payload.get("reject_rate", 0.0))
    return (
        f"[PQTS DAILY PNL] {date_label}\n"
        f"net_pnl_usd={pnl:.2f}\n"
        f"filled={filled}\n"
        f"rejected={rejected}\n"
        f"reject_rate={reject_rate:.4f}"
    )


def format_kill_switch_message(payload: Mapping[str, Any]) -> str:
    state = str(payload.get("state", "unknown"))
    reason = str(payload.get("reason", "unspecified"))
    detail = str(payload.get("detail", "")).strip()
    return (
        "[PQTS KILL SWITCH]\n"
        f"state={state}\n"
        f"reason={reason}\n"
        f"detail={detail}"
    )


class NotificationDispatcher:
    """Dispatch text notifications with dedupe and rate-limit controls."""

    def __init__(
        self,
        channels: NotificationChannels,
        *,
        dedupe_ttl_seconds: int = 3600,
        min_interval_seconds: int = 5,
        redis_url: str = "",
        state_namespace: str = "pqts_notifications",
        state: DistributedOpsState | None = None,
        timeout_seconds: float = 10.0,
    ):
        self.channels = channels
        self.dedupe_ttl_seconds = int(max(1, dedupe_ttl_seconds))
        self.min_interval_seconds = int(max(0, min_interval_seconds))
        self.timeout_seconds = float(max(1.0, timeout_seconds))
        self.state = state or DistributedOpsState(
            DistributedStateConfig(
                redis_url=str(redis_url),
                namespace=str(state_namespace),
                ttl_seconds=int(self.dedupe_ttl_seconds),
            )
        )

    def _channel_enabled(self, channel: str) -> bool:
        if channel == "discord":
            return bool(str(self.channels.discord_webhook_url).strip())
        if channel == "telegram":
            return bool(str(self.channels.telegram_bot_token).strip()) and bool(
                str(self.channels.telegram_chat_id).strip()
            )
        if channel == "slack":
            return bool(str(self.channels.slack_webhook_url).strip())
        if channel == "email":
            return bool(str(self.channels.email_webhook_url).strip())
        if channel == "sms":
            return bool(str(self.channels.sms_webhook_url).strip())
        return False

    def _should_send(self, channel: str, event_key: str) -> tuple[bool, str]:
        if not self._channel_enabled(channel):
            return False, "channel_not_configured"

        dedupe_key = f"{channel}:dedupe:{event_key}"
        if self.state.seen_recently(dedupe_key):
            return False, "dedupe_suppressed"

        if self.min_interval_seconds > 0:
            last_key = f"{channel}:last_sent"
            last = self.state.get(last_key) or {}
            last_ts = float(last.get("ts", 0.0))
            if (_now_ts() - last_ts) < float(self.min_interval_seconds):
                return False, "rate_limited"

        self.state.put(dedupe_key, {"seen": True, "ts": _now_ts()})
        self.state.put(f"{channel}:last_sent", {"ts": _now_ts()})
        return True, "ok"

    def _post_discord(self, message: str) -> Dict[str, Any]:
        url = str(self.channels.discord_webhook_url).strip()
        response = requests.post(
            url,
            json={"content": str(message)},
            timeout=self.timeout_seconds,
        )
        return {
            "ok": bool(200 <= int(response.status_code) < 300),
            "status_code": int(response.status_code),
            "channel": "discord",
            "text": str(response.text[:200]),
        }

    def _post_telegram(self, message: str) -> Dict[str, Any]:
        token = str(self.channels.telegram_bot_token).strip()
        chat_id = str(self.channels.telegram_chat_id).strip()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": str(message)},
            timeout=self.timeout_seconds,
        )
        return {
            "ok": bool(200 <= int(response.status_code) < 300),
            "status_code": int(response.status_code),
            "channel": "telegram",
            "text": str(response.text[:200]),
        }

    def _post_slack(self, message: str) -> Dict[str, Any]:
        url = str(self.channels.slack_webhook_url).strip()
        response = requests.post(
            url,
            json={"text": str(message)},
            timeout=self.timeout_seconds,
        )
        return {
            "ok": bool(200 <= int(response.status_code) < 300),
            "status_code": int(response.status_code),
            "channel": "slack",
            "text": str(response.text[:200]),
        }

    def _post_email(self, message: str) -> Dict[str, Any]:
        url = str(self.channels.email_webhook_url).strip()
        response = requests.post(
            url,
            json={"subject": "[PQTS] Ops Notification", "body": str(message)},
            timeout=self.timeout_seconds,
        )
        return {
            "ok": bool(200 <= int(response.status_code) < 300),
            "status_code": int(response.status_code),
            "channel": "email",
            "text": str(response.text[:200]),
        }

    def _post_sms(self, message: str) -> Dict[str, Any]:
        url = str(self.channels.sms_webhook_url).strip()
        response = requests.post(
            url,
            json={"message": str(message)},
            timeout=self.timeout_seconds,
        )
        return {
            "ok": bool(200 <= int(response.status_code) < 300),
            "status_code": int(response.status_code),
            "channel": "sms",
            "text": str(response.text[:200]),
        }

    def dispatch(self, message: str, *, event_key: str = "") -> Dict[str, Any]:
        payload_key = str(event_key).strip() or _short_hash(str(message))
        attempts: list[Dict[str, Any]] = []

        for channel in ("discord", "telegram", "slack", "email", "sms"):
            allowed, reason = self._should_send(channel, payload_key)
            if not allowed:
                attempts.append(
                    {
                        "channel": channel,
                        "ok": False,
                        "sent": False,
                        "reason": reason,
                    }
                )
                continue

            try:
                if channel == "discord":
                    result = self._post_discord(message)
                elif channel == "telegram":
                    result = self._post_telegram(message)
                elif channel == "slack":
                    result = self._post_slack(message)
                elif channel == "email":
                    result = self._post_email(message)
                else:
                    result = self._post_sms(message)
                attempts.append({**result, "sent": True, "reason": "ok"})
            except Exception as exc:  # pragma: no cover - network/runtime defensive path
                attempts.append(
                    {
                        "channel": channel,
                        "ok": False,
                        "sent": False,
                        "reason": "dispatch_error",
                        "error": str(exc),
                    }
                )

        sent_count = sum(1 for row in attempts if bool(row.get("sent")))
        return {
            "event_key": payload_key,
            "message": str(message),
            "attempts": attempts,
            "sent_count": int(sent_count),
            "channels_configured": int(
                sum(1 for c in ("discord", "telegram", "slack", "email", "sms") if self._channel_enabled(c))
            ),
        }
