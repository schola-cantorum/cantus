"""Registry — central catalog of registered protocols.

All three Tool entry styles (decorator, function-pass, class-first) end up
calling `Registry.register(kind, instance)`. The registry is what the
agent loop and `spec_for_llm()` consult.

The default singleton lives in `_default_registry`; tests use `Registry()`
directly to stay isolated.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from cantus._deprecation import warn_legacy

ProtocolKind = str  # only "tool" is valid

_LEGACY_KINDS = frozenset({"analyzer", "validator", "workflow"})


def _canonical_kind(kind: ProtocolKind) -> ProtocolKind:
    """Map the old kind name onto "tool", warning once per call; pass others through."""
    if kind == "skill":  # legacy-alias
        warn_legacy("W9")
        return "tool"
    return kind


def _spec_key(key: Any) -> Any:
    """Map the key used before v0.7 onto "tool", warning once per call."""
    if key == "skill":  # legacy-alias
        warn_legacy("W9")
        return "tool"
    return key


class ToolSpecMapping(dict[str, list[dict[str, Any]]]):
    """The `spec_for_llm()` result: a dict with one key, "tool".

    Reading the key used before v0.7 still answers with the tool list, and warns.
    Nothing else about the dict changes; JSON and iteration show only "tool".
    """

    def __getitem__(self, key: Any) -> list[dict[str, Any]]:
        """Return the list for ``key``; the old key answers as "tool"."""
        return super().__getitem__(_spec_key(key))

    def get(self, key: Any, default: Any = None) -> Any:
        """Return the list for ``key``, or ``default``; the old key answers as "tool".

        Args:
            key: The key to read.
            default: Returned when the key is missing.

        Returns:
            The tool list, or ``default``.
        """
        return super().get(_spec_key(key), default)

    def __contains__(self, key: object) -> bool:
        """Report whether ``key`` is present; the old key answers as "tool"."""
        return super().__contains__(_spec_key(key))


class Registry:
    """Catalog of registered protocol instances, indexed by kind and name."""

    KINDS = ("tool",)

    def __init__(self, tools: Iterable[Any] = ()) -> None:
        """Create a registry, optionally holding the given Tools.

        Args:
            tools: Any iterable of Tool instances; omit it for an empty registry.

        Raises:
            TypeError: ``tools`` is not a list-like container of Tools (a single Tool,
                a string, a mapping, a Registry, None), or an element is not a Tool
                instance.
            ValueError: An element has an empty name, or two Tools share a name.
        """
        self._by_kind: dict[ProtocolKind, dict[str, Any]] = defaultdict(dict)
        if isinstance(tools, tuple) and not tools:
            return
        from cantus.protocols.tool import Tool  # deferred: tool.py imports Registry

        if isinstance(tools, Registry):
            raise TypeError(
                "tools is already a Registry; use it directly "
                "(for example Agent(model, tools=reg))"
            )
        if (
            isinstance(tools, (Tool, str, bytes, Mapping))
            or not isinstance(tools, Iterable)
        ):
            if isinstance(tools, Tool):
                got = f"a single Tool '{getattr(tools, 'name', '')}'"
            else:
                got = type(tools).__name__
            message = (
                "tools must be a list of Tools (Agent also accepts a Registry), "
                f"got {got}"
            )
            if isinstance(tools, Tool):
                message += "; write tools=[...]"
            elif tools is None:
                message += "; omit tools for an empty Registry"
            raise TypeError(message)
        items: list[Any] = []
        for i, item in enumerate(tools):
            if not isinstance(item, Tool):
                if isinstance(item, type):
                    if issubclass(item, Tool):
                        raise TypeError(
                            f"tools[{i}] is the class {item.__name__}; "
                            f"pass an instance: {item.__name__}()"
                        )
                    raise TypeError(f"tools[{i}] is the class {item.__name__}, not a Tool")
                if callable(item):
                    label = getattr(item, "__name__", None)
                    if isinstance(label, str) and label.isidentifier():
                        raise TypeError(
                            f"tools[{i}] is the function {label!r}, not a Tool. "
                            f"Decorate it with @tool. If the name tool now means something "
                            f"else in your code, use cantus.tool({label}) after "
                            f'"import cantus".'
                        )
                    raise TypeError(
                        f"tools[{i}] is a callable of type {type(item).__name__}, "
                        "not a Tool. Write a function and decorate it with @tool."
                    )
                raise TypeError(f"tools[{i}] is {type(item).__name__}, not a Tool")
            if not item.name:
                raise ValueError(
                    "Cannot register tool without a `name` attribute on the instance "
                    f"(tools[{i}])"
                )
            items.append(item)
        seen: dict[str, int] = {}
        for i, item in enumerate(items):
            name = item.name
            if name in seen:
                j = seen[name]
                message = (
                    f"duplicate tool name {name!r} in tools (positions {j} and {i})"
                )
                if items[j] is item:
                    message += ": the same Tool twice"
                raise ValueError(message)
            seen[name] = i
        for item in items:
            self._by_kind["tool"][item.name] = item

    def register(self, kind: ProtocolKind, instance: Any) -> None:
        kind = _canonical_kind(kind)
        if kind in _LEGACY_KINDS:
            raise ValueError(
                f"Protocol kind {kind!r} was removed in cantus v0.3.0. "
                f"Analyzer and Validator are now Tool hook helpers: attach via "
                f"`@tool(pre_hook=...)` or `@tool(post_hook=...)`. "
                f"Workflow orchestration moved to the `cantus.workflows` package "
                f"(PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer). "
                f"See MIGRATION_v0.2_to_v0.3.md."
            )
        if kind not in self.KINDS:
            raise ValueError(f"Unknown protocol kind: {kind!r}. Valid: {self.KINDS}")
        name = getattr(instance, "name", None)
        if not name:
            raise ValueError(
                "Cannot register tool without a `name` attribute on the instance"
            )
        self._by_kind[kind][name] = instance

    def lookup(self, kind: ProtocolKind, name: str) -> Any | None:
        kind = _canonical_kind(kind)
        return self._by_kind.get(kind, {}).get(name)

    def names_for(self, kind: ProtocolKind) -> list[str]:
        kind = _canonical_kind(kind)
        return sorted(self._by_kind.get(kind, {}).keys())

    def spec_for_llm(self) -> ToolSpecMapping:
        """Return a JSON-friendly spec describing every registered protocol.

        The structure is `{kind: [spec, spec, ...]}` where each spec is what
        the protocol's own `.spec_for_llm()` returns. Used by the agent to
        build the system prompt and by the grammar to constrain decoding.
        """
        out: dict[str, list[dict[str, Any]]] = {kind: [] for kind in self.KINDS}
        for kind, instances in self._by_kind.items():
            for name in sorted(instances.keys()):
                instance = instances[name]
                spec = (
                    instance.spec_for_llm()
                    if hasattr(instance, "spec_for_llm")
                    else {"name": name}
                )
                out[kind].append(spec)
        return ToolSpecMapping(out)

    def clear(self) -> None:
        """For tests."""
        self._by_kind.clear()


_default_registry = Registry()


def _get_global_registry() -> Registry:
    """Return the process-wide default registry without a deprecation warning."""
    return _default_registry


def get_registry() -> Registry:  # legacy-alias
    """Return the process-wide default registry; warns, because it is deprecated.

    Returns:
        The default Registry.
    """
    warn_legacy("W8")
    return _default_registry
