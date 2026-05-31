<!-- SPECTRA:START v1.0.2 -->

# Spectra Instructions

This project uses Spectra for Spec-Driven Development(SDD). Specs live in `openspec/specs/`, change proposals in `openspec/changes/`.

## Use `$spectra-*` skills when:

- A discussion needs structure before coding → `$spectra-discuss`
- User wants to plan, propose, or design a change → `$spectra-propose`
- Tasks are ready to implement → `$spectra-apply`
- There's an in-progress change to continue → `$spectra-ingest`
- User asks about specs or how something works → `$spectra-ask`
- Implementation is done → `$spectra-archive`
- Commit only files related to a specific change → `$spectra-commit`

## Workflow

discuss? → propose → apply ⇄ ingest → archive

- `discuss` is optional — skip if requirements are clear
- Requirements change mid-work? `ingest` → resume `apply`

## Parked Changes

Changes can be parked（暫存）— temporarily moved out of `openspec/changes/`. Parked changes won't appear in `spectra list` but can be found with `spectra list --parked`. To restore: `spectra unpark <name>`. The `$spectra-apply` and `$spectra-ingest` skills handle parked changes automatically.

<!-- SPECTRA:END -->

---
profile: research
profile_version: "1.0.0"
schema_version: "1.0.0"
wiki_path: docs/llm_wiki
raw_path: docs/llm_wiki_raw
index_path: docs/llm_wiki/index.md
log_path: docs/llm_wiki/log.md
---

## Schema

Project: `cantus`. Wiki follows the shipped `research` profile (v1.0.0) defined by the wiki-schema capability suite.

- Sources live under `docs/llm_wiki_raw/` and are immutable.
- Wiki pages live under `docs/llm_wiki/` and are agent-maintained.
- Source pages MUST declare `source_url`, `ingested_at`, `source_type` (one of `paper`, `article`, `book`, `podcast`).
- `docs/llm_wiki/synthesis.md` accumulates cross-source synthesis.
- `docs/llm_wiki/log.md` uses strict format `## [YYYY-MM-DD] <op> | <title>`.

## Ingest

When a new source is dropped into `docs/llm_wiki_raw/`, the agent reads it, summarizes the key takeaways, files a source page under `docs/llm_wiki/pages/`, updates `docs/llm_wiki/index.md`, refreshes related entity and concept pages, refines `docs/llm_wiki/synthesis.md`, and appends a strict-format entry to `docs/llm_wiki/log.md`.

## Query

The agent reads `docs/llm_wiki/index.md` first, then drills into relevant pages and `docs/llm_wiki/synthesis.md` to compose answers. Citations link back to source pages.

## Lint

Periodic lint passes detect contradictions across pages, stale claims, orphan pages, missing cross-references, and synthesis gaps.

## Spectra Workflow

This repository also uses **Spectra** for Spec-Driven Development(SDD). Capability specs live in `openspec/specs/`, change proposals in `openspec/changes/`, archived changes in `openspec/changes/archive/`. Workflow ordering: `discuss? → propose → apply ⇄ ingest → archive`. See `CLAUDE.md` for the full `/spectra-*` skill block and parked-change semantics.

The Spectra workflow is orthogonal to the wiki workflow described above: Spectra governs cantus capability evolution; the `research` wiki profile (declared in the YAML frontmatter at the top of this file) governs research-source curation under `docs/llm_wiki/`.


---

## Roadmap／架構視覺化產物（不進版控）

`cantus-roadmap.html`、`cantus-explorer.html` 等路線圖與架構視覺化 HTML 屬於本地工程輔助檔（engineering artifacts），**不納入版本控制**。若要產生或更新這類產物，一律輸出到 **`.spectra/roadmap/`**（`.spectra/` 已列入 `.gitignore`，不會進版控）：

- `.spectra/roadmap/cantus-roadmap.html` — 決策稽核／時間軸／進度儀表板
- `.spectra/roadmap/cantus-explorer.html` — 互動式分層架構 + 各情境資料流模擬

兩檔以相對路徑互相連結，必須放在同一資料夾。**請勿**在 repo root 產生這類 HTML，也不要 `git add` 它們（產生後它們會自動被 `.spectra/` 的 ignore 規則蓋住）。
