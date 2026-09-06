"""Parser for executable documentation pages (ADR-0003).

Reads one English page under ``docs/site/`` and reports two things: the Python
blocks it contains, and every place where the page is *malformed* under the
rules the documentation harness enforces. The rules are restated in the
docstrings below so this module is readable on its own; the planning snapshot
they were drafted in is ``.proj.spec/docs-tutorial-and-vv.md`` Appendix A
(A.2.0 fences, A.2.1 skip markers, A.2.3 model hooks).

This module is a helper imported by the docs test modules; it holds no tests.
It cites ADR-0003 so the ADR guardrail can find it.
"""

from __future__ import annotations

import ast
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "docs" / "site"

# A.3 — the English pages whose Python blocks the harness owns. Tutorial pages
# and the piece-by-piece page join this list in the tickets that create them.
IN_SCOPE_PAGES: tuple[str, ...] = (
    "quickstart-desktop.md",
    "core/agent.md",
    "core/event-stream.md",
    "core/inspector.md",
    "protocols/skill.md",
    "protocols/memory.md",
    "protocols/analyzer.md",
    "protocols/validator.md",
    "protocols/workflows.md",
    "cookbook/patterns.md",
    "cookbook/errors.md",
    "cookbook/tips.md",
)

FenceChar = Literal["`", "~"]
MalformedKind = Literal["fence", "marker", "hook"]

# A.2.0: a fence opens on a line with at most three spaces of indentation and
# three or more backticks; the info string may not contain a backtick.
_BACKTICK_OPEN = re.compile(r"^(?P<indent>[ ]{0,3})(?P<run>`{3,})(?P<info>[^`]*)$")
# CommonMark tilde fences are recognised only so that a tilde fence carrying
# Python can be reported as malformed (A.2.0).
_TILDE_OPEN = re.compile(r"^(?P<indent>[ ]{0,3})(?P<run>~{3,})(?P<info>.*)$")
# A line of four or more spaces followed by backticks is not a fence in
# CommonMark (it is an indented code block); A.2.0 flags it when its content is
# Python that mentions cantus, because that is a fence the author meant to write.
_DEEP_INDENT_OPEN = re.compile(r"^[ ]{4,}`{3,}")

# A.2.1: the skip marker. ``[^-]`` in the reason class is what makes a hyphen a
# malformed marker rather than a valid one with a hyphen in it.
_SKIP_MARKER = re.compile(r"^[ ]*<!-- vv:skip: (?P<reason>[^-]*\S[^-]*) -->$")
_SKIP_MIN_REASON_CHARS = 8
_SKIP_TOKEN = "vv:skip"

# A.2.3: the model hook. ``=(?!=)`` keeps a bare ``x == y`` comparison from
# qualifying; an assignment whose right-hand side contains ``==`` still matches,
# because the pattern only constrains the first ``=`` after the target.
_HOOK = re.compile(
    r"^(?P<indent>[ ]*)(?P<lhs>[A-Za-z_][A-Za-z0-9_.]*)[ ]*=(?!=)[ ]*.+"
    r"# under docs tests: cantus_docs_model\(\)$"
)
HOOK_NAME = "cantus_docs_model"


@dataclass(frozen=True)
class Malformed:
    """One rule violation.

    Attributes:
        line: 1-based line in the page the violation sits on.
        kind: which rule family it breaks.
        message: what the rule requires, for the test failure output.
    """

    line: int
    kind: MalformedKind
    message: str


@dataclass(frozen=True)
class SkipMarker:
    """A valid A.2.1 marker: the 1-based line it sits on and its reason text."""

    line: int
    reason: str


@dataclass(frozen=True)
class Hook:
    """A line the harness rewrites to ``<indent><lhs> = cantus_docs_model()``.

    Attributes:
        line: 1-based line in the page.
        block_line: 0-based line within the block's content.
        indent: leading spaces to keep.
        lhs: assignment target to keep (dotted names allowed).
    """

    line: int
    block_line: int
    indent: str
    lhs: str


@dataclass(frozen=True)
class Fence:
    """One fenced code block of any language, as CommonMark delimits it.

    Attributes:
        open_line: 1-based line of the opening fence.
        close_line: 1-based line of the closing fence.
        char: the fence character (backtick or tilde).
        indent: the opening fence's indentation (0–3 spaces).
        info: the stripped info string.
        lines: content lines, dedented by ``indent`` where present.
    """

    open_line: int
    close_line: int
    char: FenceChar
    indent: str
    info: str
    lines: list[str]


@dataclass(frozen=True)
class PythonBlock:
    """A backtick fence whose info string is exactly ``python``.

    Attributes:
        index: 0-based position among the page's Python blocks.
        fence: the underlying fence.
        skip: the valid skip marker directly before it, if any.
        hooks: the A.2.3 hook lines found in its content.
    """

    index: int
    fence: Fence
    skip: SkipMarker | None
    hooks: list[Hook] = field(default_factory=list)

    @property
    def lines(self) -> list[str]:
        return self.fence.lines

    @property
    def skipped(self) -> bool:
        return self.skip is not None


@dataclass(frozen=True)
class ParsedPage:
    """What the parser saw on one page.

    Attributes:
        fences: every fence, in document order, whatever its language.
        python_blocks: the Python blocks, in document order.
        malformed: every rule violation, sorted by line.
    """

    fences: list[Fence]
    python_blocks: list[PythonBlock]
    malformed: list[Malformed]


def parse_page(text: str) -> ParsedPage:
    """Parse one page's text under the A.2.0, A.2.1 and A.2.3 rules.

    Args:
        text: the page's full markdown source.

    Returns:
        The fences, Python blocks (with skip markers and hooks attached) and
        malformed findings. A page with findings is still parsed as far as the
        rules allow, so a test can report every problem at once.
    """
    lines = text.split("\n")
    fences, malformed = _scan_fences(lines)

    python_blocks: list[PythonBlock] = []
    valid_marker_lines: set[int] = set()
    for fence in fences:
        verdict = _python_fence_verdict(fence)
        if verdict is not None:
            malformed.append(Malformed(fence.open_line, "fence", verdict))
            continue
        if fence.char == "`" and fence.info == "python":
            skip = _marker_before(lines, fence.open_line)
            if skip is not None:
                valid_marker_lines.add(skip.line)
            hooks, bad_hooks = _scan_hooks(fence)
            malformed.extend(bad_hooks)
            python_blocks.append(
                PythonBlock(index=len(python_blocks), fence=fence, skip=skip, hooks=hooks)
            )

    # A.2.1: any line anywhere containing the marker token that is not, by the
    # rule above, a valid marker directly before a Python fence is malformed.
    # This covers short reasons, hyphens, blank lines between marker and fence,
    # markers before non-Python fences, and stray mentions in prose or code.
    for number, line in enumerate(lines, start=1):
        if _SKIP_TOKEN in line and number not in valid_marker_lines:
            malformed.append(
                Malformed(
                    number,
                    "marker",
                    f"line contains {_SKIP_TOKEN!r} but is not a valid skip marker "
                    "immediately before a Python fence (A.2.1: "
                    "'<!-- vv:skip: <reason> -->', reason of at least "
                    f"{_SKIP_MIN_REASON_CHARS} non-space characters, no hyphen)",
                )
            )
    malformed.sort(key=lambda m: m.line)

    return ParsedPage(fences=fences, python_blocks=python_blocks, malformed=malformed)


def _dedent(line: str, indent: str) -> str:
    """Remove the fence's indentation from a content line, where present."""
    n = 0
    while n < len(indent) and n < len(line) and line[n] == " ":
        n += 1
    return line[n:]


def _closing_run(line: str, char: FenceChar, min_indent: int, max_indent: int) -> int:
    """Length of the fence run on a closing line, or 0 if the line is not one.

    A closing line is a run of ``char`` and nothing else, indented within
    ``[min_indent, max_indent]`` spaces.
    """
    m = re.match(
        rf"^[ ]{{{min_indent},{max_indent}}}({re.escape(char)}{{3,}})[ \t]*$", line
    )
    return len(m.group(1)) if m is not None else 0


def _opens_fence(line: str) -> bool:
    return _BACKTICK_OPEN.match(line) is not None or _TILDE_OPEN.match(line) is not None


def _scan_fences(lines: list[str]) -> tuple[list[Fence], list[Malformed]]:
    fences: list[Fence] = []
    malformed: list[Malformed] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        char: FenceChar = "`"
        m = _BACKTICK_OPEN.match(line)
        if m is None:
            m = _TILDE_OPEN.match(line)
            char = "~"
        if m is not None:
            indent, run, info = m.group("indent"), m.group("run"), m.group("info").strip()
            # A.2.0: the block ends at the next line that is at least as many
            # fence characters as the opening run, nothing else, indented by at
            # most three spaces.
            j = i + 1
            while j < len(lines) and _closing_run(lines[j], char, 0, 3) < len(run):
                j += 1
            if j >= len(lines):
                malformed.append(
                    Malformed(i + 1, "fence", f"unterminated fence opened with {run!r}")
                )
                # Everything after an unterminated fence is fence content.
                break
            fences.append(
                Fence(
                    open_line=i + 1,
                    close_line=j + 1,
                    char=char,
                    indent=indent,
                    info=info,
                    lines=[_dedent(text, indent) for text in lines[i + 1 : j]],
                )
            )
            i = j + 1
            continue
        if _DEEP_INDENT_OPEN.match(line):
            i = _check_deep_indented_block(lines, i, malformed)
            continue
        i += 1
    return fences, malformed


def _check_deep_indented_block(lines: list[str], start: int, malformed: list[Malformed]) -> int:
    """A.2.0: a fence indented by four or more spaces is not a fence.

    It never opens a block, so it cannot swallow a real fence that follows: its
    content runs until a deep-indented closing line or the next real fence
    opener, whichever comes first. If that content, dedented, is Python that
    mentions cantus, the author meant to write a fence and the page is
    malformed. Returns the index to resume scanning from.
    """
    j = start + 1
    while j < len(lines) and not _opens_fence(lines[j]):
        if _closing_run(lines[j], "`", 4, 10**6):
            break
        j += 1
    body = textwrap.dedent("\n".join(lines[start + 1 : j]))
    if "cantus" in body and _parses_as_python(body):
        malformed.append(
            Malformed(
                start + 1,
                "fence",
                "fence indented by four or more spaces is an indented code block, "
                "not a fence; its content is Python that mentions cantus",
            )
        )
    closed = j < len(lines) and not _opens_fence(lines[j])
    return j + 1 if closed else j


def _parses_as_python(source: str) -> bool:
    try:
        ast.parse(source)
    except SyntaxError:
        return False
    return True


def _python_fence_verdict(fence: Fence) -> str | None:
    """Return a malformed-fence message for a fence that carries Python under a
    wrong info string, ``None`` for anything else (including a valid block)."""
    info = fence.info
    if fence.char == "~":
        if info.startswith("py"):
            return f"tilde fence with info string {info!r}; Python blocks use backticks"
        return None
    if info == "python":
        return None
    if info == "py" or info.startswith("python"):
        return f"info string {info!r}; a Python block's info string must be exactly 'python'"
    return None


def _marker_before(lines: list[str], open_line: int) -> SkipMarker | None:
    """A.2.1: the line immediately before the opening fence, if it is a valid
    skip marker. Blank lines between marker and fence make it invalid."""
    if open_line < 2:
        return None
    candidate = lines[open_line - 2]
    m = _SKIP_MARKER.match(candidate)
    if m is None:
        return None
    reason = m.group("reason")
    if sum(1 for c in reason if not c.isspace()) < _SKIP_MIN_REASON_CHARS:
        return None
    return SkipMarker(line=open_line - 1, reason=reason)


def _scan_hooks(fence: Fence) -> tuple[list[Hook], list[Malformed]]:
    """A.2.3: a block line matching the hook pattern is a hook; any other block
    line that names the hook is malformed. Skipped blocks are scanned too (the
    harness never substitutes in them, but a wrong line there is still wrong)."""
    hooks: list[Hook] = []
    bad: list[Malformed] = []
    for offset, text in enumerate(fence.lines):
        if HOOK_NAME not in text:
            continue
        m = _HOOK.match(text)
        page_line = fence.open_line + 1 + offset
        if m is None:
            bad.append(
                Malformed(
                    page_line,
                    "hook",
                    f"line names {HOOK_NAME} but is not a hook line "
                    "(A.2.3: '<name> = <expr>  # under docs tests: cantus_docs_model()')",
                )
            )
            continue
        hooks.append(
            Hook(line=page_line, block_line=offset, indent=m.group("indent"), lhs=m.group("lhs"))
        )
    return hooks, bad
