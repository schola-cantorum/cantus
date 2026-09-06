"""Unit cases for the zh-tw parity comparison (ticket docs-tutorial-and-vv/04).

Each case is one "zh-tw pair" boundary (drafted as an A.4 row of the planning
snapshot), fed a synthetic English page and its translation. The comparison
is observed only through ``compare_pair``: whether it reports problems and
what they say. Nothing is executed.
"""

from __future__ import annotations

import sys
import textwrap

import pytest

from pathlib import Path

from tests.docs.parity import (
    compare_pair,
    compare_pair_files,
    strings_equivalent,
    tokens_of,
)


def _page(sample: str) -> str:
    return textwrap.dedent(sample).lstrip("\n")


EN = _page(
    """
    Intro.

    ```bash
    pip install cantus-agent==0.6.0
    # then run it
    ```

    ```python
    from cantus import skill

    @skill
    def greet(name: str) -> str:
        \"\"\"Say hello.\"\"\"
        return f"hello {name}"  # a comment

    print(greet("Tainan"))
    ```

    You should see:

    ```text
    hello Tainan
    ```
    """
)

ZH = _page(
    """
    簡介。

    ```bash
    pip install cantus-agent==0.6.0
    # 接著執行
    ```

    ```python
    from cantus import skill

    @skill
    def greet(name: str) -> str:
        \"\"\"打招呼。\"\"\"
        return f"hello {name}"  # 註解

    print(greet("Tainan"))
    ```

    你應該看到：

    ```text
    hello Tainan
    ```
    """
)


def test_faithful_translation_is_in_parity() -> None:
    assert compare_pair(EN, ZH) == []


def test_comment_and_docstring_may_differ() -> None:
    # Already exercised by the faithful pair; make the tolerance explicit.
    zh = ZH.replace("# 註解", "# 完全不同的註解")
    zh = zh.replace("打招呼。", "另一段說明文字。")
    assert compare_pair(EN, zh) == []


def test_block_count_differs_fails() -> None:
    zh = ZH + "\n```python\nprint(1)\n```\n"
    problems = compare_pair(EN, zh)
    assert any("block count differs" in p for p in problems)


def test_marker_on_one_side_only_fails() -> None:
    zh = ZH.replace("```python\n", "<!-- vv:skip: needs a running server -->\n```python\n", 1)
    problems = compare_pair(EN, zh)
    assert any("skip marker only on the zh-tw side" in p for p in problems)


def test_marker_reason_must_repeat_the_english_verbatim() -> None:
    en = EN.replace("```python\n", "<!-- vv:skip: needs a running server -->\n```python\n", 1)
    zh = ZH.replace("```python\n", "<!-- vv:skip: needs a running daemon -->\n```python\n", 1)
    problems = compare_pair(en, zh)
    assert any("skip reason differs" in p for p in problems)
    zh_ok = ZH.replace("```python\n", "<!-- vv:skip: needs a running server -->\n```python\n", 1)
    assert not any("skip" in p for p in compare_pair(en, zh_ok))


def test_identifier_differs_fails() -> None:
    zh = ZH.replace("def greet(", "def greeting(")
    zh = zh.replace('greet("Tainan")', 'greeting("Tainan")')
    problems = compare_pair(EN, zh)
    assert any("NAME 'greet' vs NAME 'greeting'" in p for p in problems)


def test_cjk_string_with_ascii_runs_in_english_passes() -> None:
    en = EN.replace('print(greet("Tainan"))', 'print("weather for Tainan today")')
    zh = ZH.replace('print(greet("Tainan"))', 'print("今天 Tainan 的天氣")')
    assert compare_pair(en, zh) == []


def test_cjk_string_with_ascii_run_not_in_english_fails() -> None:
    en = EN.replace('print(greet("Tainan"))', 'print("weather for Tainan today")')
    zh = ZH.replace('print(greet("Tainan"))', 'print("今天 Taipei 的天氣")')
    problems = compare_pair(en, zh)
    assert any("ASCII run 'Taipei'" in p for p in problems)


def test_ascii_only_string_difference_fails() -> None:
    zh = ZH.replace('greet("Tainan")', 'greet("Taipei")')
    problems = compare_pair(EN, zh)
    assert any("carries no CJK character" in p for p in problems)


@pytest.mark.parametrize(
    "english",
    [
        "https://example.com/docs",
        "pip install cantus-agent",
        "uv pip install cantus-agent",
        "npm run docs:dev",
    ],
)
def test_url_or_install_string_must_be_verbatim(english: str) -> None:
    assert strings_equivalent(f'"{english}"', f'"{english} 說明"') is not None
    assert strings_equivalent(f'"{english}"', f'"{english}"') is None


def test_fstring_differing_only_in_cjk_text_passes() -> None:
    zh = ZH.replace('f"hello {name}"', 'f"哈囉 {name}"')
    assert compare_pair(EN, zh) == []


def test_fstring_tokens_collapse_into_one_string_token() -> None:
    kinds = [t.kind for t in tokens_of('x = f"hello {name}"\n')]
    assert kinds == ["NAME", "OP", "STRING"]


def test_expected_output_lines_differ_fails() -> None:
    zh = ZH.replace("hello Tainan\n```", "哈囉 Tainan\n```")
    problems = compare_pair(EN, zh)
    assert any("expected-output lines differ" in p for p in problems)


def test_expected_output_missing_on_zh_side_fails() -> None:
    zh = ZH.replace("你應該看到：", "輸出如下：")
    problems = compare_pair(EN, zh)
    assert any("only on the English side" in p for p in problems)


def test_shell_fence_comment_lines_may_differ_but_commands_may_not() -> None:
    zh = ZH.replace("pip install cantus-agent==0.6.0", "pip install cantus-agent==0.5.0")
    problems = compare_pair(EN, zh)
    assert any("shell fence 0" in p and "differs outside comment lines" in p for p in problems)


def test_shell_fence_count_differs_fails() -> None:
    zh = ZH + "\n```bash\necho extra\n```\n"
    problems = compare_pair(EN, zh)
    assert any("shell fences differ in count or order" in p for p in problems)


def test_malformed_marker_on_zh_side_is_reported() -> None:
    zh = ZH.replace("簡介。", "簡介。 vv:skip 不是有效標記")
    problems = compare_pair(EN, zh)
    assert any("[marker]" in p for p in problems)


def test_missing_zh_tw_page_fails(tmp_path: Path) -> None:
    en = tmp_path / "page.md"
    en.write_text(EN, encoding="utf-8")
    problems = compare_pair_files(en, tmp_path / "zh-tw" / "page.md")
    assert problems and problems[0].startswith("zh-tw page missing:")


def test_quotes_are_delimiters_not_part_of_an_ascii_run() -> None:
    # "Tainan is the run, not the opening quote plus Tainan.
    assert strings_equivalent('"say Tainan"', '"Tainan 天氣"') is None
    assert strings_equivalent("'say Tainan'", "'Tainan 天氣'") is None
    assert strings_equivalent('f"say {name}"', 'f"{name} 天氣"') is None


def test_shell_comment_may_differ_only_at_the_same_position() -> None:
    zh = ZH.replace("# 接著執行", "echo 接著執行")
    assert any("shell fence 0" in p for p in compare_pair(EN, zh))
    zh = ZH.replace("# 接著執行\n", "# 接著執行\n# 再一行\n")
    assert any("shell fence 0" in p for p in compare_pair(EN, zh))


def test_nested_fstring_collapses_into_one_string_token() -> None:
    """A nested f-string is one string token, on every supported Python.

    The inner quotes differ from the outer ones here, which is the only nesting
    that parses before 3.12. Below 3.12 ``tokenize`` hands back the whole
    f-string as a single ``STRING``; from 3.12 it hands back an
    ``FSTRING_START`` … ``FSTRING_END`` run that the collapse folds into one.
    Both roads must end at the same three tokens, or the same page would
    compare differently depending on which interpreter ran the suite.
    """
    kinds = [t.kind for t in tokens_of("""x = f"a {f'b {c}'} d"\n""")]
    assert kinds == ["NAME", "OP", "STRING"]


@pytest.mark.skipif(
    sys.version_info < (3, 12),
    reason="reusing the outer quote inside an f-string is PEP 701, new in 3.12",
)
def test_quote_reusing_nested_fstring_collapses_into_one_string_token() -> None:
    """The 3.12 spelling of the same nesting, where the quotes may repeat.

    This is the form that produces the deepest ``FSTRING_START`` nesting, so it
    is the one that would expose a collapse that stops at the first
    ``FSTRING_END``. It cannot be written in a file that 3.10 must import,
    hence the source text and the version gate.
    """
    kinds = [t.kind for t in tokens_of('x = f"a {f"b {c}"} d"\n')]
    assert kinds == ["NAME", "OP", "STRING"]
