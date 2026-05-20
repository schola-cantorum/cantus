## ADDED Requirements

### Requirement: Cantus ships PEP 561 py.typed marker and baseline tool configuration

The `schola-cantorum/cantus` distribution SHALL ship a PEP 561 `py.typed` marker file at `cantus/py.typed` so that downstream consumers with strict type checking enabled can resolve cantus public symbols against their declared annotations rather than treating every cantus import as `Any`. The `py.typed` file SHALL be a zero-byte empty file (PEP 561 inline-typed package convention; the `partial\n` content variant SHALL NOT be used because cantus ships its annotations inline rather than via stub packages). The `pyproject.toml` SHALL declare `[tool.setuptools.package-data] cantus = ["py.typed"]` so that the marker is bundled into the wheel produced by `python -m build`.

The `pyproject.toml` SHALL ship a baseline `[tool.mypy]` configuration enabling `python_version = "3.10"`, `warn_unused_ignores = true`, `warn_redundant_casts = true`, and `check_untyped_defs = true`, with `disallow_untyped_defs = false` (cantus SHALL NOT enforce strict typing on its own code in this version — strict mode is deferred to a later release). The configuration SHALL declare `[[tool.mypy.overrides]]` entries setting `ignore_missing_imports = true` for the optional-extras adapter SDK modules (`mcp.*`, `langchain_core.*`, `dspy.*`, `transformers.*`, `openhands.*`, `anthropic.*`, `openai.*`, `google.genai.*`, `groq.*`) so that running `mypy cantus` in a base install (without optional extras) SHALL NOT fail on the lazy-import shims declared in `cantus.adapters`.

The `pyproject.toml` SHALL ship a baseline `[tool.coverage.run]` configuration with `source = ["cantus"]` and `branch = true`, a `[tool.coverage.report]` configuration with `show_missing = true` and `exclude_lines` including at least `"pragma: no cover"` and `"if TYPE_CHECKING:"`, and the `[tool.pytest.ini_options].addopts` string SHALL contain both the substring `"--cov=cantus"` and the substring `"--cov-report=term-missing"`. Running `pytest` with no additional flags inside a cantus `cantus[dev]` environment SHALL emit a coverage report section to stdout. The configuration SHALL NOT set a `fail_under` threshold in this version (the threshold is deferred until a baseline is collected over multiple releases).

#### Scenario: py.typed is shipped in the wheel

- **WHEN** a clean Python ≥ 3.10 environment runs `pip install <cantus_wheel>` where the wheel is produced by `python -m build` from a checkout at v0.3.5 or later
- **THEN** the installed `cantus` package directory contains a file `py.typed`
- **AND** `python -c "from importlib.resources import files; print(repr(files('cantus').joinpath('py.typed').read_text()))"` prints `''` (the empty string) without raising
- **AND** a downstream consumer running `mypy --strict` against code that imports cantus symbols sees the cantus public type annotations rather than `Any`

#### Scenario: pyproject ships mypy baseline that lets `mypy cantus` run without import failures

- **WHEN** a developer runs `mypy cantus` inside a cantus `cantus[dev]` install at v0.3.5 or later (without any optional extras installed beyond `dev`)
- **THEN** mypy exits with code 0 or 1 (warnings allowed; mypy SHALL NOT crash or raise a configuration parse error)
- **AND** mypy SHALL NOT emit `error: Cannot find implementation or library stub for module named "mcp"` (or for the other optional-extras adapter SDKs listed in the Requirement) because each is covered by an `ignore_missing_imports` override

#### Scenario: pytest emits coverage output by default

- **WHEN** a developer runs `pytest tests/` inside a cantus `cantus[dev]` install at v0.3.5 or later, with no additional command-line flags
- **THEN** stdout contains a coverage section identifiable by the literal substring `"---------- coverage"` or the column header `"Name              Stmts   Miss"`
- **AND** the report identifies the `cantus` package as the coverage source (the `Name` column lists `cantus/*` paths, not `tests/*` paths)
- **AND** the working directory contains a `coverage.xml` file after the pytest run completes
