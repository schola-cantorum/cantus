<!--
慣例：每個任務描述「完成後可觀察到什麼行為／契約」＋「如何驗證」。檔案路徑只是定位脈絡，不是任務本體。
[P] = 可與同群其他 [P] 任務並行（動到不同檔、無相依）。TDD：先紅測試 → 再實作到綠。
-->

## 1. Prerequisites（對照 design 的 Goals 與 Non-Goals 範圍邊界）

- [x] 1.1 讀 `proposal.md` / `design.md`（含 Goals 與 Non-Goals 範圍邊界、D1–D7）/ 兩份 spec delta，確認 baseline：`load_chat_model` 現有七個 provider（openai/anthropic/google/groq/nvidia/ollama/mlx）測試全綠。驗證：`uv run --extra dev --extra providers pytest tests/test_factory.py -q` 全綠且輸出含現有 provider 測項。

## 2. OmlxChatModel 適配器（design D1：薄 OpenAIChatModel 子類／D2：base_url 必填／D3：sentinel api_key／D4：supports_tool_use 繼承／D5：ConnectionError 覆寫）

- [x] 2.1 [P] Test（紅）：在 `tests/providers/test_omlx_adapter.py` 以假造 `openai` client（比照既有 nvidia/ollama 契約測試風格）新增測試斷言 (a) `isinstance(OmlxChatModel(model_id="m", base_url="http://localhost:8000/v1"), cantus.model.chat.ChatModel)`、(b) 亦為 `OpenAIChatModel` 子類、(c) `model_id` 正確、(d) `base_url` 原樣傳入底層 `openai.OpenAI` client。對應 spec scenarios「satisfies the ChatModel Protocol and subclasses OpenAIChatModel」「base_url passes through to the underlying OpenAI SDK client」。驗證：`pytest tests/providers/test_omlx_adapter.py -q` 先紅（無 omlx.py）。
- [x] 2.2 Code：新增 `cantus/model/providers/omlx.py` 的 `OmlxChatModel(OpenAIChatModel)`（建構子簽章 `(model_id, api_key=None, base_url=None, **client_kwargs)`、繼承 `chat`/`stream`/translators），使 2.1 轉綠。實作 Requirement: OmlxChatModel is a thin OpenAIChatModel subclass over a local OpenAI-compatible MLX server。驗證：`pytest tests/providers/test_omlx_adapter.py -q` 綠。
- [x] 2.3 Test（紅）：擴充 `tests/providers/test_omlx_adapter.py`，斷言 (a) 省略 `base_url` 建構拋 `ValueError` 且訊息同時含 `http://localhost:8000/v1` 與 `http://localhost:10240/v1`；(b) `OPENAI_API_KEY`/`OMLX_API_KEY` 未設時建構不拋且 resolved api_key == sentinel `"omlx"`；(c) 明確 `api_key="proxy-token"` 被保留；(d) `OmlxChatModel.__doc__` 揭露 api_key 對伺服器非權威；(e) `OmlxChatModel.supports_tool_use is True` 且 `"supports_tool_use" not in OmlxChatModel.__dict__`。對應 spec scenarios（base_url 必填二則、sentinel 三則、tool-use 一則）。驗證：新增測項先紅（(a)(b)(c)(d) 紅；(e) 待 2.2 子類即綠，仍納入此測試檔）。
- [x] 2.4 Code：在 `omlx.py` 實作建構子——`base_url is None` 時拋 `ValueError`（訊息含兩個範例 endpoint）；`api_key is None` 時填入 module 常數 `OMLX_API_KEY_SENTINEL = "omlx"`、不讀任何環境變數；class docstring 揭露 api_key 非權威；不在子類重定義 `supports_tool_use`（繼承 `True`）——使 2.3 轉綠。實作 Requirement: OmlxChatModel requires an explicit base_url；實作 Requirement: OmlxChatModel uses a sentinel api_key and never consults the environment；實作 Requirement: OmlxChatModel reports tool-use support。驗證：`pytest tests/providers/test_omlx_adapter.py -q` 綠。
- [x] 2.5 Test（紅）：擴充 `tests/providers/test_omlx_adapter.py`，以假造 client 在請求時拋 `openai.APIConnectionError`，斷言 (a) `chat(...)` 改拋 `ConnectionError` 且訊息含 `http://localhost:8000/v1`、`__cause__` 為原 `APIConnectionError`；(b) `stream(...)` 迭代亦拋 `ConnectionError` 含該 URL；(c) 假造 client 拋 `openai.NotFoundError` 時 `chat(...)` 原樣傳播 `NotFoundError`（非 `ConnectionError`）。對應 spec「surfaces an actionable ConnectionError when the server is unreachable」三個 scenarios。驗證：新增測項先紅。
- [x] 2.6 Code：在 `omlx.py` 覆寫 `chat`/`stream`，以 `try: super().… except openai.APIConnectionError as exc: raise ConnectionError(<含 self._base_url 與啟動 omlx／mlx-omni-server 指引> ) from exc`，其他 openai 例外不攔截，使 2.5 轉綠。實作 Requirement: OmlxChatModel surfaces an actionable ConnectionError when the server is unreachable。驗證：`pytest tests/providers/test_omlx_adapter.py -q` 綠。

## 3. Factory 註冊（model-providers）

- [x] 3.1 [P] Test（紅）：在 `tests/test_factory.py` 新增斷言 `_REGISTRY["omlx"] == ("cantus.model.providers.omlx", "OmlxChatModel")`、`_EXTRAS_HINT["omlx"] == "openai"`、未知前綴 `ValueError` 訊息含 `omlx`、缺 openai 套件的 `load_chat_model("omlx/qwen2.5-coder-7b", base_url="http://localhost:8000/v1")` 拋 `ImportError` 且訊息含 `pip install cantus[openai]` 但不含有別於 `cantus[openai]` 的 `cantus[omlx]` 提示、`omlx` 前綴派發到 `OmlxChatModel` 且 `model_id == "qwen2.5-coder-7b"`。對應 model-providers 的 omlx dispatch 與 missing-extras 兩個新 scenarios。驗證：新增測項先紅。
- [x] 3.2 Code：在 `cantus/model/factory.py` 的 `_REGISTRY` 與 `_EXTRAS_HINT` 加入 `omlx`（hint 指 `openai`），並把 module docstring 的 provider 計數由「seven」更新為「eight」（含 omlx），使 3.1 轉綠。實作 Requirement: load_chat_model factory dispatches by provider prefix with lazy import。驗證：`pytest tests/test_factory.py -q` 綠。

## 4. Extras 與 packaging（design D6：omlx documentary 別名 + omlx↔openhands conflict）

- [x] 4.1 [P] Test（紅）：在 `tests/test_pyproject_extras_conflicts.py`（同檔/同風格）新增斷言 `[project.optional-dependencies].omlx` 恰含一個自指 `cantus-agent[openai]` 需求、不含任何不在 openai 群的第三方套件；且 `[tool.uv].conflicts` 恰一條 pair 提及 `omlx` 並配 `openhands`（無其他 omlx pair）。對應 spec「omlx is a documentary extras alias resolving to cantus[openai]」兩個 scenarios。驗證：新增測項先紅。
- [x] 4.2 Code：在 `pyproject.toml` `[project.optional-dependencies]` 新增 `omlx = ["cantus-agent[openai]"]`，並在 `[tool.uv].conflicts` 新增一條 `[{ extra = "omlx" }, { extra = "openhands" }]`（比照既有 `ollama`↔`openhands`；不新增 mypy override），使 4.1 轉綠。實作 Requirement: omlx is a documentary extras alias resolving to cantus[openai]。驗證：`pytest tests/test_pyproject_extras_conflicts.py -q` 綠 + `uv run --extra dev pytest -q`（universal resolution 成功）。

## 5. 文件

- [x] 5.1 [P] Docs：在 `docs/quickstart-desktop.md` 的 `## Local LLMs via MLX (Apple Silicon)` 段之後、`## Where to go next` 之前新增 `## Local LLMs via omlx (MLX server)` 段（英文），含 `pip install cantus[openai]`、帶顯式 `base_url` 的 `load_chat_model("omlx/` Python 範例、明示泛指本機 OpenAI-compatible MLX 伺服器（omlx :8000／mlx-omni-server :10240）、明示支援 function calling（與 in-process MLX 路線相反）。對應 spec「docs/quickstart-desktop.md adds a Local LLMs via omlx (MLX server) section」兩個 scenarios。驗證：`grep -F '## Local LLMs via omlx (MLX server)' docs/quickstart-desktop.md` 恰一筆且位於 MLX 段之後、`## Where to go next` 之前；`grep -F 'pip install cantus[openai]' docs/quickstart-desktop.md` 與 `grep -F 'load_chat_model("omlx/' docs/quickstart-desktop.md` 各有命中。

## 6. 整體驗證

- [x] 6.1 全測：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/ -q` 全綠（omlx 走既有 openai SDK、契約測試以假造 client 通過）。驗證：exit 0、無 fail。
- [x] 6.2 Lint/型別：`ruff check cantus/model/providers/omlx.py cantus/model/factory.py tests/providers/test_omlx_adapter.py` 與 `mypy cantus/model/providers/omlx.py cantus/model/factory.py` 對改動檔 clean（delta-0）。驗證：兩指令 exit 0。
- [x] 6.3 Spectra：`spectra validate cantus-local-llm-omlx-server` pass。驗證：輸出 valid。

## 7. 版本欄位（design D7：版本欄位 DEFERRED）

- [x] 7.1 （DEFERRED）不得改動 `pyproject.toml` 的 `version =`、`CHANGELOG.md`、`docs/migrations/`；`.github/workflows/test.yml` 亦不變（omlx 走既有 openai extra）。`pyproject.toml` 僅允許新增 `omlx` extras 別名與 omlx↔openhands conflict（功能本身）。驗證：`grep '^version' pyproject.toml` 維持原值；`git diff --name-only` 不含 `CHANGELOG.md`、`docs/migrations/`、`.github/workflows/test.yml`。

## 8. Audit hardening — api_key 空字串 coalesce（spectra-audit MEDIUM finding）

- [x] 8.1 Test（紅）：擴充 `tests/providers/test_omlx_adapter.py`，斷言 `OmlxChatModel(model_id="m", base_url=..., api_key="")` 在 `OPENAI_API_KEY` 已設時 resolved api_key 仍為 sentinel `"omlx"`——空字串視為未提供、不經 parent `resolve_api_key` 落回 env 取到該 key。驗證：先紅（現行 `is not None` 會落回 env 取到 `OPENAI_API_KEY`）。
- [x] 8.2 Code：`omlx.py` 建構子改為 `resolved_key = api_key if api_key else OMLX_API_KEY_SENTINEL`（空字串/falsy 視為未提供），並同步更新 spec R3（「a **non-empty** explicit api_key SHALL be preserved；空字串視為 absent → 用 sentinel、不落回 env」+ 新 scenario）與 design D3 註記，使 8.1 轉綠。實作 Requirement: OmlxChatModel uses a sentinel api_key and never consults the environment。驗證：`pytest tests/providers/test_omlx_adapter.py -q` 綠 + `spectra validate` valid。同源 `OllamaChatModel` 的相同 edge 列為後續 follow-up，本 change 不動 ollama。
