"""cantus.serve — FastAPI app factory for cantus Tool registry.

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

from typing import Any

from cantus._deprecation import warn_legacy
from cantus.config import AuthMode
from cantus.serve.app import serve
from cantus.serve.channel import (
    Channel,
    LocalMockReceiver,
    QueueIntrospectable,
    RealtimeChannel,
    WebhookChannel,
)
from cantus.serve.channels._errors import ChannelSendError
from cantus.serve.channels.discord import (
    DiscordRealtimeChannel,
    DiscordSignatureError,
)
from cantus.serve.channels.googlechat import GoogleChatPubSubChannel
from cantus.serve.channels.line import LineWebhookChannel
from cantus.serve.channels.telegram import TelegramWebhookChannel
from cantus.serve.introspection import (
    DataflowEdge,
    DataflowGraph,
    DataflowNode,
    IntrospectionSnapshot,
    PermissionsSnapshot,
    QueueEntry,
    SessionEntry,
    SessionTracker,
    ToolEntry,
    WorkflowStep,
    WorkflowTrace,
    register_introspection_routes,
)
from cantus.serve.security import require_auth

__all__ = [
    "AuthMode",
    "Channel",
    "ChannelSendError",
    "DataflowEdge",
    "DataflowGraph",
    "DataflowNode",
    "DiscordRealtimeChannel",
    "DiscordSignatureError",
    "GoogleChatPubSubChannel",
    "IntrospectionSnapshot",
    "LineWebhookChannel",
    "LocalMockReceiver",
    "PermissionsSnapshot",
    "QueueEntry",
    "QueueIntrospectable",
    "RealtimeChannel",
    "SessionEntry",
    "SessionTracker",
    "TelegramWebhookChannel",
    "ToolEntry",
    "WebhookChannel",
    "WorkflowStep",
    "WorkflowTrace",
    "register_introspection_routes",
    "require_auth",
    "serve",
]


def __getattr__(name: str) -> Any:
    """Serve the legacy name as `ToolEntry`, with a deprecation warning."""
    if name == "SkillEntry":  # legacy-alias
        warn_legacy("W6")
        return ToolEntry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
