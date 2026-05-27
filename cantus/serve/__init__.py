"""cantus.serve — FastAPI app factory for cantus Skill registry.

Importing this module triggers the FastAPI SDK import. When `cantus[serve]`
is not installed, the import fails with an actionable :class:`ImportError`
pointing to the install command. Task 7.2 refines the gate to also cover
`uvicorn` and `pydantic_settings`.
"""

from __future__ import annotations

try:
    import fastapi as _fastapi  # noqa: F401
    import uvicorn as _uvicorn  # noqa: F401
    import pydantic_settings as _pydantic_settings  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "cantus.serve requires the FastAPI, Uvicorn, and pydantic-settings SDKs. "
        "Run: pip install cantus[serve]"
    ) from exc

from cantus.config import AuthMode
from cantus.serve.app import serve
from cantus.serve.channel import Channel, LocalMockReceiver, WebhookChannel
from cantus.serve.channels._errors import ChannelSendError
from cantus.serve.channels.line import LineWebhookChannel
from cantus.serve.channels.telegram import TelegramWebhookChannel
from cantus.serve.security import require_auth

__all__ = [
    "AuthMode",
    "Channel",
    "ChannelSendError",
    "LineWebhookChannel",
    "LocalMockReceiver",
    "TelegramWebhookChannel",
    "WebhookChannel",
    "require_auth",
    "serve",
]
