## Why

剛 ship 的 `cantus-local-llm-mlx-path` 走的是 **in-process** 路線（mlx-lm、`mlx/` 前綴、`supports_tool_use=False`），無法做 tool/function calling。Apple Silicon 上另有一類 **OpenAI-compatible 本機伺服器**（`omlx`、`mlx-omni-server`），以獨立行程提供 `/v1` wire。整合它們可比照既有的 Ollama／NVIDIA 薄 adapter 慣例——**零新 pip 依賴**（沿用既有 `openai` SDK），而且 **支援 function calling**（`supports_tool_use=True`）。這個 `tool_use=True` 正是本路線與 in-process 路線並存的關鍵理由：學生想在 Mac 上跑全本機、又要工具呼叫時，有一條可走的路。

## What Changes

1. 新增 `OmlxChatModel`（`cantus/model/providers/omlx.py`）——`OpenAIChatModel` 的薄子類，比照 `OllamaChatModel`，指向本機 OpenAI-compatible MLX 伺服器。
2. **`base_url` 為必填、不內建預設 port**：omlx 預設 `:8000/v1`、mlx-omni-server 預設 `:10240/v1` 兩者並存，挑一個當預設都會誤導；缺 `base_url` 時以清楚錯誤訊息同時點名兩個範例 endpoint。
3. `api_key` 採 sentinel（這類伺服器不驗證），不讀任何環境變數；明確傳入的 `api_key=` 仍保留（供 auth-proxy 前置情境）。
4. `supports_tool_use=True`（繼承自 `OpenAIChatModel`、**不**在子類覆寫）——與 in-process mlx-path 的 `False` 形成對比，是本 change 的核心差異。
5. `chat()`／`stream()` 覆寫：捕捉 `openai.APIConnectionError`、改拋 `ConnectionError`，訊息點名 `base_url` 與「請先啟動 omlx／mlx-omni-server」（比照 `OllamaChatModel`），避免學生看到原始 httpx stack trace。
6. factory 接受 `omlx` 前綴（連同既有共 **八** 個 provider）；`omlx` 缺套件時提示 `pip install cantus[openai]`（同 nvidia/ollama，**不是** phantom `cantus[omlx]`）。
7. `pyproject.toml` 新增 `omlx` documentary extras 別名（解析為 `cantus-agent[openai]`、零新第三方套件），並新增一條 `omlx`↔`openhands` `[tool.uv]` conflict（比照既有 `ollama` 條目）。
8. `docs/quickstart-desktop.md` 在 MLX 段之後新增「Local LLMs via omlx (MLX server)」段落。

## Non-Goals

Non-Goals 收錄於 design.md 的 Goals/Non-Goals 段。

## Capabilities

### New Capabilities

- `cantus-local-llm-omlx-server`: `OmlxChatModel` adapter 契約（薄 `OpenAIChatModel` 子類、`base_url` 必填且缺值報錯、sentinel `api_key`、`supports_tool_use=True` 繼承、伺服器不可達時的 `ConnectionError` 行為）、`omlx` documentary extras 別名與其 `omlx`↔`openhands` conflict、`docs/quickstart-desktop.md` 的 omlx 段落契約。

### Modified Capabilities

- `model-providers`: MODIFY Requirement *"load_chat_model factory dispatches by provider prefix with lazy import"* —— 接受的 provider prefix 加入 `omlx`（共八個）；`omlx` 缺套件時提示 `pip install cantus[openai]`（比照 nvidia/ollama，非自有 extras 閉包）；dispatch table 新增 omlx 列；factory docstring 計數由 seven 改為 eight。

## Impact

- Affected specs:
  - 新增 `openspec/specs/cantus-local-llm-omlx-server/spec.md`（delta 收在 `openspec/changes/cantus-local-llm-omlx-server/specs/cantus-local-llm-omlx-server/spec.md`）
  - 修改 `openspec/specs/model-providers/spec.md`（delta 收在 `openspec/changes/cantus-local-llm-omlx-server/specs/model-providers/spec.md`）
- Affected code（apply 階段才動，本 change 只記錄）:
  - New:
    - `cantus/model/providers/omlx.py`（OmlxChatModel adapter）
    - `tests/providers/test_omlx_adapter.py`（adapter 契約測試，假造 openai client、不連真實伺服器）
  - Modified:
    - `cantus/model/factory.py`（`_REGISTRY` + `_EXTRAS_HINT` 加 omlx；module docstring 由 seven 更新為 eight）
    - `pyproject.toml`（新增 `omlx` documentary extras 別名 + `omlx`↔`openhands` conflict）
    - `docs/quickstart-desktop.md`（新增 omlx 段，置於 MLX 段之後）
    - `tests/test_factory.py`（omlx registry / extras-hint 指向 openai / 不支援前綴訊息含 omlx 的斷言）
    - `tests/test_pyproject_extras_conflicts.py`（omlx 別名解析 + omlx↔openhands conflict 斷言）
- Dependencies: **零新第三方套件**。`omlx` extras 為 documentary 別名，解析為 `cantus-agent[openai]`（同 `ollama` 慣例）。
- CI: **不**改 `.github/workflows/test.yml`——`omlx` adapter 跑在既有 `openai` extra 上，CI 已安裝；無新 extra 需要加 install line。
- 型別: 不新增 `[[tool.mypy.overrides]]`（`openai.*` 既有覆寫已涵蓋）。
- 版本影響: 本 change 不動 `pyproject.toml` 的 `version =`、`CHANGELOG.md`、`MIGRATION`（release 階段才動）；新增 `omlx` extras 別名屬功能本身，非版本 bump。
