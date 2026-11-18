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
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, Union

from cantus._deprecation import warn_legacy
from cantus.core.action import (
    Action,
    CallToolAction,
    FinalAnswerAction,
)
from cantus.core.event_stream import EventStream
from cantus.core.observation import (
    MaxIterationsObservation,
    Observation,
    ToolErrorObservation,
    ToolObservation,
    ValidationErrorObservation,
)
from cantus.core.registry import Registry, _get_global_registry

if TYPE_CHECKING:
    from collections.abc import Iterable

    from cantus.core.action import CallToolAction as CallSkillAction  # noqa: F401  # legacy-alias
    from cantus.core.observation import ToolObservation as SkillObservation  # noqa: F401  # legacy-alias

    from cantus.identity import Soul
    from cantus.protocols.tool import Tool


def _emit_hook_debug_label(role: str, hook: Any, skill_name: str) -> None:
    """Print a `[debug] <role> '<hook_name>' …` line for @debug-wrapped hooks.

    Called from `_dispatch_tool` when a `pre_hook` / `post_hook` has been
    wrapped with `@debug`. The hook's own `@debug` traced wrapper still fires
    afterwards and prints its own args/result line; this label is the
    role-tagged announcement that the spec scenario requires.
    """
    hook_name = getattr(hook, "name", None) or getattr(hook, "__name__", "?")
    sys.stdout.write(
        f"[debug] {role} '{hook_name}' invoked from skill '{skill_name}'\n"
    )


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


class _ToolsField:
    """Descriptor: every write to `Agent.tools` resolves to a Registry."""

    def __set_name__(self, owner: type, name: str) -> None:
        self._slot = "_cantus_" + name

    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        if obj is None:
            return None
        try:
            return obj.__dict__[self._slot]
        except KeyError:
            raise AttributeError(self._slot[len("_cantus_"):]) from None

    def __set__(self, obj: Any, value: Any) -> None:
        if value is None:
            value = _get_global_registry()
            if value.names_for("tool"):
                warn_legacy("W11")
        elif not isinstance(value, Registry):
            value = Registry(tools=value)
        obj.__dict__[self._slot] = value


def _both_keywords_allowed(tools: Any, caller: Any) -> bool:
    """Say whether ``tools`` and ``registry`` may both be given to ``Agent.__init__``.

    Only ``dataclasses.replace`` (Python 3.10-3.12) and ``copy.replace`` (3.13+) do
    this, because they pass the old agent's ``tools`` along with the new ``registry``.
    The rule: the calling frame belongs to the ``dataclasses`` module and ``tools`` is
    the very object the original agent holds (the frame's local ``obj`` or ``self``).
    Known limit: a subclass whose own ``__init__`` forwards to ``super().__init__`` is
    not recognised, so ``replace(sub, registry=r2)`` raises there.
    """
    if caller.f_globals.get("__name__") != "dataclasses":
        return False
    original = caller.f_locals.get("obj", caller.f_locals.get("self"))
    return isinstance(original, Agent) and tools is original.tools


@dataclass(init=False)
class Agent:
    """Default agent that drives the model + EventStream loop.

    The agent can call the Tools passed in ``tools``; ``tools=[]`` means no tools.
    Leaving ``tools`` out is deprecated and uses the process-wide registry.
    """

    model: ModelHandle
    # mypy rejects the descriptor against the constructor's union, so the field stays Any
    tools: Any = _ToolsField()
    soul: "Soul | None" = field(default=None, kw_only=True)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Reject a subclass that still carries the pre-0.7 dispatch override.

        The loop calls ``_dispatch_tool``; an override under the old name would never
        run, so any check in it would be skipped without a sign.

        Raises:
            TypeError: If the old method name is found on the subclass or its bases.
        """
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "_dispatch_skill"):  # legacy-alias
            raise TypeError(
                f"{cls.__name__} defines _dispatch_skill, which cantus 0.7.0 no longer calls: "  # legacy-alias
                "Agent._dispatch_skill was renamed to _dispatch_tool, so the checks in your "  # legacy-alias
                "override would be skipped silently. Rename the method to _dispatch_tool, call "
                "super()._dispatch_tool(action) inside it, and read action.tool_name instead of "
                "action.skill_name. See "  # legacy-alias
                "https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/"
                "MIGRATION_v0.6.0_to_v0.7.0.md"
            )

    def __init__(
        self,
        model: ModelHandle,
        tools: "Iterable[Tool] | Registry | None" = None,
        *,
        soul: "Soul | None" = None,
        registry: "Registry | None" = None,
    ) -> None:
        """Create an agent.

        Args:
            model: The loaded model; anything with ``generate(prompt)``.
            tools: The Tools the agent may call: a list (or any iterable) of
                Tool instances, or a ready ``Registry``.
            soul: An optional Soul added to the system prompt.
            registry: Deprecated; use ``tools``.
        """
        if registry is not None:
            if not isinstance(registry, Registry):
                raise TypeError(
                    f"registry must be a Registry, got {type(registry).__name__}; "
                    "pass tools with Agent(model, tools=[...])"
                )
            # dataclasses.replace(agent, registry=r2) passes the old tools along
            # with the new registry; there the registry wins.
            if tools is not None and not _both_keywords_allowed(tools, sys._getframe(1)):
                raise TypeError(
                    "pass either tools= or registry=, not both; "
                    "registry= is deprecated, use tools="
                )
            warn_legacy("W10")
            tools = registry
        self.model = model
        self.tools = tools
        self.soul = soul

    @property
    def registry(self) -> Registry:
        """The agent's tools as a Registry.

        Raises:
            TypeError: When assigning a value that is not a Registry.
        """
        registry: Registry = self.tools
        return registry

    @registry.setter
    def registry(self, value: Any) -> None:
        if not isinstance(value, Registry):
            raise TypeError(
                f"agent.registry must be a Registry, got {type(value).__name__}; "
                "use agent.tools = [...] or Registry(tools=[...])"
            )
        self.tools = value

    def step(self, state: AgentState) -> Union[Action, Observation]:
        """One decision step: ask the model for the next action.

        Returns either an `Action` subclass (CallToolAction or
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

        Tool calls go through the registry; validator failures trigger
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

            if isinstance(action, CallToolAction):
                obs = self._dispatch_tool(action)
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
        baseline = json.dumps(
            {
                "tools": spec,
                "query": state.query,
                "events": [repr(e) for e in state.stream],
            },
            ensure_ascii=False,
        )
        if self.soul is not None:
            return self.soul.to_system_prompt() + "\n\n" + baseline
        return baseline

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

        # CallToolAction path: skill_name is present (no final_answer).
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

        registered = self.registry.names_for("tool")
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
        return CallToolAction(
            thought=thought,
            tool_name=skill_name,
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

    def _dispatch_tool(self, action: CallToolAction) -> Observation:
        """Run a CallToolAction; wrap any failure as the right Observation.

        Dispatch: a single registry lookup under "tool", followed by a
        linear `pre_hook → body → post_hook` chain. No per-kind branching.
        """
        from cantus.core.result import Result

        instance = self.registry.lookup("tool", action.tool_name)
        if instance is None:
            available = self.registry.names_for("tool")
            return ToolErrorObservation(
                tool_name=action.tool_name,
                message=f"tool '{action.tool_name}' not registered. Available: {available}",
            )

        try:
            args = (
                instance.validate_args(action.args)
                if hasattr(instance, "validate_args")
                else action.args
            )
        except Exception as exc:
            return ToolErrorObservation(
                tool_name=action.tool_name,
                message=f"args validation failed: {type(exc).__name__}: {exc}",
            )

        pre_hook = getattr(instance, "_pre_hook", None)
        if pre_hook is not None:
            if getattr(pre_hook, "_debug_enabled", False):
                _emit_hook_debug_label("pre_hook", pre_hook, action.tool_name)
            try:
                pre_out = pre_hook(**args) if isinstance(args, dict) else pre_hook(args)
            except Exception as exc:
                return ToolErrorObservation(
                    tool_name=action.tool_name,
                    message=f"pre_hook {type(exc).__name__}: {exc}",
                )
            args = pre_out if isinstance(pre_out, dict) else {"_pre_hook_value": pre_out}

        try:
            if "_pre_hook_value" in args:
                result = instance(args["_pre_hook_value"])
            else:
                result = instance(**args)
        except Exception as exc:
            return ToolErrorObservation(
                tool_name=action.tool_name,
                message=f"{type(exc).__name__}: {exc}",
            )

        post_hook = getattr(instance, "_post_hook", None)
        if post_hook is not None:
            if getattr(post_hook, "_debug_enabled", False):
                _emit_hook_debug_label("post_hook", post_hook, action.tool_name)
            try:
                result = post_hook(result)
            except Exception as exc:
                return ToolErrorObservation(
                    tool_name=action.tool_name,
                    message=f"post_hook {type(exc).__name__}: {exc}",
                )

        if isinstance(result, Result):
            if not result.ok:
                hook_name = (
                    getattr(post_hook, "name", None)
                    or getattr(post_hook, "__name__", None)
                    or action.tool_name
                )
                return ValidationErrorObservation(
                    validator_name=hook_name,
                    feedback=result.feedback or "validation failed",
                )
            return ToolObservation(tool_name=action.tool_name, result=result.value)

        return ToolObservation(tool_name=action.tool_name, result=result)


def __getattr__(name: str) -> Any:
    """Serve the legacy event class names as `CallToolAction` and `ToolObservation`."""
    if name == "CallSkillAction":  # legacy-alias
        warn_legacy("W4")
        return CallToolAction
    if name == "SkillObservation":  # legacy-alias
        warn_legacy("W5")
        return ToolObservation
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
