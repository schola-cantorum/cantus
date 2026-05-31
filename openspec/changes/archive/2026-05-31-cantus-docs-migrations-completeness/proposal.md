## Why

`cantus-docs-migrations-relocate`（PR #17，2026-05-31 已 archive）把 16 個 `MIGRATION_v*.md` 搬入 `docs/migrations/` 並對齊 `cantus-i18n-docs` spec，但依其 Non-Goal 明文延後了「README × 2 升版指南清單只到 v0.4.1 → v0.4.2，缺 6 條」這個連結斷層；同時 `CHANGELOG.md` 最近兩個版本 `[0.5.0]` 與 `[0.4.7]` 的開場敘述也漏了「See `MIGRATION_v*`」連結，破壞了 `[0.4.6]`/`[0.4.5]`/`[0.4.4]`/`[0.4.3]` 既有慣例。本案一次補齊這兩處可發現性斷層，並在 `cantus-i18n-docs` spec 新增規範化 scenario，讓未來同樣的漂移會直接被 Gate 1 audit 擋下、不再仰賴 reviewer 紀律。

## What Changes

- `README.md`「Upgrade Guides」清單在 L208 之後補入 6 條連結（涵蓋 `v0.4.2 → v0.4.3` 至 `v0.4.7 → v0.5.0`，共 6 個相鄰版本轉換）。
- `README.zhTW.md`「升版指南」清單在 L208 之後補入 6 條路徑、目標與英文版完全等價的連結。
- `CHANGELOG.md` `[0.5.0]` 入口 blockquote（L9）尾端補入一句 `See [\`MIGRATION_v0.4.7_to_v0.5.0.md\`](docs/migrations/MIGRATION_v0.4.7_to_v0.5.0.md)`；`[0.4.7]` 入口段落（L35）末尾補入一句 `See [\`MIGRATION_v0.4.6_to_v0.4.7.md\`](docs/migrations/MIGRATION_v0.4.6_to_v0.4.7.md)`。
- **MODIFIED** `cantus-i18n-docs`：在「Required English canonical docs SHALL exist and be English-only」這個 Requirement 末端追加兩個 scenario — 一為 README × 2 升版指南清單必須涵蓋每一個 `docs/migrations/MIGRATION_v*.md`、另一為 `CHANGELOG.md` 每筆 release 入口需連結對應 MIGRATION。
- 既有的 4 條 `v0.3 → v0.3.x` 短版連結維持不動（一致勝過齊一）。

## Non-Goals (optional)

- 不更新 `README.md` 的 v0.4.2 install / badge / Colab 連結 / health 端點 `cantus_version` 範例 — 延後至 `cantus-docs-v050-refresh`。
- 不更新 `docs/cookbook-{line,telegram,discord,google-chat}-channel.md`、`docs/protocols/{serve,adapters}.md`、`docs/llm_wiki/future_work/v0_2_to_v0_5_roadmap.md` 內的 0.4.x 字面引用 — 同上延後至 `cantus-docs-v050-refresh`。
- 不改 16 個 MIGRATION 檔內文（byte-identical）。
- 不動 `MANIFEST.in`（前案已修正且仍正確）。
- 不重寫 4 條既有 `v0.3 → v0.3.x` 短版連結為完整 SemVer 形式。
- 不補 `[0.4.7]` 之前已 follow 慣例的 CHANGELOG 入口。
- 不動 `openspec/changes/archive/` 內歷史 change 對 MIGRATION 的引用（凍結紀錄）。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `cantus-i18n-docs`：擴充 Requirement「Required English canonical docs SHALL exist and be English-only」追加兩個 scenario — README 升版指南清單覆蓋完整性、CHANGELOG 入口需連結對應 MIGRATION。

## Impact

- Affected specs:
  - `cantus-i18n-docs`（MODIFIED — 既有 Requirement 末端追加 2 個 scenario，3 個既有 scenario 與 Example block 不動）
- Affected code:
  - Modified: README.md、README.zhTW.md、CHANGELOG.md
  - New: openspec/changes/cantus-docs-migrations-completeness/proposal.md、openspec/changes/cantus-docs-migrations-completeness/tasks.md、openspec/changes/cantus-docs-migrations-completeness/specs/cantus-i18n-docs/spec.md
  - Removed: (無)
- Affected audits / pipelines:
  - `/spectra-audit cantus-docs-i18n-baseline`（Gate 1）會新增上述兩個 scenario 為閘門條件 — archive 完成後生效。
