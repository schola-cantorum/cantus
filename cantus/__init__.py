"""cantus — Polyphonic LLM agent framework with a dual-tier teaching API."""

__version__ = "0.3.0"

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
from cantus.env import CloudOnlyEnvironment, ColabEnvironment, LocalEnvironment
from cantus.inspect import Inspector
from cantus.model.bridge import ChatModelAsHandle
from cantus.model.chat import ChatModel, ChatResponse, Message, ToolCall
from cantus.model.factory import load_chat_model
from cantus.protocols.debug import debug
from cantus.protocols.memory import (
    BM25Memory,
    EmbeddingMemory,
    Memory,
    ShortTermMemory,
)
from cantus.protocols.skill import Skill, register_skill, skill

__all__ = [
    # Decorator entries (v0.3.0: Skill + debug only at top level;
    # analyzer/validator are now imported from cantus.hooks)
    "skill",
    "debug",
    # Function-pass entries
    "register_skill",
    # Class-first base classes (top level: Skill + Memory only;
    # Analyzer/Validator are imported from cantus.hooks)
    "Skill",
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
    "AgentState",
    "Inspector",
    # Registry
    "Registry",
    "get_registry",
    # Result type
    "Result",
    # Tier 2 ChatModel
    "ChatModel",
    "Message",
    "ToolCall",
    "ChatResponse",
    "ChatModelAsHandle",
    "load_chat_model",
    # Environment profiles
    "ColabEnvironment",
    "LocalEnvironment",
    "CloudOnlyEnvironment",
]


def mount_drive_and_load(*args, **kwargs):
    """Mount Google Drive and load Gemma 4 weights — see model.loader."""
    from cantus.model.loader import mount_drive_and_load as _impl

    return _impl(*args, **kwargs)


def load_gemma(*args, **kwargs):
    """Alias of mount_drive_and_load for direct hub loading scenarios."""
    return mount_drive_and_load(*args, **kwargs)
