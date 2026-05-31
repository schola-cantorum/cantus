## Summary

把 v0.5.0 release 後仍 hardcode 在 README ×2 與 `docs/protocols/serve.md` 的舊版號（v0.4.2 install / Colab pin、v0.4.0 health 範例）更新到 v0.5.0，並移除會持續 drift 的冗餘 static release-tag badge、改以既有的動態 PyPI badge 為唯一版本 badge；同步放寬 `cantus-distribution` 的 README badge 契約，讓動態 badge 合法。

## Motivation

v0.5.0 已上 PyPI（見 [pending-v050-docs-update] 待辦），但使用者面向的 README 仍叫人 `pip install cantus-agent==0.4.2`、Colab 連到 `blob/v0.4.2/`、health 範例顯示 `cantus_version":"0.4.0"` —— 對照真實已發佈版本 v0.5.0 會誤導學生。前一案 `cantus-docs-migrations-completeness` 已收掉 MIGRATION 連結斷層；本案收掉剩下的版號 drift。

根因之一是 README 同時有兩個版本 badge：一個既有的動態 PyPI badge（`img.shields.io/pypi/v/cantus-agent`，永不 drift）與一個冗餘的 static `release-v0.4.2` badge（每次 release 都要手動 bump，正是 drift 來源）。移除 static badge、保留動態 badge，可從結構上根除 badge drift；但 `cantus-distribution` spec 目前的 README 契約要求「badge bar 顯示 current GitHub release tag」且 scenario 直接檢查 README 原始碼第 30 行內含版號字面（如 `v0.1.4`），動態 badge 原始碼無版號字面會讓該 scenario 失敗 —— 故須同步放寬 spec 契約，承認動態 PyPI badge 為正式版本 badge。

## Proposed Solution

- **README.md 與 README.zhTW.md**（兩份保持 install / code block byte-identical，符合 cantus-i18n-docs 與 cantus-distribution 既有 sync 契約）：
  - 移除冗餘 static release-tag badge（`release-v0.4.2`）那一行，保留既有動態 PyPI version badge。
  - Open-in-Colab 連結 `blob/v0.4.2/` → `blob/v0.5.0/`（task_template 與 admin_setup 共 2 處 + badge 區 1 處）。
  - 安裝指令版號 `cantus-agent==0.4.2` / `@v0.4.2` / `[runtime]==0.4.2` / `[serve]==0.4.2` → `0.5.0`。
  - Serve Quickstart health 範例輸出 `cantus_version":"0.4.0"` → `"0.5.0"`。
- **docs/protocols/serve.md**：兩個 health 範例輸出 `cantus_version` `"0.4.0"` 與 `"0.4.1"` → `"0.5.0"`（health 端點回傳 `cantus.__version__`，現為 0.5.0）。
- **MODIFIED `cantus-distribution`**：放寬「Cantus README presents hero banner, badge bar, and Open-in-Colab call-to-action」與「Cantus README ships a Traditional Chinese variant」兩個 Requirement 的 badge-bar 條款與相關 scenario —— 版本 badge 改以「動態 PyPI version badge（URL 指向 pypi/v/cantus-agent）」滿足，不再要求 README 原始碼出現 release-tag 版號字面。Open-in-Colab CTA 仍 pin 到 current tag（本次即 v0.5.0），其餘 banner / protocols / license / 語言切換條款不動。

## Non-Goals (optional)

- **不改 cookbook 的最小版本要求**：`docs/cookbook-{line,telegram,discord,google-chat}-channel.md` 的 `cantus-agent[serve]>=0.4.5/0.4.6/0.4.7` 是「該功能自此版起可用」的正確下界（pip 仍會裝到 0.5.0），刻意保留；behavioral note（如「v0.4.5 仍不自動讀 .env」）同屬歷史正確描述，不動。
- **不改「introduced-in vX」歷史標註**：`docs/protocols/serve.md` config 表與敘述中的 v0.4.0 / v0.4.1 標註、`docs/protocols/adapters.md` 的 v0.4.0 引用、README 中「Serve extras (v0.4.0)」「Serve Quickstart (v0.4.0)」等「自 vX 引入」標記皆為歷史正確，保留。
- **不改 `docs/llm_wiki/future_work/v0_2_to_v0_5_roadmap.md`**：內部貢獻者 wiki 的 target-version 規劃快照，屬凍結規劃紀錄。
- **不動 MIGRATION 清單**：已於前案 cantus-docs-migrations-completeness 補齊且正確。
- **不改 notebook 內容本身**：只重指 Colab 連結 ref，不編輯 `.ipynb` 檔。
- **不補 `cantus-distribution` 的 Effective Version 紀錄**：該 spec 的 effective-version 區塊停在 v0.4.2，補到 v0.5.0 屬 release-time spec 維護，另案處理。
- **不動 cantus-distribution 凍結的歷史 scenario**：「non-localized content unchanged except release-tag version string」是針對 v0.1.3→v0.1.4 過渡的凍結 diff 斷言，保留。

## Alternatives Considered (optional)

- **Static badge 直接 bump 到 v0.5.0**（不改 spec）：最省事、零 spec 變更，但下次 release 又要手動 bump、drift 復發。已否決，改採動態 badge 從結構上根治（使用者明確選此方向）。
- **install 指令改 unpin（`pip install cantus-agent`）**：cantus-distribution Requirement 明文要求 recommended install 為 `pip install cantus-agent==<version>` pinned 形式，unpin 會違反 spec，故保留 pinned、只 bump 版號。

## Impact

- Affected specs:
  - `cantus-distribution`（MODIFIED — 2 個 README 契約 Requirement 的 badge-bar 條款與 scenario 放寬以承認動態 PyPI badge）
- Affected code:
  - Modified:
    - README.md
    - README.zhTW.md
    - docs/protocols/serve.md
  - New:
    - openspec/changes/cantus-docs-v050-refresh/proposal.md
    - openspec/changes/cantus-docs-v050-refresh/design.md
    - openspec/changes/cantus-docs-v050-refresh/tasks.md
    - openspec/changes/cantus-docs-v050-refresh/specs/cantus-distribution/spec.md
  - Removed: （無檔案刪除；README 移除一行冗餘 badge markup）
- Affected audits:
  - `/spectra-audit cantus-docs-i18n-baseline`（Gate 1）：README 變更仍須維持 EN/zh-TW install code block byte-identical。
