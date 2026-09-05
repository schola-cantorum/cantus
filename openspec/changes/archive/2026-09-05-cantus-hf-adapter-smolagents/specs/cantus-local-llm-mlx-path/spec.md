## MODIFIED Requirements

### Requirement: mlx is a platform-scoped extras group for Apple Silicon

The `pyproject.toml` `[project.optional-dependencies]` section SHALL declare a key named `mlx` whose value is a list containing exactly one entry for the `mlx-lm` distribution, constrained by the PEP 508 environment marker `sys_platform == 'darwin' and platform_machine == 'arm64'`. The `mlx-lm` entry SHALL pin a lower bound and an upper bound (form `mlx-lm>=X,<Y`) rather than an unbounded requirement. The framework SHALL NOT declare any `[tool.uv] conflicts` entry that names the `mlx` extras group: since the `huggingface` extras group depends on `smolagents` rather than on `transformers`, no other extras group pins `transformers` below the `>=5` floor that `mlx-lm>=0.31.1` requires, so `mlx` and `huggingface` resolve together on the Apple-Silicon resolution split without a conflict declaration. Conflict entries that do not name `mlx` (for example the `openhands` cluster) are outside this Requirement and SHALL remain governed by their own Requirements.

#### Scenario: mlx extras declares only platform-scoped mlx-lm

- **WHEN** a reader parses `pyproject.toml` `[project.optional-dependencies].mlx`
- **THEN** the list SHALL contain exactly one requirement string whose distribution name is `mlx-lm`
- **AND** that requirement string SHALL contain the marker substring `platform_machine == 'arm64'`
- **AND** that requirement string SHALL contain the marker substring `sys_platform == 'darwin'`

#### Scenario: mlx has no conflicts entry

- **WHEN** a reader parses the `[tool.uv]` `conflicts` table in `pyproject.toml` (treating an absent table as an empty list)
- **THEN** no conflict cluster SHALL contain an entry whose `extra` value is `mlx`

#### Scenario: mlx and huggingface extras resolve together on Apple Silicon

- **WHEN** a user on macOS arm64 runs `uv pip compile --extra mlx --extra huggingface pyproject.toml`
- **THEN** resolution SHALL succeed
- **AND** the resolved set SHALL contain `mlx-lm`, `smolagents`, and a `transformers` version satisfying `>=5`
