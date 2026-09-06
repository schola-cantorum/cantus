"""The docs tests leave the checkout exactly as they found it (A.2.10).

Named ``zz`` so it is collected last in this directory; see ``conftest.py``.
"""

from __future__ import annotations

from tests.docs.runner import working_tree_state


def test_working_tree_is_unchanged_after_the_docs_tests(
    working_tree_before_docs_tests: str,
) -> None:
    assert working_tree_state() == working_tree_before_docs_tests
