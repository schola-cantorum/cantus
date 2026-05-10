"""Agent loop — bounded, error-closing, transparent (with @debug).

`Agent.step(state) -> Action` is the canonical decision function.
`agent.run(workflow, query, max_iterations=8, max_retries=3)` drives the
loop until a `FinalAnswerAction` or the iteration bound is hit.

All errors (skill exceptions, unknown skill names, validator failures)
are wrapped as Observations and appended to the EventStream — they do
not propagate out of `run`. The LLM sees the error feedback in the next
prompt and is expected to self-correct.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from cantus.core.action import (
    Action,
    CallSkillAction,
    FinalAnswerAction,
)
from cantus.core.event_stream import EventStream
from cantus.core.observation import (
    MaxIterationsObservation,
    Observation,
    SkillObservation,
    ToolErrorObservation,
    ValidationErrorObservation,
)
from cantus.core.registry import Registry, get_registry


class ModelHandle(Protocol):
    """Minimal interface the agent needs from a loaded model.

    The real Gemma 4 loader returns an object with `.model`,
    `.tokenizer`, etc., but the agent only requires a `generate(prompt)`
    method that returns a string. Tests pass in a MockModel that
    matches this protocol.
    """

    def generate(self, prompt: str, **kwargs: Any) -> str:
        ...


@dataclass
class AgentState:
    """Snapshot the agent passes to `step()`."""

    query: str
    stream: EventStream = field(default_factory=EventStream)


@dataclass
class Agent:
    """Default agent that drives the model + EventStream loop."""

    model: ModelHandle
    registry: Registry = field(default_factory=get_registry)

    def step(self, state: AgentState) -> Action:
        """One decision step: ask the model for the next action."""
        prompt = self._build_prompt(state)
        raw = self.model.generate(prompt)
        return self._parse_action(raw)

    def run(
        self,
        workflow_or_query: Any,
        query: str | None = None,
        max_iterations: int = 8,
        max_retries: int = 3,
    ) -> AgentState:
        """Run the bounded agent loop.

        For v1, this is the simple loop: skill calls go through the
        registry; validator failures trigger retry of the *previous*
        action. The workflow argument is accepted for symmetry with
        future API expansions but is not currently consulted by the
        loop directly — workflows execute via the registry like any
        other protocol.
        """
        if query is None and isinstance(workflow_or_query, str):
            query = workflow_or_query
        if query is None:
            raise ValueError("Agent.run needs a query string")

        state = AgentState(query=query)
        retries_for_last_action = 0

        for i in range(max_iterations):
            action = self.step(state)
            state.stream.append(action)

            if isinstance(action, FinalAnswerAction):
                return state

            if isinstance(action, CallSkillAction):
                obs = self._dispatch_skill(action)
                state.stream.append(obs)

                if isinstance(obs, ValidationErrorObservation):
                    if retries_for_last_action < max_retries:
                        retries_for_last_action += 1
                        continue
                    # Out of retries; let the loop continue, the LLM
                    # will see the failure and decide.
                retries_for_last_action = 0
                continue

        state.stream.append(
            MaxIterationsObservation(
                iterations=max_iterations,
                last_action_summary=repr(state.stream[-1]) if len(state.stream) else "",
            )
        )
        return state

    # ----- internals -----

    def _build_prompt(self, state: AgentState) -> str:
        # Minimal prompt builder — system message + tool catalog +
        # query + serialized stream. Real implementations will call
        # `chat_template` on the loaded model; we keep this generic for
        # easier testing with a MockModel.
        spec = self.registry.spec_for_llm()
        return json.dumps(
            {
                "tools": spec,
                "query": state.query,
                "events": [repr(e) for e in state.stream],
            },
            ensure_ascii=False,
        )

    def _parse_action(self, raw: str) -> Action:
        """Parse LLM output into an Action.

        Expected JSON shape:
            {"thought": str, "action": {"skill_name": str, "args": object}}
        or
            {"thought": str, "action": {"final_answer": str}}
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return FinalAnswerAction(thought="", answer=raw)
        thought = str(data.get("thought", ""))
        action = data.get("action", {})
        if "final_answer" in action:
            return FinalAnswerAction(thought=thought, answer=str(action["final_answer"]))
        return CallSkillAction(
            thought=thought,
            skill_name=str(action.get("skill_name", "")),
            args=dict(action.get("args", {})),
        )

    def _dispatch_skill(self, action: CallSkillAction) -> Observation:
        """Run a CallSkillAction; wrap any failure as the right Observation."""
        # Skills may live in any of the four function-based kinds: skill,
        # analyzer, validator, workflow. We look in skill first, then
        # validators (since the agent may invoke a validator after a
        # skill call), then workflows for top-level orchestration.
        for kind in ("skill", "validator", "analyzer", "workflow"):
            instance = self.registry.lookup(kind, action.skill_name)
            if instance is not None:
                break
        else:
            available = self.registry.names_for("skill")
            return ToolErrorObservation(
                skill_name=action.skill_name,
                message=f"skill '{action.skill_name}' not registered. Available: {available}",
            )

        try:
            args = (
                instance.validate_args(action.args)
                if hasattr(instance, "validate_args")
                else action.args
            )
        except Exception as exc:
            return ToolErrorObservation(
                skill_name=action.skill_name,
                message=f"args validation failed: {type(exc).__name__}: {exc}",
            )

        try:
            result = instance(**args)
        except Exception as exc:
            return ToolErrorObservation(
                skill_name=action.skill_name,
                message=f"{type(exc).__name__}: {exc}",
            )

        # If this was a validator, fold its Result into the right Observation.
        from cantus.core.result import Result

        if isinstance(result, Result):
            if not result.ok:
                return ValidationErrorObservation(
                    validator_name=action.skill_name,
                    feedback=result.feedback or "validation failed",
                )
            return SkillObservation(skill_name=action.skill_name, result=result.value)

        return SkillObservation(skill_name=action.skill_name, result=result)
