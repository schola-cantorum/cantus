"""Bridge a Tier 2 ChatModel into a Tier 1 ModelHandle.

Agents consume the Tier 1 `cantus.core.agent.ModelHandle` Protocol —
`.generate(prompt: str) -> str`. A `ChatModel` (Tier 2) speaks
`chat(messages, tools=None) -> ChatResponse` instead, so callers wanting to
use a multi-provider adapter inside an existing `Agent` must wrap it with
this bridge.

The bridge is deliberately a separate class instead of a Protocol method on
`ChatModel` itself — keeping the wrap explicit means students and reviewers
can see the conversion happen, and Agent code stays unaware that Tier 2
even exists (see model-providers spec: "no isinstance branches in Agent").
"""

from __future__ import annotations

from typing import Any

from cantus.model.chat import ChatModel, Message


class ChatModelAsHandle:
    """Wrap a `ChatModel` so it satisfies the Tier 1 `ModelHandle` Protocol.

    Usage::

        from cantus import Agent, load_chat_model, ChatModelAsHandle

        chat = load_chat_model("anthropic/claude-sonnet-4-6")
        agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))

    The optional `system` argument becomes the leading `system`-role message
    on every `generate` call. Pass `None` (the default) or `""` to omit it.
    """

    def __init__(self, chat_model: ChatModel, system: str | None = None) -> None:
        self._chat = chat_model
        self._system = system

    def generate(self, prompt: str, **kwargs: Any) -> str:
        messages: list[Message] = []
        if self._system:
            messages.append(Message(role="system", content=self._system))
        messages.append(Message(role="user", content=prompt))
        response = self._chat.chat(messages, **kwargs)
        return response.message.content
