## Summary

cantus v0.3.5 釋出 quality baseline 三項基礎建設（PEP 561 `py.typed` marker、`[tool.mypy]` 設定、`[tool.coverage.*]` + pytest `--cov` 觸發），並在 cantus 內 docs 為 `adapters-batch2.md` 加 supersede note 指向 batch3。ADDITIVE release：0.3.4 → 0.3.5、無 BREAKING、無新 dependency、無新 optional extras、無 cantus public callable 變動。

## Motivation

v0.3.x 教學弧（v0.3.0 protocol-reorg → v0.3.4 adapter-layer-batch3a）封口時，cantus 累積了三項在 release 弧內未補齊的 quality 基礎建設：

1. **`pytest-cov` 已在 `cantus[dev]` 安裝但無 `[tool.coverage.run]` / `[tool.coverage.report]` 設定，且 `[tool.pytest.ini_options].addopts` 不觸發 `--cov`**：開發者跑 `pytest` 看不到 coverage 報告、CI（若日後接入）無 coverage baseline 可比對、refactor 時無法回答「這條 path 有沒有測試覆蓋」。
2. **cantus 套件無 PEP 561 `py.typed` marker**：下游使用 cantus 的 host code（教學 repo、研究專案、第三方 demo）即便開 strict mypy，也無法看到 cantus 的型別提示，所有 import 一律當 `Any` 處理。這個缺口隨著 v0.3.0 protocol-reorg 後 cantus 對外暴露 `Skill / Memory / ChatModel / Soul / AutoMemory / PromptChain` 等 typed 公開 surface 而擴大。
3. **cantus 自身無 `[tool.mypy]` 設定**：cantus repo 內 `.mypy_cache/` 存在表示有人跑過 mypy，但沒有 pinned `python_version`、`check_untyped_defs`、`warn_unused_ignores` 等基準設定，等於每個開發者跑 mypy 行為都不一致。

v0.3.4 batch3a 收尾後也留下一個 cross-link 缺口：`docs/protocols/adapters-batch2.md` 是 v0.3.3 的 batch2 spec snapshot，但 v0.3.4 batch3 釋出後 batch2 的 HF / OpenHands import 段落已 superseded by `adapters-batch3.md`。讀者直接點 batch2 會看到舊措辭（「deferred to v0.3.4 batch3」），不知 batch3 已落地。需在 batch2 開頭加一個 supersede note 明確指向 batch3，把它標示為歷史快照。

v0.3.5 同時解決這四個遺留缺口，作為下個 feature 弧前的最後一次 maintenance release。

## Proposed Solution

**libs/cantus 內變更**：

- **`pyproject.toml`**：
  - 第 7 行 `version = "0.3.4"` → `"0.3.5"`。
  - 新增 `[tool.setuptools.package-data]` 段並設定 `cantus = ["py.typed"]`，讓 wheel build 帶上 marker。
  - 新增 `[tool.coverage.run]` 段：`source = ["cantus"]`、`branch = true`、`omit = ["tests/*", "*/__pycache__/*"]`。
  - 新增 `[tool.coverage.report]` 段：`show_missing = true`、`skip_covered = false`、`exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:", "raise NotImplementedError"]`。
  - `[tool.pytest.ini_options].addopts` 從 `"-v --tb=short"` 改為 `"-v --tb=short --cov=cantus --cov-report=term-missing --cov-report=xml"`，讓 `pytest` 預設帶 coverage 輸出。
  - 新增 `[tool.mypy]` 基準段：`python_version = "3.10"`、`strict = false`（v0.3.5 不引入 type 退步壓力）、`warn_unused_ignores = true`、`warn_redundant_casts = true`、`disallow_untyped_defs = false`、`check_untyped_defs = true`、`ignore_missing_imports = false`。為 cantus 對 optional adapter dependency 加 `[[tool.mypy.overrides]]` 模組 with `ignore_missing_imports = true`，涵蓋 `mcp.*`、`langchain_core.*`、`dspy.*`、`transformers.*`、`openhands.*`、`anthropic.*`、`openai.*`、`google.genai.*`、`groq.*` 等需要 optional extras 才能 import 的 SDK。
- **新建 `cantus/py.typed`**：空檔（PEP 561 marker convention）。
- **`docs/protocols/adapters-batch2.md` 開頭**：在 first H1 / frontmatter 之後新增 supersede 提示段，內容：「**Status: Superseded by `adapters-batch3.md` (cantus v0.3.4) for the HuggingFace and OpenHands import directions; preserved as a v0.3.3 historical snapshot of the batch2 surface.**」並 cross-link 到 batch3 檔案。原 batch2 內 spec 內文 byte-identical 保留。
- **新建 `MIGRATION_v0.3.4_to_v0.3.5.md`**：說明本 release ADDITIVE 性質（host code 不需動）、新增的下游 benefit（strict mypy 在使用 cantus 時可看到 typed surface）、dev workflow 變動（`pytest` 自動跑 cov、`mypy cantus` 有 baseline 可跑），並附簡短 `mypy cantus` 範例命令。
- **`CHANGELOG.md`**：新增 v0.3.5 entry，總結三項 quality baseline 與 adapters-batch2 supersede note。

**主 repo 內變更**：

- **`openspec/specs/cantus-distribution/spec.md`** 透過 spec delta 新增一個 Requirement「Cantus ships PEP 561 py.typed marker and baseline tool configuration」，內含三個 scenarios（py.typed import 可達、mypy strict 下游可看到 typed surface、pytest 觸發 cov 報告）。

**不變更**：

- cantus public callable 完全不動（10 個 `cantus.adapters.*` callable 與 v0.3.4 byte-identical）。
- cantus public dependency 不動（pyproject `dependencies` 仍只有 `pydantic>=2.0`；所有 optional extras 不動）。
- `cantus-distribution` 既有 Requirement「Cantus framework is distributed as standalone GitHub repo」內版本字串保持 `v0.3.4`（v0.3.5 的版本字串更新由獨立的 Change 3 `bump-cantus-pin-to-v0-3-5` 負責，沿用 v0.3.0/v0.3.3/v0.3.4 的 release-content + bump-pin 拆分慣例）。
- 主 repo 學生面 overlay（README、templates、examples、submodule pointer）完全不動，由獨立的 Change 3 處理。

## Non-Goals (optional)

- **不引入 `cantus.adapters.mcp.py` 的新測試**：該模組為 SDK gate 形態，第 1-10 行 docstring 已明確記錄其職責（importing the module triggers the `mcp` SDK import gate；`McpServer` re-export；private bridge functions `_start_server` / `_mcp_list_tools` / `_mcp_call_tool` 供 `mcp_server` / `mcp_client` 使用）。`tests/adapters/test_mcp_server.py` 與 `test_mcp_client.py` 已透過呼叫端 transitively 覆蓋 mcp.py 的 bridge functions。新增 `test_mcp.py` 只能覆蓋 re-export 與 ImportError gate 兩個 trivially-true 行為，價值偏低；延後到日後 strict mypy 啟用時再評估。
- **不 backfill `docs/llm_wiki/synthesis.md`**：v0.1.4 引入時設成 `# (no sources ingested yet)` placeholder；目前 wiki 操作仍正常（research / coding_style / architecture / future_work 四 category 各自獨立運作、validator 不需要 synthesis 內容），synthesis 為 wiki profile 的 optional artifact、非阻礙性，延後到下個 wiki cleanup 弧。
- **不啟用 mypy strict**：strict 模式會在 cantus 既有程式碼上產生大量 warning（特別是 adapter lazy-import 區塊與 protocol Protocol 類別），需要先 audit + 補 annotations。v0.3.5 只做 baseline 設定，strict 啟用排到 v0.4.x。
- **不設 coverage fail-under**：首次引入 coverage 不設失敗門檻，避免「baseline 太高、CI 紅燈」或「baseline 太低、後續難拉」的雙輸局面。先收集兩三個 release 的 baseline 數據後再決定門檻。
- **不引入 ruff format / black 等格式化工具的 baseline**：cantus 既有 `[tool.ruff.lint.per-file-ignores]` 已涵蓋 notebook 例外，但 format 階段未啟用。format 啟用會產生大量 diff、與本 release 的 quality 主題不直接相關，延後。
- **不改變 cantus 對外 callable 或 import 路徑**：v0.3.5 完全 ADDITIVE，host code 不需任何改動。
- **不打 git tag**：cantus 上游 release tag 由人工執行 `git tag v0.3.5` + push 完成；本 change archive 只記錄 release content，tag 動作不在 Spectra 範圍。
- **不在主 repo 開 bump-pin**：那是獨立的 Change 3 `bump-cantus-pin-to-v0-3-5`，等 cantus v0.3.5 commit + tag 出來後另開，沿用 v0.3.0/v0.3.3/v0.3.4 的二段式 release 慣例。

## Alternatives Considered (optional)

- **把 quality baseline 跟 adapter housekeeping 拆成兩個 release（v0.3.5 = quality、v0.3.6 = adapter housekeeping）**：拒絕。adapter housekeeping 經 audit 後只剩 `adapters-batch2.md` supersede note 一行（mcp.py docstring 已存在、synthesis.md 已延後），單獨成一個 release 不划算；併入 v0.3.5 維持 release cadence 簡單。
- **新增獨立的 `quality-baseline` capability spec**：拒絕。py.typed / mypy / coverage 都是 cantus distribution 的子議題（如何 ship、如何驗證、如何讓 host 使用），跟 cantus-distribution 既有「cantus is distributed as standalone GitHub repo」/ 「cantus is licensed under ECL 2.0」/ 「cantus follows SemVer Git tags」一脈相承；併入 cantus-distribution 避免 spec 過度分裂。
- **設 mypy `strict = true`**：拒絕。v0.3.5 不引入 type 退步壓力。strict 開啟需要先 audit + 補 annotation，排到 v0.4.x 處理。
- **設 coverage fail-under = 80 / 60**：拒絕，理由同 Non-Goals 的 fail-under 段。先收集 baseline。

## Impact

- Affected specs:
  - Modified: `openspec/specs/cantus-distribution/spec.md`（ADDED Requirement「Cantus ships PEP 561 py.typed marker and baseline tool configuration」+ 三個 scenarios）
- Affected code:
  - Modified:
    - `libs/cantus/pyproject.toml`（version bump、新增 coverage / mypy / package-data 段、addopts 帶 --cov）
    - `libs/cantus/docs/protocols/adapters-batch2.md`（開頭加 supersede note，本文 byte-identical）
    - `libs/cantus/CHANGELOG.md`（新增 v0.3.5 entry）
  - New:
    - `libs/cantus/cantus/py.typed`（空檔，PEP 561 marker）
    - `libs/cantus/MIGRATION_v0.3.4_to_v0.3.5.md`（migration 文件）
- Submodule pointer：本 change 在 libs/cantus 內 commit 落地後，submodule pointer 自然指向新 commit；主 repo 的 `.gitmodules` / overlay 更新由獨立 Change 3 `bump-cantus-pin-to-v0-3-5` 處理。
- Dependencies：無新增、無移除；`pytest-cov` 與 `mypy` 已存在於 `cantus[dev]` extras。
- Downstream：v0.3.5 是 ADDITIVE，host code 無需改動；下游 host 開 strict mypy 時可以開始看到 cantus 的 typed surface（之前一律當 `Any` 處理）。
- Tags / Releases：cantus 上游需手動 `git tag v0.3.5` + push；本 Spectra archive 不直接執行 git tag。
