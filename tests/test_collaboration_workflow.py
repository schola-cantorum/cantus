"""Controls for the collaboration-workflow decisions adopted from harness-agile.

Each accepted ADR in ``docs/adr/`` must name a control that cites it back
(ADR-0003). The decisions that arrived with the harness-agile migration are
mostly about how work is recorded: where tickets live, what their frontmatter
says, what a spec review leaves behind. Those records are files in this
repository, so they can be checked. This module is the check.

Each control is a ``*_problems`` function that inspects a repository root and
returns human-readable problems. It runs once against this repository and
again against synthetic trees, so a control that silently accepts everything
cannot pass: the synthetic cases prove it rejects what it claims to reject.

Controls in this module:

- ADR-0005: after round 0, every ticket outside the maintenance epic has a
  reviewed spec behind it.
- ADR-0006: ticket status lives in frontmatter, ids are global and permanent,
  and ``blocked`` is derived rather than written.
- ADR-0007: a spec review keeps its frozen prompt and stops at two rounds.
- ADR-0008: the reviewer roles cannot write.
- ADR-0009: the structure check runs in CI (see also
  ``.github/workflows/repo-hygiene.yml``).
- ADR-0010: the Project Charter is filled in.
- ADR-0011: no Spectra or openspec machinery remains.
- ADR-0012: lightweight-path tickets state why they qualify.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

if sys.version_info < (3, 11):
    pytest.skip("scripts/verify-project.py requires Python 3.11+", allow_module_level=True)

import yaml

_ROOT = Path(__file__).resolve().parents[1]

_EPIC_DIR = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*$")
_TICKET_FILE = re.compile(r"^(T-\d{4})-[a-z0-9][a-z0-9-]*\.md$")
_WRITTEN_STATUSES = frozenset({"todo", "processing", "review", "done", "pending"})
_PENDING_FIELDS = ("pending_reason", "pending_evidence", "pending_on", "revisit_when")
_MAINTENANCE_EPIC = "0000-maintenance"


def _frontmatter(text: str) -> dict[str, object] | None:
    match = re.match(r"---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    if not match:
        return None
    data = yaml.safe_load(match.group(1))
    return data if isinstance(data, dict) else None


def _epic_dirs(root: Path, base: str) -> list[Path]:
    parent = root / base
    if not parent.is_dir():
        return []
    return sorted(p for p in parent.iterdir() if p.is_dir() and _EPIC_DIR.match(p.name))


# --- ADR-0005, ADR-0006, ADR-0012: tickets ------------------------------------


def _ticket_problems(root: Path) -> list[str]:
    """Every way the epic ticket directories break ADR-0005, ADR-0006 or ADR-0012.

    Only ``.proj.tickets/NNNN-<slug>/`` directories are inspected. ``_legacy/``
    holds frozen pre-migration work in the old layout and is out of scope.
    """
    problems: list[str] = []
    seen: dict[str, str] = {}
    blocked_by: dict[str, list[str]] = {}
    for epic in _epic_dirs(root, ".proj.tickets"):
        for path in sorted(epic.iterdir()):
            rel = path.relative_to(root).as_posix()
            if path.name == ".gitkeep":
                continue
            name = _TICKET_FILE.match(path.name)
            if not path.is_file() or not name:
                problems.append(f"{rel}: not a T-NNNN-<slug>.md ticket file")
                continue
            data = _frontmatter(path.read_text(encoding="utf-8"))
            if data is None:
                problems.append(f"{rel}: no YAML frontmatter")
                continue
            ticket_id = name.group(1)
            if data.get("id") != ticket_id:
                problems.append(f"{rel}: frontmatter id {data.get('id')!r} != filename id {ticket_id}")
            if data.get("epic") != epic.name:
                problems.append(f"{rel}: frontmatter epic {data.get('epic')!r} != directory {epic.name}")
            status = data.get("status")
            if status == "blocked":
                problems.append(f"{rel}: status 'blocked' is derived from blocked_by and never written")
            elif status not in _WRITTEN_STATUSES:
                problems.append(f"{rel}: unknown status {status!r}")
            if status == "pending":
                missing = [f for f in _PENDING_FIELDS if not data.get(f)]
                if missing:
                    problems.append(f"{rel}: pending ticket lacks {', '.join(missing)}")
            if ticket_id in seen:
                problems.append(f"{rel}: id {ticket_id} already used by {seen[ticket_id]}")
            seen.setdefault(ticket_id, rel)
            edges = data.get("blocked_by") or []
            blocked_by[rel] = [str(e) for e in edges] if isinstance(edges, list) else [str(edges)]
            if epic.name == _MAINTENANCE_EPIC:
                if not str(data.get("lightweight_reason") or "").strip():
                    problems.append(f"{rel}: maintenance ticket lacks lightweight_reason")
            else:
                spec_dir = root / ".proj.specs" / epic.name
                for required in ("spec.en.md", "traceability.md"):
                    if not (spec_dir / required).is_file():
                        problems.append(f"{rel}: epic has no .proj.specs/{epic.name}/{required}")
    for rel, edges in blocked_by.items():
        for edge in edges:
            if edge not in seen:
                problems.append(f"{rel}: blocked_by names unknown ticket {edge}")
    return problems


# --- ADR-0007: adversarial review records -------------------------------------


def _review_problems(root: Path) -> list[str]:
    """Every way an epic's review directory breaks ADR-0007."""
    problems: list[str] = []
    for epic in _epic_dirs(root, ".proj.specs"):
        review = epic / "review"
        if not review.is_dir():
            continue
        rounds = sorted(p.name for p in review.glob("round-*.md"))
        rel = review.relative_to(root).as_posix()
        if rounds and not (review / "prompt.md").is_file():
            problems.append(f"{rel}: review rounds exist but the frozen prompt.md is missing")
        for name in rounds:
            if name not in {"round-1.md", "round-2.md"}:
                problems.append(f"{rel}/{name}: two rounds is the ceiling")
        if "round-2.md" in rounds and "round-1.md" not in rounds:
            problems.append(f"{rel}: round-2.md without round-1.md")
    return problems


# --- ADR-0010, ADR-0011: charter and Spectra removal -------------------------


def _charter_problems(root: Path) -> list[str]:
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    problems = []
    if "{{PROJECT_" in text:
        problems.append("AGENTS.md still carries template project tokens")
    if "PLACEHOLDER — the user has not written this yet" in text:
        problems.append("AGENTS.md Project Charter is still the template placeholder")
    return problems


def _spectra_problems(root: Path) -> list[str]:
    problems = []
    for rel in ("openspec", ".spectra.yaml", ".gemini/commands/spectra"):
        if (root / rel).exists():
            problems.append(f"{rel} exists; Spectra was removed (ADR-0011)")
    for tree in (".claude/skills", ".agents/skills", ".gemini/skills"):
        base = root / tree
        if base.is_dir():
            problems += [f"{tree}/{p.name} is a Spectra skill" for p in base.glob("spectra-*")]
    for entry in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        path = root / entry
        if path.is_file() and "SPECTRA:START" in path.read_text(encoding="utf-8"):
            problems.append(f"{entry} still carries a SPECTRA block")
    return problems


# --- Tests against this repository --------------------------------------------


def test_tickets_follow_adr_0005_0006_and_0012() -> None:
    assert _ticket_problems(_ROOT) == []


def test_spec_reviews_follow_adr_0007() -> None:
    assert _review_problems(_ROOT) == []


def test_reviewer_roles_are_read_only_per_adr_0008() -> None:
    claude = _frontmatter((_ROOT / ".claude/agents/harness-reviewer.md").read_text(encoding="utf-8"))
    assert claude is not None
    tools = {t.strip() for t in str(claude.get("tools", "")).split(",") if t.strip()}
    assert tools and tools <= {"Read", "Glob", "Grep"}, tools
    codex = (_ROOT / ".codex/agents/harness-reviewer.toml").read_text(encoding="utf-8")
    assert re.search(r'^sandbox_mode\s*=\s*"read-only"\s*$', codex, re.M)


def test_structure_check_passes_and_runs_in_ci_per_adr_0009() -> None:
    workflow = yaml.safe_load((_ROOT / ".github/workflows/repo-hygiene.yml").read_text(encoding="utf-8"))
    runs = [step.get("run", "") for job in workflow["jobs"].values() for step in job["steps"]]
    assert any("scripts/verify-project.py" in run for run in runs)
    result = subprocess.run(
        [sys.executable, "-B", str(_ROOT / "scripts/verify-project.py")],
        cwd=_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_charter_is_filled_per_adr_0010() -> None:
    assert _charter_problems(_ROOT) == []


def test_spectra_is_gone_per_adr_0011() -> None:
    assert _spectra_problems(_ROOT) == []


# --- The controls reject what they claim to reject ----------------------------


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _ticket(ticket_id: str, epic: str, status: str = "todo", **extra: object) -> str:
    fields = {"id": ticket_id, "title": "t", "epic": epic, "status": status, "blocked_by": [], **extra}
    return "---\n" + yaml.safe_dump(fields, sort_keys=False) + "---\n\n## Context\n"


def test_a_well_formed_epic_and_maintenance_ticket_pass(tmp_path: Path) -> None:
    _write(tmp_path, ".proj.specs/0001-scenario/spec.en.md", "spec")
    _write(tmp_path, ".proj.specs/0001-scenario/traceability.md", "matrix")
    _write(tmp_path, ".proj.tickets/0001-scenario/T-0001-load.md", _ticket("T-0001", "0001-scenario"))
    _write(
        tmp_path,
        ".proj.tickets/0000-maintenance/T-0002-typo.md",
        _ticket("T-0002", "0000-maintenance", blocked_by=["T-0001"], lightweight_reason="docs only"),
    )
    _write(tmp_path, ".proj.tickets/_legacy/old/01-anything.md", "# no frontmatter, out of scope\n")
    assert _ticket_problems(tmp_path) == []


def test_the_ticket_control_rejects_each_violation(tmp_path: Path) -> None:
    epic = "0001-scenario"
    _write(tmp_path, f".proj.tickets/{epic}/T-0001-a.md", _ticket("T-0001", epic, status="blocked"))
    _write(tmp_path, f".proj.tickets/{epic}/T-0002-b.md", _ticket("T-0003", epic))
    _write(tmp_path, f".proj.tickets/{epic}/T-0004-c.md", _ticket("T-0004", epic, status="pending"))
    _write(tmp_path, f".proj.tickets/{epic}/notes.md", "loose file")
    _write(tmp_path, f".proj.tickets/{epic}/T-0005-d.md", _ticket("T-0005", epic, blocked_by=["T-0099"]))
    _write(tmp_path, ".proj.tickets/0000-maintenance/T-0006-e.md", _ticket("T-0006", "0000-maintenance"))
    _write(tmp_path, ".proj.tickets/0000-maintenance/T-0001-f.md", _ticket("T-0001", "0000-maintenance", lightweight_reason="x"))
    problems = "\n".join(_ticket_problems(tmp_path))
    assert "status 'blocked' is derived" in problems
    assert "frontmatter id 'T-0003' != filename id T-0002" in problems
    assert "pending ticket lacks pending_reason" in problems
    assert "notes.md: not a T-NNNN-<slug>.md ticket file" in problems
    assert "blocked_by names unknown ticket T-0099" in problems
    assert "maintenance ticket lacks lightweight_reason" in problems
    assert "id T-0001 already used" in problems
    assert f"epic has no .proj.specs/{epic}/spec.en.md" in problems


def test_the_review_control_rejects_a_missing_prompt_and_a_third_round(tmp_path: Path) -> None:
    _write(tmp_path, ".proj.specs/0001-x/review/round-1.md", "r1")
    _write(tmp_path, ".proj.specs/0002-y/review/prompt.md", "p")
    _write(tmp_path, ".proj.specs/0002-y/review/round-1.md", "r1")
    _write(tmp_path, ".proj.specs/0002-y/review/round-2.md", "r2")
    _write(tmp_path, ".proj.specs/0002-y/review/round-3.md", "r3")
    problems = "\n".join(_review_problems(tmp_path))
    assert "0001-x/review: review rounds exist but the frozen prompt.md is missing" in problems
    assert "round-3.md: two rounds is the ceiling" in problems


def test_the_charter_and_spectra_controls_reject_leftovers(tmp_path: Path) -> None:
    _write(tmp_path, "AGENTS.md", "**{{PROJECT_NAME}}**\n<!-- SPECTRA:START v1 -->\n")
    _write(tmp_path, "openspec/specs/x/spec.md", "x")
    _write(tmp_path, ".claude/skills/spectra-apply/SKILL.md", "x")
    assert _charter_problems(tmp_path) == ["AGENTS.md still carries template project tokens"]
    problems = "\n".join(_spectra_problems(tmp_path))
    assert "openspec exists" in problems
    assert ".claude/skills/spectra-apply is a Spectra skill" in problems
    assert "AGENTS.md still carries a SPECTRA block" in problems
