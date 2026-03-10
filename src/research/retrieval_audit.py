"""Retrieval recall@k reporting and ranked-list audit persistence."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from core.persistence import EventPersistenceStore

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(str(text or "").lower()))


@dataclass(frozen=True)
class RankedDocument:
    rank: int
    document_id: str
    source_ref: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalRecallReport:
    query: str
    relevant_count: int
    recall_at_k: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RetrievalAuditRecorder:
    """Build full rankings, compute recall, and persist audit artifacts."""

    def __init__(self, *, persistence_store: EventPersistenceStore | None = None) -> None:
        self._store = persistence_store

    def build_ranked_list(
        self,
        *,
        query: str,
        corpus: Iterable[dict[str, Any]],
    ) -> list[RankedDocument]:
        q_tokens = _tokenize(query)
        scored: list[tuple[float, str, str]] = []
        for row in list(corpus):
            if not isinstance(row, dict):
                continue
            doc_id = str(row.get("document_id", "")).strip()
            text = str(row.get("text", "")).strip()
            if not doc_id or not text:
                continue
            score = len(q_tokens.intersection(_tokenize(text))) / max(len(q_tokens), 1)
            scored.append((float(score), doc_id, str(row.get("source_ref", ""))))

        scored.sort(key=lambda item: (-item[0], item[1]))
        ranked: list[RankedDocument] = []
        for idx, (score, doc_id, source_ref) in enumerate(scored, start=1):
            ranked.append(
                RankedDocument(rank=idx, document_id=doc_id, source_ref=source_ref, score=score)
            )
        return ranked

    def compute_recall_report(
        self,
        *,
        query: str,
        ranked: list[RankedDocument],
        relevant_document_ids: set[str] | list[str] | tuple[str, ...],
        ks: tuple[int, ...] = (1, 3, 5, 10),
    ) -> RetrievalRecallReport:
        relevant = {str(item) for item in relevant_document_ids}
        relevant_count = len(relevant)
        recall: dict[str, float] = {}
        if relevant_count == 0:
            for k in ks:
                recall[f"recall@{int(k)}"] = 0.0
            return RetrievalRecallReport(query=query, relevant_count=0, recall_at_k=recall)

        ranked_ids = [row.document_id for row in ranked]
        for k in ks:
            top = set(ranked_ids[: max(int(k), 1)])
            hit_count = len(top.intersection(relevant))
            recall[f"recall@{int(k)}"] = float(hit_count / relevant_count)
        return RetrievalRecallReport(query=query, relevant_count=relevant_count, recall_at_k=recall)

    def record_audit(
        self,
        *,
        query: str,
        corpus: Iterable[dict[str, Any]],
        relevant_document_ids: set[str] | list[str] | tuple[str, ...],
        ks: tuple[int, ...] = (1, 3, 5, 10),
        timestamp: str | None = None,
    ) -> tuple[list[RankedDocument], RetrievalRecallReport]:
        ranked = self.build_ranked_list(query=query, corpus=corpus)
        report = self.compute_recall_report(
            query=query,
            ranked=ranked,
            relevant_document_ids=relevant_document_ids,
            ks=ks,
        )

        if self._store is not None:
            ts = str(timestamp) if timestamp else None
            self._store.append(
                category="retrieval_audit_ranked_list",
                payload={
                    "query": query,
                    "ranked": [row.to_dict() for row in ranked],
                },
                timestamp=ts,
            )
            self._store.append(
                category="retrieval_audit_recall_report",
                payload=report.to_dict(),
                timestamp=ts,
            )
        return ranked, report
