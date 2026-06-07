"""Real mlx-lm smoke test — skipped unless `mlx_lm` is importable.

This is the only test that touches the real `mlx-lm` package and downloads a
(tiny) model, so it is gated behind `pytest.importorskip`: on a non-Apple-
Silicon runner, or any environment without `cantus[mlx]` installed, the whole
module is skipped. The adapter's full contract is covered platform-agnostically
by `tests/providers/test_mlx_adapter.py` against a fake `mlx_lm`.
"""

from __future__ import annotations

import pytest

pytest.importorskip("mlx_lm")

from cantus import Message, load_chat_model  # noqa: E402

# A very small 4-bit instruct model keeps the download + generation cheap.
_SMOKE_MODEL = "mlx-community/SmolLM-135M-Instruct-4bit"


def test_mlx_load_and_chat_smoke() -> None:
    chat = load_chat_model(f"mlx/{_SMOKE_MODEL}")
    assert chat.supports_tool_use is False

    response = chat.chat(
        [Message(role="user", content="Say hi in one word.")],
        max_tokens=8,
    )
    assert isinstance(response.message.content, str)
    assert response.message.role == "assistant"
    assert response.stop_reason == "end_turn"
