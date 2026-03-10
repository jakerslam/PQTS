from __future__ import annotations

import pytest

from adapters.prediction_market_client import (
    AuthContext,
    ClientStateError,
    PredictionMarketClientContract,
)


def test_read_only_market_data_without_auth() -> None:
    client = PredictionMarketClientContract()
    payload = client.get_market_data(market_id="mkt-1")
    assert payload["ok"] is True
    assert payload["mode"] == "read_only"


def test_proxy_auth_requires_funder() -> None:
    client = PredictionMarketClientContract()
    with pytest.raises(ValueError, match="funder is required"):
        client.authenticate(AuthContext(signer_id="alice", signature_type="proxy", funder=None))


def test_authenticated_order_flow_requires_allowances() -> None:
    client = PredictionMarketClientContract()
    client.authenticate(AuthContext(signer_id="alice", signature_type="eoa"))
    client.create_or_derive_api_creds(seed="seed-1")
    order = client.create_order(
        token_id="token-1",
        side="buy",
        size=10.0,
        price=0.45,
        tif="GTC",
        order_type="limit",
    )
    with pytest.raises(ClientStateError, match="missing required allowances"):
        client.post_order(order, required_assets=["usdc", "ctf"])

    client.set_allowance(asset="usdc", approved=True)
    client.set_allowance(asset="ctf", approved=True)
    posted = client.post_order(order, required_assets=["usdc", "ctf"])
    assert posted["accepted"] is True
    assert posted["order_id"].startswith("ord_")


def test_batch_post_returns_stable_schema() -> None:
    client = PredictionMarketClientContract()
    client.authenticate(AuthContext(signer_id="alice", signature_type="eoa"))
    client.create_or_derive_api_creds(seed="seed-2")
    order = client.create_order(
        token_id="token-1",
        side="buy",
        size=5.0,
        price=0.40,
        tif="FOK",
        order_type="limit",
    )
    rows = client.post_orders_batch(orders=[order], required_assets=["usdc"])
    assert len(rows) == 1
    row = rows[0]
    assert row["index"] == 1
    assert row["ok"] is False
    assert isinstance(row["error"], str)
    assert isinstance(row["result"], dict)


def test_rotate_and_revoke_api_credentials_logged() -> None:
    client = PredictionMarketClientContract()
    client.authenticate(AuthContext(signer_id="alice", signature_type="safe", funder="0xabc"))
    creds_a = client.create_or_derive_api_creds(seed="seed-a")
    creds_b = client.rotate_api_creds(seed="seed-b")
    assert creds_a.key_id != creds_b.key_id
    client.revoke_api_creds()
    events = [row["event"] for row in client.audit_log]
    assert "auth.create_or_derive_api_creds" in events
    assert "auth.rotate_api_creds" in events
    assert "auth.revoke_api_creds" in events


def test_create_order_rejects_unknown_tif() -> None:
    client = PredictionMarketClientContract()
    client.authenticate(AuthContext(signer_id="alice", signature_type="eoa"))
    client.create_or_derive_api_creds(seed="seed-3")
    with pytest.raises(ValueError, match="unsupported tif"):
        client.create_order(
            token_id="token-1",
            side="buy",
            size=1.0,
            price=0.1,
            tif="IOC",
            order_type="limit",
        )
