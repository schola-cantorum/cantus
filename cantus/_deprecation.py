"""Deprecation machinery shared by every legacy name."""

from __future__ import annotations

import builtins
import sys
import warnings
from types import FrameType

_TEMPLATE = (
    "{old} is deprecated since cantus 0.7.0 and will be removed in a later release; "
    "use {new} instead.{hint} "
    "See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/"
    "MIGRATION_v0.6.0_to_v0.7.0.md"
)

# w_id (or "w_id:variant") -> (old, new, hint). Section 2.4 of the epic traceability.
_TABLE: dict[str, tuple[str, str, str]] = {
    "W1": ("cantus.Skill", "cantus.Tool", ""),  # legacy-alias
    "W2": (
        "@skill",  # legacy-alias
        "@tool",
        " @tool does not register the tool; pass it with Agent(model, tools=[...]).",
    ),
    "W3": (
        "register_skill()",  # legacy-alias
        "register_tool(fn, registry=...)",
        " register_tool needs an explicit Registry.",
    ),
    "W4": ("CallSkillAction", "CallToolAction", ""),  # legacy-alias
    "W5": ("SkillObservation", "ToolObservation", ""),  # legacy-alias
    "W6": ("SkillEntry", "ToolEntry", ""),  # legacy-alias
    "W7": ("skill_name", "tool_name", ""),  # legacy-alias
    "W8": (
        "get_registry()",  # legacy-alias
        "a Registry you build yourself",
        " Pass tools with Agent(model, tools=[...]).",
    ),
    "W9": ('the registry kind "skill"', '"tool"', ""),  # legacy-alias
    "W10": ("Agent(registry=...)", "Agent(tools=...)", ""),
    "W11": (
        "creating an Agent without tools=",
        "Agent(model, tools=[...])",
        " This agent is using tools from the global registry, which @skill and "  # legacy-alias
        "register_skill fill (possibly inside a library you use).",  # legacy-alias
    ),
    "W12:build_schema": (
        "calling build_schema without registry=",
        "build_schema(..., registry=...)",
        "",
    ),
    "W12:parse_tool_call": (
        "calling parse_tool_call without registry=",
        "parse_tool_call(..., registry=...)",
        "",
    ),
    "W13": (
        'the action key "skill_name"',  # legacy-alias
        '"tool_name"',
        " Update scripted or few-shot model outputs.",
    ),
    "W14": ("SkillsPane", "ToolsPane", ""),  # legacy-alias
    "W15": ("active_skill_names", "active_tool_names", ""),  # legacy-alias
    "W16": ("collect_skills", "collect_tools", ""),  # legacy-alias
    "W17": ("update_skills()", "update_tools()", ""),  # legacy-alias
    "W18:skill": ("the keyword skill=", "tool=", ""),  # legacy-alias
    "W18:skills": ("the keyword skills=", "tools=", ""),  # legacy-alias
}


class CantusDeprecationWarning(DeprecationWarning):
    """Category of every warning cantus emits about a legacy name."""


def warn_legacy(w_id: str, *, variant: str | None = None) -> None:
    """Emit the warning for one legacy name.

    Args:
        w_id: The table id, such as ``"W2"``.
        variant: The variant key for ids that have two (``W12``, ``W18``).

    Raises:
        KeyError: If the id or variant is not in the table.
        CantusDeprecationWarning: If an active filter turns the warning into an error
            (never for W13).
    """
    old, new, hint = _TABLE[w_id if variant is None else f"{w_id}:{variant}"]
    message = _TEMPLATE.format(old=old, new=new, hint=hint)
    frame = _attributed_frame()
    try:
        warnings.warn_explicit(
            message,
            CantusDeprecationWarning,
            frame.f_code.co_filename,
            frame.f_lineno,
            module=frame.f_globals.get("__name__", "<unknown>"),
            registry=frame.f_globals.setdefault("__warningregistry__", {}),
            # No module_globals=: warn_explicit would then call the module's loader
            # get_source(), which raises ImportError for __main__ under `python -c`.
        )
    except CantusDeprecationWarning:
        # W13 fires while parsing model output: a filter that turns warnings into
        # errors must not turn that output into an exception. Every other id raises.
        if w_id != "W13":
            raise


_filter_installed = False


def install_default_filter() -> None:
    """Make cantus warnings visible under Python's default filters, once per process.

    Python hides ``DeprecationWarning`` outside ``__main__``, which would hide every
    cantus warning from a student. This inserts one ``default`` entry for
    ``CantusDeprecationWarning`` in front of Python's own ``ignore::DeprecationWarning``,
    and only there: any filter the user or a library set on purpose is left alone.
    """
    global _filter_installed
    if _filter_installed:
        return
    _filter_installed = True
    if any(_option_covers_cantus(option) for option in sys.warnoptions):
        return
    _insert_visible_entry()


_ACTIONS = ("default", "always", "ignore", "module", "once", "error")


def _option_covers_cantus(option: str) -> bool:
    """True if a ``-W`` / ``PYTHONWARNINGS`` entry names cantus's category with no scope.

    Parsed the way Python parses it, without importing anything the option names. An
    entry that Python would reject, that names another module's class, or that is scoped
    to a message, module or line does not count.
    """
    parts = option.split(":")
    if len(parts) > 5:
        return False
    action, message, category, module, lineno = [p.strip() for p in parts] + [""] * (5 - len(parts))
    if action and action != "all" and not any(a.startswith(action) for a in _ACTIONS):
        return False
    if lineno:
        try:
            number = int(lineno)
        except (ValueError, OverflowError):
            return False
        if number != 0:  # negative is invalid, positive is scoped to a line
            return False
    if message or module:
        return False
    if category.startswith("builtins."):
        category = category[len("builtins.") :]
        if not category:  # "builtins." names nothing
            return False
    if not category:
        resolved: object = Warning
    elif "." in category:
        return False
    else:
        resolved = getattr(builtins, category, None)
    return (
        isinstance(resolved, type)
        and issubclass(resolved, Warning)
        and issubclass(CantusDeprecationWarning, resolved)
    )


def _insert_visible_entry() -> None:
    """Insert the ``default`` entry for cantus's category in front of the ignore entry."""
    seen_main = False
    for index, entry in enumerate(warnings.filters):
        action, message, category, module, lineno = entry
        if (
            action == "default"
            and message is None
            and category is DeprecationWarning
            and getattr(module, "pattern", module) == "__main__"  # str when set by the C core
            and lineno == 0
        ):
            seen_main = True
        if message is not None or module is not None or lineno != 0:
            continue
        if not issubclass(CantusDeprecationWarning, category):
            continue
        if action == "ignore" and category is DeprecationWarning and seen_main:
            _insert_locked(index)
        return


def _insert_locked(index: int) -> None:
    """Insert the entry at ``index`` and tell the warnings module its filters changed."""
    lock = getattr(warnings, "_lock", None)
    held = lock is not None and hasattr(lock, "__enter__")
    # These names are CPython-private; if neither exists the insert still takes effect on
    # the next filter lookup or is a no-op for caching interpreters, and the visibility
    # tests would show it.
    names = ("_filters_mutated_lock_held", "_filters_mutated") if held else (
        "_filters_mutated",
        "_filters_mutated_lock_held",
    )

    def insert() -> None:
        warnings.filters.insert(  # type: ignore[attr-defined]
            index, ("default", None, CantusDeprecationWarning, None, 0)
        )
        for name in names:
            mutated = getattr(warnings, name, None)
            if mutated is not None:
                mutated()
                break

    if held:
        with lock:  # type: ignore[union-attr]
            insert()
    else:
        insert()


_IMPORT_MACHINERY = frozenset(
    {
        "importlib._bootstrap",
        "importlib._bootstrap_external",
        "_frozen_importlib",
        "_frozen_importlib_external",
    }
)


def _is_internal(frame: FrameType) -> bool:
    """True for cantus frames and for the import machinery, which never own a warning."""
    name = frame.f_globals.get("__name__")
    if isinstance(name, str) and (name == "cantus" or name.startswith("cantus.")):
        return True
    return name in _IMPORT_MACHINERY


def _attributed_frame() -> FrameType:
    """Return the first frame outside cantus and the import machinery, else the outermost."""
    frame = sys._getframe(2)  # skip _attributed_frame and warn_legacy
    while True:
        if not _is_internal(frame) or frame.f_back is None:
            return frame
        frame = frame.f_back
