"""cantus — LLM agent harness teaching framework for Google Colab."""

__version__ = "0.1.4"

from cantus.core.action import (
    Action,
    CallSkillAction,
    FinalAnswerAction,
)
from cantus.core.agent import Agent, AgentState
from cantus.core.event_stream import EventStream
from cantus.core.observation import (
    MaxIterationsObservation,
    Observation,
    SkillObservation,
    ToolErrorObservation,
    ValidationErrorObservation,
)
from cantus.core.registry import Registry, get_registry
from cantus.core.result import Result
from cantus.inspect import Inspector
from cantus.protocols.analyzer import (
    Analyzer,
    analyzer,
    register_analyzer,
)
from cantus.protocols.debug import debug
from cantus.protocols.memory import (
    BM25Memory,
    EmbeddingMemory,
    Memory,
    ShortTermMemory,
)
from cantus.protocols.skill import Skill, register_skill, skill
from cantus.protocols.validator import (
    Validator,
    register_validator,
    validator,
)
from cantus.protocols.workflow import (
    Workflow,
    register_workflow,
    workflow,
)

__all__ = [
    # Decorator entries
    "skill",
    "analyzer",
    "validator",
    "workflow",
    "debug",
    # Function-pass entries
    "register_skill",
    "register_analyzer",
    "register_validator",
    "register_workflow",
    # Class-first base classes
    "Skill",
    "Analyzer",
    "Validator",
    "Workflow",
    "Memory",
    # Memory implementations
    "ShortTermMemory",
    "BM25Memory",
    "EmbeddingMemory",
    # Runtime
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
    "Inspector",
    # Registry
    "Registry",
    "get_registry",
    # Result type for validators
    "Result",
]


def mount_drive_and_load(*args, **kwargs):
    """Mount Google Drive and load Gemma 4 weights — see model.loader."""
    from cantus.model.loader import mount_drive_and_load as _impl

    return _impl(*args, **kwargs)


def load_gemma(*args, **kwargs):
    """Alias of mount_drive_and_load for direct hub loading scenarios."""
    return mount_drive_and_load(*args, **kwargs)
