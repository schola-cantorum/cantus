"""cantus.adapters package surface — three public callables, no Registry mutation."""

from __future__ import annotations


def test_three_public_functions_importable():
    from cantus.adapters import (
        expose_as_anthropic_memory_tool,
        export_as_mcp_server,
        import_mcp_server,
    )

    assert callable(export_as_mcp_server)
    assert callable(import_mcp_server)
    assert callable(expose_as_anthropic_memory_tool)


def test_registry_kinds_unchanged_after_import():
    # Importing cantus.adapters MUST NOT add new protocol kinds to the
    # Registry. v0.3.0 contract holds: `KINDS == ("skill",)`.
    import cantus.adapters  # noqa: F401
    from cantus.core.registry import Registry

    assert Registry.KINDS == ("skill",)
    assert Registry().KINDS == ("skill",)
