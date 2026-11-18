"""OrchestratorWorker: orchestrator plans subtasks, workers execute round-robin."""

from __future__ import annotations

import pytest

from cantus.core.registry import _get_global_registry
from cantus import tool
from cantus.workflows import OrchestratorWorker


def test_orchestrator_emits_subtasks_workers_execute_each():
    @tool
    def plan(input: str) -> list[str]:
        """Split into three subtasks."""
        return [f"task_{i}:{input}" for i in range(3)]

    @tool
    def fetch(task: str) -> str:
        """Execute one subtask."""
        return f"done:{task}"

    ow = OrchestratorWorker(orchestrator=plan, workers=[fetch])
    out = ow.run("tainan guide")

    assert out == [
        "done:task_0:tainan guide",
        "done:task_1:tainan guide",
        "done:task_2:tainan guide",
    ]


def test_orchestrator_worker_round_robin_workers():
    @tool
    def plan(input: str) -> list[str]:
        """Two subtasks."""
        return ["A", "B", "C"]

    @tool
    def w1(task: str) -> str:
        """Worker 1."""
        return f"w1:{task}"

    @tool
    def w2(task: str) -> str:
        """Worker 2."""
        return f"w2:{task}"

    ow = OrchestratorWorker(orchestrator=plan, workers=[w1, w2])
    out = ow.run("anything")

    # subtasks: ["A", "B", "C"] → workers: w1, w2, w1 (round-robin)
    assert out == ["w1:A", "w2:B", "w1:C"]


def test_orchestrator_worker_does_not_pollute_registry():
    @tool
    def plan(input: str) -> list[str]:
        """Plan."""
        return ["x"]

    @tool
    def work(task: str) -> str:
        """Work."""
        return task

    OrchestratorWorker(orchestrator=plan, workers=[work]).run("input")
    assert _get_global_registry().names_for("tool") == []


def test_orchestrator_worker_empty_workers_raises():
    @tool
    def plan(input: str) -> list[str]:
        """Plan."""
        return []

    with pytest.raises(ValueError):
        OrchestratorWorker(orchestrator=plan, workers=[])
