# Monitoring Runbook

> **Last Updated:** March 20, 2026  
> **Owner:** Platform Operations  
> **Classification:** Internal Use

---

## Overview

This runbook provides operational guidance for monitoring the health and performance of the Protheus trading system. It covers key metrics, alert thresholds, and standard diagnostic procedures for the observability stack.

---

## Key Metrics Dashboard

### System Health

| Metric | Warning Threshold | Critical Threshold | Check Frequency |
|--------|-------------------|--------------------|-----------------|
| CPU Usage | > 70% for 5m | > 90% for 2m | 30s |
| Memory Usage | > 80% for 5m | > 95% for 2m | 30s |
| Disk Usage | > 85% | > 95% | 5m |
| Load Average | > 4 (4-core) | > 8 (4-core) | 1m |

### Trading System Metrics

| Metric | Warning Threshold | Critical Threshold | Check Frequency |
|--------|-------------------|--------------------|-----------------|
| Order Latency p99 | > 200ms | > 500ms | 10s |
| Fill Rate | < 98% | < 95% | 1m |
| WebSocket Reconnects | > 5/hour | > 20/hour | 1m |
| Strategy Cycle Time | > 2x baseline | > 5x baseline | 30s |

---

## Alert Response Procedures

### High CPU/Memory Alert

**Initial Response:**
1. Check `htop` or `ps aux --sort=-%cpu` for top consumers
2. Identify if issue is process-specific or system-wide
3. Check recent deployment history for correlation
4. Review application logs for error patterns

**Escalation Path:**
- If related to known service: Contact service owner
- If systemic: Page infrastructure team
- Document findings in incident channel

### Order Latency Spike

**Initial Response:**
1. Check exchange API status pages
2. Verify network connectivity (`mtr`, `ping`)
3. Review recent market data for excessive volatility
4. Check execution service queue depth

**Diagnostic Commands:**
```bash
# Check execution queue status
./scripts/utils/check_service_health.sh execution

# Review recent latency distribution
tail -n 1000 logs/execution.log | grep "latency"
```

---

## Health Check Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| API Gateway | `/health` | `{"status": "healthy"}` |
| Execution Engine | `/health/ready` | HTTP 200 |
| Market Data | `/health/live` | HTTP 200 |
| Strategy Runner | `/metrics` | Prometheus format |

---

## Log Analysis Quick Reference

### Common Log Locations

```
logs/
├── api/
│   └── gateway.log
├── execution/
│   └── engine.log
├── market_data/
│   └── adapters.log
└── strategies/
    └── runner.log
```

### Useful Queries

```bash
# Find errors in last hour
grep -i error logs/*/\$(date +%Y-%m-%d)*.log | tail -50

# Check for recent warning patterns
grep -i warning logs/execution/*.log | tail -20

# Monitor real-time logs
multitail -R 2 -l "tail -f logs/api/gateway.log"
```

---

## Runbook Maintenance

**Review Schedule:** Quarterly  
**Last Review:** March 20, 2026  
**Next Review:** June 20, 2026

For suggestions or corrections, submit a PR to `docs/ops/`.

---

*This runbook complements the main Incident Response Runbook. See `incident-response-runbook.md` for escalation procedures.*
