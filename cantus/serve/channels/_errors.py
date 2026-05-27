"""cantus.serve.channels._errors — outbound failure exception."""

from __future__ import annotations


class ChannelSendError(Exception):
    """Raised when a webhook channel's outbound HTTP POST returns 4xx/5xx.

    Carries the status code, the first 200 bytes of the response body, and
    the provider name (``"line"`` or ``"telegram"``). The string form never
    references any Settings object or secret value — only the three caller-
    supplied attributes — so platform access tokens cannot leak into logs
    via exception chains.
    """

    def __init__(self, *, status_code: int, body_excerpt: str, provider: str) -> None:
        self.status_code = status_code
        self.body_excerpt = body_excerpt
        self.provider = provider
        super().__init__(
            f"{provider} send failed: HTTP {status_code} {body_excerpt}"
        )


__all__ = ["ChannelSendError"]
