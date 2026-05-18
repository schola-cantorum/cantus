"""OrchestratorWorker — orchestrator plans subtasks, workers execute them."""

from __future__ import annotations

from typing import Any, Callable, Iterable


class OrchestratorWorker:
    """Plan-and-execute pattern.

    The orchestrator Skill is called once with the input and SHALL return an
    iterable of subtask inputs. Each subtask is then dispatched to one of the
    worker Skills (round-robin by index). The result is a list of worker
    outputs in the same order as the subtasks the orchestrator emitted.

    Aggregation is left to the host: pipe the resulting list through another
    Skill or use `PromptChain` if you want a synthesis step.

    Pure Python composition — SHALL NOT touch the runtime registry.

        ow = OrchestratorWorker(orchestrator=plan, workers=[fetch_section])
        ow.run("Tainan travel guide")
    """

    def __init__(
        self,
        orchestrator: Callable[[Any], Iterable[Any]],
        workers: Iterable[Callable[..., Any]],
    ) -> None:
        self.orchestrator = orchestrator
        self.workers = list(workers)
        if not self.workers:
            raise ValueError("OrchestratorWorker requires at least one worker")

    def run(self, input: Any) -> list[Any]:
        subtasks = list(self.orchestrator(input))
        outputs: list[Any] = []
        for i, task in enumerate(subtasks):
            worker = self.workers[i % len(self.workers)]
            outputs.append(worker(task))
        return outputs
