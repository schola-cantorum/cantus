"""Unit cases for page execution and the expected-output assertion
(ticket docs-tutorial-and-vv/02).

Each case is one Page / Page script row of the planning snapshot's type ×
boundary matrix (A.4), fed a synthetic page. The runner is observed only
through ``verify_page``: whether the page passes and what its problems say.
Every page here really runs in a subprocess, the way a reader's would.
"""

from __future__ import annotations

import textwrap

import pytest

from tests.docs.pages import ROOT, parse_page
from tests.docs.runner import (
    build_page_script,
    find_expected_output,
    run_page_script,
    verify_page,
)


def _page(sample: str) -> str:
    return textwrap.dedent(sample).lstrip("\n")


_HELLO = '''
```python
print("hello")
print("world")
```

You should see:

```text
hello
world
```
'''


# --- A.2.2 expected-output block ------------------------------------------------


def test_expected_output_block_is_the_text_fence_after_you_should_see() -> None:
    parsed = parse_page(_page(_HELLO))
    found, problems = find_expected_output(_page(_HELLO), parsed)
    assert problems == []
    assert found is not None
    assert found.lines == ["hello", "world"]


@pytest.mark.parametrize(
    "preceding",
    [
        "::: tip You should see",  # a container line is not prose
        "<!-- You should see -->",  # an HTML comment is not prose
        "Output follows.",  # prose without the phrase
    ],
)
def test_text_fence_without_a_you_should_see_prose_line_is_not_expected_output(
    preceding: str,
) -> None:
    page = _page(
        f"""
        ```python
        print("hello")
        ```

        {preceding}

        ```text
        hello
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("expected-output block" in p for p in outcome.problems)


def test_you_should_see_inside_a_code_fence_does_not_count() -> None:
    page = _page(
        """
        ```python
        print("You should see")
        ```

        ```text
        You should see
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("expected-output block" in p for p in outcome.problems)


# --- A.4 Page rows -------------------------------------------------------------


def test_page_with_zero_python_blocks_fails() -> None:
    outcome = verify_page("Just prose.\n")
    assert not outcome.ok
    assert any("no Python block" in p for p in outcome.problems)


def test_page_with_two_expected_output_blocks_fails() -> None:
    page = _page(_HELLO) + _page(
        """
        You should see this again:

        ```text
        hello
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("exactly one expected-output block" in p for p in outcome.problems)


def test_empty_expected_output_block_fails() -> None:
    page = _page(
        """
        ```python
        print("hello")
        ```

        You should see:

        ```text

        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("empty" in p for p in outcome.problems)


def test_skip_only_page_with_expected_output_block_fails() -> None:
    page = _page(
        """
        <!-- vv:skip: needs a running Ollama daemon -->
        ```python
        print("hello")
        ```

        You should see:

        ```text
        hello
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("skip-only" in p for p in outcome.problems)


def test_skip_only_page_without_expected_output_block_passes_and_counts_skips() -> None:
    page = _page(
        """
        <!-- vv:skip: needs a running Ollama daemon -->
        ```python
        raise SystemExit("never runs")
        ```

        <!-- vv:skip: needs a provider key in the environment -->
        ```python
        raise SystemExit("never runs either")
        ```
        """
    )
    outcome = verify_page(page)
    assert outcome.ok, outcome.problems
    assert outcome.skipped == 2
    assert outcome.executed is False


def test_expected_lines_present_in_order_pass() -> None:
    outcome = verify_page(_page(_HELLO))
    assert outcome.ok, outcome.problems
    assert outcome.executed is True
    assert outcome.skipped == 0


def test_expected_line_absent_fails_naming_the_first_missing_line() -> None:
    page = _page(
        """
        ```python
        print("hello")
        ```

        You should see:

        ```text
        hello
        goodbye
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("goodbye" in p and "not found" in p for p in outcome.problems)


def test_expected_lines_out_of_order_fail() -> None:
    page = _page(
        """
        ```python
        print("hello")
        print("world")
        ```

        You should see:

        ```text
        world
        hello
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("hello" in p and "not found" in p for p in outcome.problems)


def test_expected_lines_may_skip_over_extra_stdout_lines() -> None:
    page = _page(
        """
        ```python
        print("noise")
        print("hello")
        print("more noise")
        print("world   ")
        ```

        You should see:

        ```text
        hello
        world
        ```
        """
    )
    assert verify_page(page).ok


# --- A.4 Page script rows ------------------------------------------------------


def test_skipped_blocks_are_dropped_and_the_rest_run_in_document_order() -> None:
    page = _page(
        """
        ```python
        x = 1
        ```

        <!-- vv:skip: needs a provider key in the environment -->
        ```python
        raise SystemExit("skipped block must not run")
        ```

        ```python
        print(x + 1)
        ```

        You should see:

        ```text
        2
        ```
        """
    )
    outcome = verify_page(page)
    assert outcome.ok, outcome.problems
    assert outcome.skipped == 1


def test_script_that_raises_fails_with_stderr_and_block_index() -> None:
    page = _page(
        """
        ```python
        x = 1
        ```

        ```python
        y = 2
        raise RuntimeError("boom from block two")
        ```

        You should see:

        ```text
        never
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    joined = "\n".join(outcome.problems)
    assert "boom from block two" in joined
    assert "block 1" in joined  # 0-based index of the second block


def test_opening_a_socket_raises_inside_the_subprocess() -> None:
    page = _page(
        """
        ```python
        import socket
        socket.create_connection(("example.com", 80))
        ```

        You should see:

        ```text
        never
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("socket" in p for p in outcome.problems)


def test_reading_a_provider_key_from_the_environment_fails() -> None:
    page = _page(
        """
        ```python
        import os
        print(os.environ["OPENAI_API_KEY"])
        ```

        You should see:

        ```text
        never
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("KeyError" in p for p in outcome.problems)


def test_environment_is_the_whitelist_only(monkeypatch: pytest.MonkeyPatch) -> None:
    # The parent's variables must not leak: a canary set here is invisible to
    # the page. macOS adds a couple of its own (LC_CTYPE, __CF_USER_TEXT_ENCODING)
    # at process launch, so the assertion is "whitelist present, canary absent",
    # not "exactly these keys".
    monkeypatch.setenv("CANTUS_DOCS_CANARY", "leak")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-leak")
    page = _page(
        """
        ```python
        import os
        print("canary:", "CANTUS_DOCS_CANARY" in os.environ, "OPENAI_API_KEY" in os.environ)
        print("whitelist:", all(k in os.environ for k in ("HOME", "PATH", "PYTHONPATH")))
        print("safepath:", os.environ.get("PYTHONSAFEPATH"))
        ```

        You should see:

        ```text
        canary: False False
        whitelist: True
        safepath: 1
        ```
        """
    )
    outcome = verify_page(page)
    assert outcome.ok, outcome.problems


def test_a_written_file_lands_in_the_temporary_cwd_not_the_repository() -> None:
    page = _page(
        """
        ```python
        import os
        from pathlib import Path
        Path("scratch.txt").write_text("x")
        print(Path("scratch.txt").resolve().parent == Path(os.environ["HOME"]).resolve())
        ```

        You should see:

        ```text
        True
        ```
        """
    )
    outcome = verify_page(page)
    assert outcome.ok, outcome.problems
    assert not (ROOT / "scratch.txt").exists()


def test_script_over_the_timeout_fails() -> None:
    page = _page(
        """
        ```python
        import time
        time.sleep(5)
        ```

        You should see:

        ```text
        never
        ```
        """
    )
    outcome = verify_page(page, timeout=1)
    assert not outcome.ok
    assert any("timed out" in p for p in outcome.problems)


def test_importing_an_extra_that_is_not_installed_fails() -> None:
    page = _page(
        """
        ```python
        import cantus_extra_that_does_not_exist
        ```

        You should see:

        ```text
        never
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("ModuleNotFoundError" in p for p in outcome.problems)


def test_hook_line_is_replaced_and_the_scripted_model_drives_an_agent() -> None:
    page = _page(
        """
        ```python
        from cantus import Agent
        model = None  # under docs tests: cantus_docs_model()
        state = Agent(model=model).run("say ok")
        print(type(list(state.stream)[-1]).__name__)
        ```

        You should see:

        ```text
        FinalAnswerAction
        ```
        """
    )
    outcome = verify_page(page)
    assert outcome.ok, outcome.problems


def test_hook_substitution_keeps_indent_and_lhs_and_leaves_skipped_blocks_alone() -> None:
    page = _page(
        """
        <!-- vv:skip: needs a running Ollama daemon -->
        ```python
        model = load("x")  # under docs tests: cantus_docs_model()
        ```

        ```python
        if True:
            self_model = make()  # under docs tests: cantus_docs_model()
        ```
        """
    )
    script = build_page_script(parse_page(page))
    assert "    self_model = cantus_docs_model()" in script.source
    assert 'load("x")' not in script.source


def test_script_directory_is_not_importable() -> None:
    page = _page(
        """
        ```python
        from pathlib import Path
        Path("helper_mod.py").write_text("VALUE = 1\\n")
        try:
            import helper_mod
            print("imported")
        except ModuleNotFoundError:
            print("not importable")
        ```

        You should see:

        ```text
        not importable
        ```
        """
    )
    outcome = verify_page(page)
    assert outcome.ok, outcome.problems


def test_run_page_script_captures_stdout_and_stderr_separately() -> None:
    result = run_page_script('import sys\nprint("out")\nprint("err", file=sys.stderr)\n')
    assert result.returncode == 0
    assert result.stdout.strip() == "out"
    assert result.stderr.strip() == "err"


def test_you_should_see_inside_a_multi_line_html_comment_does_not_count() -> None:
    page = _page(
        """
        ```python
        print("hello")
        ```

        <!-- reviewer note:
        You should see -->

        ```text
        hello
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("expected-output block" in p for p in outcome.problems)


def test_you_should_see_inside_a_container_body_counts() -> None:
    page = _page(
        """
        ```python
        print("hello")
        ```

        ::: tip
        You should see:

        ```text
        hello
        ```
        :::
        """
    )
    assert verify_page(page).ok


def test_tilde_text_fence_after_you_should_see_is_reported_not_ignored() -> None:
    page = _page(
        """
        ```python
        print("hello")
        ```

        You should see:

        ~~~text
        hello
        ~~~
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("tilde" in p for p in outcome.problems)


def test_socket_constructor_raises_inside_the_subprocess() -> None:
    page = _page(
        """
        ```python
        import socket
        socket.socket()
        ```

        You should see:

        ```text
        never
        ```
        """
    )
    outcome = verify_page(page)
    assert not outcome.ok
    assert any("socket" in p for p in outcome.problems)


def test_script_directory_is_not_importable_even_without_pythonsafepath() -> None:
    # Simulates Python 3.10, which ignores PYTHONSAFEPATH: the preamble alone
    # must keep the script directory off sys.path. The comparison is by real
    # path, because the interpreter resolves symlinks (macOS /var -> /private/var)
    # when it puts the script directory on sys.path.
    page = _page(
        """
        ```python
        from pathlib import Path
        Path("helper_mod.py").write_text("VALUE = 1\\n")
        try:
            import helper_mod
            print("imported")
        except ModuleNotFoundError:
            print("not importable")
        ```

        You should see:

        ```text
        not importable
        ```
        """
    )
    outcome = verify_page(page, env_overrides={"PYTHONSAFEPATH": None})
    assert outcome.ok, outcome.problems
