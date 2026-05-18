"""Agent.soul= kwargs and system-prompt injection (v0.3.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from cantus.core.agent import Agent, AgentState
from cantus.core.registry import Registry, get_registry
from cantus.identity import Soul


@dataclass
class _CapturingModel:
    """MockModel that stores the most recent prompt passed to generate()."""

    last_prompt: str = ""

    def generate(self, prompt: str, **kwargs) -> str:
        self.last_prompt = prompt
        return json.dumps({"thought": "ok", "action": {"final_answer": "done"}})


def _fresh_registry() -> Registry:
    """Snapshot the shared registry so tests share the same spec_for_llm result."""
    return get_registry()


def _make_soul() -> Soul:
    return Soul(
        name_and_role="Librarian",
        personality="Helpful",
        rules="Be polite",
        tools="search_book",
        output_format="plain",
        handoffs="none",
    )


def test_no_soul_baseline_byte_identical():
    m = _CapturingModel()
    agent = Agent(model=m, registry=_fresh_registry())
    state = AgentState(query="hello")

    prompt = agent._build_prompt(state)

    # The v0.3.0 baseline is the JSON dump produced by `_build_prompt` for
    # the same registry, query, and empty stream. We reconstruct it
    # independently here so any drift in the builder shows up as a diff.
    expected = json.dumps(
        {
            "tools": agent.registry.spec_for_llm(),
            "query": state.query,
            "events": [],
        },
        ensure_ascii=False,
    )
    assert prompt == expected


def test_soul_prefix_injection():
    m = _CapturingModel()
    soul = _make_soul()
    baseline_agent = Agent(model=_CapturingModel(), registry=_fresh_registry())
    soul_agent = Agent(model=m, registry=baseline_agent.registry, soul=soul)
    state = AgentState(query="hello")

    baseline = baseline_agent._build_prompt(state)
    out = soul_agent._build_prompt(state)

    expected_prefix = soul.to_system_prompt() + "\n\n"
    assert out.startswith(expected_prefix)
    assert out[len(expected_prefix):] == baseline


def test_soul_not_in_registry_spec_for_llm():
    soul = _make_soul()
    m = _CapturingModel()
    agent = Agent(model=m, soul=soul)
    spec = agent.registry.spec_for_llm()
    payload = json.dumps(spec, ensure_ascii=False)
    # No portion of the Soul body should be exposed via the LLM-facing spec.
    for attr in (
        soul.name_and_role,
        soul.personality,
        soul.rules,
        soul.tools,
        soul.output_format,
        soul.handoffs,
    ):
        assert attr not in payload, f"leak of Soul attr {attr!r} into spec_for_llm"
