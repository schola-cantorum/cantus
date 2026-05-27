"""cantus.serve.channels — channel adapters.

* v0.4.5: LINE and Telegram inbound HTTP webhook receivers + outbound reply
  clients (each conforms to :class:`cantus.serve.channel.WebhookChannel`).
* v0.4.6: Discord Gateway WebSocket bot + Ed25519-signed interactions HTTP
  endpoint (conforms to BOTH :class:`cantus.serve.channel.RealtimeChannel`
  and :class:`cantus.serve.channel.WebhookChannel`).
* v0.4.7: Google Chat over Cloud Pub/Sub streaming pull + Chat REST API
  outbound (conforms to :class:`cantus.serve.channel.RealtimeChannel`
  only — Pub/Sub pull is the sole inbound transport, no HTTP webhook
  route is required).
"""

from __future__ import annotations

from cantus.serve.channels._errors import ChannelSendError
from cantus.serve.channels.discord import (
    DiscordRealtimeChannel,
    DiscordSignatureError,
)
from cantus.serve.channels.googlechat import GoogleChatPubSubChannel
from cantus.serve.channels.line import LineWebhookChannel
from cantus.serve.channels.telegram import TelegramWebhookChannel

__all__ = [
    "ChannelSendError",
    "DiscordRealtimeChannel",
    "DiscordSignatureError",
    "GoogleChatPubSubChannel",
    "LineWebhookChannel",
    "TelegramWebhookChannel",
]
