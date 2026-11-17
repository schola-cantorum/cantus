---
status: proposed
date: 2026-11-17
---

# Stage 8 runs each non-browser surface as the real process, on an installed build

Stage 8 verifies behaviour against the surface that runs it (hard rule 4), and
`docs/agents/workflow.md` asks for the choice of non-browser harness to be recorded as an ADR.
OQ-001 left that choice open. cantus already has tests that come close: `tests/cli/` runs the CLI
(mostly in-process with uvicorn patched out, a few in a subprocess), `tests/serve/` drives the
FastAPI app through `TestClient`, and `tests/tui/` uses Textual's pilot. All of them run inside
pytest against the source tree, so none of them exercises the package as a student installs it, and
the app and pilot tests never start uvicorn, a socket, the `cantus tui` command or a terminal.

We decided that in epic 0001 (Tool rename, phase one), stage 8 for a non-browser surface runs the
real process on an installed build. The harness per surface:

| Surface | Harness | Evidence recorded |
|---|---|---|
| Python API in a script | a script run in a subprocess with the build's interpreter | the script, exit status, stdout and stderr |
| Notebook | a Jupyter kernel started from the build's environment, by hand or through nbclient; Colab by hand when the criterion names Colab (GPU, 4-bit Gemma) | the cells and their outputs; for Colab the runtime type and the installed wheel's sha256 |
| `cantus serve` | a real `cantus serve` process under uvicorn on a loopback port, driven by an HTTP client | the command line; each request with its status, headers and body; the server's log output; exit status and stderr when startup itself is the check |
| `cantus tui` | the real `cantus tui` command in a terminal (or pseudo-terminal) against that server process | the command line, server URL and auth settings; the keys pressed; the screen as captured text or a screenshot, not a description |
| A dependent package (ludus) | a fresh virtual environment with the build installed and a temporary clone at a pinned commit; nothing is committed or pushed there | the commands, the clone's `git diff`, stdout and stderr |

**The build.** cantus installed from one commit, never from the working tree: the **ticket build**
for a ticket's own stage 8 and the **branch build** where the spec says so (traceability section 1).
ticket-rules.md calls the ticket build "the ticket branch's last commit"; read that as the last
commit that changes the package, since the commit that sets `status: done` and records the
evidence comes after the run. The commit is the one stage 8 actually ran on; its SHA is recorded, and a later commit that changes
anything under `cantus/` means the affected checks run again. The build comes from a clean checkout
of that commit (`git worktree` or `git archive`, then `uv build --wheel`), or from
`pip install "git+file://<repo>@<sha>"`, and goes into a fresh environment: a new virtual
environment, or a Colab runtime. Where a protocol compares two builds in one Colab runtime
(traceability 2.6), the second build is installed with `pip install --force-reinstall` and the
runtime is restarted before it runs. A run that needs the build somewhere else uses
the locally built wheel with its sha256 recorded; nothing is pushed without the user's approval.
A baseline the spec compares against (cantus v0.6.0) is installed from PyPI by version.

**Proving which cantus ran.** The branch build still reports version `0.6.0`, so every run records
`cantus.__file__`, the Python version and the operating system next to the SHA. The source tree
must not be importable: the working directory, the script's directory and `PYTHONPATH` are all
outside the repository checkout.

**What does not count.** Results from pytest or CI may be attached to a stage-8 report, but they
are stage-5 evidence and do not cover a surface in the table. Where a ticket's stage-8 note names
CI or pytest runs next to a real surface, the real surface is the gate. A criterion about the
repository itself, with no surface in the table (the sweep test, the page runner, the CI install
smoke), is checked by CI on that commit; a rendered page or Markdown file goes through the browser
route of `docs/agents/workflow.md`. A surface that cannot be
run (no T4 runtime, no terminal) is reported as unverified, and the criteria that depend on it stay
open; it is never replaced by an in-process test.

Each ticket writes its stage-8 evidence, or a pointer to it, in its Comments section, naming the
surface and how it was driven (by hand, or by which tool). Evidence never carries a credential:
header values such as `Authorization` are written as `<redacted>`, auth settings are recorded as
the mode only, and a bearer token used for a run is a throwaway made for that run.

**Scope.** This binds epic 0001. No stage 8 had run under it when it was written, so the epic's
close-out retrospective decides whether it becomes the project's general rule and amends this ADR.
It does not change ADR-0009 (drift diagnosis on native hosts) or the release gate's three-OS
install smoke (ADR-0013). Channel gateways against a real chat platform are not decided here;
OQ-001 stays open for them.

## Considered options

- **Count the existing pytest harnesses as stage 8.** Rejected: they import the source tree, and
  `TestClient` and the pilot stop short of the process a student runs. They would repeat stage 5's
  evidence under another name.
- **Automate every surface in CI, or add a real-process serve check to the install smoke.** Not
  taken now: a Colab T4 cannot run in CI, and a workflow change is its own ticket. A harness that
  proves itself by hand can move into CI later without changing this decision.
- **Allow an editable install for script-only tickets.** Rejected: this epic moves and renames
  modules, and only an installed build shows a module that did not make it into the wheel.
- **`agent-browser` only.** Rejected: it reaches browser surfaces, which for cantus is the
  documentation site.
