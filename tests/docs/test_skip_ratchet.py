"""The number of skipped documentation blocks can only go down (ADR-0003).

The baseline file records the total across in-scope pages the last time it was
deliberately raised, with a reason. The test fails when the current total is
above it, so the suite cannot drift back towards "nothing runs" one skip at a
time. Refreshing the reason when the total is raised is review policy, not
something this test checks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.docs.pages import IN_SCOPE_PAGES, SITE, parse_page

BASELINE = Path(__file__).with_name("vv_skip_baseline.json")


def current_skip_counts() -> dict[str, int]:
    """Skipped Python blocks per in-scope page, from the pages as they are.

    Returns:
        Page path to skip count, one entry per in-scope page (zeros included).
    """
    counts: dict[str, int] = {}
    for page in IN_SCOPE_PAGES:
        parsed = parse_page((SITE / page).read_text(encoding="utf-8"))
        counts[page] = sum(1 for block in parsed.python_blocks if block.skipped)
    return counts


def _baseline() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(BASELINE.read_text(encoding="utf-8"))
    return data


def check_ratchet(counts: dict[str, int], allowed: int) -> None:
    """A.2.6: fail when the skip total is above the baseline, pass otherwise."""
    total = sum(counts.values())
    assert total <= allowed, (
        f"{total} skipped blocks across in-scope pages, baseline allows {allowed}. "
        f"Per page: {counts}. Fix the block or raise the baseline with a reason."
    )


def test_baseline_file_has_the_expected_shape() -> None:
    data = _baseline()
    assert set(data) == {"total", "reason", "pages"}
    assert isinstance(data["total"], int) and data["total"] >= 0
    assert isinstance(data["reason"], str) and data["reason"].strip()
    pages: dict[str, int] = data["pages"]
    assert set(pages) <= set(IN_SCOPE_PAGES), "pages names a page that is not in scope"
    assert sum(pages.values()) == data["total"], "per-page counts must add up to total"


def test_total_skipped_blocks_does_not_exceed_the_baseline() -> None:
    check_ratchet(current_skip_counts(), _baseline()["total"])


def test_ratchet_passes_at_or_below_the_baseline() -> None:
    check_ratchet({"a.md": 2, "b.md": 1}, allowed=3)
    check_ratchet({"a.md": 1}, allowed=3)


def test_ratchet_fails_above_the_baseline_and_names_the_page_counts() -> None:
    with pytest.raises(AssertionError, match=r"4 skipped blocks .* allows 3\. .*'a\.md': 3"):
        check_ratchet({"a.md": 3, "b.md": 1}, allowed=3)
