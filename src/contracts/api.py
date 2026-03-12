"""Canonical API/domain schemas shared across API, streams, and UI layers."""

from __future__ import annotations

from dataclasses import dataclass as _raw_dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
from sys import version_info
from typing import Any, Mapping, Sequence


def dataclass(*args: Any, **kwargs: Any) -> Any:
    """Compatibility wrapper for environments without dataclass slots."""
    if version_info < (3, 10):
        kwargs.pop("slots", None)
    return _raw_dataclass(*args, **kwargs)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    if isinstance(value, tuple):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    return value


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _dataclass_from_dict(cls: type, data: Mapping[str, Any]) -> Any:
    kwargs: dict[str, Any] = {}
    for item in fields(cls):
        if item.name not in data:
            continue
        value = data[item.name]
        if value is None:
            kwargs[item.name] = None
            continue
        if item.type is datetime:
            kwargs[item.name] = _parse_datetime(value)
        elif isinstance(item.type, type) and issubclass(item.type, Enum):
            kwargs[item.name] = item.type(value)
        else:
            kwargs[item.name] = value
    return cls(**kwargs)


class PositionDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    OCO = "oco"
    OTO = "oto"
    POST_ONLY = "post_only"
    REDUCE_ONLY = "reduce_only"
    CONTINGENT = "contingent"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"
    POV = "pov"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


class RiskLevel(str, Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    CRITICAL = "critical"


class ToolStatus(str, Enum):
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"


class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    PROVIDER = "provider"
    SYSTEM = "system"


@dataclass(slots=True)
class AccountSummary:
    account_id: str
    cash: float
    equity: float
    buying_power: float
    margin_used: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    currency: str = "USD"
    as_of: datetime = field(default_factory=_now_utc)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {f.name: _serialize(getattr(self, f.name)) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AccountSummary":
        return _dataclass_from_dict(cls, data)


@dataclass(slots=True)
class PositionSnapshot:
    position_id: str
    account_id: str
    symbol: str
    direction: PositionDirection
    quantity: float
    avg_price: float
    mark_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    as_of: datetime = field(default_factory=_now_utc)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {f.name: _serialize(getattr(self, f.name)) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PositionSnapshot":
        return _dataclass_from_dict(cls, data)


@dataclass(slots=True)
class OrderSnapshot:
    order_id: str
    account_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    quantity: float
    filled_quantity: float
    remaining_quantity: float
    submitted_at: datetime
    updated_at: datetime
    limit_price: float | None = None
    stop_price: float | None = None
    time_in_force: TimeInForce = TimeInForce.DAY
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {f.name: _serialize(getattr(self, f.name)) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OrderSnapshot":
        return _dataclass_from_dict(cls, data)


@dataclass(slots=True)
class FillSnapshot:
    fill_id: str
    order_id: str
    account_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    fee: float
    venue: str
    executed_at: datetime
    liquidity: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {f.name: _serialize(getattr(self, f.name)) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FillSnapshot":
        return _dataclass_from_dict(cls, data)


@dataclass(slots=True)
class PnLSnapshot:
    account_id: str
    period_start: datetime
    period_end: datetime
    realized_pnl: float
    unrealized_pnl: float
    gross_pnl: float
    net_pnl: float
    fees: float
    as_of: datetime = field(default_factory=_now_utc)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {f.name: _serialize(getattr(self, f.name)) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PnLSnapshot":
        return _dataclass_from_dict(cls, data)


@dataclass(slots=True)
class RiskStateSnapshot:
    account_id: str
    risk_level: RiskLevel
    max_drawdown: float
    current_drawdown: float
    var_95: float
    exposure: float
    kill_switch_active: bool
    reasons: list[str] = field(default_factory=list)
    as_of: datetime = field(default_factory=_now_utc)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {f.name: _serialize(getattr(self, f.name)) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RiskStateSnapshot":
        return _dataclass_from_dict(cls, data)


@dataclass(slots=True)
class ToolPayload:
    tool_name: str
    invocation_id: str
    status: ToolStatus
    args: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: "ErrorEnvelope | None" = None
    started_at: datetime = field(default_factory=_now_utc)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        values = {f.name: _serialize(getattr(self, f.name)) for f in fields(self)}
        if self.error is not None:
            values["error"] = self.error.to_dict()
        return values

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ToolPayload":
        parsed = dict(data)
        if "error" in parsed and isinstance(parsed["error"], Mapping):
            parsed["error"] = ErrorEnvelope.from_dict(parsed["error"])
        return _dataclass_from_dict(cls, parsed)


@dataclass(slots=True)
class ErrorEnvelope:
    code: str
    message: str
    category: ErrorCategory
    retryable: bool = False
    trace_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=_now_utc)

    def to_dict(self) -> dict[str, Any]:
        return {f.name: _serialize(getattr(self, f.name)) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ErrorEnvelope":
        return _dataclass_from_dict(cls, data)


def batch_to_dict(items: Sequence[Any]) -> list[dict[str, Any]]:
    """Serialize a sequence of schema instances into primitive dicts."""
    return [item.to_dict() for item in items]
