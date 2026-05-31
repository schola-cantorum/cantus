# Migrating cantus v0.4.2 → v0.4.3

**Release date: 2026-05-20.** v0.4.3 is a **distribution-lifecycle change with zero code-level migration**, just like v0.4.2 was. The `cantus` Python package, every public symbol, every endpoint, every default value, every extras group (`cantus[serve]` / `cantus[security]` / `cantus[providers]` / `cantus[openhands]`), and every `[tool.uv] conflicts` declaration is byte-identical to v0.4.2. The single change that affects you depends on whether you are an OSS user or a contributor.

## Breaking

None. v0.4.3 is fully ADDITIVE on the repository governance surface. `cantus.__version__` reports `"0.4.3"`; pin assertions that hardcoded `"0.4.2"` need to update — that is the only code-side touch.

## Impact on OSS users — none

If you only consume cantus via `pip install cantus-agent`, nothing changes for you. Your Python code:

```python
import cantus
print(cantus.__version__)  # "0.4.3"

import importlib.metadata
print(importlib.metadata.version("cantus-agent"))  # "0.4.3"
```

continues to work byte-identical. No new dependencies, no removed extras, no renamed modules.

Upgrade command:

```bash
pip install --upgrade cantus-agent==0.4.3
```

## Impact on contributors — specs now live in this repository

v0.4.3 ships a self-hosted Spectra spec tree inside the cantus repository. Before v0.4.3, the canonical capability spec for `cantus-distribution`, `adapter-layer`, `agent-protocols`, `agent-runtime`, `api-docs`, `cantus-i18n-docs`, `identity-protocol`, `memory-protocol`, `model-providers`, and `adapter-layer-batch2` lived only in the upstream `schola-cantorum/colab-llm-agent` repository. Starting at v0.4.3, those ten framework capability specs live in **this repository** under `openspec/specs/`, with the historical change archive (twelve curated entries) under `openspec/changes/archive/`.

### New files / directories

- `openspec/specs/` — ten framework capability `spec.md` files; cantus is now the canonical source for these.
- `openspec/changes/archive/` — twelve historical change archive entries (those whose spec deltas only touch the ten framework capabilities above).
- `.spectra.yaml` — Spectra CLI configuration at the cantus repo root (`locale: tw`, `tdd: true`, `audit: true`, `parallel_tasks: true`, plus eight `claude_effort` per-skill levels).
- `CLAUDE.md` — Spectra workflow instruction block (`<!-- SPECTRA:START v1.0.2 -->` … `<!-- SPECTRA:END -->`) that describes `/spectra-discuss`, `/spectra-propose`, `/spectra-apply`, `/spectra-ingest`, `/spectra-ask`, `/spectra-archive`, `/spectra-commit`.
- `AGENTS.md` gains a new `## Spectra Workflow` section appended after the existing wiki-profile sections; the YAML frontmatter and the `## Schema` / `## Ingest` / `## Query` / `## Lint` sections are preserved byte-identical to v0.4.2.

### Transition window (v0.4.3 → Phase 5)

The upstream `schola-cantorum/colab-llm-agent` repository retains identical copies of the ten framework spec files during the transition window between v0.4.3 and the future `colab-llm-agent-shed-framework-specs-and-align-to-pypi` change archive. **During this window, the cantus repository copies are the authoritative source.** If you spot a divergence between the two, treat the `colab-llm-agent` copies as stale.

Any new spec change that touches one of the ten framework capabilities SHOULD be proposed inside this cantus repository (via `spectra propose <change-name>` at the cantus root), not in `colab-llm-agent`.

### Course-only capabilities stay upstream

The three course-oriented capabilities — `task-template`, `model-loader`, `llm-wiki` — remain in `colab-llm-agent` only. They are part of the course curriculum, not the cantus framework, and their archive history references files that do not exist in this cantus repository.

## No breaking change to anything else

- `cantus.serve`, `cantus.config`, `cantus.serve.security`, `cantus.adapters`, `cantus.workflows`, `cantus.hooks`, and every other module preserve their v0.4.2 public API surface byte-identical.
- `Registry.KINDS`, the ten exposed callables in `cantus.adapters`, and the five `cantus.workflows` building blocks are unchanged.
- The `[tool.uv] conflicts` declaration with its six pairwise entries is unchanged.
- The `cantus[openhands]` extras `python_version >= "3.12" and python_version < "3.13"` marker is unchanged.
- The OIDC release pipeline (`.github/workflows/release.yml`) and the CI matrix (`.github/workflows/test.yml`) shipped at v0.4.2 are unchanged.

## Why ship spec self-hosting as a PATCH release?

v0.4.3 follows the same distribution-lifecycle PATCH classification as v0.4.2: the change is entirely on the repository governance surface (specs, configuration files, documentation), with no runtime API addition or modification. MINOR (`0.5.0`) is reserved for the next runtime capability arc.

## Cross-platform runtime extras 行為變更（v0.4.3 新增）

A0 跨平台桌面 runtime change（`cantus-uv-cross-platform-install`）在 `pyproject.toml` 的 `[project.optional-dependencies].runtime` 條目給 `bitsandbytes>=0.43.0` 加上 PEP 508 marker `sys_platform == 'linux'`。三 OS 上 `uv pip install cantus-agent[runtime]` 的觀察結果如下：

- **macOS Intel（x86_64）**：v0.4.2 上 install abort（bnb 無 `macosx_*_x86_64` wheel）；v0.4.3 上 install 成功，resolved set 不含 `bitsandbytes`。**這是改善**。
- **macOS arm64（Apple Silicon, macOS ≥14.0）/ Windows x86_64**：v0.4.2 上 install 成功且 resolved set 含 `bitsandbytes` 0.49.x（即便 4-bit 量化 kernel 只有 CUDA backend，這兩平台 runtime non-functional）；v0.4.3 上 resolved set 不再含 `bitsandbytes`。這移除了一個非可用的 native dependency；對曾把 bnb 當作「可 import 型別 stub」的下游程式碼是 silent breaking——若有此需求，請顯式 `pip install bitsandbytes`。
- **Linux x86_64 / aarch64**：行為與 v0.4.2 byte-identical，resolved set 仍含 `bitsandbytes` 0.49.x，4-bit Gemma 量化路徑不變。

### 給 macOS / Windows 學生的指引

cantus 4-bit local Gemma 量化路徑在 v0.4.3 仍只支援 Linux + CUDA。macOS / Windows 桌面學生請改用 API key 路徑（`load_chat_model("openai/gpt-4o-mini")` 或其他 provider），詳見新增的 [`docs/quickstart-desktop.md`](docs/quickstart-desktop.md)。`LocalEnvironment.prepare_model(...)` 在 macOS / Windows 仍會在 `import bitsandbytes` 階段拋 `RuntimeError`（v0.4.2 既有訊息維持不變）；後續 A1 `cantus-local-llm-ollama-bridge` change ship 後，錯誤訊息會改為指引到 Ollama bridge。

### CI tri-platform install smoke

v0.4.3 新增 `.github/workflows/cross-platform-install.yml`，在 push 到 `main` 與 release tag `v*.*.*` 時跑 `ubuntu-latest` / `macos-latest` / `windows-latest` 三 OS 的 install smoke matrix（含 `cantus-agent`、`cantus-agent[serve,openai]`、`cantus-agent[runtime]` 安裝與 import smoke）。`scripts/smoke_install.sh` 提供本機可重現的同步腳本。三 OS smoke 任一 OS 失敗即阻擋 PyPI release tag。
