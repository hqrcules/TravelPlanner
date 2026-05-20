from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import Settings, get_settings

_basic_scheme = HTTPBasic(auto_error=True)


def verify_basic_auth(
    credentials: HTTPBasicCredentials = Depends(_basic_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    expected_user = settings.basic_auth_user.encode("utf-8")
    expected_pass = settings.basic_auth_pass.get_secret_value().encode("utf-8")
    provided_user = credentials.username.encode("utf-8")
    provided_pass = credentials.password.encode("utf-8")

    user_ok = secrets.compare_digest(expected_user, provided_user)
    pass_ok = secrets.compare_digest(expected_pass, provided_pass)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
