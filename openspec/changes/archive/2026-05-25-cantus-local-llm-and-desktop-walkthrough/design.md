## Context

cantus v0.4.3 ship `cantus.config.Settings` + `cantus.serve()` programmatic API（v0.4.0）+ `cantus serve` CLI（v0.4.4，PR #5 squash `7cb4f59`，2026-05-25）；A0 ship `pyproject.toml` 三 OS extras + `docs/quickstart-desktop.md` 桌面 quickstart（commit `096cfd6`，2026-05-25），但 quickstart-desktop 的「`## What about local LLMs on macOS / Windows?`」段是 placeholder，等 A1' 補。`cantus/model/providers/` 已 ship 五個 provider（`openai` / `anthropic` / `google` / `groq` / `nvidia`），其中 `NvidiaChatModel(OpenAIChatModel)` 已立下「subclass OpenAIChatModel + 指向 OpenAI-compatible 端點」的 pattern（`cantus/model/providers/nvidia.py:23-39`）；`cantus/model/factory.py:21-39` 的 `_REGISTRY` + `_EXTRAS_HINT` 是兩個明確列舉的 dict，新增 provider 要 append 兩處。教學情境 [[project_teaching_context]] 明定：repo 只負責 framework、本機 LLM 統一走 Ollama bridge（bnb 4-bit Gemma 只留 Linux+CUDA）、跨平台必須三 OS 都跑、後續 B 系列 channel webhook 需要 tunnel 暴露公網 URL。

## Goals / Non-Goals

**Goals:**

- `load_chat_model("ollama/gemma3:4b")` 在 macOS / Linux / Windows 三 OS 都能起 `OllamaChatModel` instance 並指向 `http://localhost:11434/v1`
- Ollama daemon 沒在跑時 `chat()` / `stream()` 拋 `ConnectionError` 含 actionable message（含 `ollama serve` + install URL），不讓學生看到 openai SDK 原 trace
- `docs/quickstart-desktop.md` 完整覆蓋三 OS 學生 path：API key（既有）→ Ollama local LLM（A1' 新增取代 placeholder）→ Cloudflare Tunnel（A1' 新增）
- `pip install cantus[ollama]` 能裝、解析等同 `cantus[openai]`，學生有字面選項表達意圖
- `tests/integration/test_tunnel_smoke.py` 在 cloudflared 已裝環境跑 `cloudflared --version` 成功；未裝環境 `pytest.skip` 不擋 CI
- `model-providers` capability 的 prefix 列表延伸到 6 個（加 ollama）；既有 5 provider scenarios 全部保留

**Non-Goals:**

- 不引入 `ollama` Python SDK——openai SDK + base_url override 已足夠（Ollama 對 OpenAI Chat Completions 完全相容）
- 不引入 `cloudflared` Python wrapper / SDK——tunnel 純 docs walkthrough
- 不在 `cantus-distribution` 的 `.github/workflows/cross-platform-install.yml` 三 OS smoke 加 `cloudflared --version` step（避免 main CI 因 cloudflared 沒裝跳 step）
- 不改 `cantus.serve()` / `Settings` / `AuthMode` / `cantus serve` CLI surface（C1 已 freeze）
- 不破 `bitsandbytes>=0.43.0; sys_platform == 'linux'` marker（A0 已立）
- 不寫章節 notebook / 習題 / 評量（[[project_teaching_context]] 課程材料分工）
- 不引入 `cantus init` / `cantus skill list` 等新子命令（C1 預留結構，但本 change 不擴充）

## Decisions

### Ollama adapter subclasses OpenAIChatModel via Ollama's OpenAI-compatible endpoint

選 subclass。Rationale：Ollama daemon 預設在 `http://localhost:11434/v1` 暴露 OpenAI Chat Completions 100% 相容的端點，subclass `OpenAIChatModel` 可直接重用 `to_openai_messages` / `from_openai_response` translators、`stream()` chunk handling、tool-call schema；跟 `NvidiaChatModel(OpenAIChatModel)`（`cantus/model/providers/nvidia.py:23-39`）pattern 一致，已驗證可維護。Alternative「引入 `ollama` Python SDK 寫獨立 adapter」——拒絕因為純增加 supply-chain 表面（cantus 對 third-party SDK 數量是有上限的）且 openai SDK 已能跑。

### default api_key 用 sentinel "ollama" 字串、不走 resolve_api_key env 解析

Rationale：Ollama daemon 不檢查 API key（任何非空字串都會被忽略），但 openai SDK 在 `OpenAI(api_key=...)` 構造時要求非空字串；若沿用 `resolve_api_key(api_key, "OLLAMA_API_KEY")`（NVIDIA pattern），未設 env 變數時會拋 `MissingAPIKeyError`——這對本機 daemon 是 false positive。直接 hard-code sentinel 字串 `"ollama"` 是 idiomatic 的 OpenAI-compat workaround，且 sentinel 字面意義明確（不會被誤認為真的 API key）。Alternative「`os.environ.get("OLLAMA_API_KEY", "ollama")`」拒絕，因為 Ollama 沒有 API key 概念，env 變數不存在的話 fallback 到 sentinel；單純 hard-code sentinel 更乾淨。

### `OllamaChatModel.chat()` / `.stream()` wrap `openai.APIConnectionError` 為 `ConnectionError`

Rationale：openai SDK 連不到 daemon 時拋 `openai.APIConnectionError` 並帶長串 stack trace（含 httpx 細節），學生看不懂；wrap 後變 `ConnectionError("Cannot reach Ollama daemon at http://localhost:11434/v1. Is `ollama serve` running? Install: https://ollama.com/download — then `ollama pull <model>` before retrying.")` 含三條 actionable 指令。Alternative「不 wrap、讓 openai SDK error 原身拋出」拒絕，違反教學框架的 UX 約定。Implementation：override `chat` 與 `stream` 兩個方法，內層 `try: return super().chat(...)` `except openai.APIConnectionError as exc: raise ConnectionError(actionable_msg) from exc`，message 要可 grep（子字串 testable）。

### `[ollama]` 是 documentary-alias extras group，依附 `[openai]`

選 alias。Rationale：Ollama adapter 用的是 openai SDK（依 base_url 切端點），不需要新 third-party package；但學生看 `pip install cantus[openai]` 來裝 Ollama 路徑會困惑（為何不是 `[ollama]`？）。Documentary alias `ollama = ["cantus-agent[openai]"]` 沿用 v0.4.1 cantus-serve-security 立下的 `security = ["cantus-agent[serve]"]` pattern——零新 deps、學生有字面選項。Alternative「`ollama = ["ollama>=0.4,<1"]` 配獨立 `OllamaChatModel` 用 ollama SDK」拒絕，純增加 supply-chain。Alternative「不加 extras、學生記得 `cantus[openai]` 同時是 Ollama 路徑」拒絕，違反字面意圖。

**`[tool.uv] conflicts` mirroring 條目**：原本以為跟 `security` 一樣零新 `[tool.uv]` 條目即可，但 `security` 的 alias target `serve` 不在 conflicts list、而 `ollama` 的 alias target `openai` 既有與 `openhands` 的 conflict pair（v0.4.0 cantus-uv-cross-platform-install ship）。`uv sync` 做 universal resolution 時不會自動 propagate alias-target conflicts 到 alias key，導致只要 `[ollama]` 沒列為衝突項，uv 就會嘗試 `[ollama] + [openhands]` 一起 resolve 而失敗（litellm 透過 openhands-sdk 拉 openai>=2.20.0，與 `[openai] >=1.50,<2` 不相容）。本 change 因此在 `[tool.uv].conflicts` 鏡像加 `[{ extra = "ollama" }, { extra = "openhands" }]`——只鏡像 `openai` 既有的衝突 pair、不引入新的，spec scenario「ollama extras mirrors openai extras conflict pairs」codify 這條規則供未來新 alias 套用。

### `cloudflared` tunnel 走 docs walkthrough，不引入 SDK / 不加進 main CI smoke

選 docs-only + 獨立 integration test。Rationale：cloudflared 是 Go 寫的 daemon CLI，沒有 Python wrapper（cloudflare/python-cloudflare 是 API client、不是 tunnel daemon），學生要的是「裝 cloudflared、跑一行命令、拿公網 URL」這條 path——加 Python wrapper 是過度設計。獨立 `tests/integration/test_tunnel_smoke.py` 跑 `cloudflared --version` smoke 而非加進 `.github/workflows/cross-platform-install.yml` 是為了避免 main CI runner 沒裝 cloudflared 而跳 step（這違反 A0 的 tri-platform smoke 「全綠」承諾）。Alternative「在 `cross-platform-install.yml` 三 OS 各加 `cloudflared --version` step」拒絕；Alternative「不寫任何 smoke、純 docs」拒絕，因為 Gate A 的 `/humane-prose-audit` 會要求 `cloudflared --url` flag 拼字正確、有可驗證的 binary 存在路徑。

### tunnel 段擺在「Serve via CLI」之後、Ollama 段取代既有 placeholder

選位置定錨：Ollama 段取代既有 `## What about local LLMs on macOS / Windows?`、tunnel 段插入既有 `## Serve via CLI` 之後。Rationale：placeholder 已自我宣稱「ships with the upcoming `cantus-local-llm-ollama-bridge` capability (A1)」，本 change 是 A1'（合 A1+A3），就地取代最自然；tunnel 段 logically 在「跑起 server」之後（必須先有 `cantus serve` 才有東西要 expose），擺在 `## Serve via CLI` 之後 reading flow 最順。Alternative「tunnel 段擺在文件最末」拒絕，會跟「Where to go next」競爭。

### MODIFIED Requirement 走 `model-providers` 既有 capability 而非塞進新 capability

選 MODIFIED。Rationale：`load_chat_model` 是 `model-providers` capability 的核心 Requirement「load_chat_model factory dispatches by provider prefix with lazy import」（spec.md L72-L107）已明列「v0.2.1 ships only openai/anthropic/google/groq/nvidia」並有 prefix dispatch table——本 change 把這個列舉從 5 延伸到 6。若把「Ollama 加進 factory」這條塞進新 capability `cantus-local-llm-and-desktop-walkthrough`，就跟 `model-providers` 既有 Requirement 衝突（同一行為兩 spec 描述不一致）；走 MODIFIED 維持單一真相來源。新 capability 只負責 Ollama adapter 自身行為（subclass / base_url / sentinel / conn-error）+ docs + tunnel smoke。

## Implementation Contract

**Behavior**：使用者執行 `pip install cantus[ollama]` 後，`from cantus import load_chat_model; chat = load_chat_model("ollama/gemma3:4b")` 不需 env var 即回 `OllamaChatModel` instance；只要 Ollama daemon 在 `localhost:11434` 跑（`ollama serve`），`chat.chat([Message(role="user", content="hi")])` 即回 `ChatResponse`。daemon 沒跑時，`chat()` / `stream()` 拋 `ConnectionError` 含 `"Cannot reach Ollama daemon at http://localhost:11434/v1. Is \`ollama serve\` running?"` 子字串。學生讀 `docs/quickstart-desktop.md` 可循三段：API key（既有）→ Local LLMs via Ollama（裝 ollama → `ollama pull gemma3:4b` → `load_chat_model("ollama/gemma3:4b")`）→ Expose via Cloudflare Tunnel（裝 cloudflared → `cloudflared tunnel --url http://127.0.0.1:8765` → 拿公網 URL）；tunnel section 含 security note 警告 token 不持久化。

**Interface**：

- 新 Python class：`cantus.model.providers.ollama.OllamaChatModel(OpenAIChatModel)`
  - constructor 簽章 `__init__(self, model_id: str, api_key: str | None = None, base_url: str | None = None, **client_kwargs: Any)`
  - constructor 行為：`api_key=api_key if api_key is not None else "ollama"`、`base_url=base_url if base_url is not None else "http://localhost:11434/v1"`、`super().__init__(model_id=model_id, api_key=resolved_key, base_url=resolved_url, **client_kwargs)`
  - override 兩方法：`chat(messages, tools=None, **kwargs)` 與 `stream(messages, tools=None, **kwargs)` 各自 wrap `openai.APIConnectionError` → `ConnectionError`
  - class attr 繼承：`supports_tool_use = True`（沿用 OpenAIChatModel；學生需自行驗證所選 model 支援 function calling）
- 新 module constants：`OLLAMA_BASE_URL = "http://localhost:11434/v1"`、`OLLAMA_API_KEY_SENTINEL = "ollama"`
- 新 factory registry entry：`_REGISTRY["ollama"] = ("cantus.model.providers.ollama", "OllamaChatModel")`、`_EXTRAS_HINT["ollama"] = "openai"`
- 新 pyproject extras：`ollama = ["cantus-agent[openai]"]`（位置：跟在 `security` 後、`providers` 前）
- 新 docs sections（`docs/quickstart-desktop.md`，全英文，Required canonical 維持）：
  - `## Local LLMs via Ollama`（取代既有 `## What about local LLMs on macOS / Windows?` placeholder）
  - `## Expose via Cloudflare Tunnel`（插入既有 `## Serve via CLI` 段之後）
  - `## Where to go next` 補一條 cross-link
- 新 test：`tests/integration/test_tunnel_smoke.py::test_cloudflared_version_when_installed`（skip if `cloudflared` 不在 PATH 或 `FileNotFoundError`）

**Failure modes**：

- Ollama daemon unreachable（`openai.APIConnectionError` raised by openai SDK）→ `OllamaChatModel.chat()` / `.stream()` re-raise as `ConnectionError`，message 含子字串 `"Cannot reach Ollama daemon"` + `"http://localhost:11434/v1"`（或 user override 的 base_url）+ `"ollama serve"`
- Ollama daemon 跑但 model 沒 pull（HTTP 404 from `/v1/chat/completions`）→ openai SDK 原 `openai.NotFoundError` 拋出（不 wrap，由學生 `ollama pull` 解決；本 change 不負責 model-not-pulled UX）
- `load_chat_model("ollama/...")` 在環境沒裝 `openai` 套件時 → `ImportError("adapter for provider 'ollama' requires its optional extras. Run: pip install cantus[openai]")`（透過 `_EXTRAS_HINT["ollama"] = "openai"`）
- `cloudflared` 沒裝 → `subprocess.run(["cloudflared", "--version"])` `FileNotFoundError` → `tests/integration/test_tunnel_smoke.py` 用 `pytest.skip("cloudflared not installed")` 跳過

**Acceptance criteria**：

- `python -c "from cantus.model.providers.ollama import OllamaChatModel; print(OllamaChatModel.__mro__)"` 輸出含 `OpenAIChatModel`
- `python -c "from cantus import load_chat_model; m = load_chat_model('ollama/gemma3:4b'); print(type(m).__name__)"` 輸出 `OllamaChatModel`，**且**該指令在沒設 `OLLAMA_API_KEY` env 也不會拋 `MissingAPIKeyError`
- `uv pip install --dry-run -e ".[ollama]"` 與 `uv pip install --dry-run -e ".[openai]"` 解析閉包相同
- `grep -F "ollama pull gemma3:4b" docs/quickstart-desktop.md` 命中
- `grep -F "cloudflared tunnel --url http://127.0.0.1:8765" docs/quickstart-desktop.md` 命中
- `grep -E "^### Requirement: load_chat_model factory dispatches by provider prefix" openspec/changes/cantus-local-llm-and-desktop-walkthrough/specs/model-providers/spec.md` 命中（MODIFIED Requirement 出現）
- `pytest tests/integration/test_tunnel_smoke.py -v` 在 cloudflared 已裝環境 1 pass；未裝環境 1 skip
- `pytest tests/providers/test_ollama_adapter.py tests/providers/test_ollama_connection_error.py tests/model/test_factory.py --no-cov` 全綠（預期 5 + 2 + N 條 unit test，N = 既有 factory test 數 + 2 新增）
- `spectra validate cantus-local-llm-and-desktop-walkthrough` 通過

**Scope boundaries**：

- In scope：`cantus/model/providers/ollama.py`、`cantus/model/factory.py` 兩處 dict、`pyproject.toml` 一條 extras alias、`docs/quickstart-desktop.md` 兩段新增 + 一條 cross-link、`tests/providers/test_ollama_*.py` × 2、`tests/integration/test_tunnel_smoke.py`、`tests/model/test_factory.py` 兩條 extend、新 spec capability + `model-providers` MODIFIED Requirement
- Out of scope：`cantus.serve()` / `Settings` / `AuthMode` / `cantus serve` CLI surface（C1 freeze）；`bitsandbytes` sys_platform marker（A0 freeze）；`.github/workflows/cross-platform-install.yml` 三 OS smoke matrix（A0 freeze）；`cantus init` / `cantus skill list` 等新子命令；章節 notebook / 習題 / 評量（課程材料分工）；MIGRATION + CHANGELOG entries（apply 階段填）；A1' 之後的 Gate A audit（不在 apply 範圍）

## Risks / Trade-offs

- [Ollama 端 `gemma3:4b` model tag 可能 drift] → docs 只 reference 一次（不在 code 寫死）；CHANGELOG 註明「model availability 由 `ollama pull` 主導，cantus 不擋」；`OllamaChatModel(model_id="<anything>")` 純字串 pass-through，學生 model rename 自行調整
- [Cloudflare quick tunnel mode 預設未認證、任何拿到 URL 都能打 FastAPI app] → tunnel section 顯式 cross-link `cantus serve --auth-mode bearer`（C1 已 ship）並建議「tunnel + auth 一起用」；Gate A `/spectra-audit` 規則含「tunnel 段必須出現 auth cross-link」
- [`OllamaChatModel` 繼承 `supports_tool_use = True` 但實際 `gemma3:4b` 可能不支援 tool calling] → docstring + docs 段標「tool-use 是 model-dependent」；不在 adapter 層做 capability 探測（會打網路、慢），保留誠實的 capability 宣告
- [docs/quickstart-desktop.md 接近 100 行，新增 tunnel 段後可能過長] → 章節清楚標題即可（每段 < 20 行）；若超過 120 行考慮拆 `docs/cookbook/serve_tunnel.md`（但本 change 不做，YAGNI）
- [`tests/integration/test_tunnel_smoke.py` 在 CI 上一律 skip] → 既有 `tests/` 沒有 `integration/` 子目錄，新增首個 integration test；`pytest.skip` reason 字串 grep-able 讓 CI log 可見「intentional skip」而非「test missing」

## Migration Plan

- 對 PyPI 下游純加 surface（新 extras alias + 新 provider class）、非 breaking
- v0.4.3 → v0.4.4（或下一版次，由 apply 階段定）；本 change 不寫死版本字串
- apply 完成後寫 `MIGRATION_v0.4.3_to_v0.4.4.md`（或對應檔）含一段 Ollama provider availability + 三 OS local-LLM path note
- CHANGELOG `[Unreleased]` 區段加「Added: Ollama provider (`ollama/<model>`) + desktop walkthrough for local LLMs and Cloudflare Tunnel」
- rollback strategy：純加 code，刪除 `cantus/model/providers/ollama.py` + 還原 factory dict + 還原 docs sections 即恢復；無 data migration、無 schema 變動

## Open Questions

- 無
