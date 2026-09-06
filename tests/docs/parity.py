"""zh-tw parity: a Traditional Chinese page is compared to its English source,
never executed (ADR-0003, "zh-tw parity").

The rules, restated here so the module reads on its own: block-by-block token
comparison that tolerates translated comments, docstrings and CJK strings but
nothing else; identical expected-output lines; identical shell fences apart
from comment lines. Skipped blocks take part, and their markers must match
position by position with the English reason repeated verbatim. They were
drafted as A.2.7 of the planning snapshot ``.proj.spec/docs-tutorial-and-vv.md``.

This module is a helper imported by the docs test modules; it holds no tests.
"""

from __future__ import annotations

import io
import re
import tokenize
from dataclasses import dataclass
from pathlib import Path

from tests.docs.pages import Fence, Malformed, ParsedPage, PythonBlock, parse_page
from tests.docs.runner import (
    EXPECTED_OUTPUT_PHRASE,
    EXPECTED_OUTPUT_PHRASE_ZH_TW,
    find_expected_output,
    format_problem,
)

# A.2.7: a STRING may differ only when the zh-tw text carries at least one code
# point in these ranges (CJK Unified Ideographs, CJK Compatibility Ideographs,
# CJK Symbols and Punctuation).
_CJK_RANGES = ((0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x3000, 0x303F))
# A.2.7: when the English text contains any of these, the two texts must be
# equal verbatim, so a URL or an install target cannot change in translation.
_VERBATIM_MARKERS = ("://", "pip install", "uv pip", "npm ")
_ASCII_RUN_MIN = 4
_DROPPED_TOKENS = frozenset({
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENCODING,
    tokenize.ENDMARKER,
})
# Python 3.12+ tokenises f-strings into FSTRING_START … FSTRING_END; older
# interpreters emit one STRING. The run is collapsed so results do not depend on
# the interpreter version.
_FSTRING_START = getattr(tokenize, "FSTRING_START", None)
_FSTRING_END = getattr(tokenize, "FSTRING_END", None)


@dataclass(frozen=True)
class Token:
    """A comparable token: its type name and text."""

    kind: str
    text: str


def _has_cjk(text: str) -> bool:
    return any(lo <= ord(ch) <= hi for ch in text for lo, hi in _CJK_RANGES)


def _ascii_runs(text: str) -> list[str]:
    """Maximal runs of at least four characters in U+0021–U+007E.

    Runs are split by spaces and by any character outside the range.
    """
    runs: list[str] = []
    current: list[str] = []
    for ch in text + " ":
        if 0x21 <= ord(ch) <= 0x7E:
            current.append(ch)
            continue
        if len(current) >= _ASCII_RUN_MIN:
            runs.append("".join(current))
        current = []
    return runs


_STRING_PREFIX = re.compile(r"^[rRbBuUfFtT]*")


def _literal_body(token_text: str) -> str:
    """The text between a string token's delimiters (prefix and quotes dropped).

    The quotes are syntax, not translated text: an ASCII run must not start
    with the opening quote of the literal it sits in.
    """
    body = _STRING_PREFIX.sub("", token_text, count=1)
    for quote in ('"""', "\'\'\'", '"', "'"):
        if body.startswith(quote) and body.endswith(quote) and len(body) >= 2 * len(quote):
            return body[len(quote) : -len(quote)]
    return body


def strings_equivalent(english: str, zh_tw: str) -> str | None:
    """The STRING rule: may a translated string literal differ from its source?

    Args:
        english: the English STRING token text, quotes included.
        zh_tw: the zh-tw STRING token text at the same position.

    Returns:
        ``None`` when the difference is acceptable, otherwise the reason it is not.
    """
    if english == zh_tw:
        return None
    en_body, zh_body = _literal_body(english), _literal_body(zh_tw)
    if any(marker in en_body for marker in _VERBATIM_MARKERS):
        return "string containing a URL or install command must be verbatim"
    if not _has_cjk(zh_body):
        return "translated string carries no CJK character"
    for run in _ascii_runs(zh_body):
        if run not in en_body:
            return f"ASCII run {run!r} in the translated string is not in the English one"
    return None


def tokens_of(source: str) -> list[Token]:
    """Tokenise one block for comparison.

    Layout tokens are dropped and an f-string's token run is collapsed into one
    STRING carrying the source slice, so the result does not depend on the
    interpreter version.

    Args:
        source: the block's content.

    Returns:
        The comparable tokens, in order.

    Raises:
        tokenize.TokenError: when the block is not tokenisable Python.
    """
    out: list[Token] = []
    fstring: list[str] = []
    depth = 0  # nested f-strings (3.12+) are one run until the outermost end
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if _FSTRING_START is not None and tok.type == _FSTRING_START:
            depth += 1
            fstring.append(tok.string)
            continue
        if depth:
            fstring.append(tok.string)
            if tok.type == _FSTRING_END:
                depth -= 1
                if depth == 0:
                    out.append(Token("STRING", "".join(fstring)))
                    fstring = []
            continue
        if tok.type in _DROPPED_TOKENS:
            continue
        out.append(Token(tokenize.tok_name[tok.type], tok.string))
    return out


def compare_blocks(english: PythonBlock, zh_tw: PythonBlock) -> list[str]:
    """Token-level differences between one English block and its pair.

    Args:
        english: the English block.
        zh_tw: the zh-tw block at the same position.

    Returns:
        One problem per differing position, empty when the blocks match.
    """
    try:
        left = tokens_of("\n".join(english.lines) + "\n")
        right = tokens_of("\n".join(zh_tw.lines) + "\n")
    except (tokenize.TokenError, SyntaxError) as exc:
        return [f"block {english.index}: cannot tokenise: {exc}"]
    if len(left) != len(right):
        return [
            f"block {english.index}: token count differs "
            f"(English {len(left)}, zh-tw {len(right)})"
        ]
    problems: list[str] = []
    for position, (a, b) in enumerate(zip(left, right)):
        if a == b:
            continue
        if a.kind == b.kind == "STRING":
            why = strings_equivalent(a.text, b.text)
            if why is None:
                continue
            problems.append(f"block {english.index}, token {position}: {why}")
            continue
        problems.append(
            f"block {english.index}, token {position}: {a.kind} {a.text!r} vs "
            f"{b.kind} {b.text!r}"
        )
    return problems


def _zh_problem(problem: Malformed) -> str:
    return format_problem("zh-tw", problem)


def _shell_fences(parsed: ParsedPage) -> list[Fence]:
    return [f for f in parsed.fences if f.is_shell]


def _shell_fence_differs(english: Fence, zh_tw: Fence) -> bool:
    """Shell parity: identical after trailing-whitespace strip, except that a
    line beginning with ``#`` may differ (a translated comment at the same
    position). Line counts must match, so a comment cannot be added or dropped.
    """
    left = [line.rstrip() for line in english.lines]
    right = [line.rstrip() for line in zh_tw.lines]
    if len(left) != len(right):
        return True
    for a, b in zip(left, right):
        if a == b:
            continue
        if a.lstrip().startswith("#") and b.lstrip().startswith("#"):
            continue
        return True
    return False


def compare_pair_files(english_path: Path, zh_tw_path: Path) -> list[str]:
    """A.2.7 for two files on disk; a missing zh-tw page is itself a problem.

    Args:
        english_path: the English page.
        zh_tw_path: where its zh-tw pair must be.

    Returns:
        The problems, starting with the missing-page finding when the pair is absent.
    """
    if not zh_tw_path.is_file():
        return [f"zh-tw page missing: {zh_tw_path}"]
    return compare_pair(
        english_path.read_text(encoding="utf-8"), zh_tw_path.read_text(encoding="utf-8")
    )


def compare_pair(english_text: str, zh_tw_text: str) -> list[str]:
    """A.2.7 in full: every difference between a page and its zh-tw pair.

    Args:
        english_text: the English page source.
        zh_tw_text: the zh-tw page source.

    Returns:
        Human-readable problems; empty when the pair is in parity.
    """
    en = parse_page(english_text)
    zh = parse_page(zh_tw_text)
    problems = [_zh_problem(m) for m in zh.malformed]

    if len(en.python_blocks) != len(zh.python_blocks):
        problems.append(
            f"Python block count differs (English {len(en.python_blocks)}, "
            f"zh-tw {len(zh.python_blocks)})"
        )
        return problems
    for a, b in zip(en.python_blocks, zh.python_blocks):
        if a.skipped != b.skipped:
            side = "English" if a.skipped else "zh-tw"
            problems.append(f"block {a.index}: skip marker only on the {side} side")
            continue
        if a.skip is not None and b.skip is not None and a.skip.reason != b.skip.reason:
            problems.append(
                f"block {a.index}: skip reason differs "
                f"({a.skip.reason!r} vs {b.skip.reason!r}); repeat the English reason verbatim"
            )
        problems += compare_blocks(a, b)

    en_expected, _ = find_expected_output(english_text, en)
    zh_expected, zh_expected_problems = find_expected_output(
        zh_tw_text, zh, phrase=EXPECTED_OUTPUT_PHRASE_ZH_TW
    )
    problems += [_zh_problem(m) for m in zh_expected_problems]
    if (en_expected is None) != (zh_expected is None):
        side = "English" if en_expected is not None else "zh-tw"
        problems.append(
            f"expected-output block only on the {side} side (zh-tw marks it with "
            f"{EXPECTED_OUTPUT_PHRASE_ZH_TW!r}, English with {EXPECTED_OUTPUT_PHRASE!r})"
        )
    elif en_expected is not None and zh_expected is not None:
        if en_expected.lines != zh_expected.lines:
            problems.append(
                "expected-output lines differ (program output is not translated):\n"
                f"  English: {en_expected.lines}\n  zh-tw:   {zh_expected.lines}"
            )

    en_shell = _shell_fences(en)
    zh_shell = _shell_fences(zh)
    en_infos = [f.info for f in en_shell]
    zh_infos = [f.info for f in zh_shell]
    if en_infos != zh_infos:
        problems.append(
            f"shell fences differ in count or order (English {en_infos}, zh-tw {zh_infos})"
        )
    else:
        for index, (left, right) in enumerate(zip(en_shell, zh_shell)):
            if _shell_fence_differs(left, right):
                problems.append(
                    f"shell fence {index} (line {left.open_line} / zh-tw line "
                    f"{right.open_line}) differs outside comment lines"
                )
    return problems
