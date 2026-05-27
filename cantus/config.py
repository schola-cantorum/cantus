"""cantus.config — 12-factor settings via pydantic-settings.

`cantus.config.Settings` is the single configuration object consumed by
`cantus.serve(...)`. Environment variables prefixed `CANTUS_SERVE_*` populate
fields with pydantic's standard type coercion. v0.4.1 (cantus-serve-security)
adds the opt-in auth gate fields (`auth_mode`, `api_key`, `bearer_token`,
`dashboard_requires_auth`) backed by `pydantic.SecretStr` so token values are
masked in `repr`, JSON dumps, and the generated OpenAPI schema. The `env_file`
option is still intentionally NOT enabled — `.env` loading remains out of
scope. The module gates on `pydantic_settings` so a missing SDK surfaces a
clear ImportError with the install hint, mirroring the `cantus.adapters.mcp`
pattern.
"""

from __future__ import annotations

from enum import Enum

from pydantic import SecretStr

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError as exc:
    raise ImportError(
        "cantus.config requires pydantic-settings. "
        "Run: pip install cantus[serve]"
    ) from exc


class AuthMode(str, Enum):
    """Authentication mode for `cantus.serve(...)`.

    Three modes:

    * ``NONE`` — no auth gate (v0.4.0 behaviour, the default).
    * ``BEARER`` — `Authorization: Bearer <token>` header required.
    * ``API_KEY`` — `X-API-Key: <token>` header required.

    The enum is `str`-valued so pydantic-settings can coerce the
    `CANTUS_SERVE_AUTH_MODE` env variable (a string) directly to a member.
    """

    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api-key"


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

    # v0.4.1 cantus-serve-security: opt-in auth gate.
    auth_mode: AuthMode = AuthMode.NONE
    api_key: SecretStr | None = None
    bearer_token: SecretStr | None = None
    dashboard_requires_auth: bool = True

    # v0.4.5 cantus-channel-gateway-webhook: per-platform channel secrets.
    channel_line_secret: SecretStr | None = None
    channel_line_access_token: SecretStr | None = None
    channel_telegram_secret_token: SecretStr | None = None
    channel_telegram_bot_token: SecretStr | None = None

    # v0.4.6 cantus-channel-gateway-realtime: Discord bot + Ed25519 public
    # key are SecretStr; application_id is a publicly-visible identifier
    # (shows up in OAuth invite URLs) and stays plain str.
    channel_discord_bot_token: SecretStr | None = None
    channel_discord_public_key: SecretStr | None = None
    channel_discord_application_id: str | None = None

    # v0.4.7 cantus-channel-gateway-pubsub: Google Chat over Pub/Sub.
    # All three are plain str (NOT SecretStr): the credentials_path is a
    # filesystem location pointer (the JSON file's contents are sensitive,
    # but the path itself is not), and the subscription path and space ID
    # are publicly-assigned Google identifiers.
    channel_google_chat_credentials_path: str | None = None
    channel_google_chat_subscription: str | None = None
    channel_google_chat_space: str | None = None


__all__ = ["AuthMode", "Settings"]
