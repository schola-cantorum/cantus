"""Install commands on documentation pages name the distribution (ADR-0003).

The package is imported as ``cantus`` and installed as ``cantus-agent``. The
two spellings are one character apart and only one of them works, so a page
that says ``pip install cantus[mlx]`` sends a reader to a different project on
PyPI. A third-party audit found the mix-up in 2026-09; this test is what stops
it coming back.

The rule is deliberately blunt: inside a shell fence, the distribution is named
``cantus-agent`` — both after ``pip install`` and in front of an extras bracket,
which together cover the quoted, flagged and non-pip spellings of the same
command. It applies to both locales and to comment lines, because a reader
copies a commented command as readily as a bare one.

Two things are out of scope by construction. Prose is not scanned, so a sentence
naming the importable package (``cantus``) still reads naturally. And the rule
cannot tell a command from its output: the package's own gate messages say
``pip install cantus[serve]``, so a page that one day quotes such a traceback
inside a ``console`` fence would fail here. No in-scope page does today; the
fix then is to correct the message, not to loosen this test.
"""

from __future__ import annotations

import re

import pytest

from tests.docs.pages import IN_SCOPE_PAGES, SHELL_INFOS, SITE, parse_page

# Two spellings of the same mistake; a line fails if either matches. The
# lookahead is what lets the correct name through — in ``cantus-agent[mlx]`` the
# only place ``cantus`` starts is followed by ``-agent``.
#
# The first covers ``pip install cantus`` with no extras at all, and tolerates
# the flags and quoting a real command carries (``pip install --upgrade
# "cantus[mlx]"``). The second catches an extras bracket after any installer at
# all, which is how ``uv add cantus[mlx]`` is caught.
_WRONG_INSTALL_NAME = re.compile(
    r"""pip[ ]install[ ]+(?:-[\w-]+[ ]+)*["']?cantus(?!-agent)"""
    r"""|(?<![\w.-])cantus(?!-agent)\["""
)

_LOCALES: tuple[str, ...] = ("", "zh-tw")


def install_name_problems(text: str, *, name: str) -> list[str]:
    """Every shell-fence line that installs the wrong distribution name.

    Args:
        text: Full markdown source of one page.
        name: How the page should be identified in a failure message.

    Returns:
        One ``path:line: text`` message per offending line, in document order.
        Comment lines are included: a reader copies those too.
    """
    problems: list[str] = []
    for fence in parse_page(text).fences:
        if not fence.is_shell:
            continue
        for offset, line in enumerate(fence.lines):
            if _WRONG_INSTALL_NAME.search(line):
                problems.append(
                    f"{name}:{fence.open_line + 1 + offset}: {line.strip()} "
                    f"— the distribution is `cantus-agent`, not `cantus`"
                )
    return problems


@pytest.mark.parametrize("locale", _LOCALES, ids=["en", "zh-tw"])
@pytest.mark.parametrize("page", IN_SCOPE_PAGES)
def test_in_scope_page_installs_the_distribution_by_its_real_name(
    page: str, locale: str
) -> None:
    """Both locales of every in-scope page, comment lines included."""
    relative = f"{locale}/{page}" if locale else page
    path = SITE / relative
    display = f"docs/site/{relative}"

    assert path.is_file(), f"page missing: {display}"
    assert install_name_problems(path.read_text(encoding="utf-8"), name=display) == []


# --- The check fails on the shapes it targets --------------------------------


def _page(info: str, body: str) -> str:
    return f"Prose.\n\n```{info}\n{body}\n```\n"


@pytest.mark.parametrize("info", sorted(SHELL_INFOS))
def test_the_check_rejects_the_wrong_name_in_every_shell_fence_kind(info: str) -> None:
    """``bash``, ``sh`` and ``console`` are all fences a reader copies from."""
    problems = install_name_problems(_page(info, "pip install cantus[mlx]"), name="p.md")

    assert len(problems) == 1
    assert problems[0].startswith("p.md:4: pip install cantus[mlx]")


def test_the_check_rejects_the_wrong_name_on_a_comment_line() -> None:
    """A commented command is still a command a reader will paste."""
    body = "# pip install cantus[openai]\npip install cantus-agent[openai]"

    problems = install_name_problems(_page("bash", body), name="p.md")

    assert len(problems) == 1
    assert "# pip install cantus[openai]" in problems[0]


def test_the_check_rejects_the_wrong_name_without_extras() -> None:
    """``pip install cantus`` alone is the same wrong distribution."""
    assert len(install_name_problems(_page("bash", "pip install cantus"), name="p.md")) == 1


@pytest.mark.parametrize(
    "command",
    [
        'pip install "cantus[mlx]"',
        "pip install --upgrade cantus[mlx]",
        "python -m pip install -U 'cantus[mlx]'",
        "uv add cantus[mlx]",
        "uv pip install cantus[mlx]",
    ],
    ids=["quoted", "flag", "flag-and-quote", "uv-add", "uv-pip"],
)
def test_the_check_rejects_the_wrong_name_however_the_command_is_spelled(
    command: str,
) -> None:
    """The same wrong distribution reaches PyPI whichever installer asks."""
    assert len(install_name_problems(_page("bash", command), name="p.md")) == 1


def test_the_check_accepts_the_real_distribution_name() -> None:
    body = (
        "uv pip install cantus-agent\n"
        "pip install cantus-agent[serve]\n"
        'pip install --upgrade "cantus-agent[mlx]"\n'
        "uv add cantus-agent[openai]  # Apple Silicon only\n"
        "import cantus  # the importable package keeps its own name\n"
    )

    assert install_name_problems(_page("bash", body), name="p.md") == []


def test_the_check_ignores_prose_outside_a_fence() -> None:
    """The importable package is spelled ``cantus``; prose may say so."""
    text = "Install with `pip install cantus[serve]` — but this is prose.\n"

    assert install_name_problems(text, name="p.md") == []


def test_the_check_ignores_a_python_fence() -> None:
    """Only shell fences are commands; a Python block that mentions the string
    is not something a reader runs in a terminal."""
    text = _page("python", 'HINT = "pip install cantus[serve]"')

    assert install_name_problems(text, name="p.md") == []


def test_the_check_reports_every_offending_line_not_just_the_first() -> None:
    body = "pip install cantus[mlx]\necho ok\npip install cantus[openai]"

    problems = install_name_problems(_page("bash", body), name="p.md")

    assert len(problems) == 2
    assert problems[0].startswith("p.md:4:")
    assert problems[1].startswith("p.md:6:")
