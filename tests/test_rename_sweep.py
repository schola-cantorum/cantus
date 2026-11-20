"""The rename sweep: no legacy Skill identifier outside the marked places.

Enforces traceability 4.1-4.3 (AC-36, TR-130): every Git-tracked text file of the scan set is
read at test time and checked against the 16 patterns of 4.2, honouring exactly the exemptions
of 4.3. This module is itself whole-file exempt (by its own path), so it may hold the planted
legacy strings the tests below need. Phase two deletes the legacy aliases and, with them, the
exemptions.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Traceability 4.1: the scanned files.
SCAN_DIRS = ("cantus/", "tests/", "notebooks/", "docs/site/", "docs/api/")
SCAN_FILES = frozenset(
    {
        "README.md",
        "README.zhTW.md",
        "llms.txt",
        "CONTRIBUTING.md",
        "CONTRIBUTING.zhTW.md",
        "docs/quickstart-desktop.md",
        "docs/llms-txt.md",
        "docs/README.md",
        "pyproject.toml",
        "scripts/smoke_install.sh",
        "scripts/gen_docs_api.mjs",
        ".github/workflows/cross-platform-install.yml",
    }
)
NOT_SCANNED_DIRS = ("docs/site/public/",)
NOT_SCANNED_FILES = frozenset({"tests/fixtures/skill_spec_for_llm_v0_2_1.json"})

# Traceability 4.2: the patterns, one (id, regex) pair per cell.
PATTERNS = (
    ("P1", r"(?<!Agent )\bSkill\b"),
    ("P2", r"@skill\b"),
    ("P2", r"\bskill\("),
    ("P3", r"\bregister_skill\b"),
    ("P3", r"\bget_registry\b"),
    ("P4", r"\b(CallSkillAction|SkillObservation|SkillEntry|SkillsPane)\b"),
    ("P5", r"\bskill_name\b"),
    ("P5", r"\bunknown_skill\b"),
    ("P6", r"cantus\.protocols\.skill\b"),
    ("P7", r"""["']skill["']"""),
    ("P7", r"""["']skill:"""),
    ("P8", r"\bskills?="),
    (
        "P9",
        r"\b(collect_skills|update_skills|list_skills|active_skill_names|_dispatch_skill"
        r"|dashboard_list_skills|introspection_skills)\b",
    ),
    ("P9", r"\binvoke_skill_"),
    ("P10", r"(?<![A-Za-z._-])/skills\b"),
    ("P10", r"/introspection/skills\b"),
)
COMPILED = tuple((pid, source, re.compile(source)) for pid, source in PATTERNS)


# Traceability 4.3: the exemptions.
LINE_MARKER = "legacy-alias"
LINE_MARKER_DIRS = ("cantus/", "tests/")
# Built from parts so this file never contains a block marker literally.
BLOCK_START = "<!-- " + LINE_MARKER + ":start -->"
BLOCK_END = "<!-- " + LINE_MARKER + ":end -->"
BLOCK_FILES = frozenset(
    {
        "docs/site/protocols/tool.md",
        "docs/site/zh-tw/protocols/tool.md",
        "docs/api/protocols/tool.md",
    }
)
OUTSIDE_RULE = "block marker outside the Tool pages"
WHOLE_FILES = frozenset(
    {
        "docs/site/protocols/skill.md",
        "docs/site/zh-tw/protocols/skill.md",
        "docs/api/protocols/skill.md",
    }
)
WHOLE_DIRS = ("tests/legacy/",)
MODULE_PATH = Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()


class SweepSetupError(Exception):
    """The sweep cannot trust its own file list."""


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    rule: str
    regex: str
    text: str


def is_scanned(path: str) -> bool:
    if path.startswith(NOT_SCANNED_DIRS) or path in NOT_SCANNED_FILES:
        return False
    return path.startswith(SCAN_DIRS) or path in SCAN_FILES


def _git_env() -> dict[str, str]:
    """The caller's environment without GIT_DIR and friends, so ``git -C`` alone picks the repository."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def tracked_files(root: Path) -> list[str]:
    top = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        env=_git_env(),
    ).stdout
    if Path(os.fsdecode(top).strip()).resolve() != root.resolve():
        raise SweepSetupError("%s is not the top level of its Git repository" % root)
    raw = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], check=True, capture_output=True, env=_git_env()
    ).stdout
    names = [os.fsdecode(entry) for entry in raw.split(b"\0") if entry]
    scanned = sorted(name for name in names if is_scanned(name))
    if "README.md" not in scanned:
        raise SweepSetupError("the scan set is empty or lacks README.md")
    return scanned


def format_violations(violations: list[Violation]) -> str:
    return "\n".join(
        "%s:%d: %s [%s] %s" % (v.path, v.line, v.rule, v.regex, v.text.strip())
        for v in violations
    )


def _block_exempt_lines(lines: list[str]) -> set[int]:
    """Indexes strictly between each start marker and the next end marker after it."""
    exempt: set[int] = set()
    for start, line in enumerate(lines):
        if BLOCK_START not in line:
            continue
        if BLOCK_END in line[line.index(BLOCK_START) + len(BLOCK_START):]:
            continue  # the next end is on the start's own line: no line lies between them
        for end in range(start + 1, len(lines)):
            if BLOCK_END in lines[end]:
                exempt.update(range(start + 1, end))
                break
    return exempt


def scan_text(path: str, text: str) -> list[Violation]:
    found: list[Violation] = []
    lines = text.split("\n")
    if path not in BLOCK_FILES:
        for number, line in enumerate(lines, 1):
            if BLOCK_START in line or BLOCK_END in line:
                found.append(Violation(path, number, OUTSIDE_RULE, "", line))
    if path in WHOLE_FILES or path.startswith(WHOLE_DIRS) or path == MODULE_PATH:
        return found
    block_exempt = _block_exempt_lines(lines) if path in BLOCK_FILES else set()
    for index, line in enumerate(lines):
        if index in block_exempt:
            continue
        if path.startswith(LINE_MARKER_DIRS) and LINE_MARKER in line:
            continue
        for pid, source, compiled in COMPILED:
            if compiled.search(line):
                found.append(Violation(path, index + 1, pid, source, line))
    return found


def sweep(root: Path) -> list[Violation]:
    found: list[Violation] = []
    for path in tracked_files(root):
        file_path = root / path
        if not file_path.is_file():
            continue
        text = file_path.read_bytes().decode("utf-8", errors="replace")
        found.extend(scan_text(path, text))
    return found


def _repo(tmp_path: Path, files: dict[str, bytes | str]) -> Path:
    """A throwaway Git repository holding ``files`` (staged, not committed)."""
    contents = dict(files)
    contents.setdefault("README.md", "readme\n")
    for name, data in contents.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True, env=_TMP_GIT_ENV)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "core.autocrlf=false", "add", "-A"],
        check=True,
        env=_TMP_GIT_ENV,
    )
    return tmp_path


# Throwaway repositories ignore the developer's global and system Git configuration (for example a
# global excludes file that would leave a planted *.bak file untracked).
_TMP_GIT_ENV = {**_git_env(), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def _hit_paths(root: Path) -> set[str]:
    return {violation.path for violation in sweep(root)}


@pytest.mark.parametrize(
    "path",
    [
        "cantus/m.py",
        "tests/t.py",
        "notebooks/n.ipynb",
        "docs/site/p.md",
        "docs/api/p.md",
        "docs/site/publication.md",
        "tests/fixtures/other.json",
        # The 12 root files of traceability 4.1, written out independently of SCAN_FILES.
        "README.md",
        "README.zhTW.md",
        "llms.txt",
        "CONTRIBUTING.md",
        "CONTRIBUTING.zhTW.md",
        "docs/quickstart-desktop.md",
        "docs/llms-txt.md",
        "docs/README.md",
        "pyproject.toml",
        "scripts/smoke_install.sh",
        "scripts/gen_docs_api.mjs",
        ".github/workflows/cross-platform-install.yml",
    ],
)
def test_a_planted_legacy_line_is_found_in_every_scanned_path(tmp_path: Path, path: str) -> None:
    root = _repo(tmp_path, {path: "@skill\n"})

    assert path in _hit_paths(root)


@pytest.mark.parametrize(
    "path",
    [
        "docs/site/public/p.md",
        "tests/fixtures/skill_spec_for_llm_v0_2_1.json",
        "docs/adr/0001-x.md",
        "CHANGELOG.md",
        ".claude/skills/x.md",
        "scripts/other.sh",
        "cantusx/m.py",
        "docs/sitemap.md",
    ],
)
def test_a_planted_legacy_line_is_ignored_outside_the_scan_set(tmp_path: Path, path: str) -> None:
    every_planted_line = "".join(planted + "\n" for _label, planted, _cell in PATTERN_CASES)
    root = _repo(tmp_path, {path: every_planted_line})

    assert _hit_paths(root) == set()


def test_an_untracked_file_is_not_scanned(tmp_path: Path) -> None:
    root = _repo(tmp_path, {})
    (root / "cantus").mkdir()
    (root / "cantus" / "late.py").write_text("@skill\n", encoding="utf-8")

    assert _hit_paths(root) == set()


def test_a_tracked_file_deleted_from_disk_is_skipped(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"cantus/gone.py": "@skill\n", "cantus/kept.py": "@skill\n"})
    (root / "cantus" / "gone.py").unlink()

    assert _hit_paths(root) == {"cantus/kept.py"}


@pytest.mark.parametrize(
    "data",
    [b"a\x00b @skill\n", b"a\r@skill\r", b"\xe9 @skill\n"],
    ids=["nul-byte", "lone-cr", "non-utf8"],
)
def test_odd_bytes_are_still_scanned_and_do_not_abort_the_scan(
    tmp_path: Path, data: bytes
) -> None:
    root = _repo(tmp_path, {"cantus/a.py": data, "cantus/z.py": "@skill\n"})

    assert _hit_paths(root) == {"cantus/a.py", "cantus/z.py"}


@pytest.mark.parametrize(
    ("data", "line"),
    [(b"a\x0cb\n@skill\n", 2), ("x\u2028y\n@skill\n".encode(), 2), (b"a\r\n@skill\r\n", 2)],
    ids=["form-feed", "line-separator", "crlf"],
)
def test_a_violation_names_the_physical_line(tmp_path: Path, data: bytes, line: int) -> None:
    root = _repo(tmp_path, {"cantus/a.py": data})

    assert [violation.line for violation in sweep(root)] == [line]


def test_a_form_feed_does_not_split_a_line_from_its_marker(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"cantus/a.py": b"@skill\x0c  # legacy-alias\n"})

    assert sweep(root) == []


# The 16 cells of traceability 4.2, written out again here as the independent expectation.
CELL_P1 = r"(?<!Agent )\bSkill\b"
CELL_P2_DECORATOR = r"@skill\b"
CELL_P2_CALL = r"\bskill\("
CELL_P3_REGISTER = r"\bregister_skill\b"
CELL_P3_REGISTRY = r"\bget_registry\b"
CELL_P4 = r"\b(CallSkillAction|SkillObservation|SkillEntry|SkillsPane)\b"
CELL_P5_NAME = r"\bskill_name\b"
CELL_P5_UNKNOWN = r"\bunknown_skill\b"
CELL_P6 = r"cantus\.protocols\.skill\b"
CELL_P7_KIND = r"""["']skill["']"""
CELL_P7_PREFIX = r"""["']skill:"""
CELL_P8 = r"\bskills?="
CELL_P9_HELPERS = (
    r"\b(collect_skills|update_skills|list_skills|active_skill_names|_dispatch_skill"
    r"|dashboard_list_skills|introspection_skills)\b"
)
CELL_P9_INVOKE = r"\binvoke_skill_"
CELL_P10_ROOT = r"(?<![A-Za-z._-])/skills\b"
CELL_P10_INTROSPECTION = r"/introspection/skills\b"

CELL_IDS = {
    CELL_P1: "P1",
    CELL_P2_DECORATOR: "P2",
    CELL_P2_CALL: "P2",
    CELL_P3_REGISTER: "P3",
    CELL_P3_REGISTRY: "P3",
    CELL_P4: "P4",
    CELL_P5_NAME: "P5",
    CELL_P5_UNKNOWN: "P5",
    CELL_P6: "P6",
    CELL_P7_KIND: "P7",
    CELL_P7_PREFIX: "P7",
    CELL_P8: "P8",
    CELL_P9_HELPERS: "P9",
    CELL_P9_INVOKE: "P9",
    CELL_P10_ROOT: "P10",
    CELL_P10_INTROSPECTION: "P10",
}


def test_the_scanner_uses_exactly_the_16_cells_of_the_table_in_order() -> None:
    assert [(pid, source) for pid, source, _compiled in COMPILED] == [(pid, cell) for cell, pid in CELL_IDS.items()]


PATTERN_CASES = [
    ("Skill", "class Skill:", CELL_P1),
    ("decorator", "@skill", CELL_P2_DECORATOR),
    ("call", "x = skill(f)", CELL_P2_CALL),
    ("register_skill", "register_skill", CELL_P3_REGISTER),
    ("get_registry", "get_registry", CELL_P3_REGISTRY),
    ("CallSkillAction", "CallSkillAction", CELL_P4),
    ("SkillObservation", "SkillObservation", CELL_P4),
    ("SkillEntry", "SkillEntry", CELL_P4),
    ("SkillsPane", "SkillsPane", CELL_P4),
    ("skill_name", "skill_name", CELL_P5_NAME),
    ("unknown_skill", "unknown_skill", CELL_P5_UNKNOWN),
    ("module path", "import cantus.protocols.skill", CELL_P6),
    ("double-quoted kind", 'kind = "skill"', CELL_P7_KIND),
    ("single-quoted kind", "kind = 'skill'", CELL_P7_KIND),
    ("prefix", 'key = "skill:x"', CELL_P7_PREFIX),
    ("skill=", "skill=1", CELL_P8),
    ("skills=", "skills=1", CELL_P8),
    ("collect_skills", "collect_skills", CELL_P9_HELPERS),
    ("update_skills", "update_skills", CELL_P9_HELPERS),
    ("list_skills", "list_skills", CELL_P9_HELPERS),
    ("active_skill_names", "active_skill_names", CELL_P9_HELPERS),
    ("_dispatch_skill", "_dispatch_skill", CELL_P9_HELPERS),
    ("dashboard_list_skills", "dashboard_list_skills", CELL_P9_HELPERS),
    ("introspection_skills", "introspection_skills", CELL_P9_HELPERS),
    ("invoke_skill_", "invoke_skill_x", CELL_P9_INVOKE),
    ("root route", "GET /skills", CELL_P10_ROOT),
    ("introspection route", "/introspection/skills", CELL_P10_INTROSPECTION),
]


@pytest.mark.parametrize(
    ("planted", "cell"),
    [(planted, cell) for _label, planted, cell in PATTERN_CASES],
    ids=[label for label, _planted, _cell in PATTERN_CASES],
)
def test_each_pattern_cell_reports_exactly_its_own_hit(
    tmp_path: Path, planted: str, cell: str
) -> None:
    root = _repo(tmp_path, {"cantus/m.py": planted + "\n"})

    found = sweep(root)

    assert [(violation.rule, violation.regex) for violation in found] == [(CELL_IDS[cell], cell)]


def test_every_cell_of_the_table_has_a_planted_case() -> None:
    assert {cell for _label, _planted, cell in PATTERN_CASES} == {
        CELL_P1,
        CELL_P2_DECORATOR,
        CELL_P2_CALL,
        CELL_P3_REGISTER,
        CELL_P3_REGISTRY,
        CELL_P4,
        CELL_P5_NAME,
        CELL_P5_UNKNOWN,
        CELL_P6,
        CELL_P7_KIND,
        CELL_P7_PREFIX,
        CELL_P8,
        CELL_P9_HELPERS,
        CELL_P9_INVOKE,
        CELL_P10_ROOT,
        CELL_P10_INTROSPECTION,
    }


@pytest.mark.parametrize(
    "planted",
    ["see Agent Skill docs", "path .claude/skills/x", "import cantus/protocols/skill.py"],
)
def test_text_that_only_resembles_a_legacy_name_is_not_reported(
    tmp_path: Path, planted: str
) -> None:
    root = _repo(tmp_path, {"cantus/m.py": planted + "\n"})

    assert sweep(root) == []


@pytest.mark.parametrize("path", ["cantus/m.py", "tests/t.py"])
@pytest.mark.parametrize(
    "line",
    ["@skill  # legacy-alias", "@skill  # not-a-legacy-aliasing note"],
    ids=["marker", "marker-as-substring"],
)
def test_the_line_marker_exempts_a_line_under_cantus_and_tests(
    tmp_path: Path, path: str, line: str
) -> None:
    root = _repo(tmp_path, {path: line + "\n"})

    assert sweep(root) == []


def test_the_line_marker_exempts_only_its_own_line(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"cantus/m.py": "@skill  # legacy-alias\n@skill\n"})

    assert [violation.line for violation in sweep(root)] == [2]


@pytest.mark.parametrize("path", ["notebooks/n.ipynb", "docs/site/p.md", "README.md"])
def test_the_line_marker_does_not_exempt_a_line_elsewhere(tmp_path: Path, path: str) -> None:
    root = _repo(tmp_path, {path: "@skill  # legacy-alias\n"})

    assert _hit_paths(root) == {path}


MARKER_START = "<!-- " + "legacy-alias" + ":start -->"
MARKER_END = "<!-- " + "legacy-alias" + ":end -->"
EXPECTED_OUTSIDE_RULE = "block marker outside the Tool pages"
TOOL_PAGES = [
    "docs/site/protocols/tool.md",
    "docs/site/zh-tw/protocols/tool.md",
    "docs/api/protocols/tool.md",
]


def _lines(*lines: str) -> str:
    return "\n".join(lines) + "\n"


def _reported_lines(root: Path, path: str) -> list[int]:
    return [violation.line for violation in sweep(root) if violation.path == path]


@pytest.mark.parametrize("path", TOOL_PAGES)
def test_a_block_exempts_the_lines_strictly_between_its_markers(
    tmp_path: Path, path: str
) -> None:
    text = _lines("@skill", MARKER_START, "@skill", "@skill", MARKER_END, "@skill")
    root = _repo(tmp_path, {path: text})

    assert _reported_lines(root, path) == [1, 6]


@pytest.mark.parametrize("path", TOOL_PAGES)
def test_each_start_pairs_with_the_next_end(tmp_path: Path, path: str) -> None:
    text = _lines(
        "@skill", MARKER_START, "@skill", MARKER_END, "@skill", MARKER_START, "@skill", MARKER_END
    )
    root = _repo(tmp_path, {path: text})

    assert _reported_lines(root, path) == [1, 5]


@pytest.mark.parametrize("path", TOOL_PAGES)
def test_an_unclosed_start_marker_exempts_nothing(tmp_path: Path, path: str) -> None:
    root = _repo(tmp_path, {path: _lines(MARKER_START, "@skill", "@skill")})

    assert _reported_lines(root, path) == [2, 3]


@pytest.mark.parametrize("path", TOOL_PAGES)
def test_a_start_and_end_on_one_line_exempt_nothing(tmp_path: Path, path: str) -> None:
    # The next end after the start is on the start's own line, so no line lies between them;
    # a later orphan end must not be paired with that start.
    root = _repo(tmp_path, {path: _lines(MARKER_START + " " + MARKER_END, "@skill", MARKER_END)})

    assert _reported_lines(root, path) == [2]


@pytest.mark.parametrize("path", TOOL_PAGES)
def test_an_orphan_end_marker_exempts_nothing(tmp_path: Path, path: str) -> None:
    root = _repo(tmp_path, {path: _lines("@skill", MARKER_END, "@skill")})

    assert _reported_lines(root, path) == [1, 3]


@pytest.mark.parametrize(
    "path",
    [
        "docs/site/p.md",
        "tests/legacy/x.py",
        "docs/site/protocols/skill.md",
        "tests/test_rename_sweep.py",
        "docs/site/x/protocols/tool.md",
    ],
)
def test_a_block_marker_outside_the_tool_pages_is_reported(tmp_path: Path, path: str) -> None:
    root = _repo(tmp_path, {path: _lines(MARKER_START, "plain", MARKER_END)})

    found = [(v.line, v.rule) for v in sweep(root) if v.path == path]

    assert (1, EXPECTED_OUTSIDE_RULE) in found
    assert (3, EXPECTED_OUTSIDE_RULE) in found
    assert (2, EXPECTED_OUTSIDE_RULE) not in found


@pytest.mark.parametrize(
    "path",
    [
        "docs/site/protocols/skill.md",
        "docs/site/zh-tw/protocols/skill.md",
        "docs/api/protocols/skill.md",
        "tests/legacy/a.py",
        "tests/legacy/sub/b.py",
        "tests/test_rename_sweep.py",
    ],
)
def test_a_wholly_exempt_file_reports_no_legacy_line(tmp_path: Path, path: str) -> None:
    root = _repo(tmp_path, {path: "@skill\nclass Skill: ...\n"})

    assert sweep(root) == []


@pytest.mark.parametrize(
    "path",
    [
        "tests/legacy_x.py",
        "tests/legacyfoo/c.py",
        "docs/site/protocols/skill.md.bak",
        "cantus/test_rename_sweep.py",
    ],
)
def test_a_file_that_only_resembles_an_exempt_one_is_reported(
    tmp_path: Path, path: str
) -> None:
    root = _repo(tmp_path, {path: "@skill\n"})

    assert _hit_paths(root) == {path}


def test_a_root_that_is_not_the_repository_top_level_is_refused(tmp_path: Path) -> None:
    # A copy of the tree inside another repository: from the subdirectory, git lists a scan set
    # that looks complete (it has README.md), so only the top-level check can refuse it.
    repo = _repo(tmp_path, {"inner/README.md": "readme\n", "inner/cantus/m.py": "@skill\n"})

    with pytest.raises(SweepSetupError):
        tracked_files(repo / "inner")


def test_a_repository_with_no_file_in_the_scan_set_is_refused(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"other.txt": "x\n"})
    (repo / "README.md").unlink()
    subprocess.run(
        ["git", "-C", str(repo), "rm", "-q", "--cached", "README.md"], check=True, env=_TMP_GIT_ENV
    )

    with pytest.raises(SweepSetupError):
        tracked_files(repo)


def test_a_scan_set_without_the_readme_is_refused(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"cantus/m.py": "x = 1\n"})
    subprocess.run(
        ["git", "-C", str(repo), "rm", "-q", "--cached", "README.md"], check=True, env=_TMP_GIT_ENV
    )

    with pytest.raises(SweepSetupError):
        tracked_files(repo)


def test_the_tree_has_no_legacy_identifier_outside_the_exemptions() -> None:
    found = sweep(REPO_ROOT)

    assert found == [], "\n" + format_violations(found)
