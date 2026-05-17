"""Shared helpers for cloud provider adapters."""

from __future__ import annotations

import os


class MissingAPIKeyError(RuntimeError):
    """Raised when an adapter cannot find an API key in args or environment."""


def resolve_api_key(explicit: str | None, env_var: str) -> str:
    """Return the explicit key, falling back to the named environment variable.

    Raises `MissingAPIKeyError` with a Chinese guidance message (same voice as
    `cantus.model.loader.MountError`) when both sources are empty.
    """
    if explicit:
        return explicit
    from_env = os.environ.get(env_var)
    if from_env:
        return from_env
    raise MissingAPIKeyError(
        f"找不到 API key。請於建構子傳入 api_key=... 參數，"
        f"或設定環境變數 {env_var}。"
    )
