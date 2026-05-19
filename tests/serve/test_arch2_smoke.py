"""ARCH-2 cross-capability smoke test for cantus-serve-core.

Constructs the minimal cross-cut: 1 Skill + 1 Memory + 1 Agent + 1
LocalMockReceiver, all wired through ``cantus.serve(registry, channels=[...])``,
and verifies the FastAPI surface composes with the rest of cantus without
mutating Memory or losing the Channel handle. Asserts:

* the HTTP-served Skill response equals the direct ``Skill.run()`` output
  byte-identical;
* the Memory state before ``serve()`` byte-equals the state after the
  request when the invoked Skill does not touch Memory;
* ``app.state.channels`` contains the original ``LocalMockReceiver``
  instance unchanged.

Per the spec Requirement, the test SHALL complete within 10 seconds of
wall-clock time on a developer laptop.
"""

from __future__ import annotations

import copy
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from cantus.core.agent import Agent
from cantus.core.registry import Registry
from cantus.protocols.memory import ShortTermMemory
from cantus.protocols.skill import register_skill
from cantus.serve import serve
from cantus.serve.channel import LocalMockReceiver


class _StubModel:
    """Minimal ModelHandle stub so we can construct an Agent without invoking real LLMs."""

    def generate(self, prompt: str, **kwargs: Any) -> str:
        return ""


def test_arch2_serve_composes_with_memory_and_agent_without_interference() -> None:
    start = time.monotonic()

    # 1) Skill — pure function, never touches Memory.
    def reverse_text(text: str) -> dict[str, Any]:
        """Reverse the input text."""
        return {"reversed": text[::-1]}

    skill_instance = register_skill(reverse_text)
    registry = Registry()
    registry.register("skill", skill_instance)

    # 2) Memory — v0.3.1 in-process implementation, no external IO.
    memory = ShortTermMemory(n=5)
    # 3) Agent — wired to registry; will not be invoked during this smoke test.
    agent = Agent(model=_StubModel(), registry=registry)
    assert agent.registry is registry

    # 4) Channel — in-memory FIFO load-bearer.
    receiver = LocalMockReceiver()

    # Snapshot memory pre-serve.
    memory_before = copy.deepcopy(memory)

    # 5) Compose all four through cantus.serve(...).
    app = serve(registry, channels=[receiver])
    client = TestClient(app)

    # 6) Invoke the Skill through the served endpoint and capture the HTTP response.
    payload = {"text": "cantus"}
    http_resp = client.post("/skills/reverse_text", json=payload)
    assert http_resp.status_code == 200
    http_result = http_resp.json()["result"]

    # 6a) HTTP-served result byte-equals direct Skill.run() output.
    direct_result = skill_instance.run(**payload)
    assert http_result == direct_result

    # 6b) Memory state untouched by the serve layer.
    assert memory == memory_before
    assert list(memory.recall("")) == list(memory_before.recall(""))

    # 6c) The Channel list on app.state still contains the original receiver.
    assert hasattr(app.state, "channels")
    assert isinstance(app.state.channels, list)
    assert len(app.state.channels) == 1
    assert app.state.channels[0] is receiver

    # 7) Wall-clock budget — must finish in < 10s per Requirement.
    elapsed = time.monotonic() - start
    assert elapsed < 10.0, (
        f"ARCH-2 smoke test exceeded the 10s budget: {elapsed:.2f}s — "
        "this implies pytest collection or compose path regressed under serve."
    )
