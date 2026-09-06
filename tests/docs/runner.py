"""Page execution and the expected-output assertion (ADR-0003).

Takes a page parsed by :mod:`tests.docs.pages`, builds the *page script* (the
non-skipped Python blocks in document order, hook lines substituted), runs it
once in a subprocess that looks like a reader's machine, and checks the page's
*expected-output block* against the captured stdout. The rules restated below
were drafted in ``.proj.spec/docs-tutorial-and-vv.md`` Appendix A (A.2.2
expected-output block, A.2.3 hook substitution, A.2.10 page execution).

This module is a helper imported by the docs test modules; it holds no tests.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from tests.docs.pages import (
    HOOK_NAME,
    ROOT,
    Fence,
    Malformed,
    ParsedPage,
    PythonBlock,
    parse_page,
)

EXPECTED_OUTPUT_PHRASE = "You should see"
EXPECTED_OUTPUT_PHRASE_ZH_TW = "你應該看到"
EXPECTED_OUTPUT_INFO = "text"
DEFAULT_TIMEOUT_SECONDS = 120

# A.2.10: the environment a page script sees. PATH and the locale variables
# are copied from the pytest process when present; the rest are fixed.
_ENV_PASSTHROUGH = ("PATH", "LANG", "LC_ALL")

# A traceback frame that points into the page script.
_TRACEBACK_FRAME = re.compile(r'^\s*File ".*page\.py", line (?P<line>\d+)', re.MULTILINE)

# A.2.10 preamble. (a) Sockets raise, as an anti-accident measure only — a
# page that reaches for the network fails loudly instead of depending on the
# runner's connectivity. (b) The script directory leaves ``sys.path`` by value,
# so a page cannot import a file it just wrote whether or not the interpreter
# honours PYTHONSAFEPATH (3.11+). (c) ``cantus_docs_model`` answers every
# ``generate`` call with a final answer.
# Names in the preamble carry a ``_vv_`` prefix (verification and validation,
# the harness's job) so they cannot collide with a page's own names; every
# helper is deleted at the end except ``_VvScriptedModel``, which
# ``cantus_docs_model`` looks up by name and which therefore stays in the page
# namespace.
_PREAMBLE = '''\
import os as _vv_os, socket as _vv_socket, sys as _vv_sys

def _vv_no_network(*args, **kwargs):
    raise RuntimeError("docs harness: network access is disabled (socket patched)")

_vv_socket.socket = _vv_no_network
_vv_socket.create_connection = _vv_no_network
_vv_script_dir = _vv_os.path.realpath(_vv_os.path.dirname(_vv_os.path.abspath(__file__)))
_vv_sys.path[:] = [
    p for p in _vv_sys.path
    if _vv_os.path.realpath(p or _vv_os.getcwd()) != _vv_script_dir
]

class _VvScriptedModel:
    """Scripted model used by the hook: every reply is a final answer."""

    def generate(self, prompt, **kwargs):
        return '{"thought": "docs", "action": {"final_answer": "ok"}}'

def cantus_docs_model():
    return _VvScriptedModel()

del _vv_os, _vv_socket, _vv_sys, _vv_script_dir, _vv_no_network
'''


@dataclass(frozen=True)
class ExpectedOutput:
    """The A.2.2 block: the ``text`` fence and its non-empty, stripped lines."""

    fence: Fence
    lines: list[str]


@dataclass(frozen=True)
class PageScript:
    """The page script and the block each source line came from.

    Attributes:
        source: preamble plus the substituted, concatenated blocks.
        block_of_line: for each 1-based source line, the index of the Python
            block it came from, or ``None`` for preamble lines.
    """

    source: str
    block_of_line: dict[int, int | None]

    def block_for(self, line: int) -> int | None:
        """The Python block a 1-based script line came from, or ``None``."""
        return self.block_of_line.get(line)


@dataclass(frozen=True)
class RunResult:
    """What one subprocess run of a page script produced.

    Attributes:
        returncode: the exit status (``-1`` when the run timed out).
        stdout: captured standard output.
        stderr: captured standard error, kept separate from stdout.
        timed_out: whether the run was abandoned at the timeout.
    """

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


@dataclass(frozen=True)
class PageOutcome:
    """Verdict for one page.

    Attributes:
        ok: no problem was found.
        problems: human-readable findings, in the order they were found.
        skipped: number of skipped Python blocks (feeds the ratchet).
        executed: whether a page script ran (skip-only pages never run).
        run: the subprocess result when one ran.
    """

    ok: bool
    problems: list[str] = field(default_factory=list)
    skipped: int = 0
    executed: bool = False
    run: RunResult | None = None


def find_expected_output(
    text: str, parsed: ParsedPage, *, phrase: str = EXPECTED_OUTPUT_PHRASE
) -> tuple[ExpectedOutput | None, list[Malformed]]:
    """A.2.2: locate the page's expected-output block, if any.

    Args:
        text: the page source.
        parsed: its parse.
        phrase: the marker phrase the preceding prose line must contain
            (English pages use ``You should see``, zh-tw pages ``你應該看到``).

    Returns:
        The block and the problems found. Exactly one block is required on a
        page that is not skip-only and forbidden on one that is; those
        cardinality rules are applied by :func:`verify_page`, not here. This
        function reports only a block with no non-empty line, and a second
        candidate block.
    """
    lines = text.split("\n")
    inside: set[int] = set()
    for fence in parsed.fences:
        inside.update(range(fence.open_line, fence.close_line + 1))
    in_comment = _html_comment_lines(lines, inside)

    problems: list[Malformed] = []
    candidates: list[ExpectedOutput] = []
    for fence in parsed.fences:
        if fence.info != EXPECTED_OUTPUT_INFO:
            continue
        preceding = _preceding_non_blank(lines, fence.open_line)
        if preceding is None or preceding in inside or preceding in in_comment:
            continue
        prose = lines[preceding - 1].strip()
        if prose.startswith(":::") or phrase not in prose:
            continue
        if fence.char != "`":
            problems.append(
                Malformed(
                    fence.open_line,
                    "fence",
                    "expected-output block must be a backtick fence, not a tilde fence",
                )
            )
            continue
        content = [line.rstrip() for line in fence.lines if line.strip()]
        candidates.append(ExpectedOutput(fence=fence, lines=content))

    if not candidates:
        return None, problems
    first = candidates[0]
    if not first.lines:
        problems.append(
            Malformed(first.fence.open_line, "fence", "expected-output block is empty")
        )
    for extra in candidates[1:]:
        problems.append(
            Malformed(
                extra.fence.open_line,
                "fence",
                "a page has exactly one expected-output block; this is another one",
            )
        )
    return first, problems


def _html_comment_lines(lines: list[str], inside_fences: set[int]) -> set[int]:
    """1-based numbers of lines that are, or sit inside, an HTML comment.

    Fence content is not scanned, so a ``<!--`` printed by a page cannot open a
    comment. A line that both opens and closes a comment counts as a comment
    line; a line after ``-->`` on which prose follows the close is prose.
    """
    result: set[int] = set()
    open_comment = False
    for number, line in enumerate(lines, start=1):
        if number in inside_fences:
            continue
        stripped = line.strip()
        if open_comment:
            result.add(number)
            if "-->" in stripped:
                open_comment = False
                if not stripped.endswith("-->"):
                    result.discard(number)
            continue
        if stripped.startswith("<!--"):
            result.add(number)
            if "-->" not in stripped:
                open_comment = True
    return result


def _preceding_non_blank(lines: list[str], open_line: int) -> int | None:
    """1-based number of the last non-blank line before ``open_line``."""
    i = open_line - 1
    while i >= 1:
        if lines[i - 1].strip():
            return i
        i -= 1
    return None


def build_page_script(parsed: ParsedPage) -> PageScript:
    """A.2.3 + A.2.10: the runnable script for a parsed page.

    Skipped blocks are dropped; in the rest, each hook line becomes
    ``<indent><lhs> = cantus_docs_model()``; the preamble goes first.

    Args:
        parsed: the page's parse.

    Returns:
        The script source and the line-to-block map used to name the block a
        traceback points into.
    """
    out: list[str] = _PREAMBLE.split("\n")[:-1]
    block_of_line: dict[int, int | None] = {n: None for n in range(1, len(out) + 1)}
    for block in parsed.python_blocks:
        if block.skipped:
            continue
        hooks = {hook.block_line: hook for hook in block.hooks}
        for offset, line in enumerate(block.lines):
            hook = hooks.get(offset)
            text = f"{hook.indent}{hook.lhs} = {HOOK_NAME}()" if hook else line
            out.append(text)
            block_of_line[len(out)] = block.index
        out.append("")
        block_of_line[len(out)] = block.index
    return PageScript(source="\n".join(out) + "\n", block_of_line=block_of_line)


def run_page_script(
    source: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    env_overrides: dict[str, str | None] | None = None,
) -> RunResult:
    """A.2.10: run a page script once in a fresh subprocess.

    Args:
        source: the script text.
        timeout: seconds before the run is abandoned.
        env_overrides: variables to add to, or (with ``None``) remove from,
            the whitelisted environment; tests use it, pages never do.

    Returns:
        Exit status and the separately captured stdout and stderr.
    """
    with tempfile.TemporaryDirectory(prefix="cantus-docs-") as tmp:
        script = Path(tmp) / "page.py"
        script.write_text(source, encoding="utf-8")
        env: dict[str, str] = {
            "PYTHONPATH": str(ROOT),
            "PYTHONSAFEPATH": "1",
            "HOME": tmp,
        }
        for name in _ENV_PASSTHROUGH:
            value = os.environ.get(name)
            if value is not None:
                env[name] = value
        for name, value in (env_overrides or {}).items():
            if value is None:
                env.pop(name, None)
            else:
                env[name] = value
        try:
            completed = subprocess.run(
                [sys.executable, "-B", "-s", "-X", "utf8", str(script)],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return RunResult(
                returncode=-1,
                stdout=_decode(exc.stdout),
                stderr=_decode(exc.stderr),
                timed_out=True,
            )
    return RunResult(completed.returncode, completed.stdout, completed.stderr)


def _decode(data: bytes | str | None) -> str:
    if data is None:
        return ""
    return data if isinstance(data, str) else data.decode("utf-8", "replace")


def verify_page(
    text: str,
    *,
    name: str = "<page>",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    env_overrides: dict[str, str | None] | None = None,
) -> PageOutcome:
    """The reader's-eye test for one page.

    Parse it; require at least one Python block; require exactly one
    expected-output block unless every block is skipped (then require none);
    run the page script; check the expected lines appear in stdout in order.

    Args:
        text: the page source.
        name: how to refer to the page in problems.
        timeout: forwarded to :func:`run_page_script`.
        env_overrides: forwarded to :func:`run_page_script`.

    Returns:
        The verdict, every problem found, the skip count and the run result.
    """
    parsed = parse_page(text)
    problems = [format_problem(name, m) for m in parsed.malformed]
    blocks = parsed.python_blocks
    if not blocks:
        problems.append(f"{name}: in-scope page has no Python block")
        return PageOutcome(ok=False, problems=problems)

    skipped = sum(1 for b in blocks if b.skipped)
    skip_only = skipped == len(blocks)
    expected, expected_problems = find_expected_output(text, parsed)
    problems += [format_problem(name, m) for m in expected_problems]

    if skip_only:
        if expected is not None:
            problems.append(
                f"{name}:{expected.fence.open_line}: skip-only page must not carry an "
                "expected-output block (nothing runs, so nothing can be checked)"
            )
        return PageOutcome(ok=not problems, problems=problems, skipped=skipped)

    if expected is None:
        problems.append(
            f"{name}: page is not skip-only, so it needs exactly one expected-output "
            f"block: a `{EXPECTED_OUTPUT_INFO}` fence whose preceding prose line "
            f"contains {EXPECTED_OUTPUT_PHRASE!r}"
        )
    if problems:
        return PageOutcome(ok=False, problems=problems, skipped=skipped)
    assert expected is not None

    script = build_page_script(parsed)
    run = run_page_script(script.source, timeout=timeout, env_overrides=env_overrides)
    if run.timed_out:
        problems.append(f"{name}: page script timed out after {timeout:g} s")
    elif run.returncode != 0:
        problems.append(_failure_message(name, script, run, blocks))
    else:
        missing = _first_missing_line(expected.lines, run.stdout)
        if missing is not None:
            problems.append(
                f"{name}:{expected.fence.open_line}: expected-output line not found in "
                f"stdout (in order): {missing!r}\n--- stdout ---\n{run.stdout}"
            )
    return PageOutcome(
        ok=not problems, problems=problems, skipped=skipped, executed=True, run=run
    )


def format_problem(name: str, problem: Malformed) -> str:
    """``<page>:<line>: [<kind>] <message>`` — the one shape every report uses."""
    return f"{name}:{problem.line}: [{problem.kind}] {problem.message}"


def working_tree_state() -> str:
    """``git status --porcelain`` for the checkout, as one string.

    Snapshotted before the docs tests and compared after them (A.2.10), so a
    page script that writes into the checkout instead of its temporary cwd is
    caught even if every other assertion passed.
    """
    return subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _first_missing_line(expected: list[str], stdout: str) -> str | None:
    """A.2.2 comparison: each expected line must appear in stdout, in order."""
    out = [line.rstrip() for line in stdout.split("\n")]
    cursor = 0
    for want in expected:
        while cursor < len(out) and out[cursor] != want:
            cursor += 1
        if cursor >= len(out):
            return want
        cursor += 1
    return None


def _failure_message(
    name: str, script: PageScript, run: RunResult, blocks: list[PythonBlock]
) -> str:
    """Non-zero exit: show stderr and name the block the failing line came from."""
    block_index = _failing_block(script, run.stderr)
    where = ""
    if block_index is not None:
        page_line = blocks[block_index].fence.open_line
        where = f" in block {block_index} (fence at {name}:{page_line})"
    return (
        f"{name}: page script exited with status {run.returncode}{where}\n"
        f"--- stderr ---\n{run.stderr}"
    )


def _failing_block(script: PageScript, stderr: str) -> int | None:
    """The block index of the last ``page.py`` line named in the traceback."""
    found: int | None = None
    for m in _TRACEBACK_FRAME.finditer(stderr):
        block = script.block_for(int(m.group("line")))
        if block is not None:
            found = block
    return found
