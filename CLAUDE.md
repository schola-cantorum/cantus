<!-- SPECTRA:START v1.0.2 -->

# Spectra Instructions

This project uses Spectra for Spec-Driven Development(SDD). Specs live in `openspec/specs/`, change proposals in `openspec/changes/`.

## Use `/spectra-*` skills when:

- A discussion needs structure before coding → `/spectra-discuss`
- User wants to plan, propose, or design a change → `/spectra-propose`
- Tasks are ready to implement → `/spectra-apply`
- There's an in-progress change to continue → `/spectra-ingest`
- User asks about specs or how something works → `/spectra-ask`
- Implementation is done → `/spectra-archive`
- Commit only files related to a specific change → `/spectra-commit`

## Workflow

discuss? → propose → apply ⇄ ingest → archive

- `discuss` is optional — skip if requirements are clear
- Requirements change mid-work? Plan mode → `ingest` → resume `apply`

## Parked Changes

Changes can be parked（暫存）— temporarily moved out of `openspec/changes/`. Parked changes won't appear in `spectra list` but can be found with `spectra list --parked`. To restore: `spectra unpark <name>`. The `/spectra-apply` and `/spectra-ingest` skills handle parked changes automatically.

<!-- SPECTRA:END -->


---

## Roadmap／架構視覺化產物（不進版控）

`cantus-roadmap.html`、`cantus-explorer.html` 等路線圖與架構視覺化 HTML 屬於本地工程輔助檔（engineering artifacts），**不納入版本控制**。若要產生或更新這類產物，一律輸出到 **`.spectra/roadmap/`**（`.spectra/` 已列入 `.gitignore`，不會進版控）：

- `.spectra/roadmap/cantus-roadmap.html` — 決策稽核／時間軸／進度儀表板
- `.spectra/roadmap/cantus-explorer.html` — 互動式分層架構 + 各情境資料流模擬

兩檔以相對路徑互相連結，必須放在同一資料夾。**請勿**在 repo root 產生這類 HTML，也不要 `git add` 它們（產生後它們會自動被 `.spectra/` 的 ignore 規則蓋住）。
