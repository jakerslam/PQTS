"""Tests for multi-channel notification dispatch helpers."""

from __future__ import annotations

from analytics.notifications import (
    NotificationChannels,
    NotificationDispatcher,
    format_daily_pnl_message,
    format_incident_message,
    format_kill_switch_message,
)


class _FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "ok"):
        self.status_code = status_code
        self.text = text


def test_formatters_include_core_fields():
    inc = format_incident_message(
        {
            "incident_id": "inc_1",
            "severity": "critical",
            "category": "execution",
            "reason": "metric_alert_reject_rate",
            "message": "reject rate too high",
            "runbook_action": "check_router",
        }
    )
    assert "inc_1" in inc
    assert "CRITICAL" in inc

    pnl = format_daily_pnl_message(
        {"date": "2026-03-09", "net_pnl_usd": 12.5, "filled": 3, "rejected": 1, "reject_rate": 0.25}
    )
    assert "2026-03-09" in pnl
    assert "12.50" in pnl

    ks = format_kill_switch_message({"state": "halted", "reason": "drawdown_limit", "detail": "manual"})
    assert "halted" in ks
    assert "drawdown_limit" in ks


def test_dispatch_sends_to_configured_channels(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):  # noqa: ANN001
        calls.append({"url": url, "json": dict(json), "timeout": timeout})
        return _FakeResponse(200, "ok")

    monkeypatch.setattr("analytics.notifications.requests.post", fake_post)

    dispatcher = NotificationDispatcher(
        channels=NotificationChannels(
            discord_webhook_url="https://discord.test/webhook",
            telegram_bot_token="123:token",
            telegram_chat_id="-1001",
            slack_webhook_url="https://hooks.slack.test/services/a/b",
            email_webhook_url="https://email.test/hooks/send",
            sms_webhook_url="https://sms.test/hooks/send",
        ),
        dedupe_ttl_seconds=60,
        min_interval_seconds=0,
    )

    result = dispatcher.dispatch("hello", event_key="evt-1")
    assert result["sent_count"] == 5
    assert len(calls) == 5


def test_dispatch_dedupe_blocks_repeat(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):  # noqa: ANN001
        calls.append({"url": url, "json": dict(json), "timeout": timeout})
        return _FakeResponse(200, "ok")

    monkeypatch.setattr("analytics.notifications.requests.post", fake_post)

    dispatcher = NotificationDispatcher(
        channels=NotificationChannels(discord_webhook_url="https://discord.test/webhook"),
        dedupe_ttl_seconds=300,
        min_interval_seconds=0,
    )

    first = dispatcher.dispatch("hello", event_key="evt-1")
    second = dispatcher.dispatch("hello", event_key="evt-1")

    assert first["sent_count"] == 1
    assert second["sent_count"] == 0
    assert len(calls) == 1
