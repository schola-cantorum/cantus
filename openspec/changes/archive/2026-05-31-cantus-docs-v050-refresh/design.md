## Context

v0.5.0 已上 PyPI，但 README ×2 與 `docs/protocols/serve.md` 仍帶 v0.4.x 版號。README 同時存在兩個版本 badge：既有動態 PyPI badge（永不 drift）與冗餘 static `release-v0.4.2` badge（drift 來源）。`cantus-distribution` spec 的 README 契約目前要求 badge bar 顯示 GitHub release tag 且 scenario 檢查 README 原始碼含版號字面，使「純動態 badge」與 spec 衝突。本 change 同時處理 docs 版號刷新與 spec 契約放寬。

## Goals / Non-Goals

**Goals:**

- README ×2 與 serve.md 的「current/latest 版本」引用對齊 v0.5.0。
- 結構性根除 badge drift：移除冗餘 static badge、保留動態 PyPI badge。
- 放寬 cantus-distribution badge 契約使動態 badge 合法，並鎖住「版本 badge 為動態」避免回退。
- 兩份 README 的 install / code block 保持 byte-identical。

**Non-Goals:**

- cookbook `>=0.4.x` 最小版本（正確下界，保留）。
- 「introduced-in vX」歷史標註（serve.md config 表 / 敘述、adapters.md、README 的「(v0.4.0)」標記）。
- `docs/llm_wiki/future_work/v0_2_to_v0_5_roadmap.md`（凍結規劃快照）。
- MIGRATION 清單（前案已補齊）。
- notebook `.ipynb` 內容（只重指 Colab ref）。
- cantus-distribution 的 Effective Version 紀錄（停在 v0.4.2，另案維護）與凍結的 v0.1.3→v0.1.4 歷史 scenario。

## Decisions

### Decision 1: 移除冗餘 static release-tag badge、保留既有動態 PyPI badge

README ×2 badge 區同時有動態 PyPI badge（`a` 連到 pypi.org、`img` 為 `img.shields.io/pypi/v/cantus-agent.svg`）與 static release badge（連到 releases/tag/v0.4.2、`img` 為 `img.shields.io/badge/release-v0.4.2-blue`）。後者每次 release 須手動 bump、是 drift 來源，且與前者語意重複。移除 static badge 那一整行（`<a ...releases/tag/v0.4.2...></a>`），保留動態 badge 作為唯一版本 badge。

**Alternative**：保留 static、僅 bump v0.4.2→v0.5.0 —— 否決，drift 復發。

### Decision 2: Open-in-Colab 連結 pin 到 v0.5.0（不改 main）

badge 區與 notebook 表格的 3 處 Colab URL `blob/v0.4.2/` → `blob/v0.5.0/`。pin 到 release tag 讓教學情境可重現（學生看到的恆為該 release 的 notebook）；不改用 `blob/main/`（main 會變動，不保證對應已發佈版本）。

### Decision 3: install 指令維持 pinned 形式、版號 bump 到 0.5.0

`cantus-agent==0.4.2` / `@v0.4.2` / `[runtime]==0.4.2` / `[serve]==0.4.2` → `0.5.0`。cantus-distribution Requirement 明文要求 recommended install 為 `pip install cantus-agent==<version>` pinned 形式，故不 unpin、只 bump。兩份 README 對應指令保持 byte-identical。

### Decision 4: health 範例輸出對齊真實 runtime 版本 0.5.0

`GET /health` 回傳 `cantus.__version__`（現為 `"0.5.0"`）。README ×2 的 `cantus_version":"0.4.0"`、serve.md 的 `"0.4.0"`（L39 一帶）與 `"0.4.1"`（Authentication 段範例）三處全部對齊為 `"0.5.0"`，使文件範例輸出與實際 runtime 一致。

### Decision 5: 放寬 cantus-distribution badge 契約承認動態 PyPI badge

MODIFIED 兩個 Requirement：「Cantus README presents hero banner, badge bar, and Open-in-Colab call-to-action」與「Cantus README ships a Traditional Chinese variant with bidirectional language switch」。把 badge-bar 條款由「displays at minimum the current GitHub release tag」改為「displays at minimum a version badge（a dynamic PyPI version badge for `cantus-agent` whose image URL references `pypi/v/cantus-agent` satisfies this）and the ECL-2.0 license」；對應 badge scenario 由「displayed label includes the release-tag literal」改為「contains a dynamic PyPI version badge whose image URL references `img.shields.io/pypi/v/cantus-agent`」。Open-in-Colab CTA 條款（pin current tag）、banner / protocols / license / 語言切換條款全部逐字保留。每個 MODIFIED Requirement 須完整重貼（prose + 全部 scenario，含未改動者）以免 archive-time 細節流失。

**Scope boundary（spec）**：只動上述 2 個 Requirement 的 badge 相關文字；不動同 spec 的 Effective Version 區塊、不動凍結的「non-localized content unchanged except release-tag version string」歷史 scenario。

### Decision 6: MODIFIED delta 不手動帶 @trace block，交給 archive

cantus-distribution 的「README presents...」Requirement 尾端原有一個 `<!-- @trace ... -->`（source: cantus-llm-wiki-and-coding-style）。MODIFIED delta 只重貼 Requirement prose + scenario，不手動複製 @trace；archive 階段由 `spectra archive` 處理 @trace 注入／保留。修改採「就地替換 scenario 文字」而非「Requirement 與 trace 之間插入」，避免前案 cantus-docs-migrations-relocate 的孤兒 @trace 雷區。apply 收尾須驗證 archive 後 cantus-distribution 的 @trace 仍完整。

## Implementation Contract

- **Observable behaviour（docs）**：
  - README.md 與 README.zhTW.md badge 區不再出現 `release-v0.4.2`（或任何 `img.shields.io/badge/release-` 的 static release badge）；動態 PyPI badge（`img.shields.io/pypi/v/cantus-agent`）保留。
  - 兩份 README 不再出現 `0.4.2` 版號字面於 install / git ref / Colab URL；改為 `0.5.0`。Colab URL 為 `.../blob/v0.5.0/notebooks/...`。
  - 兩份 README 與 serve.md 的 health 範例 `cantus_version` 值為 `"0.5.0"`，不再有 `"0.4.0"` / `"0.4.1"` 範例輸出。
  - 兩份 README 的 pip install / git+ 指令彼此 byte-identical。
- **Observable behaviour（spec）**：cantus-distribution 套用後，README badge scenario 以「動態 PyPI badge URL 存在」為通過條件，不要求 release-tag 字面；EN 與 zh-TW 兩 Requirement 同步放寬。
- **Interface/data shape**：無程式介面變更（純文件 + spec normative 文字）。
- **Failure modes**：若任一 README 仍殘留 `release-v0.4.2` badge 或 `0.4.2` install 版號、或兩份 README install 指令不一致、或 serve.md 仍有 `"0.4.0"`/`"0.4.1"` health 範例 → 對應 verification 任務應失敗。
- **Acceptance criteria（驗證標的）**：
  - `grep` 確認兩份 README 無 `release-v0.4.2`、無 `badge/release-`、無 `0.4.2`（badge/install/Colab 區）、無 `blob/v0.4.2`。
  - `grep` 確認動態 PyPI badge 仍在兩份 README。
  - `grep` 確認 README ×2 + serve.md 無 `cantus_version":"0.4.0"` / `"0.4.1"`，且出現 `"0.5.0"`。
  - `diff` 確認兩份 README 的 install / git+ 指令逐行一致。
  - 套 spec 後（archive 階段）cantus-distribution README badge scenario 描述與「動態 badge」一致、@trace 完整。
- **Scope boundary**：只動 README ×2、docs/protocols/serve.md、cantus-distribution 上述 2 Requirement；不動 cookbook、其他 docs、其他 spec、notebook 內容。

## Risks / Trade-offs

- [移除 static badge 後，cantus-distribution 舊 scenario 失效] → 同一 change 內 MODIFIED 該 spec，兩者一起 ship；archive 套用後 scenario 與實況一致。
- [MODIFIED 大段重貼 Requirement 可能漏抄既有 scenario] → 重貼前對照 canonical spec 全文逐 scenario 核對；apply 收尾 diff 確認除 badge 文字外其餘 scenario byte-identical。
- [archive @trace 注入可能移動既有 trace] → 採就地替換而非中段插入；收尾 grep `@trace` 數量與 source 比對（同前案 completeness 的驗證手法）。
- [動態 PyPI badge 在 PyPI 短暫不可用時顯示 unknown] → 可接受；版本資訊另有 CHANGELOG / MIGRATION，且 badge 為輔助資訊非契約資料。
