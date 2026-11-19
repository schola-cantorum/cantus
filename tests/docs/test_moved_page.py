"""The moved protocol page and its zh-tw mirror (ADR-0003; epic 0001, ticket T-0017).

``docs/site/protocols/skill.md`` keeps the old URL alive as a moved page until
phase two rewrites it. It has no Python block, so it cannot be in
``IN_SCOPE_PAGES``; this module checks it instead (traceability TR-132 for the
moved page, TR-135, review finding V2-15).

The shape is checked line by line. After blank lines are dropped the page is
exactly two lines: a level-one title, then one sentence that names Tool and
carries exactly two inline links, first to the Tool page and then to the
migration guide. A second paragraph, a code block or frontmatter changes the
line count; a second sentence changes the count of sentence ends; a third inline
link changes the link list; an autolink, inline HTML or a bare URL is refused
outright. The zh-tw mirror has the same two links in the same order.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.docs.pages import SITE

MOVED_PAGE = "protocols/skill.md"
TOOL_PAGE_HREF = "./tool.md"
GUIDE_URL = (
    "https://github.com/schola-cantorum/cantus/blob/main/docs/migrations/"
    "MIGRATION_v0.6.0_to_v0.7.0.md"
)

_TITLE = re.compile(r"^# \S")
_TOOL = re.compile(r"\bTool\b")
_LINK = re.compile(r"\[([^\]\n]+)\]\(([^)\s]+)\)")
# A sentence ends at one of these marks, followed by a space or the line end
# (so the dot in "v0.6" does not count). zh-tw uses the full-width marks.
_SENTENCE_END = {
    "en": re.compile(r"[.!?](?=\s|$)"),
    "zh-tw": re.compile(r"[。！？]"),
}


def moved_page_problems(text: str, locale: str) -> list[str]:
    """The ways ``text`` departs from the moved-page shape.

    A wrong line count is reported alone, since the other checks assume the
    two lines.

    Args:
        text: the page source.
        locale: ``"en"`` or ``"zh-tw"``; picks the sentence-end marks.

    Returns:
        Human-readable problems; empty when the page has the shape.
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) != 2:
        return [f"expected a title and one sentence (2 non-blank lines), got {len(lines)}"]
    title, sentence = lines
    problems: list[str] = []
    if not _TITLE.match(title):
        problems.append(f"first line is not a level-one title: {title!r}")
    hrefs = [href for _, href in _LINK.findall(sentence)]
    if hrefs != [TOOL_PAGE_HREF, GUIDE_URL]:
        problems.append(f"links must be {[TOOL_PAGE_HREF, GUIDE_URL]}, got {hrefs}")
    prose = _LINK.sub(lambda m: m.group(1), sentence)
    if "<" in sentence or "http" in prose:
        problems.append("autolinks, inline HTML and bare URLs are not allowed in the sentence")
    ends = _SENTENCE_END[locale].findall(prose)
    if len(ends) != 1 or not _SENTENCE_END[locale].search(prose.rstrip()[-1:]):
        problems.append(
            f"expected exactly one sentence ending the line, found {len(ends)} sentence ends"
        )
    if not _TOOL.search(prose):
        problems.append("the sentence does not name Tool")
    return problems


@pytest.mark.parametrize(
    ("locale", "path"),
    [("en", SITE / MOVED_PAGE), ("zh-tw", SITE / "zh-tw" / MOVED_PAGE)],
    ids=["en", "zh-tw"],
)
def test_moved_page_is_a_title_and_one_sentence_with_two_links(locale: str, path: Path) -> None:
    assert path.is_file(), f"moved page missing: {path}"
    problems = moved_page_problems(path.read_text(encoding="utf-8"), locale)
    assert not problems, f"{path}:\n" + "\n".join(problems)


def test_zh_tw_moved_page_links_where_the_english_one_does() -> None:
    english = (SITE / MOVED_PAGE).read_text(encoding="utf-8")
    zh_tw = (SITE / "zh-tw" / MOVED_PAGE).read_text(encoding="utf-8")
    assert [h for _, h in _LINK.findall(zh_tw)] == [h for _, h in _LINK.findall(english)]
