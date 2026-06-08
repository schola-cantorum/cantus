## Context

`cantus` 的 Tier 2 provider 介面是 `ChatModel` Protocol（`cantus.model.chat`），由 `load_chat_model("<provider>/<model_id>")` factory 以 prefix 派發、lazy import 適配器模組。既有適配器分兩類：

- **雲端直連**：`OpenAIChatModel`、`AnthropicChatModel`、`GoogleChatModel`、`GroqChatModel`。
- **薄子類（指向 OpenAI-compatible endpoint）**：`NvidiaChatModel`（env 金鑰、預設 NIM base_url）、`OllamaChatModel`（sentinel 金鑰、預設 localhost base_url、`chat`/`stream` 覆寫成友善 `ConnectionError`）。

剛 ship 的 `cantus-local-llm-mlx-path` 另起一條 **in-process** 路線（`MLXChatModel` 直接實作 ChatModel、`mlx/` 前綴、`supports_tool_use=False`、自有 `mlx` extras）。本 change 補上互補的 **OpenAI-compatible 本機伺服器** 路線：Apple Silicon 上的 `omlx`（`jundot/omlx`，預設 `localhost:8000/v1`）與 `mlx-omni-server`（`madroidmaq/mlx-omni-server`，預設 `localhost:10240/v1`）都以獨立行程提供 OpenAI-compatible `/v1` wire 且支援 function calling。整合方式與 `OllamaChatModel` 幾乎同構，因此本 change 是該慣例的再一次套用，而非新架構。

約束：零新 pip 依賴（沿用 `openai` SDK）、不啟動／管理伺服器行程（只做 client adapter）、artifacts 以台灣繁體中文撰寫但 spec `.md` 用英文（normative）。

## Goals / Non-Goals

**Goals:**

- 新增 `OmlxChatModel`（`OpenAIChatModel` 薄子類）使 `load_chat_model("omlx/<model_id>", base_url=...)` 可連本機 OpenAI-compatible MLX 伺服器。
- 對 `omlx` 與 `mlx-omni-server` 兩者皆可用（透過必填 `base_url`，不綁單一產品）。
- 保留 `supports_tool_use=True`（繼承），讓本機路線可做工具呼叫——與 in-process mlx-path 的 `False` 互補。
- 伺服器未啟動時給出可行動的 `ConnectionError`（點名 URL + 啟動方式），而非原始 httpx trace。
- factory 與 packaging 比照 nvidia/ollama 慣例：零 phantom `cantus[omlx]` 套件、extras hint 指向 `openai`。

**Non-Goals:**

- **不**啟動、偵測或管理 omlx／mlx-omni-server 行程（沿用 mlx-path design D1「不代管 server」的立場；本 change 只做 client adapter）。
- **不**內建預設 `base_url` port。omlx（8000）與 mlx-omni（10240）並存，挑一個當預設會誤導另一群使用者；故 `base_url` 必填。
- **不**新增第三方 pip 套件、**不**改 `.github/workflows/test.yml`、**不**新增 mypy override（`openai.*` 既有覆寫已涵蓋）。
- **不**讀 omlx 專屬環境變數做金鑰解析（伺服器不驗證）。
- **不**支援非 Apple-Silicon 平台的伺服器安裝指引（伺服器本身限 Apple Silicon；但 adapter 純走 openai SDK，故 adapter 程式碼本身不做平台 gating）。
- **不**動 `version`／`CHANGELOG.md`／`MIGRATION`（release 階段才動）。

## Decisions

### D1：薄 OpenAIChatModel 子類

omlx／mlx-omni-server 皆為 OpenAI-compatible 伺服器，wire 與 `OpenAIChatModel` 完全相同。因此採 `class OmlxChatModel(OpenAIChatModel)`，繼承 `chat`／`stream`／translators，僅覆寫建構與錯誤處理。**替代方案**：直接實作 ChatModel（如 `MLXChatModel`）——否決，因為那會重抄 OpenAI wire 邏輯且零新依賴失去意義。模組層仍 `import openai`（沿用 ollama.py 慣例：`chat`/`stream` 需捕捉 `openai.APIConnectionError`）。

### D2：base_url 必填

omlx 預設 `:8000/v1`、mlx-omni-server 預設 `:10240/v1` 兩者並存。建構子簽章為 `(model_id, api_key=None, base_url=None, **client_kwargs)`（與 sibling 一致），但當 `base_url is None` 時 **拋出清楚錯誤**（`ValueError`），訊息同時點名兩個範例 endpoint，引導使用者明確指定。**替代方案**：(a) 預設 omlx:8000——否決，誤導 mlx-omni 使用者；(b) 預設 mlx-omni:10240——否決，與 change 命名（omlx）不符；(c) 必填（採用）——最不誤導、把選擇權交還使用者。與 `OllamaChatModel`（有預設）唯一的行為差異即此。

### D3：sentinel api_key

omlx／mlx-omni-server 不驗證請求（mlx-omni 文件用 `api_key="not-needed"`）。比照 `OllamaChatModel`：建構子 `api_key=None` 時填入 module 常數 sentinel（`OMLX_API_KEY_SENTINEL = "omlx"`），**不** consult 任何環境變數，故 `OPENAI_API_KEY` 未設也不會拋 `MissingAPIKeyError`；明確傳入的 `api_key=` 仍保留（供使用者於伺服器前置 auth-proxy 時用）。class docstring 須揭露此「api_key 被接受但對伺服器無作用」的行為（比照 ollama 的 docstring 測試）。**替代方案**：讀 env（如 nvidia）——否決，本機伺服器無金鑰概念，徒增 `MissingAPIKeyError` 噪音。**Audit hardening（spectra-audit MEDIUM）**：coalesce 用 truthiness（`api_key if api_key else SENTINEL`）而非 `is not None`——否則 `api_key=""` 會以空字串傳給 parent，parent 的 `resolve_api_key` 對空字串走 truthiness 落回 `OPENAI_API_KEY`，等於暗中重開本 adapter 刻意關掉的 env 諮詢（且 env 未設時拋出點名 `OPENAI_API_KEY` 的混淆錯誤）。故空字串／falsy 一律視為未提供→用 sentinel。同源 `OllamaChatModel` 有相同 edge，列為 follow-up（本 change 不動 ollama）。

### D4：supports_tool_use 繼承

omlx／mlx-omni-server 皆支援 function calling。`OpenAIChatModel.supports_tool_use = True` 為 class attribute；`OmlxChatModel` **不** 重新定義此屬性（測試斷言 `"supports_tool_use" not in OmlxChatModel.__dict__`，比照 ollama）。這是本路線相對 in-process mlx-path（`False`）的核心價值。**替代方案**：覆寫成 False 求保守——否決，會抹除本 change 的存在理由。

### D5：ConnectionError 覆寫

本機伺服器常見失敗模式是「沒啟動」。比照 `OllamaChatModel`，覆寫 `chat()`／`stream()`：以 `try: super().… except openai.APIConnectionError as exc: raise ConnectionError(<訊息>) from exc`。訊息點名 `self._base_url` 與「請先啟動 omlx 或 mlx-omni-server」。其他 openai 例外（`NotFoundError` 模型未載入、`AuthenticationError` 等）原樣傳播，讓呼叫端能區分。**替代方案**：完全不覆寫（如 nvidia）——否決，學生會看到無用的 httpx stack trace。

### D6：omlx documentary 別名 + omlx↔openhands conflict

`OmlxChatModel` runtime 只依賴 `openai` SDK，故：
- `pyproject.toml` 的 `[project.optional-dependencies]` 新增 `omlx = ["cantus-agent[openai]"]`（documentary 別名，比照 `ollama`；**無** 新第三方套件）。
- factory `_EXTRAS_HINT["omlx"] = "openai"`，缺套件時提示 `pip install cantus[openai]`（非 phantom `cantus[omlx]`）。
- `[tool.uv].conflicts` 新增一條 `[{ extra = "omlx" }, { extra = "openhands" }]`：因 `omlx` 解析為 `openai`，而 `openai`↔`openhands` 既已互斥，沿用 `ollama`↔`openhands` 的同形條目維持 `uv` universal resolution 一致。

**替代方案**：給 omlx 自有 extras 閉包（如 mlx）——否決，沒有任何新套件可放，會造成 phantom group。

### D7：版本欄位 DEFERRED

本 change 不動 `version`／`CHANGELOG.md`／`MIGRATION`。新增 `omlx` extras 別名屬功能本身、非版本 bump；實際 release（建議 `v0.6.0` bundle mlx-path + 本件）於後續 release 流程處理。

## Implementation Contract

**行為（apply 後可觀察）：**

- `load_chat_model("omlx/qwen2.5-coder-7b", base_url="http://localhost:8000/v1")` 回傳一個 `OmlxChatModel`（亦為 `ChatModel`、`OpenAIChatModel` 子類），`model_id == "qwen2.5-coder-7b"`，可對該 endpoint 做 `chat`／`stream`，並支援 `tools=`。
- 省略 `base_url` 呼叫 `load_chat_model("omlx/<model>")`（或直接 `OmlxChatModel(model_id=...)`）拋 `ValueError`，訊息含 `http://localhost:8000/v1`（omlx）與 `http://localhost:10240/v1`（mlx-omni-server）兩個範例。
- 伺服器未啟動時，`chat`／`stream` 拋 `ConnectionError`（非 `openai.APIConnectionError`），訊息含 `base_url` 與啟動指引。
- `OPENAI_API_KEY` 未設時建構不報錯（sentinel）。

**介面／資料形狀：**

- 模組 `cantus.model.providers.omlx`，類別 `OmlxChatModel(OpenAIChatModel)`，建構子 `(model_id: str, api_key: str | None = None, base_url: str | None = None, **client_kwargs: Any)`。
- module 常數 `OMLX_API_KEY_SENTINEL = "omlx"`。
- factory `_REGISTRY["omlx"] = ("cantus.model.providers.omlx", "OmlxChatModel")`、`_EXTRAS_HINT["omlx"] = "openai"`；factory module docstring 的 provider 計數 seven → eight。
- `pyproject.toml`：`omlx = ["cantus-agent[openai]"]` + `[tool.uv].conflicts` 增 `[{ extra = "omlx" }, { extra = "openhands" }]`。
- `docs/quickstart-desktop.md`：MLX 段之後新增 `## Local LLMs via omlx (MLX server)`。

**失敗模式：**

- 缺 `base_url` → `ValueError`（建構期，fail-fast）。
- 伺服器不可達 → `ConnectionError`（從 `openai.APIConnectionError` 轉譯，`from exc` 保留 cause）。
- 其他 openai 例外（模型未載入、auth proxy 拒絕）→ 原樣傳播。

**驗收標準：**

- 新增 `tests/providers/test_omlx_adapter.py`：以假造 openai client 驗 base_url passthrough、必填 base_url 報錯、sentinel 金鑰（無 env 不報錯）、`supports_tool_use is True` 且不在子類 `__dict__`、`APIConnectionError`→`ConnectionError` 轉譯、docstring 揭露。
- `tests/test_factory.py`：omlx 在 `_REGISTRY`、`_EXTRAS_HINT["omlx"] == "openai"`、缺套件提示含 `pip install cantus[openai]` 且不含 `cantus[omlx]`、不支援前綴訊息含 omlx。
- `tests/test_pyproject_extras_conflicts.py`：omlx 別名解析為 openai 閉包、且 omlx↔openhands conflict 存在。
- `spectra analyze`（4 維）+ `spectra validate` 通過；ruff／mypy 對改動檔 delta-0。

**Scope 邊界：**

- In scope：上述 adapter、factory 兩列、pyproject 兩處、一段文件、對應測試。
- Out of scope：啟動／管理伺服器、平台 gating（adapter 端）、CI 變更、版本欄位、mypy override、in-process mlx 路線（屬已 ship 的 mlx-path）。

## Risks / Trade-offs

- [必填 base_url 比 Ollama 多一步、可能讓使用者初次困惑] → 建構期 `ValueError` 直接給兩個範例 URL；docs 範例一律顯式帶 `base_url`，降低踩坑。
- [`omlx` 前綴與真正連到的伺服器（可能是 mlx-omni-server）名稱不一致] → 與 `ollama/` 連遠端 Ollama 同理；docs 明說 `omlx` 前綴泛指「本機 OpenAI-compatible MLX 伺服器」、`base_url` 決定實際目標。
- [omlx 屬活躍開發、API 可能變動] → adapter 只依賴 OpenAI-compatible `/v1` Chat Completions 這個穩定子集，不碰 omlx 專屬端點，受其改版影響極小。
- [契約測試假造 openai client，未連真實伺服器] → 與既有 ollama/nvidia 契約測試同策略；真機驗證屬手動 smoke、非本 change 範圍（無 CI runner 具 Apple-Silicon MLX 伺服器）。

## Migration Plan

無資料遷移。純新增 provider，向後相容；既有 `load_chat_model` 呼叫不受影響。Rollback＝還原所列檔案即可（無狀態、無 schema 變更）。
