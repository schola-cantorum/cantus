## Why

cantus v0.3.5（quality-baseline）在 `pyproject.toml` 啟用 `[tool.mypy] warn_unused_ignores = true` 後，跑 `mypy cantus` 會回報 15 條 redundant `# type: ignore[...]` warning。這些 ignore 註解多半是 v0.2.x / v0.3.x 早期為了繞過當時的 import-resolution 問題加上的，現在 mypy override（line 152-164 of `libs/cantus/pyproject.toml`）已對所有 optional-extras adapter SDK 設 `ignore_missing_imports = true`，這些行內 ignore 已成 noise。

留著的代價：

1. **稀釋 mypy baseline 訊號** — 開發者跑 `mypy cantus` 永遠看到 15 條 noise，未來真的有 redundant ignore 時看不出來。
2. **違反 v0.3.5 release notes 的精神** — quality baseline 的 stated goal 是「mypy cantus 跑得起來且訊號有意義」，目前訊號被噪音掩蓋。
3. **memory 上掛了一條 known follow-up**，越早收尾越省 cognitive load。

## What Changes

- 刪除 cantus 原始碼內 15 條 mypy 報告為 `[unused-ignore]` 的 `# type: ignore[...]` 註解（11 個檔案，詳見 `tasks.md`）。
- `libs/cantus/pyproject.toml` 版本 `0.3.5 → 0.3.6`（PATCH，無 BREAKING、無 public API 變動、無新依賴、無新 optional extras）。
- 新增 `libs/cantus/CHANGELOG.md` v0.3.6 entry（**Internal** 區段為主，註明 user-facing surface 完全不變）。
- 新增 `libs/cantus/MIGRATION_v0.3.5_to_v0.3.6.md`（一行說明：no user-facing change，純 internal cleanup，無需任何 user action）。
- 在 cantus v0.3.6 tag 處保持 git history clean — 此 change archive 時同步在 cantus submodule tag v0.3.6 並 bump submodule pointer 留給 Phase A2 處理（**不在本 change scope**）。

## Non-Goals (optional)

- **不修 `[all]` 與 `[openhands]` extras 的 dependency conflict**：本次 mypy 跑 `uv run --frozen` 才繞過 resolver 衝突，但根因是 `cantus[all]` 與 `cantus[openhands]` 因 fastmcp/websockets/google-genai 鏈互不相容。這是 v0.3.4「永久放棄 OpenHands import」後遺留的 release engineering issue，scope 與性質與「清 redundant ignore」不同，另開 follow-up 處理。
- **不開 spec delta**：cantus distribution capability 既有 Scenario「pyproject ships mypy baseline that lets mypy cantus run without import failures」允許 mypy `exits with code 0 or 1 (warnings allowed)`，清完 ignore 後 cantus 仍滿足現有 spec；不主動 strengthening 為「全綠」以避免將來新檔案引入新 ignore 時被 spec gate 阻擋。
- **不 bump 主 repo submodule pointer**：跨 submodule 邊界的 `bump-cantus-pin-to-v0-3-6 + teacher_setup ipynb refresh` 屬於主 repo capability scope，另開 change 處理。
- **不調整 mypy 設定**：`warn_unused_ignores = true` 既有設定保留；不啟用 strict mode（v0.4.x deferred）。
- **不調整 CI**：cantus 目前無 GitHub Actions workflow，不在本 change 範圍引入。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

（無 — 純 internal code-comment cleanup，不修改任何 capability 的 requirements；既有 cantus distribution capability 的 mypy baseline scenario 允許 warning，本 change 後仍滿足）

## Impact

- Affected specs: 無（不開 spec delta）
- Affected code（皆位於 `libs/cantus/` submodule 內）：
  - Modified:
    - `libs/cantus/cantus/adapters/openhands.py`（line 20）
    - `libs/cantus/cantus/adapters/mcp.py`（lines 17, 68）
    - `libs/cantus/cantus/adapters/langchain.py`（lines 17, 18, 77）
    - `libs/cantus/cantus/adapters/dspy.py`（line 17）
    - `libs/cantus/cantus/adapters/huggingface.py`（line 22）
    - `libs/cantus/cantus/protocols/debug.py`（line 68）
    - `libs/cantus/cantus/model/providers/openai.py`（line 45）
    - `libs/cantus/cantus/model/providers/groq.py`（line 41）
    - `libs/cantus/cantus/model/providers/anthropic.py`（line 44）
    - `libs/cantus/cantus/model/providers/google.py`（line 46）
    - `libs/cantus/cantus/model/loader.py`（lines 118, 119）
    - `libs/cantus/pyproject.toml`（version 0.3.5 → 0.3.6）
    - `libs/cantus/CHANGELOG.md`（新增 v0.3.6 entry）
  - New:
    - `libs/cantus/MIGRATION_v0.3.5_to_v0.3.6.md`
  - Removed: 無
- 對下游消費者：零影響（無 public API、版本字串、安裝介面變動以外的影響；wheel 內容 byte-for-byte 與 v0.3.5 差別僅在於 15 行原始碼註解與 version pin）。
- 對主 repo（`colab-llm-agent`）：本 change archive 後，主 repo 仍指向 cantus v0.3.5 submodule SHA；bump 動作由 Phase A2 的 `bump-cantus-pin-to-v0-3-6-and-refresh-teacher-setup` change 完成。
