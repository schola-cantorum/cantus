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


# --- v0.3.0 version stamp -----------------------------------------------


def test_version_is_0_3_0():
    import cantus

    assert cantus.__version__ == "0.3.0"
