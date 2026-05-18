# Changelog

All notable changes to `cantus` will be documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.6] - 2026-05-18 — Internal Cleanup

**ADDITIVE — no public API change, no BREAKING, no new dependencies, no new
optional extras, no user-facing surface change.** Clears the 15 redundant
`# type: ignore[...]` comments that the v0.3.5 `warn_unused_ignores = true`
mypy baseline started reporting, so `mypy cantus` runs cleanly with no
`[unused-ignore]` warnings on a `cantus[dev]` install.

### Internal

- `cantus/adapters/openhands.py` — removed `# type: ignore[import-not-found]`
  from the SDK-gate `from openhands.events import Action` (mypy override
  `openhands.*` already covers the missing-import case).
- `cantus/adapters/mcp.py` — removed `# type: ignore[import-not-found]` from
  the SDK-gate `import mcp as _mcp` and removed `# type: ignore[misc]` from
  the `server.tool(...)` decorator call.
- `cantus/adapters/langchain.py` — removed `# type: ignore[import-not-found]`
  from both SDK-gate imports (`import langchain_core`,
  `from langchain_core.tools import BaseTool`) and removed
  `# type: ignore[misc, valid-type]` from the `class _ExposedLangChainTool(BaseTool)`
  declaration.
- `cantus/adapters/dspy.py` — removed `# type: ignore[import-not-found]` from
  the SDK-gate `import dspy`.
- `cantus/adapters/huggingface.py` — narrowed
  `# type: ignore[import-not-found,attr-defined]` to
  `# type: ignore[attr-defined]` (the `import-not-found` code is now redundant
  under the `transformers.*` mypy override; `attr-defined` is still needed
  for the dynamic `Tool` name exposure).
- `cantus/protocols/debug.py` — narrowed
  `# type: ignore[union-attr,attr-defined]` to `# type: ignore[union-attr]`
  on the `target._debug_enabled = True` monkey-patch.
- `cantus/model/loader.py` — removed `# type: ignore` from the lazy `import
  torch` and `from transformers import (...)` block inside
  `_load_with_quant_config()`.
- `cantus/model/providers/openai.py`, `groq.py`, `anthropic.py` — removed
  `# type: ignore[import-not-found]` from the `_get_client()` lazy imports.
- `cantus/model/providers/google.py` — narrowed
  `# type: ignore[import-not-found,attr-defined,import-untyped]` to
  `# type: ignore[attr-defined,import-untyped]` on the lazy
  `from google import genai` import.

### Notes

- The `cantus[all]` + `cantus[openhands]` optional-extras pair is currently
  unresolvable by `uv` / `pip` due to a transitive
  `fastmcp` → `websockets>=15.0.1` requirement clashing with
  `google-genai` → `websockets<15.0.dev0`. This is a release engineering
  issue surfaced (not introduced) by v0.3.6 and is tracked as a separate
  follow-up; it is intentionally out of scope for this internal-cleanup
  release. As a workaround, `uv run --frozen --extra dev` reuses the existing
  lockfile and bypasses the conflict.
- Strict mypy (`strict = true`) remains deferred to v0.4.x — narrowing
  individual ignores does not move that gate.
- Maintainers adding new ignores SHALL prefer the narrowest error-code list
  possible (`# type: ignore[specific-code]` over bare `# type: ignore`) so
  that `warn_unused_ignores` can surface drift in future cantus releases.

## [0.3.5] - 2026-05-18 — Quality Baseline

PATCH release. **ADDITIVE — no BREAKING change, no new dependencies, no new
optional extras, no cantus public callable change.** Ships the v0.3.x
educational arc's deferred quality infrastructure so the next feature arc
starts on a verifiable baseline.

### Added

- `cantus/py.typed` — PEP 561 inline-typed marker. Downstream consumers running
  `mypy --strict` against code that imports cantus symbols now see cantus'
  declared annotations instead of `Any`. The marker is bundled into the wheel
  via a new `[tool.setuptools.package-data]` entry (`cantus = ["py.typed"]`)
  so `python -m build` produces wheels that ship the marker.
- `[tool.mypy]` baseline configuration in `pyproject.toml`. Pins
  `python_version = "3.10"`, enables `warn_unused_ignores`,
  `warn_redundant_casts`, and `check_untyped_defs`, leaves
  `disallow_untyped_defs = false` (strict mode is deferred to v0.4.x), and
  declares `[[tool.mypy.overrides]]` setting `ignore_missing_imports = true`
  for the lazy-import adapter SDKs (`mcp.*`, `langchain_core.*`, `dspy.*`,
  `transformers.*`, `openhands.*`, `anthropic.*`, `openai.*`,
  `google.genai.*`, `groq.*`) so a bare `cantus[dev]` install can run
  `mypy cantus` without optional extras installed.
- `[tool.coverage.run]` and `[tool.coverage.report]` baseline configuration.
  Branch coverage is enabled (`branch = true`); the report shows missing
  lines and excludes `pragma: no cover`, `if TYPE_CHECKING:`, and
  `raise NotImplementedError` from coverage accounting. No `fail_under`
  threshold is set in this release — baseline data is collected first.
- `pytest` addopts now trigger coverage by default
  (`--cov=cantus --cov-report=term-missing --cov-report=xml`). Running
  `pytest tests/` without any flag emits a terminal coverage section and a
  `coverage.xml` artifact in the working directory.
- `MIGRATION_v0.3.4_to_v0.3.5.md` — user-facing migration note documenting
  the ADDITIVE nature of this release and the new dev workflow signals.

### Changed

- `docs/protocols/adapters-batch2.md` — the existing v0.3.4 supersede
  blockquote at the top of the file is reformatted to lead with
  `**Status:** Superseded by [adapters-batch3.md](./adapters-batch3.md)
  (cantus v0.3.4) for the HuggingFace and OpenHands import directions;
  preserved as a v0.3.3 historical snapshot of the batch2 surface.` so the
  file is unambiguously identifiable as a historical snapshot at a glance.
  The spec body below the note is byte-identical.

### Internal

- Added `tests/test_distribution_config.py` with six assertions covering the
  PEP 561 marker, the setuptools package-data wiring, the mypy baseline, the
  coverage baseline, the pytest addopts contract, and the v0.3.5 version
  pin. These tests double as the verification target for the
  `Cantus ships PEP 561 py.typed marker and baseline tool configuration`
  Requirement.

### Notes

- Strict mypy (`strict = true`) is intentionally deferred to v0.4.x — it
  requires an audit + annotation pass on cantus' Protocol classes and
  `getattr`-driven adapter shims.
- Coverage `fail_under` threshold is intentionally deferred until a
  multi-release baseline has been collected; setting it now would either
  inflate CI false positives (threshold too high) or anchor regressions
  (threshold too low).
- Maintainers adding a new optional-extras adapter SDK SHALL append its
  top-level module glob to `[[tool.mypy.overrides]]` so `mypy cantus`
  continues to pass on a bare `cantus[dev]` install.

## [0.3.4] - 2026-05-18

PATCH release. **PATCH additive — no BREAKING.** Closes the cross-framework
adapter matrix by adding the HuggingFace import direction (`import_hf_tool`),
and converts the v0.3.3 "deferred to v0.3.4 batch3" wording for the OpenHands
import direction into a permanent "not applicable" decision. All v0.3.0,
v0.3.1, v0.3.2, and v0.3.3 imports, constructors, and behaviours remain
byte-identical.

### Added

- `cantus.adapters.import_hf_tool(tool: transformers.Tool) -> Skill` — wraps a
  HuggingFace `transformers.Tool` as a cantus Skill (requires
  `cantus[huggingface]`). Adds a `_HuggingFaceRemoteSkill(_RemoteSkillBase)`
  internal subclass that derives the v0.3.0 JSON Schema from `tool.inputs`
  (every declared input field becomes required, mirroring HF's lack of an
  "optional input" concept) and dispatches `skill(**kwargs)` to
  `tool(**kwargs)`. Errors during dispatch surface as
  `RuntimeError("huggingface_remote_error: ...")`; schema parsing errors
  surface as `RuntimeError("huggingface_handshake_failed: ...")`; non-Tool
  inputs surface as `TypeError("import_hf_tool expects transformers.Tool")`.
- `docs/protocols/adapters-batch3.md` — new design document covering the
  v0.3.4 close-out, including the four-framework bidirectional matrix and
  the OpenHands "not applicable" rationale.
- `MIGRATION_v0.3.3_to_v0.3.4.md` — user-facing migration note with usage
  examples for `import_hf_tool` and guidance on the OpenHands export-only
  path.

### Changed

- `cantus.adapters.openhands` docstring now describes the OpenHands import
  direction as permanently not applicable (was: "deferred to v0.3.4 batch3").
  `openhands.events.Action` is a declarative event record dispatched by the
  OpenHands host runtime; it exposes no `__call__` that
  `Skill.run(**kwargs)` could delegate to, so wrapping it as a Skill is a
  semantic mismatch rather than a tooling gap.
- `cantus.adapters.huggingface` docstring rewritten — the v0.3.3 "import
  direction deferred" paragraph is removed; the module now documents the
  bidirectional contract and points at `_RemoteSkillBase` as the import-path
  shared base.
- `cantus.adapters.__init__` docstring expanded to enumerate ten top-level
  callables (3 from v0.3.2 + 6 from v0.3.3 + 1 from v0.3.4) and to spell
  out the OpenHands export-only stance.
- `docs/protocols/adapters-batch2.md` carries a supersede note pointing
  readers at `adapters-batch3.md` for the current HF / OpenHands import
  story.
- `openspec/specs/adapter-layer-batch2/spec.md` (in the main repo) gains a
  new Requirement `import_hf_tool wraps HuggingFace transformers Tool as
  cantus Skill`, and the `expose_as_hf_tool` / `expose_as_openhands_action`
  Requirements have their "deferred to v0.3.4 batch3 evaluation" language
  removed; the OpenHands counterpart now explains the omission as a
  permanent semantic mismatch.

### Removed

- `tests/adapters/test_huggingface.py::test_import_hf_tool_not_exported` —
  the v0.3.3 "defensive ImportError" test is gone; the symbol is now
  exported. The OpenHands counterpart (`test_import_openhands_action_not_exported`)
  stays, with its docstring updated to call out the permanence of the
  decision.

### Not changed

- `cantus.adapters._RemoteSkillBase` is untouched; v0.3.4 only adds a new
  concrete subclass.
- All LangChain / DSPy / MCP / Anthropic Memory adapter modules and tests
  are byte-identical with v0.3.3.
- `Registry.KINDS` remains `("skill",)`.
- No new dependencies or extras; `cantus[huggingface]` (`transformers>=4.40,<5`)
  is reused.

## [0.3.3] - 2026-05-18

MINOR release. **MINOR additive — no BREAKING.** Extends `cantus.adapters`
with six cross-framework callables (LangChain / DSPy / HuggingFace /
OpenHands) and lifts the v0.3.2 `_RemoteSkill` pattern into a private
`_RemoteSkillBase` shared base. All v0.3.0, v0.3.1, and v0.3.2 imports,
constructors, and behaviours remain byte-identical.

### Added

- `cantus.adapters` gains six new top-level callables (in addition to
  the three v0.3.2 callables):
  - `expose_as_langchain_tool(skill) -> BaseTool` and
    `import_langchain_tool(tool) -> Skill` — bidirectional bridge to
    `langchain_core.tools.BaseTool`.
  - `expose_as_dspy_tool(skill) -> dspy.Tool` and
    `import_dspy_tool(tool) -> Skill` — bidirectional bridge to
    `dspy.Tool` with a `{str, int, float, bool}` ↔ JSON Schema type
    mapping.
  - `expose_as_hf_tool(skill) -> transformers.Tool` — export-only
    bridge to HuggingFace `transformers.Tool` (import direction
    deferred to v0.3.4 batch3).
  - `expose_as_openhands_action(skill) -> openhands.events.Action` —
    export-only bridge to OpenHands actions (import direction deferred
    to v0.3.4 batch3).
- `cantus.adapters._remote_skill._RemoteSkillBase` — private shared
  base for every `import_*` adapter. Subclass to add new `import_*`
  bridges without re-implementing the v0.3.0 `Skill.spec_for_llm()`
  shape contract or the `is_remote = True` marker. The class is private
  (leading underscore in the module name) and is intentionally NOT
  re-exported from `cantus.adapters.__init__`.
- `cantus.adapters.mcp_client._RemoteSkill` now inherits from
  `_RemoteSkillBase` — refactor only; v0.3.2 observable behaviour
  remains byte-identical and the existing `test_mcp_client.py`
  test suite passes without modification.
- Four new extras groups in `pyproject.toml`:
  - `cantus[langchain]` → `langchain-core>=0.3,<1`
  - `cantus[dspy]` → `dspy-ai>=2.5,<3`
  - `cantus[huggingface]` → `transformers>=4.40,<5`
  - `cantus[openhands]` → `openhands>=1.16,<2`
  Each adapter module gates on its respective SDK at import time; a
  missing SDK surfaces as `ImportError("... pip install cantus[<name>]")`.

### Unchanged

- All v0.3.0 / v0.3.1 / v0.3.2 imports continue to resolve identically.
- `Skill.spec_for_llm()` JSON shape stays
  `{"name", "description", "args_schema"}` before and after any
  `cantus.adapters.*` submodule is imported — the existing
  `test_skill_spec_for_llm_invariant.py` contract is extended to cover
  all nine adapter modules (3 v0.3.2 + 5 v0.3.3).
- `Registry.KINDS` remains `("skill",)` — batch2 adapters do NOT
  introduce a new protocol kind.
- The `providers` aggregator continues to install only OpenAI /
  Anthropic / Google / Groq; the four batch2 extras require explicit
  opt-in.

## [0.3.2] - 2026-05-18

MINOR release. **MINOR additive — no BREAKING.** Adds the
`cantus.adapters` subpackage with three MVP bridges: MCP server +
MCP client + Anthropic Memory tool dict. All v0.3.0 and v0.3.1
imports, constructors, and behaviours remain byte-identical.

### Added

- `cantus.adapters` subpackage with three top-level callables:
  - `export_as_mcp_server(skills, *, name, version) -> McpServer`
    wraps cantus Skills as a stdio / streamable-HTTP MCP server.
  - `import_mcp_server(*, transport, command_or_url) -> list[Skill]`
    connects to a remote MCP server and returns each remote tool as
    a cantus Skill with `is_remote = True`.
  - `expose_as_anthropic_memory_tool(memory) -> dict` returns the
    Anthropic Memory tool spec dict (4-action `view`/`create`/
    `str_replace`/`delete`); pure-Python, no SDK dependency.
- `cantus[mcp]` extras pinning `mcp>=0.1,<2` — required for any
  `cantus.adapters.mcp_*` use; `expose_as_anthropic_memory_tool`
  works in the core install.
- `cantus.adapters.mcp` gate module that raises `ImportError("...
  pip install cantus[mcp]")` when the SDK is missing.
- `Skill.is_remote: bool = False` class attribute; MCP-imported
  Skills override to `True`. The marker is NOT leaked into
  `spec_for_llm()` — v0.3.0 shape contract `{"name", "description",
  "args_schema"}` is preserved across adapter import and use.

### Security

- `export_as_mcp_server` rejects `name` / `version` values that fail
  the regex `^[A-Za-z0-9][A-Za-z0-9._-]*$` (length 1-64) — guards
  against JSON-RPC payload injection.
- `import_mcp_server(transport="stdio", ...)` rejects shell
  metacharacters (`|`, `>`, `<`, `&`, `;`, `$`, backtick, newline)
  in `command_or_url` — `subprocess.Popen` is never invoked via a
  shell.
- `import_mcp_server(transport="http", ...)` rejects URLs whose
  scheme is not `http` / `https` or whose netloc is empty.
- `McpServer.run(transport="http")` fails loud with
  `OSError("Address already in use")` on a busy port; the framework
  does NOT silently hang or retry.

### Unchanged

- All v0.3.0 / v0.3.1 imports continue to resolve identically.
- `Skill.spec_for_llm()` JSON shape stays
  `{"name", "description", "args_schema"}` before and after any
  `cantus.adapters` submodule is imported.
- `Registry.KINDS` remains `("skill",)` — adapters do NOT introduce
  a new protocol kind.

## [0.3.1] - 2026-05-18

MINOR release. **PATCH-equivalent additive — no BREAKING.** Adds the
Memory dual-tier API, the `Soul` identity abstraction, and an opt-in
JSON-Lines persistence plug for `EventStream`. All v0.3.0 imports,
constructors, and behaviours remain byte-identical when the new
keywords / classes are not used.

### Added

- `cantus.protocols.memory.MarkdownMemory(path, top_k=10)` — file-backed
  lower-tier Memory with frontmatter chunks and a resolve-then-classify
  safe-path policy that rejects path traversal, Unix system roots
  (`/etc`, `/sys`, `/proc`, `/dev`, `/root`, plus macOS `/private/*`
  canonical equivalents), FIFO / socket / block-device entries, and
  Windows UNC paths.
- `cantus.protocols.memory.AutoMemory(backend)` — upper-tier wrapper
  that exposes 4 LLM-facing `Skill` tools (`view`, `create`,
  `str_replace`, `delete`) mirroring the Anthropic Memory tool spec.
  `AutoMemory` uses composition (NOT inheritance) and returns a cached
  `tools` list whose docstring carries the literal `"LLM has full CRUD
  access"` foot-gun warning.
- `cantus.identity.Soul` and `Soul.from_file(path)` / `Soul.from_text(text)`
  parsers for the six-section SOUL.md format (`Name & Role`,
  `Personality`, `Rules`, `Tools`, `Output format`, `Handoffs`).
  Case-sensitive H2 matching; failures raise `SoulParseError` with
  `missing_sections`, `duplicates`, and `unexpected` lists.
- `cantus.core.event_stream_persistence.JsonLinesPersistence(path)` —
  optional append-only JSON-Lines persistence plug with `os.fsync` after
  every write, POSIX `0o600` file mode on first creation, and a
  serialise-before-open contract that prevents partial writes on
  non-serialisable input.
- `Agent.__init__` now accepts a keyword-only `soul: Soul | None = None`.
  When supplied, the agent prepends `soul.to_system_prompt() + "\n\n"`
  to the system prompt; when `None` (default), system-prompt construction
  is byte-identical to v0.3.0.
- `Turn` dataclass gains two optional metadata fields: `timestamp:
  datetime | None` and `type: Literal["user", "assistant"] | None`. The
  `type` Literal is restricted to the two derivable values; `"system"`
  and `"tool"` are explicitly rejected to keep `Turn` semantically
  unambiguous. Whitespace-only Turn(user="   ", assistant="") raises
  `ValueError("empty Turn ...")`.

### Unchanged

- All v0.3.0 imports continue to resolve identically (`from cantus
  import Skill, Memory, Agent, skill`, `from cantus.hooks import ...`,
  `from cantus.workflows import ...`).
- `from cantus import memory` and `from cantus import register_memory`
  still raise `ImportError` — Memory remains class-only entry per the
  v0.3.0 `agent-protocols` Requirement.
- In-memory `EventStream` is unchanged; `JsonLinesPersistence` is a
  separate opt-in plug that host code drives explicitly.

## [0.3.0] - 2026-05-18

MAJOR release. **BREAKING** — protocol surface reorganized: `Analyzer` and
`Validator` are demoted from top-level protocol kinds to `Skill` pre/post hook
helpers; the `@workflow` decorator is removed and replaced by explicit
`cantus.workflows` building blocks (`PromptChain`, `Router`, `Parallel`,
`OrchestratorWorker`, `EvaluatorOptimizer`). See
[`MIGRATION_v0.2_to_v0.3.md`](./MIGRATION_v0.2_to_v0.3.md) for the mechanical
conversion recipe.

### BREAKING

- `from cantus import Workflow, workflow, register_workflow` → `ImportError`.
  `cantus.protocols.workflow` is hard-removed.
- `from cantus import Analyzer, Validator, analyzer, validator,
  register_analyzer, register_validator` → `ImportError`. Use
  `from cantus.hooks import …` instead.
- `Registry.KINDS` shrunk from `("skill", "analyzer", "validator", "workflow")`
  to `("skill",)`. `Registry.register("analyzer"|"validator"|"workflow", …)`
  raises `ValueError` with a migration hint pointing at `pre_hook=` / `post_hook=`
  / `cantus.workflows`.
- The agent loop no longer scans four protocol kinds. `Agent._dispatch_skill`
  now performs a single `registry.lookup("skill", …)` followed by a linear
  `pre_hook → body → post_hook` chain.
- `@debug` no longer accepts `@workflow` as a stack target (it can't — the
  decorator no longer exists). Still works on `@skill`, `@analyzer`,
  `@validator`.

### Added

- `cantus.hooks` submodule: re-exports `analyzer`, `validator`, `Analyzer`,
  `Validator`, `Result`, and `ReservedValidatorNameError` from a single
  namespace that emphasises their hook-helper role.
- `cantus.workflows` package: five orchestration primitives ported from
  Anthropic's *Building Effective Agents* playbook. Each is a plain Python
  class with a `.run(input) → output` method; none of them touch the runtime
  registry.
- `Skill` instances gain `_pre_hook` and `_post_hook` attributes. The `@skill`
  decorator now accepts both bare (`@skill`) and parameterised
  (`@skill(pre_hook=…, post_hook=…)`) forms.
- `Skill.spec_for_llm()` JSON shape is preserved — top-level keys remain
  exactly `{"name", "description", "args_schema"}` regardless of hook
  attachment. A fixture-backed snapshot test guards this for downstream
  adapter consumers (v0.3.2 `cantus-adapter-layer`).

### Changed

- `Agent._dispatch_skill` body shrunk and straight-lined: no per-kind
  `if`/`elif` ladder, no four-kind fallback scan. Hook exceptions are wrapped
  as `ToolErrorObservation` with `pre_hook` / `post_hook` labels in the
  message. A `post_hook` returning `Result(ok=False, …)` still produces a
  `ValidationErrorObservation` carrying the hook function's name.
- `@analyzer` and `@validator` decorators are no longer registry side-effects;
  they return reusable callable helpers. The `RESERVED_VALIDATOR_NAMES` guard
  (`non_empty_final_answer`, `action_parse`) continues to apply.

### Removed

- `cantus.protocols.workflow` module (hard-removed; no deprecated shim).
- `Workflow` class, `@workflow` decorator, `register_workflow` function.
- Top-level re-exports of `Analyzer`, `Validator`, `analyzer`, `validator`,
  `register_analyzer`, `register_validator` from the `cantus` package.

## [0.2.1] - 2026-05-17

PATCH release that completes the v0.2.0 multi-provider scope. v0.2.0 shipped
OpenAI + Anthropic; this release adds Google Gemini, Groq, and NVIDIA NIM
direct-connect adapters. The dual-tier `ChatModel` Protocol, `ChatModelAsHandle`
bridge, `load_chat_model` factory, and Environment profiles from v0.2.0 are
**unchanged** — this is purely additive.

### Added

- **`GoogleChatModel` adapter** (`cantus.model.providers.google`) — direct
  adapter against the `google-genai` SDK (`from google import genai`,
  `client.models.generate_content`). Resolves API key from explicit
  `api_key=` kwarg then `GOOGLE_API_KEY` env var; raises `MissingAPIKeyError`
  when both are absent. Extracts system messages as the top-level
  `system_instruction=` kwarg via `to_google_messages`. Translates
  `assistant` → Gemini `model` and `tool` → Gemini `function` with
  `function_response` parts.
- **`GroqChatModel` adapter** (`cantus.model.providers.groq`) — direct adapter
  against the `groq` SDK's Chat Completions endpoint. Reuses the existing
  `to_openai_messages` / `from_openai_response` pure functions (Groq is
  OpenAI-compatible at the wire layer). Resolves `GROQ_API_KEY` from env.
- **`NvidiaChatModel` adapter** (`cantus.model.providers.nvidia`) — thin
  subclass of `OpenAIChatModel` that hard-codes
  `base_url="https://integrate.api.nvidia.com/v1"` and reads `NVIDIA_API_KEY`.
  All `chat` / `stream` / translator behavior is inherited unchanged.
- **`to_google_messages` / `from_google_response` translators**
  (`cantus.model.providers._translate`) — pure functions for Gemini's
  `contents` / `parts` wire shape. Maps Gemini `STOP` / `MAX_TOKENS` /
  `SAFETY` / `TOOL_CALL` finish reasons to cantus stop reasons.
- **`google` and `groq` optional extras** in `pyproject.toml` with pinned
  upper bounds: `google = ["google-genai>=0.3,<1"]`,
  `groq = ["groq>=0.11,<1"]`. The `providers` aggregator now installs all
  four primary adapters (`cantus[openai,anthropic,google,groq]`).
- **`scripts/audit_cassettes.sh`** — secret-pattern scan for provider VCR
  cassettes; extends the cantus-distribution Pre-push security audit
  (Authorization / Bearer / `x-api-key` / `x-goog-api-key` / `sk-` / `hf_` /
  `ghp_` / `AIza` / `AKIA` patterns). Closes the v0.2.0 follow-up to bring
  cassette paths into the pre-push security gate.
- **`notebooks/multi_provider_smoke_batch2.ipynb`** — release-time human
  smoke for Google / Groq / NVIDIA (chat + stream each).

### Changed

- `load_chat_model` factory `_REGISTRY` extended from two to five providers
  (`openai`, `anthropic`, `google`, `groq`, `nvidia`). Unknown-prefix
  `ValueError` now lists all five supported prefixes.
- `load_chat_model("nvidia/...")` missing-extras hint points at
  `pip install cantus[openai]` (the OpenAI SDK is the actual runtime
  dependency), **not** a phantom `cantus[nvidia]` group.
- `cantus.__version__` bumped from `0.2.0` to `0.2.1`.
- `README.md` and `README.zhTW.md` "Multi-provider quickstart" sections gain
  Google, Groq, and NVIDIA quickstart code blocks (byte-identical between
  language variants, matching the v0.2.0 contract).

### Notes

- **NVIDIA NIM ships through `cantus[openai]`**, by design. NIM's endpoint
  is OpenAI Chat Completions-compatible (`base_url=...`), so the adapter is
  a thin subclass of `OpenAIChatModel`. Opening a dedicated `cantus[nvidia]`
  extras would mislead users into installing a phantom `nvidia` SDK package.
- **Google adapter uses the new `google-genai` SDK**, not the legacy
  `google-generativeai`. Import path is `from google import genai`. The two
  SDKs share the `google.*` namespace but expose different APIs
  (`client.models.generate_content` vs. `GenerativeModel(...).generate_content`).
  The legacy SDK is intentionally unsupported — silently falling back would
  surface as an obscure `AttributeError` rather than a clear `ImportError`.
- **Groq SDK pin `groq>=0.11,<1`** acknowledges Groq's tool-use schema
  churn during 2025–2026. Re-record cassettes when bumping the upper bound.
- **LiteLLM is still not a dependency** at any layer (v0.2.0 decision —
  「不引入 LiteLLM」— driven by the 2026-03 LiteLLM 1.82.7/1.82.8
  supply-chain incident). Direct adapters keep the supply-chain surface
  auditable per provider.
- **`google-generativeai` is still not a dependency** at any layer
  (intentional, see Google adapter note above).
- **No `[nvidia]` extras** — `pip install cantus[nvidia]` is intentionally
  unresolvable so users hit a clear pip error rather than a misleading
  installation path; README and the factory's missing-extras hint both
  direct users to `cantus[openai]`.

## [0.2.0] - 2026-05-17

First framework-化 minor release. Introduces the **dual-tier API** (ARCH-1)
that the discussion `openspec/discussions/cantus-framework-shift.md` froze on
2026-05-17 as the design principle for all v0.2+ work. v0.1.x notebooks and
the existing `mount_drive_and_load()` entry point remain **100% behavior- and
signature-compatible** — no `DeprecationWarning` is emitted in v0.2.0.

### Added

- **Tier 2 `ChatModel` Protocol** (`cantus.model.chat`) — chat-style
  multi-provider interface with `chat(messages, tools=None) -> ChatResponse`
  and `stream(messages, tools=None) -> Iterator[str]`. Three companion
  dataclasses: `Message` (role + content + tool_calls), `ToolCall` (id, name,
  parsed-JSON arguments), and `ChatResponse` (message + stop_reason + usage +
  provider-native `raw` escape hatch). Re-exported at top-level `cantus`.
- **`ChatModelAsHandle` bridge** (`cantus.model.bridge`) — wraps a Tier 2
  `ChatModel` so it satisfies the existing Tier 1 `ModelHandle` Protocol,
  letting any `Agent` consume a cloud provider without a single line of
  Agent change.
- **`load_chat_model("provider/model_id")` factory** (`cantus.model.factory`)
  — lazy-import dispatch with friendly missing-extras errors of the form
  `pip install cantus[openai]`. v0.2.0 accepts the `openai` and `anthropic`
  prefixes; unknown prefixes raise `ValueError` naming the supported set.
- **`OpenAIChatModel` adapter** (`cantus.model.providers.openai`) — direct
  adapter against the `openai` SDK's Chat Completions API (not the Responses
  API; revisit in v0.3.x). Accepts `base_url` from day one so v0.2.1 NVIDIA
  NIM can reuse it without an API change. Resolves API key from explicit
  `api_key=` kwarg then `OPENAI_API_KEY` env var; raises `MissingAPIKeyError`
  with a Chinese guidance message when both are absent.
- **`AnthropicChatModel` adapter** (`cantus.model.providers.anthropic`) —
  direct adapter against the `anthropic` SDK's Messages API. Correctly
  extracts system messages from the `messages` list and passes them as the
  top-level `system=` kwarg. Same auth resolution + `MissingAPIKeyError`
  shape as the OpenAI adapter, against `ANTHROPIC_API_KEY`.
- **Environment profile module** (`cantus.env`) with three classes:
  `ColabEnvironment` (mounts Drive when in Colab, then loads locally with
  4-bit quantization — equivalent to the legacy `mount_drive_and_load`),
  `LocalEnvironment` (same load path, never mounts Drive), and
  `CloudOnlyEnvironment` (refuses to load locally; redirects callers to
  `load_chat_model('provider/...')` and verifiably does NOT import
  transformers / bitsandbytes / torch).
- **Three new optional-dependency groups** in `pyproject.toml`:
  `openai` (`openai>=1.50,<2`), `anthropic` (`anthropic>=0.40,<1`), and
  `providers` (aggregator pulling both). The `dev` group gains
  `pytest-recording>=0.13` and `respx>=0.21`.
- **ARCH-2 integration smoke test** (`tests/test_integration_smoke.py`)
  proves that `import cantus` does NOT transitively load `openai` or
  `anthropic`, and that the SDK only loads on first `_get_client()` call —
  protecting the Tier 1 teaching path from cloud-SDK import cost.
- **Multi-provider quickstart README section** in both `README.md` and
  `README.zhTW.md`, with byte-identical OpenAI + Anthropic code blocks.
  v0.1.x Gemma quickstart preserved unchanged above it.
- **Manual smoke notebook** `notebooks/multi_provider_smoke.ipynb` that the
  release manager runs by hand against real provider endpoints before
  tagging v0.2.0 (one cell each for OpenAI / Anthropic chat + stream + a
  bridge round-trip through `Agent`).

### Changed

- **`mount_drive_and_load()`** internally refactored to a thin delegate of
  `ColabEnvironment().prepare_model(...)`. Signature, return type, exception
  types (`ValueError`, `MountError`, `ModelNotFoundError`), Chinese error
  messages, and `CANTUS_MODEL_ROOT` environment variable resolution are
  byte-for-byte preserved. **No `DeprecationWarning` is emitted** —
  v0.1.x notebooks run unchanged on v0.2.0. The existing
  `tests/test_loader.py` suite passes without a single modification.
- **`cantus.__init__`** exports the new Tier 2 symbols (`ChatModel`,
  `Message`, `ToolCall`, `ChatResponse`, `ChatModelAsHandle`,
  `load_chat_model`) plus the three Environment profiles. The version
  string is bumped to `0.2.0`. `AgentState` is now also re-exported for
  consistency with `Agent`.

### Notes

- **No LiteLLM at any layer.** The 2026-03 LiteLLM supply-chain compromise
  (malicious code in versions 1.82.7 / 1.82.8) makes adding LiteLLM as
  either a hard or optional dependency a non-trivial governance burden:
  the framework would need to ship its own version-range check, document a
  refusal policy, and educate users on detecting bad versions. v0.2.0
  instead ships direct provider SDK adapters with their own optional
  extras, accepting the trade-off of writing one adapter per provider in
  exchange for a clean supply-chain story. See
  `openspec/discussions/cantus-framework-shift.md` lines 290 and 359–367
  for the framing.
- **ARCH-1 dual-tier API** is now a load-bearing principle. Tier 1
  (`ModelHandle.generate(prompt) -> str`) stays the teaching entrypoint
  because students should be able to plug in any `.generate`-shaped object
  including a 5-line mock. Tier 2 (`ChatModel.chat / stream / tool use`)
  is the industry-aligned surface. The two MUST connect through the
  explicit `ChatModelAsHandle` bridge — `Agent` is **not** taught to
  recognise `ChatModel`, because adding an `isinstance` branch would
  pollute Tier 1 with Tier 2 knowledge.
- **Test strategy: SDK-level mocks, not VCR cassettes (yet).** Provider
  contract tests under `tests/providers/` use `monkeypatch` on the SDK
  client classes rather than recorded HTTP cassettes. CI does not hold any
  real API keys; hand-crafted cassettes were rejected as fragile vs. the
  signal they would carry. The cassette infrastructure (`conftest.py` with
  `filter_headers` for `authorization` / `x-api-key` / `api-key` /
  `x-goog-api-key`, and `record_mode='none'`) IS in place so v0.2.1 can
  record real cassettes when adding Google / Groq / NVIDIA against the
  same gate. **Follow-up for v0.2.1**: when the first real cassettes
  land, extend the cantus-distribution pre-push secret-pattern hook
  (currently `sk-`, `Bearer `, `api_key`, `authorization:`) to cover
  `tests/providers/cassettes/**` paths.
- **Deferred to v0.2.1** (`cantus-multi-provider-di-batch2`): Google
  (`google-genai`, NOT the older `google-generativeai`), Groq, and
  NVIDIA NIM (which is the `openai` SDK pointed at
  `https://integrate.api.nvidia.com/v1` — `OpenAIChatModel.base_url`
  already supports this from day one).
- **Deferred to v0.3.x**: Anthropic content blocks (images, citations,
  thinking) — currently reachable via `ChatResponse.raw`. OpenAI Responses
  API. Tool-call streaming deltas (`stream()` yields text only).
- **Deferred to v0.4.1**: unified secret management via `pydantic-settings`
  (belongs to the `cantus-serve-security` capability — pulling it forward
  would have broken the planned capability ordering).

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
