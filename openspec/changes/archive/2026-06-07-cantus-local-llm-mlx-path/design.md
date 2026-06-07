## Context

cantus 的 Tier-2 多 provider 介面是 `cantus.model.chat.ChatModel`（runtime_checkable Protocol，含 `supports_tool_use: bool`、`model_id: str`、`chat(messages, tools=None, **kwargs) -> ChatResponse`、`stream(...) -> Iterator[str]`）。現有六個 provider（openai/anthropic/google/groq/nvidia/ollama）全是 OpenAI Chat Completions 形狀——五個直接走 openai SDK，nvidia/ollama 是 `OpenAIChatModel` 子類指向 OpenAI-compatible endpoint。

MLX（`mlx-lm`）**不是** OpenAI-compatible：它以 `mlx_lm.load(model_id) -> (model, tokenizer)` 載入本地權重，再以 `mlx_lm.generate(model, tokenizer, prompt, ...)` / `mlx_lm.stream_generate(...)` 生成純文字。沒有 chat-completions endpoint、沒有結構化 tool-call 輸出、沒有 API key 概念。因此無法沿用 `OpenAIChatModel` 的繼承路線，必須直接實作 ChatModel Protocol。

MLX 僅在 Apple Silicon（macOS arm64）可用，與既有 `bitsandbytes; sys_platform == 'linux'` 同屬「平台限定依賴」。

## Goals / Non-Goals

### Goals
- 提供 `MLXChatModel`，讓 Apple Silicon 使用者以 `load_chat_model("mlx/<model-id>")` 取得可用的本地 chat 模型。
- 以平台 marker 安全打包 `mlx-lm`，使非 arm64 環境 `pip install cantus[mlx]` 不致失敗（解析為空），且 import 失敗時給可行動訊息。
- 與既有 provider 體驗一致：同一個 `load_chat_model` 入口、同一個 `ChatResponse` 形狀、同樣的 lazy-import / 缺套件 ImportError 慣例。

### Non-Goals
- **Tool use / function calling**：首版 `supports_tool_use = False`。mlx-lm 無原生結構化 tool-call，prompt-templated 解析留待後續 change。
- **tool-call streaming**：沿用 ChatModel 既有設計（`stream` 僅 yield 文字 delta）。
- **macOS arm64 CI job**：本 change 不新增 CI runner；MLX 測試以 `importorskip` 在非 arm64 自動 skip。專屬 arm64 CI 留待後續。
- **模型下載 / 量化自動化**：使用者自備 HF/MLX model id；不代管權重下載。
- **修改既有六個 provider 或 Ollama 路徑**。

## Decisions

### D1：直接實作 ChatModel
mlx-lm 的 API 與 OpenAI Chat Completions 無交集（無 client、無 endpoint、無 tool schema），繼承只會帶進不適用的 api_key/base_url 語意。直接實作 Protocol 的四個成員最乾淨。
- **替代方案**：包一層 OpenAI-compatible local server（如 `mlx_lm.server`）再用 OpenAIChatModel 指過去 → 否決：多一個常駐 server 行程、與「零設定本地推論」訴求相悖、且把 Ollama 已涵蓋的形狀再做一次。

### D2：tokenizer chat template
`chat(messages, ...)` 把 `list[Message]` 轉成 mlx-lm tokenizer 的 `apply_chat_template(conversation, add_generation_prompt=True)` 輸入（role/content 對應），交給 `generate`。回傳組成 `ChatResponse(message=Message(role="assistant", content=<text>), stop_reason="end_turn", usage=None, raw=<mlx 原始輸出>)`。`stream` 以 `stream_generate` yield 文字 delta。
- **替代方案**：手刻各模型的 prompt 格式 → 否決：tokenizer 已內建正確 template，手刻易錯且不可攜。

### D3：tools 報錯
`chat()` / `stream()` 收到非 None 且非空的 `tools` 時，SHALL 拋 `NotImplementedError`，訊息含 `MLXChatModel does not support tool use`。不靜默忽略——避免 agent loop 以為工具可用卻得不到 tool_call 而靜默退化。
- **替代方案**：靜默忽略 tools → 否決：對 agent harness 是隱性失敗，違反「fail loud」。

### D4：平台 gating
`cantus/model/providers/mlx.py` 在模組層 `try: import mlx_lm except ImportError` 後，於建構或 import 時拋出可行動 `ImportError`：訊息 SHALL 含 `pip install cantus[mlx]`；當 `sys.platform != "darwin"` 或 `platform.machine() != "arm64"` 時，訊息 SHALL 另含表明「MLX 僅支援 Apple Silicon (macOS arm64)」的子字串。factory 的 lazy-import 會把此 ImportError 以 `from exc` 串接（factory 自身 generic 訊息 `pip install cantus[mlx]` 為外層、平台訊息保留在 `__cause__`）。
- **替代方案**：在 factory 特例化 mlx 訊息 → 否決：factory 對所有 provider 一致處理較好維護；平台 nuance 由 adapter 自負並經由 `__cause__` 鏈保留。

### D5：mlx extras
`pyproject.toml` `[project.optional-dependencies]` 新增 `mlx = ["mlx-lm>=<pin>; sys_platform == 'darwin' and platform_machine == 'arm64'"]`。平台 marker 使 uv/pip 在非 arm64 解析為空集合。`_EXTRAS_HINT["mlx"] = "mlx"`（自有閉包，非指向 openai）。
- pin 下限於 apply 時以當時 `mlx-lm` 最新穩定版定錨（apply 階段定為 `mlx-lm>=0.31,<1`，0.31.3 為最新），採 `>=X,<Y` 區間避免無上限漂移。
- **需一條 `mlx`↔`huggingface` `[tool.uv] conflicts`**（apply 階段實測修正）：bitsandbytes 先例不需 conflicts 是因為它不拉衝突的 transitive 依賴；但 `mlx-lm>=0.31.1` 依賴 `transformers>=5`（0.31.0 已 yank），而 `cantus[huggingface]` pin `transformers>=4.40,<5`。兩個 extras 可在同一 arm64/darwin split 同時被要求，平台 marker 無法隔離 → uv universal resolution 失敗（`cantus[mlx]` 與 `cantus[huggingface]` incompatible）。解法比照既有 `google`↔`openhands` websockets 衝突：加 `[{ extra = "mlx" }, { extra = "huggingface" }]`。pip 不做 universal resolution、忽略 `[tool.uv]`，故 pip 使用者不受影響。除 huggingface 外不需其他 mlx conflicts（runtime 的 `transformers>=4.53.0` 無上界、相容 5.x）。

## Implementation Contract

- **新類別 `MLXChatModel`（`cantus/model/providers/mlx.py`）**
  - 建構子：`MLXChatModel(model_id: str, **kwargs)`。`model_id` 為 HF/MLX 模型路徑（如 `"mlx-community/Mistral-7B-Instruct-v0.3-4bit"`）。設 `self.model_id = model_id`、`self.supports_tool_use = False`。模型/ tokenizer 採 lazy load（首次 `chat`/`stream` 才 `mlx_lm.load`），避免建構即重 I/O。
  - `chat(messages, tools=None, **kwargs) -> ChatResponse`：tools 非空 → 拋 `NotImplementedError`（含 `MLXChatModel does not support tool use`）。否則以 tokenizer chat template 組 prompt、`mlx_lm.generate` 產文字，回傳 `ChatResponse(message=Message(role="assistant", content=text), stop_reason="end_turn")`。
  - `stream(messages, tools=None, **kwargs) -> Iterator[str]`：tools 非空 → 同上報錯；否則 `mlx_lm.stream_generate` yield 文字 delta。
  - 模組 import 守衛：mlx_lm 不可用時拋 `ImportError`，訊息含 `pip install cantus[mlx]`；非 arm64/非 darwin 另含 Apple-Silicon-only 子字串。
  - `isinstance(MLXChatModel(...), ChatModel)` 為真（滿足 runtime_checkable Protocol）。
- **factory（`cantus/model/factory.py`）**：`_REGISTRY["mlx"] = ("cantus.model.providers.mlx", "MLXChatModel")`；`_EXTRAS_HINT["mlx"] = "mlx"`；module docstring「six providers」→「seven providers」。`load_chat_model("mlx/<id>")` 解析 MLXChatModel；未支援前綴的 ValueError 訊息會自動含 `mlx`（因 sorted(_REGISTRY)）。
- **extras（`pyproject.toml`）**：新增 `mlx` group（平台 marker）；不新增 conflicts。
- **docs（`docs/quickstart-desktop.md`）**：新增 `## Local LLMs via MLX (Apple Silicon)` 段，含 `load_chat_model("mlx/` 的 Python 範例、`pip install cantus[mlx]`、明示僅支援 Apple Silicon、明示首版不支援 tool use。
- **驗收**：
  - `tests/providers/test_mlx_adapter.py`：以 monkeypatch 假造 `mlx_lm.load`/`generate`/`stream_generate`，斷言（a）ChatModel 介面滿足、（b）`supports_tool_use is False`、（c）傳入 tools 拋 NotImplementedError、（d）chat 回 ChatResponse 且 content 為生成文字、（e）平台/缺套件 ImportError 訊息含必要子字串。
  - `tests/test_factory.py`：`_REGISTRY["mlx"]`、`_EXTRAS_HINT["mlx"] == "mlx"`、未知前綴 ValueError 含 `mlx`、缺 mlx extras 的 ImportError 含 `pip install cantus[mlx]`。
  - `tests/integration/test_mlx_smoke.py`：`pytest.importorskip("mlx_lm")` 後做最小載入/生成 smoke（非 arm64 自動 skip）。
  - 全綠：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/ -q`（mlx 未裝 → smoke skip）；`ruff check` / `mypy` 對改動檔 clean。
- **In scope**：mlx provider 類別、factory 註冊、mlx extras、docs 段、上述測試。
- **Out of scope**：tool-use 解析、stream tool-call、CI arm64 job、權重下載、既有 provider 改動、版本欄位。

## Risks / Trade-offs

- [非 arm64 使用者誤裝 `cantus[mlx]` 後仍 import 失敗] → adapter ImportError 明示 Apple-Silicon-only；docs 段標明平台限制。
- [mlx-lm API 在版本間變動（load/generate 簽名）] → extras 採 `>=X,<Y` 區間鎖定；測試以假造模組驗契約，不綁實際 API 細節以外的行為。
- [首版無 tool use 對 agent loop 用途受限] → 明確 fail loud（NotImplementedError）而非靜默退化；roadmap 已將 tool-call 解析列為後續 change。
- [CI 無 arm64 runner → MLX 程式碼路徑未在 CI 跑] → 以 importorskip skip，並在 Non-Goals 記錄；adapter 契約測試用假造模組可在任何平台跑，覆蓋核心邏輯。

## Migration Plan

無資料遷移。純新增能力，向後相容；既有 provider 與 Ollama 路徑不受影響。發佈時併入下一個 release 的 CHANGELOG（release 階段才動版本欄位）。
