"""Tests for retrieval ranked-list audit and recall reporting."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.persistence import EventPersistenceStore
from research.retrieval_audit import RetrievalAuditRecorder


def _corpus() -> list[dict[str, str]]:
    return [
        {"document_id": "doc_a", "source_ref": "a", "text": "Revenue grew in Q4 and margin rose."},
        {"document_id": "doc_b", "source_ref": "b", "text": "Operating margin was 18.2 in Q4."},
        {"document_id": "doc_c", "source_ref": "c", "text": "Weather forecast shifted lower."},
    ]


def test_compute_recall_report_values() -> None:
    recorder = RetrievalAuditRecorder()
    ranked = recorder.build_ranked_list(query="Q4 margin", corpus=_corpus())
    report = recorder.compute_recall_report(
        query="Q4 margin",
        ranked=ranked,
        relevant_document_ids={"doc_b"},
        ks=(1, 2),
    )
    assert report.recall_at_k["recall@1"] in {0.0, 1.0}
    assert report.recall_at_k["recall@2"] == 1.0


def test_record_audit_persists_ranked_list_and_report(tmp_path: Path) -> None:
    store = EventPersistenceStore(dsn=f"sqlite:///{tmp_path}/audit.db")
    recorder = RetrievalAuditRecorder(persistence_store=store)
    ranked, report = recorder.record_audit(
        query="Q4 margin",
        corpus=_corpus(),
        relevant_document_ids={"doc_a", "doc_b"},
        ks=(1, 3),
        timestamp="2026-03-10T00:00:00+00:00",
    )
    assert len(ranked) == 3
    assert report.relevant_count == 2

    ranked_rows = store.read(category="retrieval_audit_ranked_list", limit=10)
    report_rows = store.read(category="retrieval_audit_recall_report", limit=10)
    assert len(ranked_rows) == 1
    assert len(report_rows) == 1
    assert ranked_rows[0].payload["query"] == "Q4 margin"
