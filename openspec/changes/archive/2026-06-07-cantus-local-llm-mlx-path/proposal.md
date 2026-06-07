## Why

cantus 目前的本地 LLM 路徑只有 Ollama（`cantus-local-llm-and-desktop-walkthrough`），但 Ollama 在 Apple Silicon 上是透過 llama.cpp 後端，並非 Apple 原生最佳化。MLX（`mlx-lm`）是 Apple 針對 M 系列晶片的原生推論框架，在 Mac 上載入快、記憶體佔用低、吞吐更好。本專案的教學情境有相當比例使用者持 Apple Silicon Mac，提供 MLX 路徑可讓他們在無網路、零雲端成本下取得更順的本地推論體驗。此為 Era 3 / v1.0 roadmap 的 Tier 2（A2）項目，屬 v1.0 強化、**不擋** v1.0 發佈。

## What Changes

- 新增第二條本地 LLM provider 路徑 `MLXChatModel`（provider prefix `mlx`），與既有 Ollama 平行。使用者以 `load_chat_model("mlx/<hf-or-mlx-model-id>")` 取得實例。
- `MLXChatModel` **直接實作** Tier-2 `ChatModel` Protocol（`cantus.model.chat.ChatModel`），**不**繼承 `OpenAIChatModel`——mlx-lm 並非 OpenAI-compatible，而是以 `mlx_lm.load` 載入模型、`mlx_lm.generate` / `mlx_lm.stream_generate` 生成，prompt 透過 tokenizer 的 chat template 由 `Message` list 組出。
- **首版 `supports_tool_use = False`**：mlx-lm 無原生結構化 tool-call 輸出。當 caller 傳入非空 `tools` 時，`chat()` / `stream()` SHALL 明確報錯（不靜默忽略）。prompt-templated tool-call 解析留待後續 change。
- `model-providers` 的 factory dispatch 契約擴充：`load_chat_model` 接受的 provider prefix 由六個增為七個（加 `mlx`）；`mlx` 擁有**自己的** extras 依賴閉包（不同於 `nvidia` / `ollama` 指向 `openai`），缺套件時 ImportError 提示 `pip install cantus[mlx]`。
- `pyproject.toml` 新增 `mlx` optional-dependency extras group，以平台 marker 鎖定 Apple Silicon：`mlx-lm` 僅在 `sys_platform == 'darwin' and platform_machine == 'arm64'` 安裝（比照既有 `bitsandbytes; sys_platform == 'linux'`）。**另需**一條 `mlx`↔`huggingface` 的 `[tool.uv] conflicts` 條目：`mlx-lm>=0.31.1` 依賴 `transformers>=5`，與 `cantus[huggingface]` 的 `transformers>=4.40,<5` 在同一 Apple-Silicon split 互斥，平台 marker 無法隔離（bitsandbytes 先例不拉衝突的 transitive 依賴，故當時不需）。除此之外**不**新增任何提及 `mlx` 的 conflicts。
- 非 Apple-Silicon 平台或未安裝 mlx-lm 時，`MLXChatModel` 路徑 SHALL 拋出可行動的 `ImportError`（提示 `pip install cantus[mlx]`，並在非 arm64 平台額外標明 MLX 僅支援 Apple Silicon）。
- `docs/quickstart-desktop.md` 新增 `## Local LLMs via MLX (Apple Silicon)` 段，仿既有 Ollama 段格式。
- **無 BREAKING change**：純新增一個 provider 與一個 extras group；既有六個 provider、Ollama 路徑、所有現有測試行為不變。

## Non-Goals

- 留待 design.md 的 Goals / Non-Goals 段記錄（tool-use 解析、macOS arm64 CI job、模型下載自動化等排除項）。

## Capabilities

### New Capabilities

- `cantus-local-llm-mlx-path`: MLXChatModel 適配器契約（直接實作 ChatModel Protocol、Apple-Silicon 平台 gating、supports_tool_use=False 與 tools 報錯行為）、`mlx` 平台-marker extras group、quickstart-desktop.md 的 MLX 段落契約。

### Modified Capabilities

- `model-providers`: MODIFY Requirement *"load_chat_model factory dispatches by provider prefix with lazy import"* —— 接受的 provider prefix 加入 `mlx`（共七個）；`mlx` 缺套件時提示其自有 extras group `pip install cantus[mlx]`（不同於 nvidia/ollama 指向 openai）；dispatch table 新增 mlx 列。

## Impact

- Affected specs:
  - 新增 `openspec/specs/cantus-local-llm-mlx-path/spec.md`（delta 收在 `openspec/changes/cantus-local-llm-mlx-path/specs/cantus-local-llm-mlx-path/spec.md`）
  - 修改 `openspec/specs/model-providers/spec.md`（delta 收在 `openspec/changes/cantus-local-llm-mlx-path/specs/model-providers/spec.md`）
- Affected code（apply 階段才動，本 change 只記錄）:
  - New:
    - `cantus/model/providers/mlx.py`（MLXChatModel 適配器）
    - `tests/providers/test_mlx_adapter.py`（適配器契約測試，無真實模型載入）
    - `tests/integration/test_mlx_smoke.py`（`pytest.importorskip("mlx_lm")` smoke）
  - Modified:
    - `cantus/model/factory.py`（`_REGISTRY` + `_EXTRAS_HINT` 加 mlx；module docstring 由「six providers」更新為「seven」）
    - `pyproject.toml`（新增 `mlx` extras group，平台 marker）
    - `docs/quickstart-desktop.md`（新增 MLX 段）
    - `tests/test_factory.py`（mlx registry / extras-hint / 不支援前綴訊息含 mlx 的斷言）
- Dependencies: 新增 `mlx-lm`（僅 darwin/arm64）；新增一條 `mlx`↔`huggingface` `[tool.uv] conflicts`（mlx-lm 拉 `transformers>=5` vs huggingface `transformers<5`）。
- CI: **不**將 `mlx` 加入 `.github/workflows/test.yml` 的 install line（Linux/x86 runner 裝不起來）；MLX 測試以 `importorskip` 在非 arm64 自動 skip。macOS arm64 CI job 列為 Non-Goal（後續）。
- 版本影響: 本 change 不動 `pyproject.toml` 的 `version =`、`CHANGELOG.md`、`MIGRATION`（release 階段才動）；新增 `mlx` extras 屬功能本身，非版本 bump。
