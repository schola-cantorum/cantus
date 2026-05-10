"""Registry — central catalog of registered protocols.

All three entry styles (decorator, function-pass, class-first) end up
calling `Registry.register(kind, instance)`. The registry is what the
agent loop and `spec_for_llm()` consult.

The default singleton lives in `_default_registry`; tests use `Registry()`
directly to stay isolated.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

ProtocolKind = str  # one of: "skill", "analyzer", "validator", "workflow"


class Registry:
    """Catalog of registered protocol instances, indexed by kind and name."""

    KINDS = ("skill", "analyzer", "validator", "workflow")

    def __init__(self) -> None:
        self._by_kind: dict[ProtocolKind, dict[str, Any]] = defaultdict(dict)

    def register(self, kind: ProtocolKind, instance: Any) -> None:
        if kind not in self.KINDS:
            raise ValueError(f"Unknown protocol kind: {kind!r}. Valid: {self.KINDS}")
        name = getattr(instance, "name", None)
        if not name:
            raise ValueError(
                f"Cannot register {kind} without a `name` attribute on the instance"
            )
        self._by_kind[kind][name] = instance

    def lookup(self, kind: ProtocolKind, name: str) -> Any | None:
        return self._by_kind.get(kind, {}).get(name)

    def names_for(self, kind: ProtocolKind) -> list[str]:
        return sorted(self._by_kind.get(kind, {}).keys())

    def spec_for_llm(self) -> dict[str, list[dict[str, Any]]]:
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
        return out

    def clear(self) -> None:
        """For tests."""
        self._by_kind.clear()


_default_registry = Registry()


def get_registry() -> Registry:
    """Return the process-wide default registry (used by decorators)."""
    return _default_registry
