## Why

`MIGRATION_v*.md` 16 個檔目前散在 repo root，與 README / CHANGELOG / pyproject.toml 同層；隨版本累積（v0.2→v0.5.0）已造成根目錄視覺噪音，新 contributor 第一眼難以辨識主要文件。同時 `cantus-i18n-docs` spec 第 39–46 行的 Required English canonical Requirement 把 MIGRATION 檔列為「at repo root」分類成員 — 當前 root 位置是 spec-normative contract。本 change 把 MIGRATION 收進 `docs/migrations/` 子目錄，同步修 spec、release artifact build（MANIFEST.in）與 README/CHANGELOG 連結，是純位置調整。

## What Changes

- 16 個 MIGRATION 檔自 repo root 搬入新建的 `docs/migrations/` 目錄（內容 byte-identical）。
- MANIFEST.in 的 root-level glob include 改為 `docs/migrations/` 的 recursive-include，保留 PyPI sdist 仍帶 MIGRATION。
- README.md 與 README.zhTW.md 第 199–208 行的 10 條相對連結加入 `docs/migrations/` 路徑前綴。
- CHANGELOG.md 9 處 MIGRATION_v 引用（4 處 Markdown link + 5 處 backtick code-span）加入 `docs/migrations/` 路徑前綴。
- **MODIFIED** `cantus-i18n-docs`：將原本「at repo root」的 MIGRATION 檔位置描述改為 `docs/migrations/`；以檔名 pattern 表達的 Requirement scenario（命名規則、humane-prose-audit 例外）不動。
- `cantus-distribution` 三處 `<!-- @trace -->` block 內 `code:` 清單條目補上 `docs/migrations/` 路徑前綴 — 屬非 normative 註解 metadata 更新，不算 Requirement 行為變更、不列入 Modified Capabilities。

## Non-Goals (optional)

- **不修補 README 連結斷層**：README × 2 的 MIGRATION 清單目前只到 v0.4.1→v0.4.2，缺 v0.4.2→v0.4.3 起 7 個版本 — 屬於後續另案 `cantus-docs-migrations-completeness`。
- **不更新 docs/ 內 0.4.x 引用**：cookbook、protocols、quickstart 等檔案內提到 0.4.x 的版本字面與範例輸出 — 屬於後續另案 `cantus-docs-v050-refresh`。
- **不動 MIGRATION 檔內容**：純位置調整，逐檔內文 byte-identical；MIGRATION 檔內互引 sibling 的相對連結（5 個檔）搬入同一資料夾後仍有效。
- **不動 .worktrees/ 副本**：其他 audit branch 的 MIGRATION 副本屬凍結狀態。
- **不動 openspec/changes/archive/**：歷史 change 內 MIGRATION 引用為凍結紀錄。
- **不擴大為 docs/ 結構重整**：`docs/cookbook-*.md` 平鋪檔與 `docs/cookbook/` 子目錄並存的 mixed pattern 留作另案。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cantus-i18n-docs`：Required English canonical 分類條目對 MIGRATION 檔的位置從 repo root 改為 `docs/migrations/`；對應新 MIGRATION 的 scenario 同步更新 location；以檔名 pattern 表達的 humane-prose-audit 例外條目（pattern-by-filename）保持不變。

## Impact

- Affected specs:
  - cantus-i18n-docs（MODIFIED — Requirement: Required English canonical docs SHALL exist and be English-only）
- Affected code:
  - New:
    - docs/migrations/MIGRATION_v0.2_to_v0.3.md
    - docs/migrations/MIGRATION_v0.3_to_v0.3.1.md
    - docs/migrations/MIGRATION_v0.3_to_v0.3.2.md
    - docs/migrations/MIGRATION_v0.3_to_v0.3.3.md
    - docs/migrations/MIGRATION_v0.3.3_to_v0.3.4.md
    - docs/migrations/MIGRATION_v0.3.4_to_v0.3.5.md
    - docs/migrations/MIGRATION_v0.3.5_to_v0.3.6.md
    - docs/migrations/MIGRATION_v0.3.6_to_v0.4.0.md
    - docs/migrations/MIGRATION_v0.4.0_to_v0.4.1.md
    - docs/migrations/MIGRATION_v0.4.1_to_v0.4.2.md
    - docs/migrations/MIGRATION_v0.4.2_to_v0.4.3.md
    - docs/migrations/MIGRATION_v0.4.3_to_v0.4.4.md
    - docs/migrations/MIGRATION_v0.4.4_to_v0.4.5.md
    - docs/migrations/MIGRATION_v0.4.5_to_v0.4.6.md
    - docs/migrations/MIGRATION_v0.4.6_to_v0.4.7.md
    - docs/migrations/MIGRATION_v0.4.7_to_v0.5.0.md
  - Modified:
    - MANIFEST.in
    - README.md
    - README.zhTW.md
    - CHANGELOG.md
    - openspec/specs/cantus-i18n-docs/spec.md
    - openspec/specs/cantus-distribution/spec.md
  - Removed:
    - MIGRATION_v0.2_to_v0.3.md
    - MIGRATION_v0.3_to_v0.3.1.md
    - MIGRATION_v0.3_to_v0.3.2.md
    - MIGRATION_v0.3_to_v0.3.3.md
    - MIGRATION_v0.3.3_to_v0.3.4.md
    - MIGRATION_v0.3.4_to_v0.3.5.md
    - MIGRATION_v0.3.5_to_v0.3.6.md
    - MIGRATION_v0.3.6_to_v0.4.0.md
    - MIGRATION_v0.4.0_to_v0.4.1.md
    - MIGRATION_v0.4.1_to_v0.4.2.md
    - MIGRATION_v0.4.2_to_v0.4.3.md
    - MIGRATION_v0.4.3_to_v0.4.4.md
    - MIGRATION_v0.4.4_to_v0.4.5.md
    - MIGRATION_v0.4.5_to_v0.4.6.md
    - MIGRATION_v0.4.6_to_v0.4.7.md
    - MIGRATION_v0.4.7_to_v0.5.0.md
