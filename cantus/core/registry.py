"""Registry — central catalog of registered protocols.

All three Tool entry styles (decorator, function-pass, class-first) end up
calling `Registry.register(kind, instance)`. The registry is what the
agent loop and `spec_for_llm()` consult.

The default singleton lives in `_default_registry`; tests use `Registry()`
directly to stay isolated.
"""

from __future__ import annotations

from collections import defaultdict
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


class ToolSpecMapping(dict[str, Any]):
    """The `spec_for_llm()` result: a dict with one key, "tool".

    Reading the key used before v0.7 still answers with the tool list, and warns.
    Nothing else about the dict changes; JSON and iteration show only "tool".
    """

    def __getitem__(self, key: Any) -> Any:
        if key == "skill":  # legacy-alias
            warn_legacy("W9")
            key = "tool"
        return super().__getitem__(key)

    def get(self, key: Any, default: Any = None) -> Any:
        if key == "skill":  # legacy-alias
            warn_legacy("W9")
            key = "tool"
        return super().get(key, default)

    def __contains__(self, key: object) -> bool:
        if key == "skill":  # legacy-alias
            warn_legacy("W9")
            key = "tool"
        return super().__contains__(key)


class Registry:
    """Catalog of registered protocol instances, indexed by kind and name."""

    KINDS = ("tool",)

    def __init__(self) -> None:
        self._by_kind: dict[ProtocolKind, dict[str, Any]] = defaultdict(dict)

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
    """Return the process-wide default registry; warns, because it is deprecated."""
    warn_legacy("W8")
    return _default_registry
