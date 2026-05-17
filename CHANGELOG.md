# Changelog

All notable changes to `cantus` will be documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.4] - 2026-05-17

Documentation-only release that bundles two long-standing dev/contributor needs
into a single patch tag: the cantus internal LLM Wiki (a curated knowledge base
for contributors and LLM agents working on the framework), and the previously
unreleased Traditional Chinese README variant carried over from commit
`744b4a7`. **No code changes, no API changes** — runtime, protocols, grammar,
and model loader are byte-for-byte identical to `v0.1.3`.

### Added

- **`docs/llm_wiki/` internal developer knowledge base** with `research/`,
  `coding_style/`, `architecture/`, and `future_work/` sections. Every research
  entry pins verified source URLs (10 entries spanning Anthropic Building
  Effective Agents, OpenClaw, OpenHarness, OpenHands SDK, SOUL.md, MCP, the
  LiteLLM March 2026 supply-chain incident, FastAPI + Pydantic, Cloudflare
  Tunnel vs ngrok, and Google Chat HTTP/Pub-Sub). The `coding_style/` section
  anchors on Linus Torvalds' four philosophical principles with a Python
  adaptation table and a worked indirect-pointer linked-list example. The
  `architecture/` section ships the authoritative ARCH-1 (two-tier API) and
  ARCH-2 (10-item cross-capability integration audit) definitions that every
  v0.2+ change proposal will link back to. The `future_work/` roadmap
  enumerates the 9 ordered changes planned through v0.5.0. Scaffolded via the
  `/wiki` suite (`wiki-init` with a custom `.profile.yaml` that overrides the
  shipped `research` profile to add `required_dirs` for the four cantus
  categories) and validated via `wiki-validator` on every commit.
- **`README.zhTW.md` Traditional Chinese variant** with bidirectional language
  switch (carries over commit `744b4a7` from v0.1.3-1, previously unreleased).
  The English and Traditional Chinese READMEs share byte-identical Install
  commands, Quickstart code, and Open-in-Colab URL fragments so copy-paste
  produces identical behavior across both variants. Both READMEs gain a new
  link to `docs/llm_wiki/index.md` in their Documentation section, marking the
  wiki as the developer / contributor entry point.

## [0.1.3] - 2026-05-11

This release bundles ready-to-run Colab notebooks and visual identity assets into
the cantus repository itself, and rewrites the README around a hero banner with
an Open-in-Colab call-to-action. **No code changes, no API changes** — the
framework runtime, protocols, grammar, and model loader are byte-for-byte
identical to `v0.1.2`. The release is purely distribution + documentation.

### Added

- **`notebooks/task_template.ipynb`.** End-user notebook with the four-cell
  contract from the `task-template` capability: mount Drive → pick variant +
  install Cantus + load model → write protocols → run agent → Inspector
  replay. Pre-wired to `cantus_version = "v0.1.3"` and `model_variant = "E4B"`,
  with the embedded E2B retry guidance markdown. Drive paths are presented as
  generic `@param` form fields so any administrator can point the notebook at
  the directory they populated.
- **`notebooks/admin_setup.ipynb`.** Administrator-facing one-time setup
  notebook that mirrors `google/gemma-4-E2B-it` and `google/gemma-4-E4B-it`
  from Hugging Face Hub to a Drive directory. The cell-zero header identifies
  the audience as administrator (中文：管理者) — no role-specific organization
  labels. Five-step structure (mount Drive → optional HF login → download both
  variants → verify files → optional smoke test) plus an advanced
  pre-quantised storage appendix.
- **`notebooks/README.md`.** Index for the bundled notebooks with audience
  matrix and Open-in-Colab badge URLs pinned to the `v0.1.3` tag.
- **`assets/banner_hero.jpeg`.** Brand-identity hero banner (chorus + Cantus
  wordmark + five protocol icons) committed as a binary blob. Referenced from
  the README via the repo-relative path `assets/banner_hero.jpeg`.
- **`assets/banner_protocols.jpeg`.** Five-protocol overview banner (musical
  staff weaving Skill / Analyzer / Validator / Workflow / Memory icons)
  committed as a binary blob. Referenced from the README immediately above the
  five-protocol introductions.

### Changed

- **`README.md` rewritten.** Top of the document now opens with the hero
  banner, a badge bar (release `v0.1.3`, ECL-2.0 license, Open-in-Colab), an
  Open-in-Colab CTA pointing at `notebooks/task_template.ipynb`, and a
  five-minute "open in Colab" path table. The five-protocol overview now
  appears below the inline `assets/banner_protocols.jpeg` reference. Install
  command examples bump from `@v0.1.1` / `@v0.1.2` to `@v0.1.3`. The existing
  30-second Quickstart, Documentation links, and License section are
  preserved.
- **`llms.txt`.** New "Versioning" section names the current `v0.1.3` install
  command and points external LLMs at the Open-in-Colab notebook URL. The
  remaining priming content (public API surface, five-protocol templates,
  tool-call grammar, style rules) is unchanged.
- **`cantus.__version__`** bumps from `"0.1.2"` to `"0.1.3"`.
- **`pyproject.toml`** `version` bumps from `"0.1.2"` to `"0.1.3"`.

### Notes

- **No code changes.** `cantus/core/`, `cantus/protocols/`, `cantus/grammar/`,
  and `cantus/model/` are byte-for-byte identical to v0.1.2. The pytest suite
  retains the v0.1.2 baseline of 95 passed / 2 skipped. v0.1.2 users upgrading
  to v0.1.3 do not need to change any import, any `Agent.run` call site, any
  `@skill` / `@analyzer` / `@validator` / `@workflow` definition, or any
  `Memory` subclass.
- **No API changes.** The public surface listed in `cantus.__init__.py`
  `__all__` is unchanged. No new exports, no removed exports, no signature
  changes.
- The Open-in-Colab badge URLs hardcode the `v0.1.3` tag. Future releases will
  bump those URLs alongside the `cantus_version` pin and `pyproject.toml`
  version string — `grep -nF '@v0.1.3'` and `grep -nF 'blob/v0.1.3/'` give the
  complete list of strings to update.

## [0.1.2] - 2026-05-11

This release implements the five failure-handling Requirements added to the
`agent-runtime` canonical spec by the `agent-loop-empty-finalanswer-hardening`
change, plus the `errors.md` cookbook section mandated by the `api-docs`
canonical spec. The originating bug observation: Gemma 4 E2B (sub-3B variant)
short-circuits `agent.run` on iteration 1 by emitting an empty `FinalAnswerAction`
without calling any skill. v0.1.2 closes that loophole from four angles
(schema-level, runtime-level, framework defaults, documentation).

### Added

- **`FinalAnswerAction.answer` is non-empty (schema + runtime).** The
  `cantus/grammar/tool_call.py` schema now constrains the `final_answer` JSON
  string with `{"type": "string", "minLength": 1}`, so grammar-constrained
  decoders (`outlines`, `xgrammar`) reject empty answers at decode time. The
  `parse_tool_call()` runtime check enforces the same invariant for callers who
  bypass the grammar. When either layer trips, the agent loop appends a
  `ValidationErrorObservation(validator_name="non_empty_final_answer",
  feedback="FinalAnswerAction.answer must be non-empty after str.strip(); call a
  skill or write a substantive answer")` to the EventStream and continues.

- **`Action parse failures fall back to ValidationErrorObservation`.** Malformed
  JSON, missing `action` field, an `action` object that contains neither
  `skill_name` nor `final_answer`, and an unknown `skill_name` at parse time all
  produce `ValidationErrorObservation(validator_name="action_parse",
  feedback=<three-segment>)`. The feedback format is a closed contract:

  1. First line: `error_type: <json_syntax|missing_field|unknown_skill>`
     (case-sensitive, closed vocabulary).
  2. Optional `detail:` line with a one-sentence explanation.
  3. `raw_output_preview:` block with up to 500 characters of the offending
     raw output; longer payloads are truncated and suffixed with the literal
     token `…[truncated]`. Newlines in the raw output are preserved as the
     two-character sequence `\n` for greppability.

- **`MaxIterationsObservation.partial_state` (deep copy).** When `agent.run`
  exhausts `max_iterations` without producing a `FinalAnswerAction`, it now
  appends `MaxIterationsObservation(iterations=N, last_action_summary=...,
  partial_state=<deep copy of EventStream>)` as the final event. The
  `partial_state` is a `copy.deepcopy` of the stream as it stood *before* the
  observation was appended, so caller mutation cannot leak back into subsequent
  `agent.run` invocations. The framework never raises an exception nor
  fabricates a `FinalAnswerAction` on this path.

- **`Default loop budgets and small-model recommendation`.** `Agent.run`
  defaults remain `max_iterations=8`, `max_retries=3` (unchanged from v0.1.1).
  The `Agent.run` docstring now records the sub-3B caller-supplied override:
  Gemma 4 E2B and other sub-3B variants benefit from `max_iterations=12`. This
  is documentation, not a framework default — `max_iterations=12` does NOT
  apply unless the caller passes it explicitly.

- **`Validator name vocabulary is closed and case-sensitive`.** New module-level
  constant `cantus.protocols.validator.RESERVED_VALIDATOR_NAMES = frozenset({
  "non_empty_final_answer", "action_parse"})` plus a new
  `ReservedValidatorNameError` (subclass of `ValueError`). The `@validator`
  decorator and `register_validator()` function-pass entry both reject
  collisions case-sensitively. User code attempting to register a validator
  named `non_empty_final_answer` or `action_parse` raises immediately at
  registration — no silent rename, no warning-only fallback.

- **`cantus.__version__ = "0.1.2"`** as a public module attribute.

- **`tests/test_failure_handling.py`** — 17 new pytest cases covering all five
  Requirements above, including round-trip stream assertions and the deep-copy
  isolation property.

- **`docs/cookbook/errors.md` section 8 (`空 FinalAnswer 與小模型 robustness`).**
  Four-point cookbook entry (schema minLength → runtime fallback → sub-3B
  `max_iterations=12` recommendation → EventStream replay worked example)
  designed for NotebookLM upload + grammar-constrained retry diagnosis.

### Changed

- **BREAKING: malformed JSON from the model no longer becomes a
  `FinalAnswerAction(answer=raw_output)`.** v0.1.1 silently wrapped raw text
  as a final answer when `json.loads` failed; v0.1.2 returns a
  `ValidationErrorObservation(validator_name="action_parse",
  error_type=json_syntax)` from `Agent.step` and lets the loop retry. The
  `Agent.step` return type is now `Union[Action, Observation]`; callers that
  pattern-matched `Action` exclusively need to widen their match.

- **BREAKING: unknown `skill_name` at parse time produces a
  `ValidationErrorObservation` instead of `ToolErrorObservation`.** v0.1.1
  let unknown skill names flow through `_dispatch_skill` which then emitted
  `ToolErrorObservation`; v0.1.2 catches them in `_parse_action` and emits
  `ValidationErrorObservation(validator_name="action_parse",
  error_type=unknown_skill)` instead. `ToolErrorObservation` remains the
  response for runtime dispatch failures (registered skill that raises at
  call time, args validation failure).

- **`pyproject.toml` version is now `0.1.2`** (the v0.1.1 git tag was
  pushed without bumping the in-source version; this release fixes that
  drift).

### Fixed

- The empty-`FinalAnswerAction` short-circuit bug originally observed on
  Gemma 4 E2B inside `examples/01_book_recommender/notebook.ipynb` is now
  framework-side hardened. Students who select E2B see retry events in their
  EventStream instead of a silently-empty answer.

### Spec / Doc Notes

- This release brings the cantus codebase into conformance with the
  `Effective Version` clauses in `colab-llm-agent/openspec/specs/agent-runtime/spec.md`,
  `openspec/specs/api-docs/spec.md`, and `openspec/specs/task-template/spec.md`.
  All five `agent-runtime` Requirements (`FinalAnswerAction.answer is
  non-empty`, `Action parse failures fall back to ValidationErrorObservation`,
  `max_iterations exhaustion appends MaxIterationsObservation`, `Default loop
  budgets and small-model recommendation`, `Validator name vocabulary is
  closed and case-sensitive`) and the `api-docs` `errors.md` cookbook
  Requirement now have shipping implementations.

- The `api-docs` spec references the cookbook section under
  `docs/api/cookbook/errors.md`; the actual cantus repo layout uses
  `docs/cookbook/errors.md` (no `api/` segment). This release appends the new
  section to the existing real-path file. The spec/repo path discrepancy is a
  pre-existing inconsistency that predates this change and is not addressed
  here; a future follow-up change is expected to either restructure cantus
  docs to `docs/api/` or amend the spec path.

## [0.1.1] - 2026-05-11

### Fixed

- `cantus.mount_drive_and_load` and `load_gemma` public wrappers now correctly
  pass through `**kwargs` (notably `drive_root`) to the underlying loader.

## [0.1.0] - 2026-05-11

### Added

- Initial release: framework extracted from `colab-llm-agent` and published as
  the standalone `schola-cantorum/cantus` repository under ECL 2.0.
- Core: `Action` / `Observation` dataclass hierarchy, `EventStream`,
  `Agent.step` / `Agent.run` bounded loop, `Registry`, `Result`.
- Protocols: `Skill`, `Analyzer`, `Validator`, `Workflow` (decorator,
  function-pass, class-first), `Memory` (class-only base + `ShortTermMemory`
  / `BM25Memory` / `EmbeddingMemory`), `@debug` decorator.
- Grammar: `cantus.grammar.tool_call.build_schema()` and `parse_tool_call()`
  for JSON-shape tool-call constraints with free-form `thought`.
- Model: `cantus.model.loader.mount_drive_and_load` for Colab + Drive
  workflows.
- Docs: `docs/overview.md`, `docs/quickstart.md`, `docs/protocols/*.md`,
  `docs/cookbook/*.md`, `docs/llms-txt.md`, plus `llms.txt` at repo root.
