## Why

cantus v0.4.3 ship 後，C1（`cantus-serve-cli`，PR #5 squash `7cb4f59`）已補上 `cantus serve` 命令，但 `docs/quickstart-desktop.md` 在「`## What about local LLMs on macOS / Windows?`」段仍是 placeholder，明寫「ships with the upcoming `cantus-local-llm-ollama-bridge` capability (A1)」——這個坑要 A1' 補。本 change 合併 roadmap A1（Ollama bridge）+ A3（desktop walkthrough 完工）為一件，原因：兩件改的是同一份學生材料，合一件少跑一輪 propose/validate/Gate；教學終點是「學生在筆電（Win/macOS/Linux）跑通 LINE/Discord/Telegram/Google Chat demo」，本機 LLM 統一走 **Ollama bridge**（bnb 4-bit Gemma 只留 Linux+CUDA，其它平台走 Ollama），同時補上 Cloudflare Tunnel walkthrough 讓 `cantus serve` 可暴露成公網 URL（後續 B 系列 webhook channel 直接用）。

## What Changes

- 新增 `cantus/model/providers/ollama.py`：`OllamaChatModel(OpenAIChatModel)` thin subclass——default `base_url="http://localhost:11434/v1"`（Ollama 預設 daemon 埠）、default `api_key="ollama"` sentinel（Ollama 不認 API key 但 openai SDK 要求非空字串）、`chat()` / `stream()` 在 `openai.APIConnectionError` 時 re-raise 為 `ConnectionError` 並含 actionable message（含 base_url + `ollama serve` + install link）
- 修改 `cantus/model/factory.py`：`_REGISTRY` 加 `"ollama": ("cantus.model.providers.ollama", "OllamaChatModel")`、`_EXTRAS_HINT` 加 `"ollama": "openai"`（沿用 NVIDIA NIM pattern，install 走 `cantus[openai]`）；模組 docstring 從「v0.2.1 五 providers」更新成「六 providers」
- 修改 `pyproject.toml`：`[project.optional-dependencies]` 新增 `ollama = ["cantus-agent[openai]"]` documentary alias（仿 v0.4.1 `security = ["cantus-agent[serve]"]` pattern），不引入新 third-party dependency
- 修改 `docs/quickstart-desktop.md`：將既有 `## What about local LLMs on macOS / Windows?` placeholder 段改寫為 `## Local LLMs via Ollama`（含 install 步驟、`ollama pull gemma3:4b`、`load_chat_model("ollama/gemma3:4b")` Python 範例、三 OS 支援聲明、tool-use model-dependent 提醒）；在既有 `## Serve via CLI` 段之後插入 `## Expose via Cloudflare Tunnel` 段（含 cloudflared 安裝 + `cloudflared tunnel --url http://127.0.0.1:8765` + security note 警告 quick-tunnel 不持久化 token / named-tunnel 勿 commit cert.pem）；`## Where to go next` 補一條 cross-link 到 `docs/llm_wiki/research/cloudflare_tunnel_vs_ngrok.md`
- 新增 `tests/integration/test_tunnel_smoke.py`：cloudflared 已裝時 `subprocess.run(["cloudflared", "--version"], check=False)` assert exit 0、未裝時 `pytest.skip` 不擋 CI
- 新 capability `cantus-local-llm-and-desktop-walkthrough` spec：規範 Ollama provider 行為（base_url default / api_key sentinel / conn-error UX）、`[ollama]` documentary-alias extras、quickstart-desktop 兩段新增 docs 內容、tunnel smoke test 行為
- 修改既有 `model-providers` capability：擴充 `load_chat_model` 支援的 provider prefix 列表從 5 個（openai / anthropic / google / groq / nvidia）變 6 個（加 ollama）；更新 prefix dispatch table 含 ollama 列；MODIFIED Requirement 對應 spec.md L72-L107 的「load_chat_model factory dispatches by provider prefix with lazy import」

## Non-Goals (optional)

- **不**引入 `ollama` Python SDK——Ollama 完全相容 OpenAI Chat Completions wire，subclass `OpenAIChatModel` 即可重用 translators / streaming / tool-call handling
- **不**引入 `cloudflared` Python wrapper / SDK / `cantus.serve` 整合 code——tunnel 純 docs walkthrough，學生自行裝 cloudflared 跑命令
- **不**寫章節 notebook / 習題 / 評量——課程材料由使用者自備（[[project_teaching_context]] 已明定 repo 只負責 framework）
- **不**動 `cantus.serve()` / `Settings` / `AuthMode` / `cantus serve` CLI surface——C1 剛 ship freeze
- **不**破 `bitsandbytes>=0.43.0; sys_platform == 'linux'` marker——A0 已立的 cantus-distribution Requirement
- **不**新增 `cantus-distribution` 的跨平台 install smoke step——tunnel smoke 走獨立 `tests/integration/test_tunnel_smoke.py`，不擠進 `.github/workflows/cross-platform-install.yml`（避免 main CI 因 cloudflared 沒裝跳 step）
- **不**改 `cantus-i18n-docs` 的 quickstart-desktop English-only Required canonical 規範——本 change 新增的兩段都用英文寫
- **不**改 `MIGRATION_*.md` / `CHANGELOG.md`——bookkeeping 由 apply 階段依當下版本號定，本 propose 不寫死版本字串
- Alternative「為 Ollama 開獨立 extras group `ollama = ["ollama>=0.4,<1"]`」——拒絕，因為 openai SDK 已能跑、加 `ollama` SDK 純增加 supply-chain surface
- Alternative「不 wrap connection error、讓 `openai.APIConnectionError` 原身拋出」——拒絕，學生看到 openai SDK trace 而非 cantus 友善提示，違反教學框架的 UX
- Alternative「tunnel section 用 ngrok 而非 cloudflared」——拒絕，`docs/llm_wiki/research/cloudflare_tunnel_vs_ngrok.md` 已明定 cloudflared 為 cantus 教學的 default（無 token 即可起、隨機公網 URL、Ctrl-C 收乾淨）

## Capabilities

### New Capabilities

- `cantus-local-llm-and-desktop-walkthrough`: Ollama provider 註冊 + `[ollama]` documentary-alias extras + quickstart-desktop 兩段新增 docs（Local LLMs via Ollama + Expose via Cloudflare Tunnel）+ tunnel smoke test 的合一 capability

### Modified Capabilities

- `model-providers`: 擴充 `load_chat_model` 支援的 provider prefix 列表（5 → 6，加 ollama）；對應既有 Requirement「load_chat_model factory dispatches by provider prefix with lazy import」的 prefix 列舉、ValueError 訊息、dispatch table 三處需同步更新

## Impact

- Affected specs: 新 `cantus-local-llm-and-desktop-walkthrough`（`openspec/specs/cantus-local-llm-and-desktop-walkthrough/spec.md` 於 archive 時建立）；既有 `model-providers`（`openspec/specs/model-providers/spec.md` MODIFIED Requirement）
- Affected code:
  - New: `cantus/model/providers/ollama.py`、`tests/providers/test_ollama_adapter.py`、`tests/providers/test_ollama_connection_error.py`、`tests/integration/__init__.py`、`tests/integration/test_tunnel_smoke.py`
  - Modified: `cantus/model/factory.py`（`_REGISTRY` + `_EXTRAS_HINT` + docstring）、`pyproject.toml`（`[project.optional-dependencies]` 加 `ollama` 行）、`docs/quickstart-desktop.md`（既有 placeholder 段改寫 + 新增 tunnel 段 + 「Where to go next」cross-link）、`tests/model/test_factory.py`（extend with ollama-in-registry + ollama-extras-hint asserts）
  - Removed: （無）
- Dependencies: 不新增 third-party package；`[ollama]` 解析到 `cantus[openai]` 的閉包（`openai>=1.50,<2`），已在既有 lock
- 對 PyPI 下游：新增 console-visible install 字面 `pip install cantus[ollama]`；既有 `pip install cantus[openai]` 不變；不破任何既有 programmatic API
- CI 行為：既有 `cross-platform-install.yml` 三 OS smoke matrix 不變；新增 `tests/integration/test_tunnel_smoke.py` 由 `pytest tests/` 自動收集，cloudflared 已裝跑、沒裝跳 skip
- 教學文件：A1' ship 後，`docs/quickstart-desktop.md` 完整覆蓋三 OS 學生 path（API key / Ollama local / Cloudflare Tunnel exposed）；A1' 後跟 A0 + C1 一起進 Gate A 雙閘 audit
