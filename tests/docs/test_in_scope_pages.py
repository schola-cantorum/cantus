"""Every in-scope English page parses cleanly (ticket docs-tutorial-and-vv/01).

This is the executable-documentation harness's page test (ADR-0003): a
page that the parser cannot read unambiguously fails here, before anything is
executed. Later tickets add execution, the expected-output assertion and the
zh-tw parity comparison on top of the same parse.
"""

from __future__ import annotations

import pytest

from tests.docs.pages import IN_SCOPE_PAGES, SITE, parse_page
from tests.docs.parity import compare_pair_files
from tests.docs.runner import format_problem, verify_page


@pytest.mark.parametrize("page", IN_SCOPE_PAGES)
def test_in_scope_page_exists_and_is_well_formed(page: str) -> None:
    path = SITE / page
    assert path.is_file(), f"in-scope page missing: docs/site/{page}"
    parsed = parse_page(path.read_text(encoding="utf-8"))
    problems = [format_problem(f"docs/site/{page}", m) for m in parsed.malformed]
    assert not problems, "\n".join(problems)
    assert parsed.python_blocks, f"docs/site/{page} has no Python block"


@pytest.mark.parametrize("page", IN_SCOPE_PAGES)
def test_in_scope_page_runs_and_prints_its_expected_output(page: str) -> None:
    """The reader's-eye test: run what the page says to run, in a process that
    looks like a reader's, and compare with what the page says you will see."""
    path = SITE / page
    outcome = verify_page(path.read_text(encoding="utf-8"), name=f"docs/site/{page}")
    assert outcome.ok, "\n".join(outcome.problems)


@pytest.mark.parametrize("page", IN_SCOPE_PAGES)
def test_zh_tw_page_is_in_parity_with_its_english_source(page: str) -> None:
    """A.2.7: the zh-tw page is compared to the English page, never executed."""
    problems = compare_pair_files(SITE / page, SITE / "zh-tw" / page)
    assert not problems, f"docs/site/zh-tw/{page}:\n" + "\n".join(problems)
