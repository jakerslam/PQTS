"""SQL persistence layer for API resources (Postgres-first, SQLite-compatible)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import Request
from sqlalchemy import Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from contracts.api import (
    AccountSummary,
    FillSnapshot,
    OrderSnapshot,
    PnLSnapshot,
    PositionSnapshot,
    RiskStateSnapshot,
)
from services.api.state import APIRuntimeStore


class Base(DeclarativeBase):
    pass


class AccountRow(Base):
    __tablename__ = "api_accounts"
    account_id: Mapped[str] = mapped_column(primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class PositionRow(Base):
    __tablename__ = "api_positions"
    position_id: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class OrderRow(Base):
    __tablename__ = "api_orders"
    order_id: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class FillRow(Base):
    __tablename__ = "api_fills"
    fill_id: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class PnLRow(Base):
    __tablename__ = "api_pnl_snapshots"
    snapshot_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class RiskStateRow(Base):
    __tablename__ = "api_risk_states"
    account_id: Mapped[str] = mapped_column(primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class RiskIncidentRow(Base):
    __tablename__ = "api_risk_incidents"
    incident_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class OperatorActionRow(Base):
    __tablename__ = "api_operator_actions"
    action_id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[str] = mapped_column(index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class PromotionRecordRow(Base):
    __tablename__ = "api_promotion_records"
    strategy_id: Mapped[str] = mapped_column(primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


def _ensure_sqlite_parent(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    db_path = Path(url[len("sqlite:///") :]).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True)


def _loads(payload: str) -> dict[str, Any]:
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise TypeError("Expected JSON object payload.")
    return parsed


@dataclass
class APIPersistence:
    database_url: str
    session_factory: sessionmaker[Session]

    @classmethod
    def connect(cls, database_url: str) -> "APIPersistence | None":
        value = database_url.strip()
        if not value:
            return None
        value = _normalize_database_url(value)
        _ensure_sqlite_parent(value)
        try:
            engine = create_engine(value, future=True, pool_pre_ping=True)
        except (ModuleNotFoundError, ImportError):
            # Keep API startup non-fatal when optional Postgres driver/libpq is unavailable.
            return None
        session_factory = sessionmaker(bind=engine, future=True)
        return cls(database_url=value, session_factory=session_factory)

    def initialize(self) -> None:
        engine = self.session_factory.kw["bind"]
        Base.metadata.create_all(bind=engine)

    def seed_if_empty(self, store: APIRuntimeStore) -> None:
        with self.session_factory() as session:
            existing = session.scalar(select(AccountRow.account_id).limit(1))
            if existing:
                return
        for account in store.accounts.values():
            self.upsert_account(account)
        for rows in store.positions.values():
            for row in rows:
                self.append_position(row)
        for rows in store.orders.values():
            for row in rows:
                self.append_order(row)
        for rows in store.fills.values():
            for row in rows:
                self.append_fill(row)
        for rows in store.pnl_snapshots.values():
            for row in rows:
                self.append_pnl_snapshot(row)
        for risk in store.risk_states.values():
            self.upsert_risk_state(risk)
        for incidents in store.risk_incidents.values():
            for incident in incidents:
                self.append_risk_incident(incident)
        for action in store.operator_actions:
            self.append_operator_action(action)
        for record in store.promotion_records.values():
            self.upsert_promotion_record(record)

    def hydrate_store(self, store: APIRuntimeStore) -> None:
        store.accounts = {}
        store.positions = {}
        store.orders = {}
        store.fills = {}
        store.pnl_snapshots = {}
        store.risk_states = {}
        store.risk_incidents = {}
        store.operator_actions = []
        store.promotion_records = {}

        with self.session_factory() as session:
            for row in session.scalars(select(AccountRow)).all():
                account = AccountSummary.from_dict(_loads(row.payload))
                store.accounts[account.account_id] = account

            for row in session.scalars(select(PositionRow)).all():
                snapshot = PositionSnapshot.from_dict(_loads(row.payload))
                store.positions.setdefault(snapshot.account_id, []).append(snapshot)

            for row in session.scalars(select(OrderRow)).all():
                snapshot = OrderSnapshot.from_dict(_loads(row.payload))
                store.orders.setdefault(snapshot.account_id, []).append(snapshot)

            for row in session.scalars(select(FillRow)).all():
                snapshot = FillSnapshot.from_dict(_loads(row.payload))
                store.fills.setdefault(snapshot.account_id, []).append(snapshot)

            for row in session.scalars(select(PnLRow)).all():
                snapshot = PnLSnapshot.from_dict(_loads(row.payload))
                store.pnl_snapshots.setdefault(snapshot.account_id, []).append(snapshot)

            for row in session.scalars(select(RiskStateRow)).all():
                snapshot = RiskStateSnapshot.from_dict(_loads(row.payload))
                store.risk_states[snapshot.account_id] = snapshot

            for row in session.scalars(select(RiskIncidentRow)).all():
                incident = _loads(row.payload)
                account_id = str(incident.get("account_id", "paper-main"))
                store.risk_incidents.setdefault(account_id, []).append(incident)

            action_rows = session.scalars(
                select(OperatorActionRow).order_by(OperatorActionRow.created_at.desc())
            ).all()
            store.operator_actions = [_loads(row.payload) for row in action_rows]

            for row in session.scalars(select(PromotionRecordRow)).all():
                record = _loads(row.payload)
                strategy_id = str(record.get("strategy_id", row.strategy_id)).strip() or row.strategy_id
                store.promotion_records[strategy_id] = record

    def upsert_account(self, snapshot: AccountSummary) -> None:
        with self.session_factory() as session:
            row = AccountRow(account_id=snapshot.account_id, payload=_dumps(snapshot.to_dict()))
            session.merge(row)
            session.commit()

    def get_account(self, account_id: str) -> AccountSummary | None:
        with self.session_factory() as session:
            row = session.get(AccountRow, account_id)
            if row is None:
                return None
            return AccountSummary.from_dict(_loads(row.payload))

    def append_position(self, snapshot: PositionSnapshot) -> None:
        with self.session_factory() as session:
            row = PositionRow(
                position_id=snapshot.position_id,
                account_id=snapshot.account_id,
                payload=_dumps(snapshot.to_dict()),
            )
            session.merge(row)
            session.commit()

    def list_positions(self, account_id: str) -> list[PositionSnapshot]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(PositionRow).where(PositionRow.account_id == account_id)
            ).all()
            return [PositionSnapshot.from_dict(_loads(row.payload)) for row in rows]

    def append_order(self, snapshot: OrderSnapshot) -> None:
        with self.session_factory() as session:
            row = OrderRow(
                order_id=snapshot.order_id,
                account_id=snapshot.account_id,
                payload=_dumps(snapshot.to_dict()),
            )
            session.merge(row)
            session.commit()

    def list_orders(self, account_id: str) -> list[OrderSnapshot]:
        with self.session_factory() as session:
            rows = session.scalars(select(OrderRow).where(OrderRow.account_id == account_id)).all()
            return [OrderSnapshot.from_dict(_loads(row.payload)) for row in rows]

    def append_fill(self, snapshot: FillSnapshot) -> None:
        with self.session_factory() as session:
            row = FillRow(
                fill_id=snapshot.fill_id,
                account_id=snapshot.account_id,
                payload=_dumps(snapshot.to_dict()),
            )
            session.merge(row)
            session.commit()

    def list_fills(self, account_id: str) -> list[FillSnapshot]:
        with self.session_factory() as session:
            rows = session.scalars(select(FillRow).where(FillRow.account_id == account_id)).all()
            return [FillSnapshot.from_dict(_loads(row.payload)) for row in rows]

    def append_pnl_snapshot(self, snapshot: PnLSnapshot) -> None:
        with self.session_factory() as session:
            row = PnLRow(account_id=snapshot.account_id, payload=_dumps(snapshot.to_dict()))
            session.add(row)
            session.commit()

    def list_pnl_snapshots(self, account_id: str) -> list[PnLSnapshot]:
        with self.session_factory() as session:
            rows = session.scalars(select(PnLRow).where(PnLRow.account_id == account_id)).all()
            return [PnLSnapshot.from_dict(_loads(row.payload)) for row in rows]

    def upsert_risk_state(self, snapshot: RiskStateSnapshot) -> None:
        with self.session_factory() as session:
            row = RiskStateRow(account_id=snapshot.account_id, payload=_dumps(snapshot.to_dict()))
            session.merge(row)
            session.commit()

    def get_risk_state(self, account_id: str) -> RiskStateSnapshot | None:
        with self.session_factory() as session:
            row = session.get(RiskStateRow, account_id)
            if row is None:
                return None
            return RiskStateSnapshot.from_dict(_loads(row.payload))

    def append_risk_incident(self, incident: dict[str, Any]) -> None:
        with self.session_factory() as session:
            row = RiskIncidentRow(
                account_id=str(incident.get("account_id", "paper-main")),
                payload=_dumps(dict(incident)),
            )
            session.add(row)
            session.commit()

    def list_risk_incidents(self, account_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(RiskIncidentRow).where(RiskIncidentRow.account_id == account_id)
            ).all()
            return [_loads(row.payload) for row in rows]

    def append_operator_action(self, action: dict[str, Any]) -> None:
        action_id = str(action.get("id", "")).strip()
        if not action_id:
            return
        with self.session_factory() as session:
            row = OperatorActionRow(
                action_id=action_id,
                created_at=str(action.get("created_at", "")),
                payload=_dumps(dict(action)),
            )
            session.merge(row)
            session.commit()

    def list_operator_actions(self, limit: int = 100) -> list[dict[str, Any]]:
        bounded = max(1, int(limit))
        with self.session_factory() as session:
            rows = session.scalars(
                select(OperatorActionRow)
                .order_by(OperatorActionRow.created_at.desc())
                .limit(bounded)
            ).all()
            return [_loads(row.payload) for row in rows]

    def upsert_promotion_record(self, record: dict[str, Any]) -> None:
        strategy_id = str(record.get("strategy_id", "")).strip()
        if not strategy_id:
            return
        with self.session_factory() as session:
            row = PromotionRecordRow(
                strategy_id=strategy_id,
                payload=_dumps(dict(record)),
            )
            session.merge(row)
            session.commit()

    def list_promotion_records(self) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.scalars(select(PromotionRecordRow)).all()
            return [_loads(row.payload) for row in rows]


def get_persistence(request: Request) -> APIPersistence | None:
    persistence = getattr(request.app.state, "persistence", None)
    if isinstance(persistence, APIPersistence):
        return persistence
    return None
