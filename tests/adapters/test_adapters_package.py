"""cantus.adapters package surface — nine public callables (v0.3.2 + v0.3.3)."""

from __future__ import annotations


def test_three_v032_public_functions_importable():
    """v0.3.2 callables remain byte-identically importable."""
    from cantus.adapters import (
        expose_as_anthropic_memory_tool,
        export_as_mcp_server,
        import_mcp_server,
    )

    assert callable(export_as_mcp_server)
    assert callable(import_mcp_server)
    assert callable(expose_as_anthropic_memory_tool)


def test_six_v033_public_functions_importable():
    """v0.3.3 batch2 callables are exposed at the top of cantus.adapters."""
    from cantus.adapters import (
        expose_as_dspy_tool,
        expose_as_hf_tool,
        expose_as_langchain_tool,
        expose_as_openhands_action,
        import_dspy_tool,
        import_langchain_tool,
    )

    for fn in (
        expose_as_langchain_tool,
        import_langchain_tool,
        expose_as_dspy_tool,
        import_dspy_tool,
        expose_as_hf_tool,
        expose_as_openhands_action,
    ):
        assert callable(fn)


def test_v033_all_includes_nine_callables():
    """`cantus.adapters.__all__` enumerates v0.3.2 (3) + v0.3.3 (6) = 9 names."""
    import cantus.adapters as adapters

    expected = {
        # v0.3.2
        "export_as_mcp_server",
        "import_mcp_server",
        "expose_as_anthropic_memory_tool",
        # v0.3.3
        "expose_as_langchain_tool",
        "import_langchain_tool",
        "expose_as_dspy_tool",
        "import_dspy_tool",
        "expose_as_hf_tool",
        "expose_as_openhands_action",
    }
    assert expected.issubset(set(adapters.__all__))


def test_remote_skill_base_is_not_public():
    """`_RemoteSkillBase` is private — must not appear in cantus.adapters."""
    import cantus.adapters as adapters

    assert not hasattr(adapters, "_RemoteSkillBase")
    # But it remains importable via the underscore-prefixed private module:
    from cantus.adapters._remote_skill import _RemoteSkillBase

    assert _RemoteSkillBase.__name__ == "_RemoteSkillBase"


def test_registry_kinds_unchanged_after_import():
    # Importing cantus.adapters MUST NOT add new protocol kinds to the
    # Registry. v0.3.0 contract holds: `KINDS == ("skill",)`.
    import cantus.adapters  # noqa: F401
    from cantus.core.registry import Registry

    assert Registry.KINDS == ("skill",)
    assert Registry().KINDS == ("skill",)
