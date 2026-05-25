"""Contract tests for OllamaChatModel actionable connection-error wrapping.

When the local Ollama daemon is not reachable, the underlying openai SDK
raises ``openai.APIConnectionError`` with a long httpx-laden stack trace
that is unhelpful to students. ``OllamaChatModel.chat`` and
``OllamaChatModel.stream`` MUST re-raise as ``ConnectionError`` with an
actionable message naming the daemon URL, ``ollama serve``, and the
install link. All other openai exception types MUST propagate unchanged.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from cantus.model.chat import Message
from cantus.model.providers.ollama import OllamaChatModel


def _install_failing_openai_client(monkeypatch, exc: Exception) -> None:
    """Replace ``openai.OpenAI`` with a fake client whose ``create`` raises ``exc``."""

    def _fake_create(**_kwargs: Any) -> Any:
        raise exc

    class _Client:
        chat = SimpleNamespace(completions=SimpleNamespace(create=_fake_create))

    import openai

    monkeypatch.setattr(openai, "OpenAI", lambda **_kw: _Client())


def _required_substrings(base_url: str) -> tuple[str, ...]:
    return (
        "Cannot reach Ollama daemon at ",
        base_url,
        "`ollama serve`",
        "https://ollama.com/download",
    )


# ---------- chat() wraps APIConnectionError ---------------------------------


def test_chat_apiconnectionerror_re_raises_connectionerror(monkeypatch):
    import openai

    original = openai.APIConnectionError(message="boom", request=None)  # type: ignore[arg-type]
    _install_failing_openai_client(monkeypatch, original)

    model = OllamaChatModel(model_id="gemma3:4b")
    with pytest.raises(ConnectionError) as exc_info:
        model.chat([Message(role="user", content="hi")])

    msg = str(exc_info.value)
    for substring in _required_substrings("http://localhost:11434/v1"):
        assert substring in msg, f"missing substring {substring!r} in {msg!r}"
    assert exc_info.value.__cause__ is original


# ---------- stream() wraps APIConnectionError ------------------------------


def test_stream_apiconnectionerror_re_raises_connectionerror(monkeypatch):
    import openai

    original = openai.APIConnectionError(message="boom", request=None)  # type: ignore[arg-type]
    _install_failing_openai_client(monkeypatch, original)

    model = OllamaChatModel(model_id="gemma3:4b")
    with pytest.raises(ConnectionError) as exc_info:
        # iterate the generator to trigger the failure
        for _ in model.stream([Message(role="user", content="hi")]):
            pass

    msg = str(exc_info.value)
    for substring in _required_substrings("http://localhost:11434/v1"):
        assert substring in msg, f"missing substring {substring!r} in {msg!r}"
    assert exc_info.value.__cause__ is original


# ---------- non-connection openai errors propagate unchanged ----------------


def test_notfounderror_propagates_unchanged(monkeypatch):
    import openai

    # Build a NotFoundError that won't trip on missing kwargs in older openai versions.
    try:
        original: Exception = openai.NotFoundError(
            message="model not found",
            response=SimpleNamespace(  # type: ignore[arg-type]
                request=None,
                status_code=404,
                headers={},
            ),
            body=None,
        )
    except TypeError:
        # Older openai SDK shape — fall back to APIStatusError-ish construction.
        original = openai.NotFoundError("model not found")  # type: ignore[call-arg]

    _install_failing_openai_client(monkeypatch, original)

    model = OllamaChatModel(model_id="gemma3:4b")
    with pytest.raises(openai.NotFoundError):
        model.chat([Message(role="user", content="hi")])
    # And the wrap MUST NOT have fired:
    # (re-running raises the same NotFoundError, never ConnectionError)


# ---------- explicit base_url is reflected in the wrapped error message -----


def test_chat_apiconnectionerror_message_uses_resolved_base_url(monkeypatch):
    """The wrapped message must show the *resolved* base_url, not the default."""
    import openai

    original = openai.APIConnectionError(message="boom", request=None)  # type: ignore[arg-type]
    _install_failing_openai_client(monkeypatch, original)

    custom = "http://192.168.1.5:11434/v1"
    model = OllamaChatModel(model_id="gemma3:4b", base_url=custom)
    with pytest.raises(ConnectionError) as exc_info:
        model.chat([Message(role="user", content="hi")])
    assert custom in str(exc_info.value)
    assert "http://localhost:11434/v1" not in str(exc_info.value)
