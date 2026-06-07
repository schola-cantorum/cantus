<!--
慣例：每個任務描述「完成後可觀察到什麼行為／契約」＋「如何驗證」。檔案路徑只是定位脈絡，不是任務本體。
[P] = 可與同群其他 [P] 任務並行（動到不同檔、無相依）。TDD：先紅測試 → 再實作到綠。
-->

## 1. Prerequisites（對照 design 的 Goals 與 Non-Goals 範圍邊界）

- [x] 1.1 讀 `proposal.md` / `design.md`（含 Goals 與 Non-Goals 範圍邊界）/ 兩份 spec delta，確認 baseline：`load_chat_model` 現有六個 provider 測試全綠（`uv run --extra dev --extra providers pytest tests/test_factory.py -q`）。驗證：指令全綠且輸出含現有 provider 測項。

## 2. MLXChatModel 適配器（design D1：直接實作 ChatModel／D2：tokenizer chat template／D3：tools 報錯／D4：平台 gating）

- [x] 2.1 [P] Test（紅）：在 `tests/providers/test_mlx_adapter.py` 以 monkeypatch 假造 `mlx_lm`（`load`/`generate`/`stream_generate`），新增測試斷言 (a) `isinstance(MLXChatModel("m"), cantus.model.chat.ChatModel)`、(b) `model_id` 正確、(c) 建構不呼叫 `mlx_lm.load`（lazy）。對應 spec scenarios「satisfies the ChatModel Protocol shape」「construction does not load weights eagerly」。驗證：`pytest tests/providers/test_mlx_adapter.py -q` 先紅（無 mlx.py）。
- [x] 2.2 Code：新增 `cantus/model/providers/mlx.py` 的 `MLXChatModel`（直接實作 ChatModel Protocol、`supports_tool_use=False`、`model_id` 設定、lazy `mlx_lm.load`），使 2.1 轉綠。實作 Requirement: MLXChatModel implements the Tier 2 ChatModel Protocol against mlx-lm。驗證：`pytest tests/providers/test_mlx_adapter.py -q` 綠。
- [x] 2.3 Test（紅）：擴充 `tests/providers/test_mlx_adapter.py`，斷言 `chat()` 回傳 `ChatResponse(message.role="assistant", content=<generated text>, stop_reason="end_turn")`、`stream()` 依序 yield 文字 delta。對應 spec scenarios「chat returns a ChatResponse carrying the generated text」「stream yields text deltas」。驗證：新增測項先紅。
- [x] 2.4 Code：在 `mlx.py` 實作 `chat`（tokenizer chat template → `mlx_lm.generate` → ChatResponse）與 `stream`（`mlx_lm.stream_generate` yield delta），使 2.3 轉綠。驗證：`pytest tests/providers/test_mlx_adapter.py -q` 綠。
- [x] 2.5 Test（紅）：擴充 `tests/providers/test_mlx_adapter.py`，斷言 `supports_tool_use is False`、`chat(..., tools=[{...}])` 與 `stream(..., tools=[{...}])` 皆拋 `NotImplementedError` 且訊息含 `MLXChatModel does not support tool use`。對應 spec「reports no tool-use support and rejects tool arguments」三個 scenarios。驗證：新增測項先紅。
- [x] 2.6 Code：在 `mlx.py` 的 `chat`/`stream` 開頭加入非空 `tools` → `NotImplementedError` 守衛，使 2.5 轉綠。實作 Requirement: MLXChatModel reports no tool-use support and rejects tool arguments。驗證：`pytest tests/providers/test_mlx_adapter.py -q` 綠。
- [x] 2.7 Test（紅）：擴充 `tests/providers/test_mlx_adapter.py`，模擬 `mlx_lm` import 失敗 與 非 arm64/非 darwin 平台，斷言拋 `ImportError` 且訊息含 `pip install cantus[mlx]`；非 Apple-Silicon 時另含 `Apple Silicon` 與 `arm64`。對應 spec「surfaces an actionable error when mlx-lm is unavailable or the platform is not Apple Silicon」兩個 scenarios。驗證：新增測項先紅。
- [x] 2.8 Code：在 `mlx.py` 模組層加入 mlx_lm import 守衛與平台偵測（`sys.platform` / `platform.machine()`），拋出含上述子字串的可行動 `ImportError`，使 2.7 轉綠。實作 Requirement: MLXChatModel surfaces an actionable error when mlx-lm is unavailable or the platform is not Apple Silicon。驗證：`pytest tests/providers/test_mlx_adapter.py -q` 綠。

## 3. Factory 註冊（model-providers）

- [x] 3.1 [P] Test（紅）：在 `tests/test_factory.py` 新增斷言 `_REGISTRY["mlx"] == ("cantus.model.providers.mlx", "MLXChatModel")`、`_EXTRAS_HINT["mlx"] == "mlx"`、未知前綴 `ValueError` 訊息含 `mlx`、缺 mlx extras 的 `load_chat_model("mlx/...")` 拋 `ImportError` 且訊息含 `pip install cantus[mlx]`。對應 model-providers 兩個新 scenarios。驗證：新增測項先紅。
- [x] 3.2 Code：在 `cantus/model/factory.py` 的 `_REGISTRY` 與 `_EXTRAS_HINT` 加入 `mlx`，並把 module docstring「six providers」更新為「seven providers」（含 mlx），使 3.1 轉綠。實作 Requirement: load_chat_model factory dispatches by provider prefix with lazy import。驗證：`pytest tests/test_factory.py -q` 綠。

## 4. Extras 與 packaging（design D5：mlx extras）

- [x] 4.1 [P] Test（紅）：新增 pyproject 解析測試（與既有 pyproject 測試同檔/同風格），斷言 `[project.optional-dependencies].mlx` 恰含一個 `mlx-lm` 需求字串、含 marker `platform_machine == 'arm64'` 與 `sys_platform == 'darwin'`、且 `[tool.uv].conflicts` 恰一條 pair 提及 `mlx` 且配 `huggingface`（無其他 mlx pair）。對應 spec「mlx is a platform-scoped extras group」兩個 scenarios。驗證：新增測項先紅。
- [x] 4.2 Code：在 `pyproject.toml` `[project.optional-dependencies]` 新增 `mlx = ["mlx-lm>=0.31,<1; sys_platform == 'darwin' and platform_machine == 'arm64'"]`（0.31.3 為當時最新穩定版）；並新增一條 `mlx`↔`huggingface` `[tool.uv] conflicts`（mlx-lm>=0.31.1 拉 `transformers>=5`，與 huggingface 的 `transformers<5` 互斥；apply 階段實測修正），使 4.1 轉綠。實作 Requirement: mlx is a platform-scoped extras group for Apple Silicon。驗證：`pytest <pyproject 測試> -q` 綠 + `uv run --extra dev pytest`（universal resolution 成功）+ `uv pip install --dry-run -e '.[mlx]'` 在本機 arm64 成功解析。

## 5. Smoke 與文件

- [x] 5.1 [P] Test：新增 `tests/integration/test_mlx_smoke.py`，以 `pytest.importorskip("mlx_lm")` 開頭，做最小 `load_chat_model("mlx/<小模型>")` + 一次短 `chat` smoke（非 arm64/未裝 mlx 自動 skip）。驗證：本機未裝 mlx 時該檔 skip、裝了則綠。
- [x] 5.2 [P] Docs：在 `docs/quickstart-desktop.md` 新增 `## Local LLMs via MLX (Apple Silicon)` 段（英文），含 `pip install cantus[mlx]`、`load_chat_model("mlx/` Python 範例、明示僅支援 Apple Silicon (macOS arm64)、明示首版不支援 tool use。對應 spec「docs/quickstart-desktop.md adds a Local LLMs via MLX (Apple Silicon) section」兩個 scenarios。驗證：`grep -E '^## Local LLMs via MLX \(Apple Silicon\)$' docs/quickstart-desktop.md` 恰一筆，且 `grep -F 'pip install cantus[mlx]' docs/quickstart-desktop.md`、`grep -F 'load_chat_model("mlx/' docs/quickstart-desktop.md` 各有命中。

## 6. 整體驗證

- [x] 6.1 全測：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/ -q` 全綠（mlx 未裝 → smoke skip，其餘 mlx 契約測試以假造模組通過）。驗證：exit 0、無 fail。
- [x] 6.2 Lint/型別：`ruff check cantus/model/providers/mlx.py cantus/model/factory.py tests/providers/test_mlx_adapter.py` 與 `mypy cantus/model/providers/mlx.py cantus/model/factory.py` 對改動檔 clean（delta-0）。驗證：兩指令 exit 0。
- [x] 6.3 Spectra：`spectra validate cantus-local-llm-mlx-path` pass。驗證：輸出 valid。

## 7. 版本欄位（DEFERRED）

- [x] 7.1 （DEFERRED）不得改動 `pyproject.toml` 的 `version =`、`CHANGELOG.md`、`docs/migrations/`。`pyproject.toml` 僅允許新增 `mlx` extras（功能本身）。驗證：`git diff --name-only` 不含版本欄位變更（`grep '^version' pyproject.toml` 維持原值）。
