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


# --- The supply-chain guardrail (ADR-0001) ---------------------------------

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


# --- The execution-context guardrail (ADR-0003) ------------------------------
#
# A pull request from a fork runs its own Python in the test job: pytest, and
# since ADR-0003 the documentation pages too. The controls that bound what such
# a run can do are the workflow's, not the harness's, and ADR-0003 names four:
# no privileged trigger, no secret reference, no persisted checkout credentials,
# a read-only token. Each is asserted from the YAML here, with a synthetic
# negative case so the assertion is known to fail on the shape it targets.

# Triggers that hand a pull request the base repository's token and secrets.
_PRIVILEGED_TRIGGERS = frozenset({"pull_request_target", "workflow_run"})
_READ_ONLY_CONTENTS = {"contents": "read"}
# `secrets.X` reads one secret; `secrets:` (a passthrough map, or `secrets:
# inherit`) forwards them to a reusable workflow. Neither may appear.
_SECRET_REFERENCE = re.compile(r"secrets[.:]")


def _trigger_names(workflow: dict) -> set[str]:
    """The event names a workflow runs on, whatever shape ``on:`` takes.

    Args:
        workflow: A parsed workflow document.

    Returns:
        The trigger names. PyYAML resolves a bare ``on:`` key to the boolean
        ``True``; the value may be a string, a list or a mapping.
    """
    triggers = workflow.get("on", workflow.get(True, {}))
    if isinstance(triggers, str):
        return {triggers}
    return {str(t) for t in triggers}


def _checkout_steps(workflow: dict) -> list[tuple[str, dict]]:
    """Every ``actions/checkout`` step, tagged with its job name."""
    return [
        (job_name, step)
        for job_name, job in workflow.get("jobs", {}).items()
        for step in job.get("steps", [])
        if str(step.get("uses", "")).startswith("actions/checkout")
    ]


def _execution_context_violations(workflow: dict, text: str) -> list[str]:
    """Every way a workflow breaks the ADR-0003 execution-context controls.

    Args:
        workflow: The parsed workflow document.
        text: The raw file contents, for the ``secrets.`` check, which is a
            textual rule: the string may appear nowhere, comments included.
            ``secrets:`` (a reusable-workflow passthrough) counts as well.

    Returns:
        One message per violation, each prefixed with the control it breaks,
        so a synthetic case can assert exactly which control tripped.
    """
    problems: list[str] = []

    privileged = _trigger_names(workflow) & _PRIVILEGED_TRIGGERS
    if privileged:
        problems.append(f"trigger: runs on {sorted(privileged)}")

    if _SECRET_REFERENCE.search(text):
        problems.append("secrets: the file references `secrets.`")

    for job_name, step in _checkout_steps(workflow):
        persisted = (step.get("with") or {}).get("persist-credentials")
        if persisted is not False:
            problems.append(
                f"checkout: job '{job_name}' checks out without "
                f"`persist-credentials: false`"
            )

    # Also asserted for every workflow further up; repeated here so this
    # function is the complete, self-contained statement of the ADR-0003 rule.
    perms = workflow.get("permissions")
    if perms != _READ_ONLY_CONTENTS:
        problems.append(f"permissions: {perms!r} is not `contents: read`")

    return problems


def test_test_workflow_satisfies_the_execution_context_controls() -> None:
    """ADR-0003 claims four controls on the workflow that runs untrusted code.

    Each is a fact about ``test.yml`` that a reviewer could otherwise only
    check by hand; the sibling synthetic tests show each one can fail.
    """
    path = _WORKFLOWS / "test.yml"
    text = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)

    assert _checkout_steps(workflow), "test.yml has no actions/checkout step"
    assert _execution_context_violations(workflow, text) == []


_CONFORMING_WORKFLOW = """\
on:
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false
      - run: pytest
"""


def _violations_of(text: str) -> list[str]:
    return _execution_context_violations(yaml.safe_load(text), text)


def test_the_execution_context_check_passes_a_conforming_workflow() -> None:
    assert _violations_of(_CONFORMING_WORKFLOW) == []


@pytest.mark.parametrize("trigger", sorted(_PRIVILEGED_TRIGGERS))
def test_the_execution_context_check_rejects_a_privileged_trigger(trigger: str) -> None:
    """``pull_request_target`` and ``workflow_run`` run fork code with the base
    repository's token and secrets; neither may appear in the trigger set."""
    synthetic = _CONFORMING_WORKFLOW.replace("pull_request:", f"{trigger}:")

    problems = _violations_of(synthetic)

    assert problems == [f"trigger: runs on ['{trigger}']"]


def test_the_execution_context_check_reads_list_and_string_triggers() -> None:
    """``on:`` may be written as a list or a bare string; both shapes count."""
    as_list = _CONFORMING_WORKFLOW.replace("  pull_request:\n", "").replace(
        "on:\n", "on: [pull_request, workflow_run]\n"
    )
    as_string = _CONFORMING_WORKFLOW.replace("  pull_request:\n", "").replace(
        "on:\n", "on: pull_request_target\n"
    )

    assert _violations_of(as_list) == ["trigger: runs on ['workflow_run']"]
    assert _violations_of(as_string) == ["trigger: runs on ['pull_request_target']"]


def test_the_execution_context_check_rejects_a_secret_reference() -> None:
    """A workflow that reads ``secrets.`` has something to leak; even a
    reference in a comment is a claim the file must not make."""
    in_a_step = _CONFORMING_WORKFLOW.replace(
        "      - run: pytest\n",
        "      - run: pytest\n        env:\n          TOKEN: ${{ secrets.API_KEY }}\n",
    )
    in_a_comment = _CONFORMING_WORKFLOW + "# TODO: pass secrets.API_KEY here\n"
    inherited = _CONFORMING_WORKFLOW + (
        "  reuse:\n    uses: ./.github/workflows/other.yml\n    secrets: inherit\n"
    )

    assert _violations_of(in_a_step) == ["secrets: the file references `secrets.`"]
    assert _violations_of(in_a_comment) == ["secrets: the file references `secrets.`"]
    assert _violations_of(inherited) == ["secrets: the file references `secrets.`"]


@pytest.mark.parametrize(
    "with_block",
    [
        "",
        "        with:\n          fetch-depth: 0\n",
        "        with:\n          persist-credentials: true\n",
    ],
    ids=["no-with", "with-but-no-key", "explicit-true"],
)
def test_the_execution_context_check_rejects_a_checkout_that_keeps_credentials(
    with_block: str,
) -> None:
    """``actions/checkout`` persists the token into ``.git/config`` unless told
    not to; absence of the key is the default and therefore a violation."""
    synthetic = _CONFORMING_WORKFLOW.replace(
        "        with:\n          persist-credentials: false\n", with_block
    )

    problems = _violations_of(synthetic)

    assert problems == [
        "checkout: job 'test' checks out without `persist-credentials: false`"
    ]


def test_the_execution_context_check_finds_every_checkout_not_just_the_first() -> None:
    """Two jobs, one compliant and one not: the non-compliant one is named."""
    synthetic = _CONFORMING_WORKFLOW + (
        "  lint:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v6\n"
        "      - run: ruff check .\n"
    )

    problems = _violations_of(synthetic)

    assert problems == [
        "checkout: job 'lint' checks out without `persist-credentials: false`"
    ]


@pytest.mark.parametrize(
    "permissions_block",
    [
        "",
        "permissions:\n  contents: write\n",
        "permissions:\n  contents: read\n  pull-requests: write\n",
        "permissions: write-all\n",
    ],
    ids=["absent", "contents-write", "extra-scope", "write-all"],
)
def test_the_execution_context_check_rejects_permissions_beyond_contents_read(
    permissions_block: str,
) -> None:
    """The token must be exactly ``contents: read``: absent means the
    repository default, and any extra scope is a capability fork code gets."""
    synthetic = _CONFORMING_WORKFLOW.replace(
        "permissions:\n  contents: read\n", permissions_block
    )

    problems = _violations_of(synthetic)

    assert len(problems) == 1
    assert problems[0].startswith("permissions: ")
    assert problems[0].endswith("is not `contents: read`")


# --- Every ADR declares a status; every accepted ADR and its control cite each
# other by number --------------------------------------------------------------
#
# The supply-chain test above checks one ADR by hand. This loop is the same
# invariant for all of them: an ADR that says it is in force must name a
# control that exists, and the control must cite the ADR back, so that naming
# a file that merely exists cannot pass. A `proposed` ADR is a decision not yet
# in force and is exempt. ADR-0003 defines the rule; this module is its control.

# The directories a control may live in. Anything else an ADR names (a package
# module, a prose page) is context, not a control.
_CONTROL_DIRS = (".github/workflows", "tests", "scripts")
_CONTROL_PATH = re.compile(
    r"(?<![\w/])((?:" + "|".join(re.escape(d) for d in _CONTROL_DIRS) + r")/[\w./-]*\w)"
)
_KNOWN_STATUSES = frozenset({"accepted", "proposed"})


def _adr_files() -> list[Path]:
    return sorted(_ADR_DIR.glob("*.md"))


def _adr_number(path: Path) -> str:
    """The four-digit prefix of an ADR filename, e.g. ``0002``."""
    match = re.match(r"(\d{4})-", path.name)
    assert match, f"{path.name} is not an NNNN-slug ADR filename"
    return match.group(1)


def _adr_status(text: str) -> str | None:
    """The ``status:`` declared in an ADR's YAML front matter.

    Args:
        text: Full markdown source of the ADR.

    Returns:
        The status word, or ``None`` when the file has no front matter or the
        front matter has no ``status:`` line. Only front matter counts, so the
        word "status" appearing in prose is never mistaken for a declaration.
    """
    match = re.match(r"---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    if not match:
        return None
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "status":
            # Tolerate the YAML a hand would write: a trailing comment, quotes.
            value = value.split("#", 1)[0].strip().strip("'\"")
            return value or None
    return None


def _control_paths_named(text: str) -> set[str]:
    """Paths under the control directories that the ADR text names."""
    return set(_CONTROL_PATH.findall(text))


def _controls_citing(number: str, named: set[str], root: Path) -> set[str]:
    """The named paths that exist under ``root`` and cite ``ADR-<number>``."""
    literal = f"ADR-{number}"
    citing: set[str] = set()
    for rel in named:
        candidate = root / rel
        if candidate.is_file() and literal in candidate.read_text(encoding="utf-8"):
            citing.add(rel)
    return citing


def _adr_problem(path: Path, root: Path) -> str | None:
    """Why this ADR fails the loop, or ``None`` when it passes.

    Args:
        path: The ADR file.
        root: The repository root the named control paths are relative to.

    Returns:
        A message naming the ADR and the missing piece: no status, an unknown
        status word, or an accepted ADR with no control that cites it back.
    """
    text = path.read_text(encoding="utf-8")
    status = _adr_status(text)
    if status is None:
        return f"{path.name} declares no `status:` in its front matter"
    if status not in _KNOWN_STATUSES:
        return f"{path.name} has status {status!r}; expected one of {sorted(_KNOWN_STATUSES)}"
    if status != "accepted":
        return None
    number = _adr_number(path)
    named = _control_paths_named(text)
    if not named:
        return (
            f"{path.name} is accepted but names no path under "
            f"{_CONTROL_DIRS} as its control"
        )
    if not _controls_citing(number, named, root):
        return (
            f"{path.name} is accepted and names {sorted(named)}, but none of "
            f"them both exists and contains the literal 'ADR-{number}'"
        )
    return None


@pytest.mark.parametrize("adr", _adr_files(), ids=lambda p: p.name)
def test_every_adr_declares_a_status_and_every_accepted_adr_has_a_citing_control(
    adr: Path,
) -> None:
    """An ADR in force points at its control, and the control points back."""
    assert _adr_problem(adr, _ROOT) is None


def test_the_adr_loop_covers_the_decision_records_it_was_written_for() -> None:
    """The loop is only a guardrail if it actually iterates the ADRs that exist."""
    numbers = {_adr_number(p) for p in _adr_files()}
    assert {"0001", "0002", "0003", "0004"} <= numbers


def _write_adr(directory: Path, number: str, body: str) -> Path:
    path = directory / f"{number}-synthetic.md"
    path.write_text(body, encoding="utf-8")
    return path


def test_the_adr_loop_rejects_an_adr_with_no_status_line(tmp_path: Path) -> None:
    no_front_matter = _write_adr(tmp_path, "0101", "# A decision\n\nProse.\n")
    front_matter_without_status = _write_adr(
        tmp_path, "0102", "---\nsupersedes: 0001\n---\n\n# A decision\n"
    )

    assert _adr_problem(no_front_matter, tmp_path) == (
        "0101-synthetic.md declares no `status:` in its front matter"
    )
    assert _adr_problem(front_matter_without_status, tmp_path) == (
        "0102-synthetic.md declares no `status:` in its front matter"
    )


def test_the_adr_loop_reads_front_matter_a_hand_would_write() -> None:
    """CRLF endings, no final newline, a trailing comment and quotes are all
    still a declaration, not a missing one."""
    assert _adr_status("---\r\nstatus: accepted\r\n---\r\n# T\n") == "accepted"
    assert _adr_status("---\nstatus: proposed\n---") == "proposed"
    assert _adr_status("---\nstatus: accepted  # since ticket 05\n---\n") == "accepted"
    assert _adr_status("---\nstatus: 'accepted'\n---\n") == "accepted"
    assert _adr_status("---\nstatus:\n---\n") is None


def test_the_adr_loop_ignores_the_word_status_in_prose(tmp_path: Path) -> None:
    """Only front matter declares a status; a sentence about status does not."""
    adr = _write_adr(tmp_path, "0103", "# A decision\n\nstatus: accepted, we said.\n")

    assert _adr_problem(adr, tmp_path) == (
        "0103-synthetic.md declares no `status:` in its front matter"
    )


def test_the_adr_loop_rejects_an_unknown_status_word(tmp_path: Path) -> None:
    """A typo such as ``acepted`` must not silently become an exemption."""
    adr = _write_adr(tmp_path, "0104", "---\nstatus: acepted\n---\n\n# A decision\n")

    problem = _adr_problem(adr, tmp_path)

    assert problem is not None
    assert problem.startswith("0104-synthetic.md has status 'acepted'")


def test_the_adr_loop_exempts_a_proposed_adr(tmp_path: Path) -> None:
    """A proposed decision is not in force, so it need not name a control yet."""
    adr = _write_adr(tmp_path, "0105", "---\nstatus: proposed\n---\n\n# Not yet built.\n")

    assert _adr_problem(adr, tmp_path) is None


def test_the_adr_loop_rejects_an_accepted_adr_naming_no_control(tmp_path: Path) -> None:
    adr = _write_adr(
        tmp_path,
        "0106",
        "---\nstatus: accepted\n---\n\n# Built.\n\nEnforced by `cantus/config.py`.\n",
    )

    problem = _adr_problem(adr, tmp_path)

    assert problem == (
        "0106-synthetic.md is accepted but names no path under "
        f"{_CONTROL_DIRS} as its control"
    )


def test_the_adr_loop_rejects_a_named_control_that_does_not_exist(tmp_path: Path) -> None:
    adr = _write_adr(
        tmp_path,
        "0107",
        "---\nstatus: accepted\n---\n\n# Built.\n\nEnforced by `tests/test_missing.py`.\n",
    )

    problem = _adr_problem(adr, tmp_path)

    assert problem == (
        "0107-synthetic.md is accepted and names ['tests/test_missing.py'], but "
        "none of them both exists and contains the literal 'ADR-0107'"
    )


def test_the_adr_loop_rejects_a_control_that_exists_but_does_not_cite_back(
    tmp_path: Path,
) -> None:
    """Naming a real file is not enough: the file must cite the ADR by number.

    This is the case the hand-written supply-chain test cannot tell apart from
    a pass, and the reason the loop demands the literal.
    """
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_thing.py").write_text(
        "# enforces the thing decided in ADR-0999\n", encoding="utf-8"
    )
    adr = _write_adr(
        tmp_path,
        "0108",
        "---\nstatus: accepted\n---\n\n# Built.\n\nControl: `tests/test_thing.py`.\n",
    )

    problem = _adr_problem(adr, tmp_path)

    assert problem == (
        "0108-synthetic.md is accepted and names ['tests/test_thing.py'], but "
        "none of them both exists and contains the literal 'ADR-0108'"
    )


def test_the_adr_loop_passes_when_one_named_control_cites_back(tmp_path: Path) -> None:
    """One citing control among several named paths is enough."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "check.sh").write_text("# ADR-0109\n", encoding="utf-8")
    adr = _write_adr(
        tmp_path,
        "0109",
        "---\nstatus: accepted\n---\n\n# Built.\n\n"
        "See `scripts/check.sh` and `.github/workflows/gone.yml`.\n",
    )

    assert _adr_problem(adr, tmp_path) is None


def test_the_control_path_pattern_reads_backticked_and_bare_paths() -> None:
    """Paths are read whether backticked, parenthesised or bare, and a path
    outside the control directories is not a control."""
    text = (
        "Enforced by `tests/serve/channels/test_exception_policy.py` and\n"
        "(.github/workflows/supply-chain.yml); scripts/check_no_dev_paths.sh too.\n"
        "Context lives in cantus/config.py and docs/adr/0001-x.md.\n"
    )

    assert _control_paths_named(text) == {
        "tests/serve/channels/test_exception_policy.py",
        ".github/workflows/supply-chain.yml",
        "scripts/check_no_dev_paths.sh",
    }
