"""Authentication and role guards for the PQTS API service."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Callable

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


class APIRole(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


ROLE_RANK: dict[APIRole, int] = {
    APIRole.VIEWER: 0,
    APIRole.OPERATOR: 1,
    APIRole.ADMIN: 2,
}


@dataclass(frozen=True)
class APIIdentity:
    subject: str
    role: APIRole
    token: str
    auth_scheme: str

    def to_dict(self) -> dict[str, str]:
        return {
            "subject": self.subject,
            "role": self.role.value,
            "auth_scheme": self.auth_scheme,
        }


def _parse_role(raw: str) -> APIRole:
    normalized = raw.strip().lower()
    for role in APIRole:
        if role.value == normalized:
            return role
    raise ValueError(f"Unsupported role value: {raw!r}")


def build_token_store(raw: str) -> dict[str, APIRole]:
    """Parse token mapping string: `token_a:admin,token_b:viewer`."""
    mapping: dict[str, APIRole] = {}
    raw = raw.strip()
    if not raw:
        return {
            "pqts-dev-admin-token": APIRole.ADMIN,
            "pqts-dev-operator-token": APIRole.OPERATOR,
            "pqts-dev-viewer-token": APIRole.VIEWER,
        }

    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        token, sep, role_raw = item.partition(":")
        if not sep:
            raise ValueError(
                "Invalid token mapping entry. Expected `token:role` pairs separated by commas."
            )
        token_value = token.strip()
        if not token_value:
            raise ValueError("Token value cannot be empty in auth mapping.")
        mapping[token_value] = _parse_role(role_raw)
    if not mapping:
        raise ValueError("Auth token mapping cannot be empty.")
    return mapping


def get_token_store(request: Request) -> dict[str, APIRole]:
    mapping = getattr(request.app.state, "token_store", None)
    if isinstance(mapping, dict):
        return mapping
    return build_token_store("")


_bearer = HTTPBearer(auto_error=False)


def require_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    token_store: Annotated[dict[str, APIRole], Depends(get_token_store)],
    session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> APIIdentity:
    token = ""
    auth_scheme = ""
    if credentials is not None:
        token = credentials.credentials.strip()
        auth_scheme = "bearer"
    elif session_token:
        token = session_token.strip()
        auth_scheme = "session"

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    role = token_store.get(token)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    return APIIdentity(
        subject=f"user:{token[:8]}",
        role=role,
        token=token,
        auth_scheme=auth_scheme,
    )


def role_guard(min_role: APIRole) -> Callable[[APIIdentity], APIIdentity]:
    def dependency(
        identity: Annotated[APIIdentity, Depends(require_identity)],
    ) -> APIIdentity:
        if ROLE_RANK[identity.role] < ROLE_RANK[min_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role; requires at least `{min_role.value}`.",
            )
        return identity

    return dependency


require_operator = role_guard(APIRole.OPERATOR)
require_admin = role_guard(APIRole.ADMIN)
