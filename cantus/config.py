"""cantus.config — 12-factor settings via pydantic-settings.

`cantus.config.Settings` is the single configuration object consumed by
`cantus.serve(...)`. Environment variables prefixed `CANTUS_SERVE_*` populate
fields with pydantic's standard type coercion. The `env_file` option is
intentionally NOT enabled in v0.4.0 — secret + .env management lands in
cantus-serve-security (v0.4.1). The module gates on `pydantic_settings` so a
missing SDK surfaces a clear ImportError with the install hint, mirroring
the `cantus.adapters.mcp` pattern.
"""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError as exc:
    raise ImportError(
        "cantus.config requires pydantic-settings. "
        "Run: pip install cantus[serve]"
    ) from exc


class Settings(BaseSettings):
    """12-factor configuration for `cantus.serve(...)`.

    Each field maps to an environment variable named
    ``CANTUS_SERVE_<UPPER_FIELD>`` (pydantic-settings handles the prefix
    + uppercase conversion). String env values are coerced into the
    declared field type by pydantic's standard validation pipeline.
    """

    model_config = SettingsConfigDict(env_prefix="CANTUS_SERVE_")

    host: str = "127.0.0.1"
    port: int = 8765
    dashboard: bool = True
    docs_url: str | None = "/docs"
    openapi_url: str | None = "/openapi.json"
    redoc_url: str | None = "/redoc"


__all__ = ["Settings"]
