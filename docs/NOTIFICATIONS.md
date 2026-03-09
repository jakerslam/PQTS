# Telegram and Discord Notifications

PQTS supports deterministic outbound notifications to Discord and Telegram for:

- incident alerts
- daily PnL summaries
- kill-switch state changes

## Environment Variables

- `PQTS_DISCORD_WEBHOOK_URL`
- `PQTS_TELEGRAM_BOT_TOKEN`
- `PQTS_TELEGRAM_CHAT_ID`

## Incident Automation Notifications

Run incident automation and dispatch alerts when incidents are generated:

```bash
python scripts/run_incident_automation.py \
  --ops-events data/analytics/ops_events.jsonl \
  --incident-log data/analytics/incidents.jsonl \
  --discord-webhook-url "$PQTS_DISCORD_WEBHOOK_URL" \
  --telegram-bot-token "$PQTS_TELEGRAM_BOT_TOKEN" \
  --telegram-chat-id "$PQTS_TELEGRAM_CHAT_ID"
```

## Generic Notification Sender

Use `send_ops_notification.py` for ad-hoc/manual notifications:

```bash
python scripts/send_ops_notification.py --mode raw --message "PQTS heartbeat"
python scripts/send_ops_notification.py --mode daily_pnl --payload-json payload.json
python scripts/send_ops_notification.py --mode kill_switch --payload-json payload.json
```

## Delivery Controls

- Deduplication TTL is configurable (`--dedupe-ttl-seconds` / `--notify-dedupe-ttl-seconds`).
- Minimum interval between sends is configurable (`--min-interval-seconds` / `--notify-min-interval-seconds`).
