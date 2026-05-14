from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "live_data_soak_report.py"
SPEC = importlib.util.spec_from_file_location("live_data_soak_report", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_live_data_soak_report_labels_alpha_override_and_price_ranges(tmp_path: Path) -> None:
    snapshot = tmp_path / "paper_campaign_snapshot_20260511T000000Z.json"
    snapshot.write_text(
        json.dumps(
            {
                "campaign_expected_alpha_source": "cli_override",
                "stats": {"submitted": 2, "filled": 2, "rejected": 0},
                "readiness": {"ready_for_canary": True},
                "promotion_gate": {"decision": "remain_in_paper"},
                "ops_health": {"summary": {"critical": 0, "warning": 0}},
                "market_data_resilience": {
                    "metrics": {
                        "replay_quotes": 1,
                        "failover_quotes": 0,
                        "sanity_reject_quotes": 0,
                        "synthetic_quotes": 0,
                        "unresolved_quotes": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    tca = tmp_path / "tca.csv"
    tca.write_text(
        "\n".join(
            [
                "trade_id,timestamp,symbol,exchange,side,quantity,price,notional",
                "1,2026-05-11T00:00:00Z,BTC-USD,coinbase,buy,1,80000,50",
                "2,2026-05-11T00:01:00Z,BTC-USD,coinbase,sell,1,81000,50",
            ]
        ),
        encoding="utf-8",
    )

    payload = MODULE.build_report(snapshot_path=snapshot, tca_path=tca)

    assert payload["simulation_only_alpha_override"] is True
    assert payload["data_quality_incidents"]["replay_quotes"] == 1
    assert payload["price_ranges"]["BTC-USD"]["trades"] == 2
    assert payload["price_ranges"]["BTC-USD"]["min_price"] == 80000.0
    assert payload["price_ranges"]["BTC-USD"]["max_price"] == 81000.0
