"""Building blocks for composing Skills into multi-step workflows.

v0.3.0 replaced the `@workflow` decorator with these five explicit, plain-Python
classes (taken from Anthropic's "Building Effective Agents" playbook). They
take registered `Skill` instances (or any callable) in their constructor and
expose a `.run(input) -> output` method. They SHALL NOT register themselves
into the runtime `Registry` and SHALL NOT appear in `registry.spec_for_llm()`.

    from cantus.workflows import PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer
"""

from cantus.workflows.evaluator_optimizer import EvaluatorOptimizer
from cantus.workflows.orchestrator_worker import OrchestratorWorker
from cantus.workflows.parallel import Parallel
from cantus.workflows.prompt_chain import PromptChain
from cantus.workflows.router import Router

__all__ = [
    "EvaluatorOptimizer",
    "OrchestratorWorker",
    "Parallel",
    "PromptChain",
    "Router",
]
