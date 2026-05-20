## Context

cantus v0.2.0（archived `2026-05-17-cantus-multi-provider-di`）已固化雙層 API、`ChatModel` Protocol、`Message` / `ToolCall` / `ChatResponse` 三 dataclass、`ChatModelAsHandle` bridge、`load_chat_model` factory、`ColabEnvironment` / `LocalEnvironment` / `CloudOnlyEnvironment` 三 Environment profile，以及 OpenAI + Anthropic 兩家直連 adapter。`tests/providers/conftest.py` 的 VCR 基礎建設已存在（`filter_headers` 已含 `x-goog-api-key`、`record_mode="none"`），但 v0.2.0 沒有錄製任何 cassette。

v0.2.0 將 Google / Groq / NVIDIA 三家延後至 v0.2.1 batch2，理由集中在三個技術風險：

1. **Google package 命名混淆**：PyPI 上同時存在 `google-generativeai`（舊版、Google AI Python SDK、停更）與 `google-genai`（新版、Gemini API & Vertex AI 統一 SDK）。新版 import path 是 `from google import genai`（命名空間共用 `google.*`），與舊版 `import google.generativeai as genai` 並存風險。
2. **NVIDIA NIM 是 OpenAI SDK 假身分**：NIM endpoint `https://integrate.api.nvidia.com/v1` 完全相容 OpenAI Chat Completions wire format，正規做法是 `openai.OpenAI(base_url=...)`；若另開 `nvidia` SDK extras 等於誤導使用者裝兩套 SDK。v0.2.0 `OpenAIChatModel.base_url` 已預留（"Day one 不接受會在 v0.2.1 反悔"，archive 記憶引述）。
3. **Groq tool-use schema churn**：Groq SDK 走 OpenAI Chat Completions 形狀但 tool_choice / function_call 細節在 2025 ~ 2026 多次調整；採用「複用 `to_openai_messages` 翻譯 + 鎖 SDK 上下界」收斂 surface。

利害關係人：v0.2.0 既有使用者（adapter API 必須是純 additive）、cantus v0.3+ 設計者（本 change 留下的 Google translator 是 Vertex AI 路徑前置）、教師（多 provider quickstart 文件雙語對照不可破）。

關鍵約束：
- v0.2.0 既有 5 條 model-providers Requirement 與 1 條 cantus-distribution extras Requirement 不能改變行為，僅可 RENAME 或 MODIFY 對「列出哪些 provider prefix」的描述
- 不引入 `litellm`（v0.2.0 固化、2026-03 供應鏈攻擊）
- 不引入 `google-generativeai` 舊套件
- CI 仍不持有真實 API key，全部走 cassette replay

## Goals / Non-Goals

**Goals:**

- 把 v0.2.0 留下的 Google / Groq / NVIDIA 三家補齊，讓 `load_chat_model("google/gemini-2.0-flash")` / `load_chat_model("groq/llama-3.3-70b")` / `load_chat_model("nvidia/meta/llama-3.3-70b-instruct")` 全部可用
- Google adapter 透過 `google-genai` 新 SDK，import path `from google import genai`，避開舊 `google-generativeai` 路徑
- Groq adapter 透過 `groq` SDK 走 OpenAI Chat Completions 形狀，**最大程度複用** v0.2.0 既有 `to_openai_messages` / `from_openai_response` 兩個純函式翻譯器
- NVIDIA adapter 為 `OpenAIChatModel` 的薄 subclass（< 30 行實作），hard-code `base_url="https://integrate.api.nvidia.com/v1"`，不另開 SDK 依賴、不另開 `cantus[nvidia]` extras
- `cantus[providers]` 聚合器擴為四家（openai / anthropic / google / groq），NVIDIA 走 `cantus[openai]` 在文件指引
- v0.2.0 既有 cassette 安全 invariant（CI `record_mode="none"`、`filter_headers` 預設遮蔽四種 header）延伸到三家新 adapter，外加擴充 distribution pre-push hook secret-pattern 涵蓋 cassette 路徑（v0.2.0 archive 留 follow-up）
- README 雙語對照繼續 byte-identical code block 規則
- version bump 0.2.0 → 0.2.1（PATCH，因 v0.2.0 already shipped）

**Non-Goals:**

- 不修改 Tier 2 Protocol、`Message` / `ToolCall` / `ChatResponse` dataclass shape
- 不修改 `ChatModelAsHandle` bridge、`Agent`、`AgentState`、`EventStream` 任何一行
- 不引入 `google-generativeai` 舊 SDK；不為 Google 同時引入 Vertex AI 認證流程（Vertex 路徑留 v0.3+）
- 不引入 `litellm` 任何形式
- 不切到 Anthropic content blocks、OpenAI Responses API、Gemini multimodal input、Groq audio model
- 不實作 tool-call streaming delta（v0.2.0「`stream()` 只 yield 文字 delta」契約延續）
- 不為 NVIDIA NIM 開獨立 `cantus[nvidia]` extras
- 不寫 live integration test（CI 不持有 API key，限制延續 v0.2.0 決策）
- 不為 Gemini safety_settings / system_instruction 開 first-class API，僅透過 `**kwargs` 透傳 + `ChatResponse.raw` escape hatch
- 不修改 v0.1.x 既有 5 份 notebook 任何一份；不為 v0.2.0 既有 `multi_provider_smoke.ipynb` 加 cell（新建 `_batch2.ipynb` 分離）

## Decisions

### Google adapter 採 google-genai 新 SDK 而非 google-generativeai 舊 SDK

`google-genai`（PyPI 名稱 `google-genai`，import path `from google import genai`）是 Google 官方 2024 年起統一 Gemini API + Vertex AI 的新 SDK，stable namespace。`google-generativeai`（import path `import google.generativeai as genai`）是 2023 年的舊 SDK，已標記為 maintenance-only。

理由：(1) 舊 SDK 與新 SDK namespace 共用 `google.*` 但子模組不同，並存會造成「`from google import genai` 抓到舊版」的混淆；(2) v0.3+ 若要把 cantus 帶到 Vertex AI 教學情境，新 SDK 直接走 `genai.Client(vertexai=True, project=...)` 一行切換；(3) 舊 SDK 的 `GenerativeModel(...).generate_content(...)` API 與新 SDK 的 `client.models.generate_content(...)` 形狀不同，鎖新 SDK 不必兩套翻譯。

替代方案 A：採 `google-generativeai` 舊 SDK — 拒絕，Google 已宣告新 SDK 為前進方向、Vertex AI 路徑只在新 SDK。
替代方案 B：同時 ship 兩個 adapter 並讓使用者選 — 拒絕，並存等於把命名混淆移到使用者腦中。
替代方案 C：直接走 `httpx` 自寫 wire — 拒絕，SDK 已處理 retry / auth / streaming chunked event，自寫等於回到 v0.1.x「每家從零」的反模式。

### NVIDIA adapter 為 OpenAIChatModel 的薄 subclass，固定 NIM base_url，不開獨立 extras

`NvidiaChatModel` 繼承 `OpenAIChatModel`，建構子 hard-code `base_url="https://integrate.api.nvidia.com/v1"`，僅覆寫 `resolve_api_key` 改讀 `NVIDIA_API_KEY` 環境變數。實作預計 < 30 行。

對應 `pyproject.toml`：**不開** `cantus[nvidia]` extras。`load_chat_model("nvidia/...")` 在 `openai` SDK 未安裝時拋 `ImportError("install cantus[openai]")` 而非 `cantus[nvidia]`，明示「NIM 是 OpenAI SDK + base_url 的別名」。

理由：(1) NIM endpoint 已宣告完全相容 OpenAI Chat Completions wire format；(2) 開獨立 extras 會誤導使用者裝兩套 SDK（`openai` + 不存在的 `nvidia` package）；(3) v0.2.0 `OpenAIChatModel.base_url` 從 day one 就是為此預留；(4) subclass 模式讓 v0.2.0 既有 cassette pattern（OpenAI Chat Completions JSON shape）可直接 reuse 到 NVIDIA cassette。

替代方案 A：開獨立 `cantus[nvidia]` extras 配 `nvidia` SDK — 拒絕，PyPI 上 `nvidia` SDK 並不存在於 NIM context；NIM 官方文件直接指 `openai` SDK + base_url。
替代方案 B：把 base_url 寫進 NVIDIA-specific factory 但 reuse `OpenAIChatModel` 不 subclass — 拒絕，使用者直接 `from cantus.model.providers.nvidia import NvidiaChatModel` 比 `OpenAIChatModel(base_url=NIM_ENDPOINT)` 更有 discoverability。

### Groq adapter 透過 groq SDK 並複用 OpenAI 翻譯器

`GroqChatModel` 透過 `groq` SDK（PyPI `groq`）的 `client.chat.completions.create(...)`，wire format 與 OpenAI Chat Completions 等價。`to_openai_messages` / `from_openai_response` / `extract_tool_calls_openai` 三個既有純函式直接 reuse，無需新 translator。

理由：(1) Groq SDK 自宣告 OpenAI-compatible；(2) 重複實作翻譯器會與 OpenAI translator 行為漂移；(3) Groq tool-use schema churn 風險集中在「Groq 偶爾自己加欄位」—— 鎖 SDK upper bound `<1` + 季更新 cassette 收斂。

替代方案 A：直接讓使用者用 `OpenAIChatModel(base_url=GROQ_ENDPOINT)` — 拒絕，雖然可行但 Groq SDK 已封裝 retry / rate-limit / Groq-specific extra header（`x-groq-region`），跳過 SDK 是技術債。
替代方案 B：新寫 `to_groq_messages` translator — 拒絕，與 OpenAI translator 99% 重複，第一次 Groq 加欄位時兩邊都要改。

### Google translator 為新增純函式 to_google_messages / from_google_response，不抽 base translator

`google-genai` SDK 用 `contents=[{"role": "user"|"model", "parts": [{"text": "..."}]}]` 形狀，與 OpenAI/Anthropic 翻譯器都不同。Role 從 cantus `"assistant"` 翻成 Gemini `"model"`，cantus `"tool"` 翻成 Gemini `"function"` + `function_response` part shape。

理由：(1) Google `parts` 結構與 OpenAI `content` 字串、Anthropic content blocks 互不重疊，沒有有意義的共用；(2) v0.2.0 既定路線「translator pure functions、不抽 base class」延續；(3) Gemini `system_instruction` 為 `generate_content` 的 top-level kwarg（類似 Anthropic 的 `system=`），純函式回傳 `(system_instruction, contents)` tuple 與 `to_anthropic_messages` 對齊。

替代方案：抽 `BaseChatTranslator` 共用 base — 拒絕，v0.2.0 已固化決策「leaky abstraction 不抽 base」，本 change 不重啟。

### Three new adapters opt out of top-level cantus re-export

v0.2.0 既有 `cantus.OpenAIChatModel` / `cantus.AnthropicChatModel` 並**未**在 top-level `cantus` 暴露（archive 確認：`cantus/__init__.py` 只 export `load_chat_model` / `ChatModelAsHandle` / Tier 2 dataclass）。本 change 保持一致：`GoogleChatModel` / `GroqChatModel` / `NvidiaChatModel` 從 `cantus.model.providers.<provider>` 顯式 import，不上 top-level `__all__`。

理由：(1) 五家 adapter 都暴露 = 增加 IDE 噪音 + 違反 v0.2.0 既定 export contract；(2) factory `load_chat_model("provider/...")` 是教學情境主要入口；(3) lazy import 機制依賴「adapter 不上 top-level」，否則 `import cantus` 會 transitive 拉所有 SDK（破壞 ARCH-2 smoke test）。

### 擴充 cantus-distribution pre-push secret-pattern hook 涵蓋 cassette 路徑

v0.2.0 archive 留下 follow-up：「cassette 路徑未在 pre-push hook secret scan 中」。本 change 完成此項，pre-push hook 新增 grep pattern：
- `sk-[A-Za-z0-9]{20,}` / `Bearer ` / `Authorization:` / `x-api-key:` / `x-goog-api-key:` 等
- Scope 限定 `libs/cantus/tests/providers/cassettes/**/*.yaml`

對應 `cantus-distribution` capability「Pre-push security audit gates initial publication」需要 MODIFY，把 audit 路徑列表加 cassette glob。

理由：cassette 是 v0.2.1 第一次真實錄製（v0.2.0 conftest 在，cassette 尚未錄），audit 路徑覆蓋是上線必要前提。

### Version bump 為 PATCH 0.2.0 → 0.2.1 而非 MINOR

本 change 為 additive only（既有 API 簽名不變、僅新 adapter + 新 extras），符合 SemVer PATCH。

理由：(1) v0.2.0 已 ship、`schola-cantorum/cantus` Git tag `v0.2.0` 不可動；(2) 三家新 provider 是 v0.2.0 設計時就規劃好的「分批 ship」；(3) MINOR bump 0.3.0 留給 ARCH 級變更（v0.3+ roadmap 已排 Responses API / multimodal / Vertex AI）。

替代方案：MINOR bump 0.3.0 — 拒絕，違反「MINOR 為新行為、PATCH 為相容擴充」的內部約定。

## Implementation Contract

**Behavior — three new adapters**

- `GoogleChatModel(model_id: str, api_key: str | None = None, **client_kwargs)` 從 `cantus.model.providers.google` 可 import；建構子解析 key 順序 `api_key=` > `GOOGLE_API_KEY`；缺 key 時拋 `MissingAPIKeyError` 名 `GOOGLE_API_KEY`；`supports_tool_use = True`；`chat(messages, tools=None, **kwargs)` 走 `client.models.generate_content(model=self.model_id, contents=...)`；system message 透過 `to_google_messages` 抽離為 top-level `system_instruction=` kwarg；`stream()` 走 `client.models.generate_content_stream` 並 yield 純文字 delta。
- `GroqChatModel(model_id: str, api_key: str | None = None, **client_kwargs)` 從 `cantus.model.providers.groq` 可 import；建構子解析 key 順序 `api_key=` > `GROQ_API_KEY`；缺 key 時拋 `MissingAPIKeyError` 名 `GROQ_API_KEY`；`supports_tool_use = True`；`chat(messages, tools=None, **kwargs)` 走 `client.chat.completions.create(...)` 並複用 `to_openai_messages` / `from_openai_response`；`stream()` 同 OpenAI streaming 邏輯（yield text delta）。
- `NvidiaChatModel(model_id: str, api_key: str | None = None, **client_kwargs)` 從 `cantus.model.providers.nvidia` 可 import；繼承 `OpenAIChatModel`；建構子強制 `base_url="https://integrate.api.nvidia.com/v1"`（若使用者顯式傳入不同 base_url 仍可覆寫）；解析 key 順序 `api_key=` > `NVIDIA_API_KEY`；缺 key 時拋 `MissingAPIKeyError` 名 `NVIDIA_API_KEY`；`supports_tool_use = True`；`chat` / `stream` 行為繼承 `OpenAIChatModel`。

**Behavior — factory dispatch**

`load_chat_model(spec)` `_REGISTRY` 從 v0.2.0 兩條擴為五條：
- `openai` → `cantus.model.providers.openai.OpenAIChatModel`（不變）
- `anthropic` → `cantus.model.providers.anthropic.AnthropicChatModel`（不變）
- `google` → `cantus.model.providers.google.GoogleChatModel`
- `groq` → `cantus.model.providers.groq.GroqChatModel`
- `nvidia` → `cantus.model.providers.nvidia.NvidiaChatModel`

未知 prefix 的 `ValueError` 訊息列舉五家。Missing-extras `ImportError` 訊息：
- `google` / `groq` → `pip install cantus[google]` / `pip install cantus[groq]`
- `nvidia` → `pip install cantus[openai]`（特例提示，因 NIM 走 OpenAI SDK）
- `openai` / `anthropic` 訊息不變

**Behavior — Google translator**

`to_google_messages(messages: list[Message]) -> tuple[str | None, list[dict]]` 純函式：
- 抽出 `role="system"` 為 `system_instruction`（多條 system 以 `"\n"` 串接）
- `role="assistant"` 翻成 `"role": "model"`
- `role="user"` 維持 `"role": "user"`
- `role="tool"` 翻成 `"role": "function"` 並把 content 包成 `{"function_response": {"name": msg.name, "response": {"result": msg.content}}}` part
- 一般文字內容包成 `[{"text": content}]` parts
- `tool_calls` 翻成 `[{"function_call": {"name": tc.name, "args": tc.arguments}}]` parts

`from_google_response(raw)` 純函式：
- 從 `candidates[0].content.parts` 重組 cantus `Message`
- `parts[*].text` 串接為 `message.content`
- `parts[*].function_call` 翻回 `ToolCall`
- `finish_reason` 映射：`STOP` → `end_turn`、`MAX_TOKENS` → `max_tokens`、`SAFETY` → `error`、`TOOL_CALL` → `tool_use`、其他 → `error`
- `usage_metadata.prompt_token_count` / `candidates_token_count` 映射為 cantus usage

**Interface — pyproject.toml extras**

```
[project.optional-dependencies]
openai = ["openai>=1.50,<2"]
anthropic = ["anthropic>=0.40,<1"]
google = ["google-genai>=0.3,<1"]
groq = ["groq>=0.11,<1"]
providers = ["cantus[openai,anthropic,google,groq]"]
```

`nvidia` 不在 extras 列表（intentional）。`dev` 仍包含 `pytest-recording>=0.13`。core dependencies 不變、無 `litellm`。

**Failure modes**

- `load_chat_model("vertex/...")` 或其他未知 prefix → `ValueError("unsupported provider 'vertex'; v0.2.1 ships only: anthropic, google, groq, nvidia, openai")`
- `load_chat_model("google/gemini-2.0-flash")` 在無 `google-genai` 安裝 → `ImportError(... pip install cantus[google])`
- `load_chat_model("nvidia/...")` 在無 `openai` 安裝 → `ImportError(... pip install cantus[openai])`
- `GoogleChatModel()` 缺 `GOOGLE_API_KEY` → `MissingAPIKeyError` 含中文訊息名 `GOOGLE_API_KEY`
- `GroqChatModel()` 缺 `GROQ_API_KEY` → `MissingAPIKeyError` 含中文訊息名 `GROQ_API_KEY`
- `NvidiaChatModel()` 缺 `NVIDIA_API_KEY` → `MissingAPIKeyError` 含中文訊息名 `NVIDIA_API_KEY`
- `Agent(model=GoogleChatModel(...))` 不包 bridge → `AttributeError`（無 `.generate`，與 v0.2.0 既定行為一致）

**Acceptance criteria**

- `cd libs/cantus && uv run pytest -v` 全綠
- `cd libs/cantus && uv run pytest tests/providers/ --record-mode=none` 全綠（含三家新 adapter 各三條 cassette）
- `python -c "import cantus; assert cantus.__version__ == '0.2.1'"`
- `python -c "import sys, cantus; assert 'google' not in sys.modules and 'google.genai' not in sys.modules and 'groq' not in sys.modules"` 通過（NVIDIA 不列因走 openai SDK）
- `python -c "from cantus.model.providers.google import GoogleChatModel; import sys; assert 'google.genai' in sys.modules or 'google' in sys.modules"`
- `python -c "from cantus.model.providers.nvidia import NvidiaChatModel; m = NvidiaChatModel(model_id='meta/llama-3.3-70b-instruct', api_key='dummy'); assert m._base_url == 'https://integrate.api.nvidia.com/v1'"`
- `python -c "from cantus import load_chat_model; load_chat_model('nvidia/x')"` 在無 `openai` 安裝時拋 `ImportError("... pip install cantus[openai]")`
- `pip install -e ".[providers]"` 在乾淨 venv 下同時裝 openai / anthropic / google-genai / groq 四家 SDK，不裝 `nvidia` 任何 package、不裝 `litellm`、不裝 `google-generativeai`
- README.md 與 README.zhTW.md 的 Multi-provider quickstart code block byte-identical（diff 三個新 provider 的 7 行 code block 全部對齊）
- pre-push hook secret-pattern grep 在 `libs/cantus/tests/providers/cassettes/**/*.yaml` 結果為空
- 手動 smoke：`libs/cantus/notebooks/multi_provider_smoke_batch2.ipynb` 三家各兩 cell 跑完無 error

**Scope boundaries**

- **In scope**：三家新 adapter（Google / Groq / NVIDIA）、Google translator pure functions、factory `_REGISTRY` 擴充、`_common.py` env var 解析（call site）、`pyproject.toml` 加 `google` / `groq` 兩 extras 與 `providers` 擴充、三組 cassette 測試、`tests/test_factory.py` / `tests/test_integration_smoke.py` 擴充、pre-push hook secret-pattern 加 cassette 路徑、README zh/en 同步、CHANGELOG + version bump 0.2.0 → 0.2.1、新 smoke notebook `_batch2.ipynb`
- **Out of scope**：修改 Tier 2 Protocol / dataclass / bridge / Agent 程式碼、修改 v0.2.0 既有 OpenAI/Anthropic adapter 行為、引入 `google-generativeai` 或 `litellm`、Anthropic content blocks / OpenAI Responses API / Gemini multimodal / Groq audio model、tool-call streaming delta、開 `cantus[nvidia]` extras、live integration test、修改 v0.1.x 既有 5 份 notebook、修改 v0.2.0 既有 `multi_provider_smoke.ipynb`

## Risks / Trade-offs

- [Google SDK 在 v0.x 階段尚未進入 v1.0、`>=0.3,<1` 可能在 v0.5 / v0.6 引入 breaking change] → Pin upper bound `<1`，CHANGELOG 註記「Google SDK pre-1.0 cassette 季更新節奏」；release 前手動 smoke notebook 跑過 Google cell；若 SDK 0.x → 1.0 升級在 v0.2.x 期間落地，本 change 結束後建 v0.2.2 follow-up issue 處理 pin 上調
- [Groq tool-use schema 在 cassette 與 prod 之間漂移] → 鎖 `groq>=0.11,<1` 上下界，cassette 三條（chat / chat+tools / stream）涵蓋實際 schema；CHANGELOG 註記 Groq schema churn 風險與「升級 SDK 前需重錄 cassette」流程
- [NVIDIA NIM endpoint URL 或 wire format 變動] → endpoint 在 `NvidiaChatModel` 內 hard-code 為單一字串常數（不分散在多處），URL 變動時改一行；wire format 變動風險低（NIM 公開合約綁 OpenAI Chat Completions）
- [`google-genai` SDK import path `from google import genai` 與其他 google.* package 共存衝突] → 在 `tests/test_integration_smoke.py` 加一條測試確認 `import cantus` 後 `google.genai` 不在 `sys.modules`；CHANGELOG / README Notes 節明示「採 google-genai 而非 google-generativeai 並列出兩者區別」
- [cassette 不小心錄到 API key] → v0.2.0 既有 `filter_headers` 已含 `x-goog-api-key`；本 change 同時擴 pre-push hook secret-pattern 涵蓋 cassette 路徑作為 belt-and-suspenders；cassette PR review checklist 維持
- [使用者誤把新 ChatModel 直接餵 Agent 而忘了 bridge] → 與 v0.2.0 既定方案一致：README quickstart 三家新 provider 的 code block 都明示 `ChatModelAsHandle(load_chat_model(...))`，Agent 不加 isinstance 分支
- [Groq SDK 自己加未文件化欄位導致 from_openai_response raise KeyError] → `from_openai_response` 已用 `.get(..., default)` 防禦；cassette PR review checklist 新增「Groq cassette 變動需貼 SDK changelog 連結」

## Migration Plan

- v0.2.0 → v0.2.1 升級無需任何 user-side 程式碼變更（既有 `OpenAIChatModel` / `AnthropicChatModel` / `load_chat_model("openai/...")` / `load_chat_model("anthropic/...")` 全部沿用）
- 新使用者透過 README「Multi-provider quickstart」區段學三家新 provider 的 `load_chat_model("<provider>/<model>") + ChatModelAsHandle(...) + Agent(model=...)`
- Rollback：若 v0.2.1 release 後發現任一家新 adapter 有 regression，可直接 revert 對應 adapter 檔案 + 從 `_REGISTRY` 移除該 prefix + 退回 0.2.0 extras matrix；其他既有 provider 不受影響
- 教師 release 前手動跑 `multi_provider_smoke_batch2.ipynb`（三家各兩 cell）+ `multi_provider_smoke.ipynb`（v0.2.0 既有 OpenAI/Anthropic 雙家迴歸）確認五家全 healthy
- Git tag 推送順序：先 push commits → 跑 pre-push hook（含擴充後的 cassette secret-pattern scan）→ tag `v0.2.1` → push tag

## Open Questions

無。所有開放決策（三家 adapter 形態、NVIDIA 不開獨立 extras、Google 採新 SDK、Groq 複用 OpenAI translator、version bump 為 PATCH）皆透過 v0.2.0 archive 記憶與本 change 設計階段收斂；apply 時遇細節（如具體 Groq SDK pin 版本、Google model_id 範例字串）可在 cassette 錄製階段就地決定。
