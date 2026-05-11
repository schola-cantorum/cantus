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

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Protocol, Union

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

    def step(self, state: AgentState) -> Union[Action, Observation]:
        """One decision step: ask the model for the next action.

        Returns either an `Action` subclass (CallSkillAction or
        FinalAnswerAction) when the model output parses cleanly, or a
        `ValidationErrorObservation` when the output fails the
        `non_empty_final_answer` or `action_parse` validators (see the
        agent-runtime spec). Callers SHALL handle both branches; the
        run loop appends the result directly to the EventStream.
        """
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

        Default budgets are `max_iterations=8` and `max_retries=3`. For
        sub-3B variants such as Gemma 4 E2B that frequently short-circuit
        to an empty `final_answer`, callers MAY pass `max_iterations=12`
        explicitly to give the framework more retries to converge on a
        substantive answer; this is a caller-supplied override, NOT a
        framework default.

        Skill calls go through the registry; validator failures trigger
        retry of the *previous* action. The workflow argument is accepted
        for symmetry with future API expansions but is not currently
        consulted by the loop directly — workflows execute via the
        registry like any other protocol.

        On `max_iterations` exhaustion the framework appends a
        `MaxIterationsObservation(iterations=N, last_action_summary=...,
        partial_state=<deep copy of EventStream>)` as the final event and
        returns the partial state. The framework SHALL NOT raise an
        exception nor fabricate a `FinalAnswerAction` on this path.
        """
        if query is None and isinstance(workflow_or_query, str):
            query = workflow_or_query
        if query is None:
            raise ValueError("Agent.run needs a query string")

        state = AgentState(query=query)
        retries_for_last_action = 0

        for i in range(max_iterations):
            outcome = self.step(state)

            # Parse-level failure: append the observation directly, continue.
            if isinstance(outcome, Observation):
                state.stream.append(outcome)
                if isinstance(outcome, ValidationErrorObservation):
                    if retries_for_last_action < max_retries:
                        retries_for_last_action += 1
                        continue
                retries_for_last_action = 0
                continue

            action = outcome
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

        # max_iterations exhaustion: append MaxIterationsObservation with a
        # deep-copied snapshot of the stream as it stood, BEFORE appending
        # the observation itself (spec: partial_state contains all events
        # up to but NOT including this observation).
        partial_state = copy.deepcopy(state.stream)
        state.stream.append(
            MaxIterationsObservation(
                iterations=max_iterations,
                last_action_summary=(
                    repr(state.stream[-1]) if len(state.stream) else ""
                ),
                partial_state=partial_state,
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

    def _parse_action(self, raw: str) -> Union[Action, Observation]:
        """Parse LLM output into an Action or a parse-error Observation.

        Expected JSON shape:
            {"thought": str, "action": {"skill_name": str, "args": object}}
        or
            {"thought": str, "action": {"final_answer": str}}

        On failure the framework appends a `ValidationErrorObservation`
        per the `agent-runtime` failure-handling Requirements:

        - malformed JSON → `validator_name="action_parse"`,
          `error_type: json_syntax`
        - action object missing both `skill_name` and `final_answer`
          → `validator_name="action_parse"`, `error_type: missing_field`
        - `skill_name` present but not in the current registry and no
          `final_answer` key → `validator_name="action_parse"`,
          `error_type: unknown_skill`
        - `final_answer` present but empty after `str.strip()` →
          `validator_name="non_empty_final_answer"`

        The framework SHALL NOT silently fall back to constructing
        `FinalAnswerAction(answer=raw_output)` from unparseable text.
        """
        # JSON syntax check.
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            return ValidationErrorObservation(
                validator_name="action_parse",
                feedback=self._format_parse_feedback(
                    error_type="json_syntax",
                    detail=f"expected JSON object, got JSONDecodeError: {exc.msg}",
                    raw=raw,
                ),
            )
        if not isinstance(data, dict):
            return ValidationErrorObservation(
                validator_name="action_parse",
                feedback=self._format_parse_feedback(
                    error_type="json_syntax",
                    detail=f"top-level must be a JSON object, got {type(data).__name__}",
                    raw=raw,
                ),
            )

        thought = str(data.get("thought", ""))
        action = data.get("action", None)
        if not isinstance(action, dict):
            return ValidationErrorObservation(
                validator_name="action_parse",
                feedback=self._format_parse_feedback(
                    error_type="missing_field",
                    detail="action object missing or not a JSON object; required keys: skill_name or final_answer",
                    raw=raw,
                ),
            )

        has_final = "final_answer" in action
        has_skill = "skill_name" in action

        # Missing both required keys.
        if not has_final and not has_skill:
            return ValidationErrorObservation(
                validator_name="action_parse",
                feedback=self._format_parse_feedback(
                    error_type="missing_field",
                    detail="action object must contain either 'skill_name' or 'final_answer'",
                    raw=raw,
                ),
            )

        if has_final:
            answer = action["final_answer"]
            # Non-empty FinalAnswer check (runtime layer; the grammar
            # schema layer enforces the same constraint at decode time).
            if not isinstance(answer, str) or answer.strip() == "":
                return ValidationErrorObservation(
                    validator_name="non_empty_final_answer",
                    feedback=(
                        "FinalAnswerAction.answer must be non-empty after "
                        "str.strip(); call a skill or write a substantive answer"
                    ),
                )
            return FinalAnswerAction(thought=thought, answer=str(answer))

        # CallSkillAction path: skill_name is present (no final_answer).
        skill_name = action.get("skill_name", "")
        if not isinstance(skill_name, str):
            return ValidationErrorObservation(
                validator_name="action_parse",
                feedback=self._format_parse_feedback(
                    error_type="missing_field",
                    detail=f"skill_name must be a string, got {type(skill_name).__name__}",
                    raw=raw,
                ),
            )

        registered = self.registry.names_for("skill")
        if registered and skill_name not in registered:
            return ValidationErrorObservation(
                validator_name="action_parse",
                feedback=self._format_parse_feedback(
                    error_type="unknown_skill",
                    detail=(
                        f"skill_name {skill_name!r} not in current skill registry; "
                        f"available: {registered}"
                    ),
                    raw=raw,
                ),
            )

        args = action.get("args", {})
        if not isinstance(args, dict):
            args = {}
        return CallSkillAction(
            thought=thought,
            skill_name=skill_name,
            args=dict(args),
        )

    @staticmethod
    def _format_parse_feedback(*, error_type: str, detail: str, raw: str) -> str:
        """Build the three-part feedback block for `action_parse` errors.

        Layout (case-sensitive, newline-separated):
            error_type: <json_syntax|missing_field|unknown_skill>
            detail: <human-readable explanation>
            raw_output_preview: <≤500 chars; appends `…[truncated]` if longer>

        Newlines in `raw` are preserved as the two-character sequence `\\n`
        (the literal characters), per the spec.
        """
        preview = raw[:500]
        truncated_suffix = "…[truncated]" if len(raw) > 500 else ""
        preview_with_literal_newlines = preview.replace("\n", "\\n")
        return (
            f"error_type: {error_type}\n"
            f"detail: {detail}\n"
            f"raw_output_preview: {preview_with_literal_newlines}{truncated_suffix}"
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
