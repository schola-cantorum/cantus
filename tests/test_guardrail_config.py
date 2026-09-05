"""Tests for the guardrails this repository claims to have.

A *claimed guardrail* is an automated check that one of this project's own
documents asserts exists. An *unimplemented guardrail* is a claimed guardrail
with no implementation — the failure mode this module exists to prevent, because
nothing else in the suite can tell that a documented tool has no implementation.

These tests assert observable facts about the repository's own configuration and
documentation. They say nothing about how the underlying tools behave: running
the linter in CI is the check on the linter, not this module's job. They must
therefore pass regardless of which lint findings happen to exist today.

Feature: unimplemented-guardrails (see .proj.spec/unimplemented-guardrails.md)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

if sys.version_info < (3, 11):
    pytest.skip("tomllib requires Python 3.11+", allow_module_level=True)

import tomllib

import yaml

_ROOT = Path(__file__).resolve().parent.parent
_WORKFLOWS = _ROOT / ".github" / "workflows"
_CONTRIBUTING = _ROOT / "CONTRIBUTING.md"
_PYPROJECT = _ROOT / "pyproject.toml"

# A backticked token in the Code Style section is read as a claim that the
# project runs that tool — by default, so that a tool nobody taught this module
# about is still caught. Two things narrow it, both structural rather than
# curated: tools are lowercase distribution names, which excludes the section's
# protocol and exception-type names (they are CapWords); and this short set
# holds the lowercase words that are demonstrably not tools.
#
# An allowlist of known tool names was the first attempt and is the wrong shape:
# it only catches the tools it already knows, which is the maintenance
# obligation this invariant exists to remove.
_NOT_TOOLS = frozenset({"cantus", "python"})

# Backticked filenames are not tool claims. Excluded by suffix rather than by
# name so that naming a new config file never needs this module updated.
_FILENAME_SUFFIXES = (".toml", ".md", ".py", ".yml", ".yaml", ".json", ".cfg", ".ini", ".txt")


def _load_workflow(name: str) -> dict:
    path = _WORKFLOWS / name
    assert path.is_file(), f"{path.relative_to(_ROOT)} missing"
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _run_steps(job: dict) -> list[str]:
    """Every shell command the job runs, as raw strings."""
    return [step["run"] for step in job.get("steps", []) if "run" in step]


def _lint_jobs(workflow: dict) -> dict[str, dict]:
    """Jobs that invoke the linter's check mode."""
    return {
        name: job
        for name, job in workflow.get("jobs", {}).items()
        if any("ruff check" in cmd for cmd in _run_steps(job))
    }


def _dev_dependency_names() -> set[str]:
    with _PYPROJECT.open("rb") as fh:
        cfg = tomllib.load(fh)
    dev = cfg["project"]["optional-dependencies"]["dev"]
    # Strip version specifiers, extras and environment markers.
    return {re.split(r"[<>=!~;\[\s]", entry, maxsplit=1)[0].strip().lower() for entry in dev}


def _code_style_section(text: str) -> str:
    """The Code Style section of the contributor guide, heading excluded."""
    match = re.search(r"^## Code Style\s*$(.*?)^## ", text, re.MULTILINE | re.DOTALL)
    assert match, "CONTRIBUTING.md has no '## Code Style' section"
    return match.group(1)


def _tools_named_in(section: str) -> set[str]:
    """Tooling names the section claims the project uses.

    Args:
        section: Markdown body of the contributor guide's Code Style section.

    Returns:
        Every backticked lowercase token that is not a known non-tool. The
        default is to treat a token as a tool claim, so a tool this module has
        never heard of is still caught. Two structural exclusions: CapWords
        tokens (protocol names, exception types) and filenames.
    """
    tokens = set(re.findall(r"`([A-Za-z][\w.-]*)`", section))
    lowercase = {t for t in tokens if re.fullmatch(r"[a-z][a-z0-9_.-]*", t)}
    named = {t for t in lowercase if not t.endswith(_FILENAME_SUFFIXES)}
    return named - _NOT_TOOLS


# --- The lint guardrail ---------------------------------------------------


def test_test_workflow_declares_a_lint_job() -> None:
    """CI runs the linter, so 'CI enforces lint' describes something real."""
    workflow = _load_workflow("test.yml")
    lint = _lint_jobs(workflow)

    assert lint, (
        "no job in test.yml runs 'ruff check' — CONTRIBUTING claims CI enforces "
        "lint, so a job must exist that does"
    )


def test_lint_job_is_separate_from_the_test_job() -> None:
    """A lint failure and a test failure are different findings."""
    workflow = _load_workflow("test.yml")
    lint = _lint_jobs(workflow)

    for name, job in lint.items():
        assert not any(
            "pytest" in cmd for cmd in _run_steps(job)
        ), f"job '{name}' runs both the linter and the tests; keep them separate"


def test_lint_job_runs_once_not_across_a_matrix() -> None:
    """Lint results are platform-independent, so a matrix repeats identical work."""
    workflow = _load_workflow("test.yml")

    for name, job in _lint_jobs(workflow).items():
        assert not job.get("strategy", {}).get("matrix"), (
            f"lint job '{name}' declares a strategy matrix; lint results do not "
            "vary by platform or Python version"
        )
        assert isinstance(job.get("runs-on"), str), (
            f"lint job '{name}' must pin a single runner"
        )


def test_lint_job_does_not_enforce_formatting() -> None:
    """A formatter check is out of scope; it would report the whole tree."""
    workflow = _load_workflow("test.yml")

    for name, job in _lint_jobs(workflow).items():
        assert not any("ruff format" in cmd for cmd in _run_steps(job)), (
            f"lint job '{name}' runs a formatter check — that is a separate "
            "change with a separate diff"
        )


def test_the_lint_rule_set_is_declared_not_inherited() -> None:
    """A check whose verdict moves with its tool version is not a guardrail.

    Ruff's *default* selection widens between releases — 0.16 turned on isort,
    pyupgrade and several RUF rules that 0.15 left off. With an unpinned
    ``ruff>=...`` requirement that made the lint verdict depend on which version
    happened to resolve: clean locally, 146 findings in CI. Declaring the set
    fixes the answer regardless of which ruff runs.
    """
    with _PYPROJECT.open("rb") as fh:
        cfg = tomllib.load(fh)

    select = cfg.get("tool", {}).get("ruff", {}).get("lint", {}).get("select")

    assert select, (
        "[tool.ruff.lint].select is not declared, so the lint job checks "
        "whatever rule set the installed ruff happens to default to"
    )


# --- The invariant that catches the next stale tool reference -------------


def test_every_tool_named_in_code_style_is_installed() -> None:
    """Naming a tool in the contributor guide is a claim that it is available.

    This is the assertion that generalises. It caught `black` — named with a
    line length, present in no dependency group, configured nowhere — and it
    will catch whatever is named next without being taught about it.
    """
    section = _code_style_section(_CONTRIBUTING.read_text(encoding="utf-8"))
    declared = _dev_dependency_names()

    for tool in sorted(_tools_named_in(section)):
        assert tool in declared, (
            f"CONTRIBUTING's Code Style section names '{tool}', but '{tool}' is "
            f"not in the dev dependency group. Either add it there, or stop "
            f"claiming the project uses it. If '{tool}' is not a tool at all, "
            f"add it to _NOT_TOOLS."
        )


def test_the_invariant_detects_a_tool_that_is_not_installed() -> None:
    """The invariant is only worth having if it fails on the shape it targets."""
    synthetic = "- **Python** — `isort` with a profile, plus `ruff` default rules.\n"

    named = _tools_named_in(synthetic)

    assert named == {"isort", "ruff"}
    assert "isort" not in _dev_dependency_names()


def test_the_invariant_catches_a_tool_it_was_never_taught_about() -> None:
    """The point of the invariant: it must not need teaching.

    An allowlist of known tool names would pass every other test in this module
    and still miss this one, which is why the check defaults to treating a
    backticked lowercase token as a claim.
    """
    synthetic = "- **Python** — `refurb` for lint hints, `docformatter` for docstrings.\n"

    assert _tools_named_in(synthetic) == {"refurb", "docformatter"}


def test_the_invariant_ignores_backticked_filenames() -> None:
    """A config file named in prose is not a claim that a tool is installed."""
    synthetic = "- **Python** — rule set declared in `pyproject.toml`, run by `ruff`.\n"

    assert _tools_named_in(synthetic) == {"ruff"}


def test_the_invariant_ignores_backticked_non_tools() -> None:
    """Exception types and protocol names in the same section are not claims."""
    synthetic = (
        "- **Naming** — protocol classes stay unprefixed (`Skill`, `Memory`).\n"
        "- **No silent fallback** — prefer raising `ImportError` or `TypeError`.\n"
    )

    assert _tools_named_in(synthetic) == set()


# --- The supply-chain guardrail -------------------------------------------

# The project declares mutually exclusive extras, so no single dependency set
# covers the whole install surface. These are the three groups that between them
# do, and the audit must keep covering all of them: dropping one silently
# narrows the guardrail without changing anything a reader would notice.
_AUDIT_GROUPS = frozenset({"main", "openhands", "mlx"})


def _audit_jobs(workflow: dict) -> dict[str, dict]:
    return {
        name: job
        for name, job in workflow.get("jobs", {}).items()
        if any("pip-audit" in cmd for cmd in _run_steps(job))
    }


def test_supply_chain_workflow_exists_and_is_separate_from_tests() -> None:
    """A supply-chain red and a test red must be distinguishable at a glance."""
    workflow = _load_workflow("supply-chain.yml")

    assert _audit_jobs(workflow), (
        "supply-chain.yml declares no job running pip-audit — the ARCH-2 "
        "supply-chain item claims this control exists"
    )

    test_workflow = _load_workflow("test.yml")
    assert not _audit_jobs(test_workflow), (
        "the dependency audit runs inside test.yml; it belongs in its own "
        "workflow so its red badge is distinguishable from a test failure"
    )


def test_supply_chain_workflow_runs_on_pull_requests_and_a_schedule() -> None:
    """The schedule is what catches an advisory published after the last merge."""
    workflow = _load_workflow("supply-chain.yml")
    # PyYAML resolves the bare `on:` key to the boolean True.
    triggers = workflow.get("on", workflow.get(True, {}))

    assert "pull_request" in triggers, "supply-chain.yml is not triggered by pull requests"
    assert "schedule" in triggers, (
        "supply-chain.yml has no schedule; without one, an advisory published "
        "after the last merge is never noticed"
    )


def test_supply_chain_audit_covers_all_three_install_groups() -> None:
    """Mutually exclusive extras mean one combination cannot cover the surface."""
    workflow = _load_workflow("supply-chain.yml")

    covered: set[str] = set()
    for job in _audit_jobs(workflow).values():
        for entry in job.get("strategy", {}).get("matrix", {}).get("include", []):
            covered.add(str(entry.get("group")))

    missing = _AUDIT_GROUPS - covered
    assert not missing, (
        f"the dependency audit does not cover {sorted(missing)}. A single-"
        f"combination audit omits the transitive dependency the ARCH-2 item "
        f"was written about."
    )


def test_supply_chain_finding_fails_the_workflow() -> None:
    """A finding must fail, not warn — a warning nobody reads is not a guardrail."""
    workflow = _load_workflow("supply-chain.yml")

    for name, job in _audit_jobs(workflow).items():
        assert job.get("continue-on-error") is not True, (
            f"job '{name}' is continue-on-error, so a finding cannot fail the "
            f"workflow"
        )
        for step in job.get("steps", []):
            if "pip-audit" in step.get("run", ""):
                assert step.get("continue-on-error") is not True, (
                    f"the audit step in job '{name}' is continue-on-error"
                )


# --- The ARCH-2 checklist tells the truth about item 7 --------------------

_ARCH2 = _ROOT / "docs" / "llm_wiki" / "architecture" / "arch_2_integration_audit.md"
_ADR_DIR = _ROOT / "docs" / "adr"


def _arch2_item_seven_lines(text: str) -> list[str]:
    """Every line of the checklist that speaks about audit item 7.

    Args:
        text: Full markdown source of the ARCH-2 checklist.

    Returns:
        The lines mentioning item 7. Scoped deliberately: the checklist covers
        ten items, and a phrase ban applied to the whole file would go red
        because some *other* item recorded a gap.
    """
    return [
        line
        for line in text.split("\n")
        if re.search(r"^7\. |#7\b|item #?7\b", line, re.IGNORECASE)
    ]


def test_arch2_supply_chain_item_points_at_a_control_that_exists() -> None:
    """The checklist may only claim a control that is on disk.

    This is the same invariant as the Code Style one, applied to the audit
    checklist: a claim is only allowed if the thing it names can be found.
    """
    text = _ARCH2.read_text(encoding="utf-8")

    # Only paths under the workflows directory are read as workflow claims, so
    # an unrelated YAML mentioned in prose is not mistaken for one.
    referenced = set(re.findall(r"\.github/workflows/([a-z0-9][\w.-]*\.yml)", text))
    assert "supply-chain.yml" in referenced, (
        "the ARCH-2 checklist does not name the supply-chain workflow, so its "
        "supply-chain item still describes a control nobody can point at"
    )
    for name in sorted(referenced):
        assert (_WORKFLOWS / name).is_file(), (
            f"the ARCH-2 checklist names workflow '{name}', which does not exist"
        )


def test_arch2_item_seven_no_longer_claims_a_framework_runtime_scan() -> None:
    """The control runs in CI. Claiming a startup scan would re-create the gap."""
    lines = _arch2_item_seven_lines(_ARCH2.read_text(encoding="utf-8"))
    assert lines, "no line in the ARCH-2 checklist mentions audit item 7"

    for line in lines:
        assert "At startup" not in line, (
            "the ARCH-2 checklist still claims a startup-time dependency scan "
            f"for item 7; no such scan exists in the cantus package: {line!r}"
        )
        assert "NOT IMPLEMENTED" not in line, (
            f"the ARCH-2 compliance table still records item 7 as unimplemented: {line!r}"
        )
        assert "open gap" not in line.lower(), (
            f"the ARCH-2 checklist still records item 7 as an open gap: {line!r}"
        )


def test_supply_chain_decision_is_recorded_and_cross_referenced() -> None:
    """A reader who wonders why the control is not in the framework can find out."""
    assert _ADR_DIR.is_dir(), "docs/adr/ missing"

    supply = [p for p in sorted(_ADR_DIR.glob("*.md")) if "supply" in p.name]
    assert supply, "no architecture decision record covers the supply-chain decision"

    adr = supply[0].read_text(encoding="utf-8")
    assert "supply-chain.yml" in adr, "the decision record does not name the control it decided on"

    arch2 = _ARCH2.read_text(encoding="utf-8")
    assert supply[0].name in arch2, (
        "the ARCH-2 checklist does not link to the decision record, so the two "
        "can drift apart unnoticed"
    )


# --- Gate D audit M6: every workflow pins the token it hands third-party code --


def _workflow_files() -> list[str]:
    return sorted(p.name for p in _WORKFLOWS.glob("*.yml"))


def test_every_workflow_declares_a_permissions_block() -> None:
    """A workflow with no ``permissions:`` receives the repository default
    token scope. Every workflow here runs third-party code (``npm ci``,
    ``pip install``, actions), so each one states its scope explicitly."""
    missing = []
    for name in _workflow_files():
        wf = _load_workflow(name)
        at_top = "permissions" in wf
        on_every_job = all("permissions" in job for job in wf.get("jobs", {}).values())
        if not (at_top or on_every_job):
            missing.append(name)
    assert missing == [], f"workflows without a permissions block: {missing}"


def test_workflows_that_only_verify_get_read_only_contents() -> None:
    """Only the release workflow needs more than ``contents: read`` (it uploads
    to PyPI via OIDC). Everything else verifies and must not be able to write."""
    for name in _workflow_files():
        if name == "release.yml":
            continue
        perms = _load_workflow(name)["permissions"]
        assert perms == {"contents": "read"}, f"{name}: permissions = {perms!r}"
