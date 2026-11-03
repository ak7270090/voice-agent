"""Endpoints under /runtime are only for the agent runtime, which sends a shared bearer token."""

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from studio_backend.core.config import SettingsDep

BEARER_PREFIX = "Bearer "


def require_runtime_token(
    settings: SettingsDep, authorization: Annotated[str, Header()] = ""
) -> None:
    token = authorization.removeprefix(BEARER_PREFIX)
    expected = settings.runtime_api_token
    if not expected or not secrets.compare_digest(token, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid runtime token")


RuntimeAuthDep = Depends(require_runtime_token)
