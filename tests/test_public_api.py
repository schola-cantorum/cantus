"""Verify the public import surface of cantus v0.3.0."""

import pytest


# --- Skill and core entries (top-level) ---------------------------------


def test_skill_decorator_importable():
    from cantus import skill, debug

    assert callable(skill)
    assert callable(debug)


def test_register_skill_importable():
    from cantus import register_skill

    assert callable(register_skill)


def test_class_first_base_classes_importable():
    """v0.3.0: only Skill and Memory are top-level; Analyzer/Validator moved to cantus.hooks."""
    from cantus import Memory, Skill

    for cls in (Skill, Memory):
        assert isinstance(cls, type)


def test_runtime_types_importable():
    from cantus import (
        Action,
        Agent,
        CallSkillAction,
        EventStream,
        FinalAnswerAction,
        Inspector,
        MaxIterationsObservation,
        Observation,
        Result,
        SkillObservation,
        ToolErrorObservation,
        ValidationErrorObservation,
    )

    assert all(
        isinstance(t, type)
        for t in (
            Action,
            Observation,
            EventStream,
            Agent,
            Inspector,
            Result,
            CallSkillAction,
            FinalAnswerAction,
            SkillObservation,
            ToolErrorObservation,
            ValidationErrorObservation,
            MaxIterationsObservation,
        )
    )


def test_loader_callable():
    from cantus import load_gemma, mount_drive_and_load

    assert callable(mount_drive_and_load)
    assert callable(load_gemma)


def test_public_mount_drive_and_load_accepts_drive_root(tmp_path):
    from cantus import mount_drive_and_load
    from cantus.model.loader import ModelNotFoundError

    with pytest.raises(ModelNotFoundError):
        mount_drive_and_load(
            variant="E4B",
            drive_root=str(tmp_path),
            allow_hub_fallback=False,
        )


def test_public_load_gemma_accepts_drive_root(tmp_path):
    from cantus import load_gemma
    from cantus.model.loader import ModelNotFoundError

    with pytest.raises(ModelNotFoundError):
        load_gemma(
            variant="E4B",
            drive_root=str(tmp_path),
            allow_hub_fallback=False,
        )


# --- v0.3.0: removed top-level imports ----------------------------------


def test_workflow_removed_from_top_level():
    with pytest.raises(ImportError):
        from cantus import Workflow  # noqa: F401


def test_workflow_decorator_removed_from_top_level():
    with pytest.raises(ImportError):
        from cantus import workflow  # noqa: F401


def test_register_workflow_removed_from_top_level():
    with pytest.raises(ImportError):
        from cantus import register_workflow  # noqa: F401


def test_analyzer_decorator_no_longer_top_level():
    """v0.3.0: @analyzer moved to cantus.hooks; top-level import SHALL fail."""
    with pytest.raises(ImportError):
        from cantus import analyzer  # noqa: F401


def test_validator_decorator_no_longer_top_level():
    with pytest.raises(ImportError):
        from cantus import validator  # noqa: F401


def test_Analyzer_class_no_longer_top_level():
    with pytest.raises(ImportError):
        from cantus import Analyzer  # noqa: F401


def test_Validator_class_no_longer_top_level():
    with pytest.raises(ImportError):
        from cantus import Validator  # noqa: F401


def test_register_analyzer_no_longer_top_level():
    with pytest.raises(ImportError):
        from cantus import register_analyzer  # noqa: F401


def test_register_validator_no_longer_top_level():
    with pytest.raises(ImportError):
        from cantus import register_validator  # noqa: F401


def test_workflow_protocol_module_removed():
    """v0.3.0: cantus.protocols.workflow file SHALL be hard-removed."""
    with pytest.raises(ImportError):
        import cantus.protocols.workflow  # noqa: F401


# --- v0.3.0: new submodule surface --------------------------------------


def test_cantus_hooks_importable():
    from cantus.hooks import (  # noqa: F401
        Analyzer,
        Result,
        Validator,
        analyzer,
        validator,
    )


def test_cantus_workflows_importable():
    from cantus.workflows import (  # noqa: F401
        EvaluatorOptimizer,
        OrchestratorWorker,
        Parallel,
        PromptChain,
        Router,
    )


# --- Memory (unchanged) -------------------------------------------------


def test_memory_has_no_decorator_entry():
    """Memory is class-only — `from cantus import memory` must fail."""
    with pytest.raises(ImportError):
        from cantus import memory  # noqa: F401


def test_memory_has_no_function_pass_entry():
    with pytest.raises(ImportError):
        from cantus import register_memory  # noqa: F401


# --- v0.3.1: new public surface -----------------------------------------


def test_v031_memory_implementations_importable():
    from cantus import AutoMemory, MarkdownMemory
    from cantus.protocols.memory import AutoMemory as A2
    from cantus.protocols.memory import MarkdownMemory as M2

    assert AutoMemory is A2
    assert MarkdownMemory is M2


def test_v031_identity_module_importable():
    from cantus import Soul, SoulParseError
    from cantus.identity import Soul as S2
    from cantus.identity import SoulParseError as E2

    assert Soul is S2
    assert SoulParseError is E2


def test_v031_event_stream_persistence_importable():
    from cantus import JsonLinesPersistence
    from cantus.core.event_stream_persistence import JsonLinesPersistence as J2

    assert JsonLinesPersistence is J2


def test_v031_all_includes_new_names():
    import cantus

    for name in (
        "MarkdownMemory",
        "AutoMemory",
        "Soul",
        "SoulParseError",
        "JsonLinesPersistence",
    ):
        assert name in cantus.__all__, f"{name} missing from cantus.__all__"


def test_v030_names_still_in_all():
    """v0.3.1 is additive; the v0.3.0 public surface must not regress."""
    import cantus

    for name in (
        "skill",
        "debug",
        "register_skill",
        "Skill",
        "Memory",
        "ShortTermMemory",
        "BM25Memory",
        "EmbeddingMemory",
        "Action",
        "CallSkillAction",
        "FinalAnswerAction",
        "Observation",
        "SkillObservation",
        "ToolErrorObservation",
        "ValidationErrorObservation",
        "MaxIterationsObservation",
        "EventStream",
        "Agent",
        "AgentState",
        "Inspector",
        "Registry",
        "get_registry",
        "Result",
        "ChatModel",
        "Message",
        "ToolCall",
        "ChatResponse",
        "ChatModelAsHandle",
        "load_chat_model",
        "ColabEnvironment",
        "LocalEnvironment",
        "CloudOnlyEnvironment",
    ):
        assert name in cantus.__all__, f"v0.3.0 name {name!r} dropped from __all__"


# --- v0.3.2: cantus.adapters subpackage ---------------------------------


def test_v032_adapters_three_callables_importable():
    from cantus.adapters import (
        expose_as_anthropic_memory_tool,
        export_as_mcp_server,
        import_mcp_server,
    )

    assert callable(export_as_mcp_server)
    assert callable(import_mcp_server)
    assert callable(expose_as_anthropic_memory_tool)


def test_v032_anthropic_memory_works_without_mcp_sdk():
    """`expose_as_anthropic_memory_tool` MUST NOT require the mcp SDK."""
    from cantus import ShortTermMemory
    from cantus.adapters import expose_as_anthropic_memory_tool

    tool_dict = expose_as_anthropic_memory_tool(ShortTermMemory(n=2))
    assert set(tool_dict.keys()) == {"type", "name", "description", "commands"}


def test_v032_mcp_gate_requires_extras(monkeypatch):
    """`cantus.adapters.mcp` (the gate module) raises ImportError without mcp SDK."""
    import sys

    for mod_name in list(sys.modules.keys()):
        if mod_name == "cantus.adapters.mcp" or mod_name.startswith("cantus.adapters.mcp."):
            del sys.modules[mod_name]
    monkeypatch.setitem(sys.modules, "mcp", None)

    with pytest.raises(ImportError, match=r"pip install cantus\[mcp\]"):
        import cantus.adapters.mcp  # noqa: F401


# --- v0.3.3: cantus.adapters batch2 cross-framework callables -----------


def test_v033_adapters_six_batch2_callables_importable():
    """The six batch2 callables are importable as lazy stubs from cantus.adapters."""
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


@pytest.mark.parametrize(
    "module_name, extras",
    [
        ("cantus.adapters.langchain", "langchain"),
        ("cantus.adapters.dspy", "dspy"),
        ("cantus.adapters.huggingface", "huggingface"),
        ("cantus.adapters.openhands", "openhands"),
    ],
)
def test_v033_batch2_gates_require_extras(monkeypatch, module_name, extras):
    """Each batch2 adapter module raises actionable ImportError without its SDK."""
    import importlib
    import sys

    # Map the cantus adapter module to the underlying framework SDK module.
    sdk_module = {
        "cantus.adapters.langchain": "langchain_core",
        "cantus.adapters.dspy": "dspy",
        "cantus.adapters.huggingface": "transformers",
        "cantus.adapters.openhands": "openhands",
    }[module_name]

    for mod_name in list(sys.modules.keys()):
        if mod_name == module_name:
            del sys.modules[mod_name]
        if mod_name == sdk_module or mod_name.startswith(f"{sdk_module}."):
            del sys.modules[mod_name]
    monkeypatch.setitem(sys.modules, sdk_module, None)

    with pytest.raises(ImportError, match=rf"pip install cantus\[{extras}\]"):
        importlib.import_module(module_name)


# --- version stamp ------------------------------------------------------


def test_version_is_0_4_1() -> None:
    import cantus

    assert cantus.__version__ == "0.4.1"
