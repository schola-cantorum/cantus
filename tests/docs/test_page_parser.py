"""Unit cases for the documentation page parser (ticket docs-tutorial-and-vv/01).

Each case is one row of the planning snapshot's type × boundary matrix (A.4), fed an inline
markdown sample so the boundary is visible in the test itself. The parser is
observed only through ``parse_page``: what it reports as Python blocks and what
it reports as malformed.
"""

from __future__ import annotations

import textwrap

import pytest

from tests.docs.pages import parse_page


def _page(sample: str) -> str:
    return textwrap.dedent(sample).lstrip("\n")


# --- A.2.0 fences -------------------------------------------------------------


def test_python_fence_at_column_zero_is_a_block() -> None:
    page = _page(
        """
        Intro.

        ```python
        print("hi")
        ```
        """
    )
    parsed = parse_page(page)
    assert parsed.malformed == []
    assert [b.lines for b in parsed.python_blocks] == [['print("hi")']]


def test_python_fence_indented_up_to_three_spaces_is_a_block_and_dedented() -> None:
    page = _page(
        """
        1. Step one:

           ```python
           x = 1
             y = 2
           ```
        """
    )
    parsed = parse_page(page)
    assert parsed.malformed == []
    assert [b.lines for b in parsed.python_blocks] == [["x = 1", "  y = 2"]]


def test_fence_inside_a_container_is_a_block_like_any_other() -> None:
    page = _page(
        """
        ::: details The world
        ```python
        world = {}
        ```
        :::
        """
    )
    parsed = parse_page(page)
    assert parsed.malformed == []
    assert [b.lines for b in parsed.python_blocks] == [["world = {}"]]


def test_non_python_fences_are_kept_but_are_not_python_blocks() -> None:
    page = _page(
        """
        ```bash
        pip install cantus-agent==0.6.0
        ```

        ```text
        hello
        ```
        """
    )
    parsed = parse_page(page)
    assert parsed.malformed == []
    assert parsed.python_blocks == []
    assert [f.info for f in parsed.fences] == ["bash", "text"]


@pytest.mark.parametrize("info", ["py", "python3", "python title=x", "python{1}"])
def test_wrong_python_info_string_is_malformed(info: str) -> None:
    page = _page(
        f"""
        ```{info}
        print(1)
        ```
        """
    )
    parsed = parse_page(page)
    assert parsed.python_blocks == []
    assert [(m.line, m.kind) for m in parsed.malformed] == [(1, "fence")]


def test_tilde_fence_carrying_python_is_malformed() -> None:
    page = _page(
        """
        ~~~python
        print(1)
        ~~~
        """
    )
    parsed = parse_page(page)
    assert parsed.python_blocks == []
    assert [(m.line, m.kind) for m in parsed.malformed] == [(1, "fence")]


def test_tilde_fence_without_python_is_not_malformed() -> None:
    page = _page(
        """
        ~~~text
        output
        ~~~
        """
    )
    assert parse_page(page).malformed == []


def test_unterminated_fence_is_malformed() -> None:
    page = _page(
        """
        text

        ```python
        print(1)
        """
    )
    parsed = parse_page(page)
    assert parsed.python_blocks == []
    assert [(m.line, m.kind) for m in parsed.malformed] == [(3, "fence")]


def test_longer_closing_fence_closes_a_shorter_opening() -> None:
    page = _page(
        """
        ````python
        print("```")
        `````
        """
    )
    parsed = parse_page(page)
    assert parsed.malformed == []
    assert [b.lines for b in parsed.python_blocks] == [['print("```")']]


def test_four_space_indented_python_mentioning_cantus_is_malformed() -> None:
    page = _page(
        """
        - item

            ```python
            from cantus import Agent
            ```
        """
    )
    parsed = parse_page(page)
    assert parsed.python_blocks == []
    assert [(m.line, m.kind) for m in parsed.malformed] == [(3, "fence")]


def test_four_space_indented_block_without_cantus_is_ignored() -> None:
    page = _page(
        """
        - item

            ```python
            print(1)
            ```
        """
    )
    parsed = parse_page(page)
    assert parsed.malformed == []
    assert parsed.python_blocks == []


# --- A.2.1 skip markers -------------------------------------------------------


def test_valid_marker_directly_before_python_fence_marks_the_block_skipped() -> None:
    page = _page(
        """
        <!-- vv:skip: needs a running Ollama daemon -->
        ```python
        model = load_chat_model("ollama/gemma")
        ```

        ```python
        print(1)
        ```
        """
    )
    parsed = parse_page(page)
    assert parsed.malformed == []
    assert [b.skipped for b in parsed.python_blocks] == [True, False]
    assert parsed.python_blocks[0].skip is not None
    assert parsed.python_blocks[0].skip.reason == "needs a running Ollama daemon"


def test_indented_marker_before_indented_fence_is_valid() -> None:
    page = _page(
        """
        1. Step:

           <!-- vv:skip: needs a provider key in the environment -->
           ```python
           import os
           ```
        """
    )
    parsed = parse_page(page)
    assert parsed.malformed == []
    assert [b.skipped for b in parsed.python_blocks] == [True]


@pytest.mark.parametrize(
    "marker",
    [
        "<!-- vv:skip: short -->",  # fewer than eight non-space characters
        "<!-- vv:skip: a b c d e f g -->",  # eight chars only when spaces are counted
        "<!-- vv:skip: needs-a-server -->",  # hyphen inside the reason
        "<!-- vv:skip:needs a server -->",  # missing space after the colon
        "<!-- vv:skip: needs a server-->",  # missing space before the close
    ],
)
def test_marker_with_bad_reason_is_malformed(marker: str) -> None:
    page = _page(
        f"""
        {marker}
        ```python
        print(1)
        ```
        """
    )
    parsed = parse_page(page)
    assert [(m.line, m.kind) for m in parsed.malformed] == [(1, "marker")]
    assert [b.skipped for b in parsed.python_blocks] == [False]


def test_marker_then_blank_line_then_fence_is_malformed() -> None:
    page = _page(
        """
        <!-- vv:skip: needs a running server -->

        ```python
        print(1)
        ```
        """
    )
    parsed = parse_page(page)
    assert [(m.line, m.kind) for m in parsed.malformed] == [(1, "marker")]
    assert [b.skipped for b in parsed.python_blocks] == [False]


def test_marker_before_non_python_fence_is_malformed() -> None:
    page = _page(
        """
        <!-- vv:skip: needs a running server -->
        ```bash
        cantus serve
        ```
        """
    )
    parsed = parse_page(page)
    assert [(m.line, m.kind) for m in parsed.malformed] == [(1, "marker")]


def test_stray_marker_in_prose_is_malformed() -> None:
    page = _page(
        """
        Use vv:skip when a block cannot run.

        ```python
        print(1)
        ```
        """
    )
    parsed = parse_page(page)
    assert [(m.line, m.kind) for m in parsed.malformed] == [(1, "marker")]


def test_marker_text_inside_a_code_block_is_malformed() -> None:
    page = _page(
        """
        ```python
        # <!-- vv:skip: this is inside a block and so is stray -->
        print(1)
        ```
        """
    )
    parsed = parse_page(page)
    assert [(m.line, m.kind) for m in parsed.malformed] == [(2, "marker")]


# --- A.2.3 model hooks --------------------------------------------------------


def test_hook_line_is_recorded_with_indent_and_lhs() -> None:
    page = _page(
        """
        ```python
        model = load_chat_model("ollama/gemma")  # under docs tests: cantus_docs_model()
        if True:
            self.model = build()  # under docs tests: cantus_docs_model()
        ```
        """
    )
    parsed = parse_page(page)
    assert parsed.malformed == []
    block = parsed.python_blocks[0]
    assert [(h.block_line, h.indent, h.lhs) for h in block.hooks] == [
        (0, "", "model"),
        (2, "    ", "self.model"),
    ]
    assert [h.line for h in block.hooks] == [2, 4]


def test_hook_name_on_a_non_matching_block_line_is_malformed() -> None:
    page = _page(
        """
        ```python
        print(cantus_docs_model)
        a, b = f()  # under docs tests: cantus_docs_model()
        ```
        """
    )
    parsed = parse_page(page)
    assert [(m.line, m.kind) for m in parsed.malformed] == [(2, "hook"), (3, "hook")]
    assert parsed.python_blocks[0].hooks == []


def test_bare_comparison_is_malformed_but_assignment_with_comparison_is_a_hook() -> None:
    # A.2.3 constrains only the first ``=`` after the target, so an assignment
    # whose right-hand side compares with ``==`` is a hook; the A.4 row
    # "``==`` comparison on the marked line" is the bare ``x == y`` statement.
    page = _page(
        """
        ```python
        ok = model == other  # under docs tests: cantus_docs_model()
        x == y  # under docs tests: cantus_docs_model()
        ```
        """
    )
    parsed = parse_page(page)
    block = parsed.python_blocks[0]
    assert [(h.block_line, h.lhs) for h in block.hooks] == [(0, "ok")]
    assert [(m.line, m.kind) for m in parsed.malformed] == [(3, "hook")]


def test_skipped_blocks_are_scanned_for_hooks_and_malformed_hooks_alike() -> None:
    page = _page(
        """
        <!-- vv:skip: needs a running Ollama daemon -->
        ```python
        model = load_chat_model("ollama/gemma")  # under docs tests: cantus_docs_model()
        x = cantus_docs_model
        ```
        """
    )
    parsed = parse_page(page)
    block = parsed.python_blocks[0]
    assert block.skipped
    assert [h.lhs for h in block.hooks] == ["model"]
    assert [(m.line, m.kind) for m in parsed.malformed] == [(4, "hook")]


def test_hook_name_in_prose_outside_a_block_is_not_a_hook_finding() -> None:
    page = _page(
        """
        The harness defines cantus_docs_model for you.

        ```python
        print(1)
        ```
        """
    )
    assert parse_page(page).malformed == []


def test_four_space_indented_nested_python_mentioning_cantus_is_still_malformed() -> None:
    # Review finding: per-line stripping broke nested structure and hid this case.
    page = _page(
        """
        - item

            ```python
            from cantus import Agent
            if True:
                agent = Agent(model=None)
            ```
        """
    )
    parsed = parse_page(page)
    assert [(m.line, m.kind) for m in parsed.malformed] == [(3, "fence")]


def test_four_space_indented_pseudo_fence_does_not_swallow_a_real_fence() -> None:
    # Review finding: an unclosed deep-indented pseudo-fence must not open a
    # block, otherwise a real fence after it silently disappears.
    page = _page(
        """
        - item

            ```python
            print("not closed at four spaces")

        ```python
        from cantus import Agent
        ```
        """
    )
    parsed = parse_page(page)
    assert parsed.malformed == []
    assert [b.lines for b in parsed.python_blocks] == [["from cantus import Agent"]]


def test_four_space_indented_tilde_python_mentioning_cantus_is_malformed() -> None:
    # Review finding: A.2.0 does not limit the deep-indent rule to backticks.
    page = _page(
        """
        - item

            ~~~python
            from cantus import Agent
            ~~~
        """
    )
    parsed = parse_page(page)
    assert parsed.python_blocks == []
    assert [(m.line, m.kind) for m in parsed.malformed] == [(3, "fence")]
