from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

_access_token_var: ContextVar[Optional[str]] = ContextVar("access_token", default=None)


def set_access_token(token: Optional[str]) -> None:
    _access_token_var.set(token)


def get_access_token() -> Optional[str]:
    return _access_token_var.get()


__all__ = ["get_access_token", "set_access_token"]
