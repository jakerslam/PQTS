"""SEC EDGAR adapter utilities."""

from adapters.sec.client import SECClient, SECIdentityConfig, validate_sec_user_agent
from adapters.sec.companyconcept import (
    CompanyConceptPoint,
    ingest_companyconcept,
    parse_companyconcept,
    validate_concept,
    validate_taxonomy,
)
from adapters.sec.companyfacts import CompanyFactPoint, ingest_companyfacts, traverse_companyfacts
from adapters.sec.issuer_registry import IssuerRecord, ingest_company_tickers, parse_company_tickers
from adapters.sec.submissions import SubmissionRecord, ingest_submissions, parse_submissions_recent
from adapters.sec.utils import normalize_cik

__all__ = [
    "CompanyConceptPoint",
    "CompanyFactPoint",
    "IssuerRecord",
    "SECClient",
    "SECIdentityConfig",
    "SubmissionRecord",
    "ingest_companyconcept",
    "ingest_companyfacts",
    "ingest_company_tickers",
    "ingest_submissions",
    "parse_companyconcept",
    "parse_company_tickers",
    "parse_submissions_recent",
    "validate_concept",
    "validate_taxonomy",
    "traverse_companyfacts",
    "normalize_cik",
    "validate_sec_user_agent",
]
