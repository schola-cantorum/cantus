"""Verify the public import surface of cantus."""


def test_decorator_entries_importable():
    from cantus import skill, analyzer, validator, workflow, debug

    assert all(callable(d) for d in (skill, analyzer, validator, workflow, debug))


def test_function_pass_entries_importable():
    from cantus import (
        register_skill,
        register_analyzer,
        register_validator,
        register_workflow,
    )

    assert all(
        callable(f)
        for f in (
            register_skill,
            register_analyzer,
            register_validator,
            register_workflow,
        )
    )


def test_class_first_base_classes_importable():
    from cantus import Skill, Analyzer, Validator, Workflow, Memory

    for cls in (Skill, Analyzer, Validator, Workflow, Memory):
        assert isinstance(cls, type)


def test_runtime_types_importable():
    from cantus import (
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

    # Just ensure they all loaded without error
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
    from cantus import mount_drive_and_load, load_gemma

    assert callable(mount_drive_and_load)
    assert callable(load_gemma)


def test_public_mount_drive_and_load_accepts_drive_root(tmp_path):
    """Public re-export must propagate drive_root to the loader impl."""
    import pytest

    from cantus import mount_drive_and_load
    from cantus.model.loader import ModelNotFoundError

    with pytest.raises(ModelNotFoundError):
        mount_drive_and_load(
            variant="E4B",
            drive_root=str(tmp_path),
            allow_hub_fallback=False,
        )


def test_public_load_gemma_accepts_drive_root(tmp_path):
    """load_gemma alias must also propagate drive_root."""
    import pytest

    from cantus import load_gemma
    from cantus.model.loader import ModelNotFoundError

    with pytest.raises(ModelNotFoundError):
        load_gemma(
            variant="E4B",
            drive_root=str(tmp_path),
            allow_hub_fallback=False,
        )


def test_memory_has_no_decorator_entry():
    """Memory is class-only — `from cantus import memory` must fail."""
    import pytest

    with pytest.raises(ImportError):
        from cantus import memory  # noqa: F401


def test_memory_has_no_function_pass_entry():
    import pytest

    with pytest.raises(ImportError):
        from cantus import register_memory  # noqa: F401
