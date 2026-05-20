## Why

cantus v0.2.0 把雙層 API 與 OpenAI/Anthropic 兩個直連 adapter 建好，但 Google / Groq / NVIDIA 三家因為「package 命名混淆（`google-genai` 新 vs `google-generativeai` 舊）」、「NVIDIA NIM 其實是 OpenAI SDK + `base_url`」、「Groq tool-use schema 變動快」三個風險點集中而 deferred 到 v0.2.1。本 change 完成 v0.2.0 留下的 batch2 缺口：在 `model-providers` 加入這三家 adapter、在 `cantus-distribution` 補對應 extras matrix（含 NIM 直接走 `cantus[openai]` 不另開 extras），讓 v0.2.0 已固化的 Tier 2 Protocol、bridge、factory、Environment profile 全部沿用、Agent 程式碼一行不改。

## What Changes

- 新增 `GoogleChatModel`（`libs/cantus/cantus/model/providers/google.py`，使用 `google-genai`（新版 SDK，import path 為 `from google import genai`），呼叫 `client.models.generate_content` 對齊 Gemini API；明示不使用 `google-generativeai` 舊套件）
- 新增 `GroqChatModel`（`libs/cantus/cantus/model/providers/groq.py`，使用 `groq` SDK 走 OpenAI-compatible Chat Completions 形狀；複用 `to_openai_messages` / `from_openai_response` translator）
- 新增 `NvidiaChatModel`（`libs/cantus/cantus/model/providers/nvidia.py`，作為 `OpenAIChatModel` 的薄 subclass，hard-code `base_url="https://integrate.api.nvidia.com/v1"`，不另開 SDK 依賴）
- 擴充 `cantus/model/providers/_translate.py`，新增 `to_google_messages` / `from_google_response` 兩個純函式（Google `contents` 陣列、`parts` 結構、`role` 從 `assistant` 翻成 `model`）；`_translate.py` OpenAI 既有翻譯函式以 module 級別公開讓 Groq 直接複用
- 擴充 `cantus/model/factory.py` `_REGISTRY` 加入 `google` / `groq` / `nvidia` 三個 prefix；`ValueError` 訊息更新為五家 prefix 列舉；missing-extras `ImportError` 對 `nvidia` 特例提示 `pip install cantus[openai]`（因 NIM 走 openai SDK），對 `google` / `groq` 維持 `pip install cantus[<provider>]`
- 擴充 `cantus/model/providers/_common.py` 新增 `GOOGLE_API_KEY` / `GROQ_API_KEY` / `NVIDIA_API_KEY` 三條 env var 解析路徑（沿用 `resolve_api_key` 既有實作，僅 call site 變更）
- 更新 `cantus/__init__.py`：版本 bump 至 `0.2.1`；不暴露三個新 adapter class 在 top-level（保持 `cantus.OpenAIChatModel` 等 v0.2.0 不變的 export contract，新 adapter 走子模組直接 import 或 factory）
- 更新 `pyproject.toml`：新增 optional extras `google = ["google-genai>=0.3,<1"]`、`groq = ["groq>=0.11,<1"]`；`providers` 聚合器擴充為 `cantus[openai,anthropic,google,groq]`；不為 `nvidia` 開獨立 extras（文件指引 `pip install cantus[openai]`）；core dependencies 仍不變、仍不引入 `litellm`；version bump 0.2.0 → 0.2.1
- 新增 cassette 為基礎的 contract test 三組：`tests/providers/test_google_adapter.py` / `tests/providers/test_groq_adapter.py` / `tests/providers/test_nvidia_adapter.py`，沿用 v0.2.0 既有 `tests/providers/conftest.py`（已含 `x-goog-api-key` 在 `filter_headers`）；每組三條 cassette（chat / chat+tools / stream）+ 一條 `MissingAPIKeyError` 測試
- 擴充 `tests/test_factory.py` 五條案例：三家新 prefix 解析、Nvidia 走 OpenAI SDK 後 `client.base_url` 為 NIM endpoint、Groq missing-extras 訊息驗證、ValueError 訊息列舉五家
- 擴充 `tests/test_integration_smoke.py` 兩條：`import cantus` 後 `sys.modules` 仍不含 `google.genai` / `groq`；顯式 import 對應 adapter 模組後 SDK 才出現
- 擴充 cantus-distribution pre-push secret-pattern hook 涵蓋 `libs/cantus/tests/providers/cassettes/**`（v0.2.0 archive 留下的 follow-up scope）
- 更新 `libs/cantus/README.md` 與 `libs/cantus/README.zhTW.md` 的 Multi-provider quickstart 區段，三個新 provider 各加一個 7 行 code block（code block byte-identical 維持與 v0.2.0 相同的雙語對照）
- 更新 `libs/cantus/CHANGELOG.md` 新增 v0.2.1 條目，Notes 節說明 NIM 採 subclass 不開獨立 extras 的決策、Google `google-genai` 與 `google-generativeai` 命名選擇、Groq schema churn 風險
- 新增 `libs/cantus/notebooks/multi_provider_smoke_batch2.ipynb` 手動 smoke notebook，Google / Groq / NVIDIA 各兩 cell（chat + stream），release 前 release manager 人工跑過

## Non-Goals

- 不修改 v0.2.0 已固化的 Tier 2 Protocol、`Message` / `ToolCall` / `ChatResponse` dataclass 形狀
- 不修改 `ChatModelAsHandle` bridge 或 Agent 程式碼任何一行
- 不引入 `google-generativeai` 舊 SDK（package 命名混淆的根因）；亦不同時引入兩個 Google SDK 做 fallback
- 不引入 `litellm`（v0.2.0 已固化決策、2026-03 供應鏈攻擊事件）
- 不切到 Anthropic content blocks、OpenAI Responses API、Gemini multimodal input、Groq audio model
- 不實作 tool-call streaming delta（v0.2.0 既有「`stream()` 只 yield 文字 delta」契約延續）
- 不為 NVIDIA NIM 開獨立 extras `cantus[nvidia]`（NIM 直接走 `openai` SDK，多開一個 extras 等於誤導使用者裝兩個 SDK）
- 不為 Google 的 safety settings / system_instruction 細節做 cantus-side first-class API（透過 `ChatResponse.raw` + `**kwargs` 透傳即可）
- 不修改 v0.1.x 既有 5 份 notebook 任何一份（templates × 3、libs/cantus/notebooks × 1、examples/01_book_recommender × 1）
- 不寫 live integration test（CI 不持有 API key 的限制延續 v0.2.0 決策）

## Capabilities

### New Capabilities

（無新 capability）

### Modified Capabilities

- `model-providers`: 新增三條 Requirement「GoogleChatModel 走 google-genai SDK 並對齊 Gemini API」、「GroqChatModel 走 groq SDK 並複用 OpenAI 翻譯」、「NvidiaChatModel 為 OpenAIChatModel 之 subclass 並固定 NIM base_url」；MODIFY 既有 Requirement「load_chat_model factory dispatches by provider prefix with lazy import」把支援的 prefix 從兩家擴為五家、`nvidia` 的 missing-extras 提示為 `pip install cantus[openai]`、`ValueError` 訊息更新；MODIFY 既有 Requirement「Core import does not transitively load provider SDKs」把保護範圍從 openai/anthropic 擴及 google/groq（NVIDIA 不另列因走 openai SDK）
- `cantus-distribution`: MODIFY 既有 Requirement「Distribution extras matrix exposes openai, anthropic, and providers groups」為 `google` / `groq` 新增 extras 與版本上下界、`providers` 聚合器擴為四家（openai / anthropic / google / groq）、明示 NVIDIA NIM 不開獨立 extras 而沿用 `cantus[openai]`；MODIFY 既有 Requirement「Pre-push security audit gates initial publication」把 audit 路徑涵蓋 `libs/cantus/tests/providers/cassettes/**`（v0.2.0 archive 已留 follow-up）

## Impact

- Affected specs: `model-providers`（修改 2 Requirement、新增 3 Requirement）、`cantus-distribution`（修改 2 Requirement）
- Affected code:
  - New:
    - libs/cantus/cantus/model/providers/google.py
    - libs/cantus/cantus/model/providers/groq.py
    - libs/cantus/cantus/model/providers/nvidia.py
    - libs/cantus/tests/providers/test_google_adapter.py
    - libs/cantus/tests/providers/test_groq_adapter.py
    - libs/cantus/tests/providers/test_nvidia_adapter.py
    - libs/cantus/notebooks/multi_provider_smoke_batch2.ipynb
  - Modified:
    - libs/cantus/cantus/model/providers/_translate.py
    - libs/cantus/cantus/model/providers/_common.py
    - libs/cantus/cantus/model/factory.py
    - libs/cantus/cantus/__init__.py
    - libs/cantus/pyproject.toml
    - libs/cantus/CHANGELOG.md
    - libs/cantus/README.md
    - libs/cantus/README.zhTW.md
    - libs/cantus/tests/test_factory.py
    - libs/cantus/tests/test_integration_smoke.py
  - Removed: 無
- Dependencies: 新增 `google-genai>=0.3,<1`、`groq>=0.11,<1` 皆為 optional extras；core 依賴不變；不引入 `google-generativeai` 與 `litellm`
- Backward compatibility: 100% 相容 — v0.2.0 既有 `OpenAIChatModel` / `AnthropicChatModel` / `load_chat_model` 簽名與行為不變；`Agent` / `AgentState` / `EventStream` 程式碼仍一行不改
