"""Tests for API ops data helper command builders."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.api.ops_data import build_notify_command  # noqa: E402


def test_build_notify_command_supports_all_channels() -> None:
    slack = build_notify_command({"channel": "slack", "slack_webhook": "https://hooks.slack.test/a", "message": "x"})
    email = build_notify_command({"channel": "email", "email_webhook": "https://email.test/hook", "message": "x"})
    sms = build_notify_command({"channel": "sms", "sms_webhook": "https://sms.test/hook", "message": "x"})

    assert "--slack-webhook" in slack
    assert "--email-webhook" in email
    assert "--sms-webhook" in sms


def test_build_notify_command_falls_back_to_stdout_for_unknown_channel() -> None:
    cmd = build_notify_command({"channel": "pagerduty", "message": "hello"})
    assert cmd[:4] == ["main.py", "notify", "test", "--channel"]
    assert "stdout" in cmd
