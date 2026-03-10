"""Prediction-market client contract with explicit auth and trading guardrails."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

SignatureType = str
_ALLOWED_SIGNATURE_TYPES = {"eoa", "proxy", "safe"}
_ALLOWED_TIF = {"GTC", "FOK", "GTD", "FAK"}


class ClientStateError(RuntimeError):
    """Raised when an action is attempted in an invalid client state."""


@dataclass(frozen=True)
class APICredentials:
    """Scoped API credentials for authenticated venue actions."""

    key_id: str
    secret: str
    passphrase: str
    created_at: str


@dataclass(frozen=True)
class AuthContext:
    """Authentication context describing signer and wallet routing contract."""

    signer_id: str
    signature_type: SignatureType
    funder: str | None = None


class PredictionMarketClientContract:
    """Venue client guardrails for read-only and authenticated trading actions."""

    def __init__(self) -> None:
        self._authenticated = False
        self._auth_context: AuthContext | None = None
        self._api_credentials: APICredentials | None = None
        self._allowances: dict[str, bool] = {}
        self._audit_log: list[dict[str, Any]] = []

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit_log)

    def authenticate(self, context: AuthContext) -> None:
        signature_type = str(context.signature_type).strip().lower()
        if signature_type not in _ALLOWED_SIGNATURE_TYPES:
            raise ValueError(f"unsupported signature_type: {context.signature_type}")
        if signature_type in {"proxy", "safe"} and not str(context.funder or "").strip():
            raise ValueError("funder is required for proxy/safe signature types")
        self._authenticated = True
        self._auth_context = AuthContext(
            signer_id=str(context.signer_id).strip(),
            signature_type=signature_type,
            funder=str(context.funder).strip() if context.funder else None,
        )
        self._append_audit("auth.authenticate", {"signature_type": signature_type})

    def deauthenticate(self) -> None:
        self._authenticated = False
        self._auth_context = None
        self._api_credentials = None
        self._append_audit("auth.deauthenticate", {})

    def create_or_derive_api_creds(self, *, seed: str) -> APICredentials:
        self._require_authenticated()
        digest = hashlib.sha256(str(seed).encode("utf-8")).hexdigest()
        creds = APICredentials(
            key_id=f"key_{digest[:12]}",
            secret=f"sec_{digest[12:44]}",
            passphrase=f"pp_{digest[44:60]}",
            created_at=self._now_iso(),
        )
        self._api_credentials = creds
        self._append_audit("auth.create_or_derive_api_creds", {"key_id": creds.key_id})
        return creds

    def rotate_api_creds(self, *, seed: str) -> APICredentials:
        self._require_authenticated()
        creds = self.create_or_derive_api_creds(seed=seed)
        self._append_audit("auth.rotate_api_creds", {"key_id": creds.key_id})
        return creds

    def revoke_api_creds(self) -> None:
        self._require_authenticated()
        key_id = self._api_credentials.key_id if self._api_credentials else ""
        self._api_credentials = None
        self._append_audit("auth.revoke_api_creds", {"key_id": key_id})

    def set_allowance(self, *, asset: str, approved: bool) -> None:
        token = str(asset).strip().lower()
        if not token:
            raise ValueError("asset is required")
        self._allowances[token] = bool(approved)
        self._append_audit("allowance.set", {"asset": token, "approved": bool(approved)})

    def pretrade_allowance_check(self, required_assets: Iterable[str]) -> list[str]:
        missing: list[str] = []
        for asset in required_assets:
            token = str(asset).strip().lower()
            if not token:
                continue
            if not self._allowances.get(token, False):
                missing.append(token)
        return sorted(set(missing))

    def get_market_data(self, *, market_id: str) -> dict[str, Any]:
        token = str(market_id).strip()
        if not token:
            raise ValueError("market_id is required")
        self._append_audit("market.get", {"market_id": token})
        return {"market_id": token, "mode": "read_only", "ok": True}

    def create_order(
        self,
        *,
        token_id: str,
        side: str,
        size: float,
        price: float | None = None,
        tif: str = "GTC",
        order_type: str = "limit",
    ) -> dict[str, Any]:
        self._require_authenticated()
        self._require_api_creds()
        tif_token = str(tif).strip().upper()
        if tif_token not in _ALLOWED_TIF:
            raise ValueError(f"unsupported tif: {tif}")
        if str(order_type).strip().lower() == "limit" and price is None:
            raise ValueError("limit order requires price")
        payload = {
            "token_id": str(token_id).strip(),
            "side": str(side).strip().lower(),
            "size": float(size),
            "price": None if price is None else float(price),
            "tif": tif_token,
            "order_type": str(order_type).strip().lower(),
            "auth_mode": self._auth_context.signature_type if self._auth_context else "unknown",
        }
        self._append_audit("order.create", {"token_id": payload["token_id"], "tif": tif_token})
        return payload

    def post_order(self, order: dict[str, Any], *, required_assets: Iterable[str]) -> dict[str, Any]:
        self._require_authenticated()
        self._require_api_creds()
        missing_allowances = self.pretrade_allowance_check(required_assets)
        if missing_allowances:
            self._append_audit(
                "order.reject.missing_allowance",
                {"missing_allowances": missing_allowances, "token_id": order.get("token_id", "")},
            )
            raise ClientStateError(
                f"missing required allowances: {', '.join(sorted(missing_allowances))}"
            )
        self._append_audit("order.post", {"token_id": order.get("token_id", "")})
        return {
            "accepted": True,
            "order_id": f"ord_{hashlib.sha256(str(order).encode('utf-8')).hexdigest()[:16]}",
            "token_id": order.get("token_id", ""),
        }

    def post_orders_batch(
        self,
        *,
        orders: Iterable[dict[str, Any]],
        required_assets: Iterable[str],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for idx, order in enumerate(list(orders), start=1):
            try:
                posted = self.post_order(order, required_assets=required_assets)
                rows.append({"index": idx, "ok": True, "result": posted, "error": ""})
            except Exception as exc:  # noqa: BLE001
                rows.append({"index": idx, "ok": False, "result": {}, "error": str(exc)})
        self._append_audit("order.post_batch", {"count": len(rows)})
        return rows

    def _require_authenticated(self) -> None:
        if not self._authenticated or self._auth_context is None:
            raise ClientStateError("authenticated client state required")

    def _require_api_creds(self) -> None:
        if self._api_credentials is None:
            raise ClientStateError("api credentials required")

    def _append_audit(self, event: str, payload: dict[str, Any]) -> None:
        self._audit_log.append(
            {
                "event": str(event),
                "payload": dict(payload),
                "timestamp": self._now_iso(),
            }
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
