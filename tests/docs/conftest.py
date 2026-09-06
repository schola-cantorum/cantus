"""Docs-harness fixtures (ADR-0003).

The session-scoped snapshot below is taken when the first docs test starts. The
tree-unchanged test compares against it; that test file is named so pytest's
alphabetical collection within this directory runs it after every other docs
test (an ordering pytest documents for files in one directory, not a plugin).
"""

from __future__ import annotations

import pytest

from tests.docs.runner import working_tree_state


@pytest.fixture(scope="session", autouse=True)
def working_tree_before_docs_tests() -> str:
    return working_tree_state()
