<!--
Decisions referenced: Decision 1 (remove static badge / keep dynamic), Decision 2 (Colab pin v0.5.0),
Decision 3 (install pinned bump), Decision 4 (health output 0.5.0), Decision 5 (cantus-distribution
badge contract relaxation), Decision 6 (MODIFIED delta @trace handling).
Spec Requirements modified: "Cantus README presents hero banner, badge bar, and Open-in-Colab
call-to-action" and "Cantus README ships a Traditional Chinese variant with bidirectional language switch".
-->

## 1. Pre-flight & baseline snapshot

- [x] 1.1 Working tree clean on a dedicated branch (not `main`): `git status --short` shows no tracked-file modifications and `git branch --show-current` ≠ `main`. Establishes attributable starting state.
- [x] 1.2 Confirm the precondition for Decision 1 and Decision 4: both `README.md` and `README.zhTW.md` already contain the dynamic PyPI badge (`grep -c "img.shields.io/pypi/v/cantus-agent" README.md README.zhTW.md` ≥ 1 each), and `python -c "import cantus; print(cantus.__version__)"` prints `0.5.0` (so the health example target value is correct). Snapshot baseline counts: `grep -c "release-v0.4.2\|0\.4\.2\|cantus_version\":\"0\.4" README.md README.zhTW.md docs/protocols/serve.md`.

## 2. README.md version refresh

- [x] 2.1 [P] `README.md` badge bar + install + Colab + health refreshed in one pass: per **Decision 1: 移除冗餘 static release-tag badge、保留既有動態 PyPI badge** remove the redundant static release-tag badge line (the `<a href=".../releases/tag/v0.4.2">` anchor wrapping the `img.shields.io/badge/release-v0.4.2` image) while keeping the dynamic PyPI badge; per **Decision 2: Open-in-Colab 連結 pin 到 v0.5.0（不改 main）** repoint all Open-in-Colab URLs `blob/v0.4.2/` → `blob/v0.5.0/` (badge-bar CTA + the two notebook-table links); per **Decision 3: install 指令維持 pinned 形式、版號 bump 到 0.5.0** bump pinned install commands `cantus-agent==0.4.2` / `@v0.4.2` / `[runtime]==0.4.2` / `[serve]==0.4.2` → `0.5.0` (keep the pinned `==<version>` form); per **Decision 4: health 範例輸出對齊真實 runtime 版本 0.5.0** change the Serve Quickstart health example `cantus_version":"0.4.0"` → `"0.5.0"`. Verified by: `grep` shows, in `README.md`, zero of each stale form — `release-v0.4.2`, `img.shields.io/badge/release-`, `releases/tag/v0.4.2`, `==0.4.2`, `@v0.4.2`, `blob/v0.4.2`, `cantus_version":"0.4.0"` — AND the dynamic PyPI badge line still present, AND `blob/v0.5.0` + `cantus_version":"0.5.0"` present. NOTE: the Upgrade Guides MIGRATION-list lines `v0.4.1 → v0.4.2` and `v0.4.2 → v0.4.3` legitimately contain the bare string `0.4.2` and MUST remain — the verification targets the specific stale install/badge/Colab/health forms above, not the bare `0.4.2` substring.

## 3. README.zhTW.md version refresh (two-README sync)

- [x] 3.1 [P] `README.zhTW.md` receives the byte-identical badge/install/Colab/health edits as §2.1 (same Decision 1–4 changes), preserving the cantus-i18n-docs / cantus-distribution "install + code blocks byte-identical across the two READMEs" contract. Verified by: same `grep` assertions as §2.1 against `README.zhTW.md`, AND `diff <(grep -nE 'pip install|git\+https' README.md) <(grep -nE 'pip install|git\+https' README.zhTW.md)` shows the install/git commands are line-for-line identical (ignoring surrounding localized prose).

## 4. docs/protocols/serve.md health examples

- [x] 4.1 [P] Per **Decision 4**, both `GET /health` example outputs in `docs/protocols/serve.md` (`cantus_version":"0.4.0"` in the Quickstart area and `cantus_version": "0.4.1"` in the Authentication section) change to `"0.5.0"`, matching the value the running v0.5.0 health endpoint returns. The "introduced-in v0.4.0 / v0.4.1" annotations in the config table and narrative are deliberately NOT touched (Non-Goal). Verified by: `grep -c 'cantus_version": *"0.5.0"' docs/protocols/serve.md` ≥ 2 AND `grep -c 'cantus_version": *"0.4' docs/protocols/serve.md` == 0.

## 5. cantus-distribution spec delta alignment

- [x] 5.1 Per **Decision 5: 放寬 cantus-distribution badge 契約承認動態 PyPI badge** and **Decision 6: MODIFIED delta 不手動帶 @trace block，交給 archive**, the change ships a `cantus-distribution` delta that MODIFIES the Requirement "Cantus README presents hero banner, badge bar, and Open-in-Colab call-to-action" and the Requirement "Cantus README ships a Traditional Chinese variant with bidirectional language switch": the badge-bar clause now mandates a dynamic PyPI version badge (`img.shields.io/pypi/v/cantus-agent`) instead of a hardcoded release-tag literal, each scenario adds a "does NOT contain a hardcoded `img.shields.io/badge/release-` badge" anti-regression assertion, and each MODIFIED Requirement is re-declared in full (all scenarios, including the frozen v0.1.3-diff scenario) without hand-placing any `<!-- @trace -->` block (left to `spectra archive`). Verified by: `spectra analyze cantus-docs-v050-refresh --json` reports no Critical/Warning and `spectra validate cantus-docs-v050-refresh` exits 0; the doc edits in §2/§3 satisfy both modified scenarios (dynamic badge present, no static release badge).

## 6. Badge anti-regression smoke

- [x] 6.1 Neither README contains a static release-tag badge and both keep the dynamic one: `grep -L "img.shields.io/pypi/v/cantus-agent" README.md README.zhTW.md` prints nothing (both have it) AND `grep -l "img.shields.io/badge/release-" README.md README.zhTW.md` prints nothing (neither has it). Directly verifies the Decision 1 contract and the new spec anti-regression assertion.

## 7. Version-refresh coverage smoke

- [x] 7.1 No stale current-version literal remains in the refreshed install/badge/Colab/health surfaces: `grep -REn "release-v0\.4\.2|releases/tag/v0\.4\.2|==0\.4\.2|@v0\.4\.2|blob/v0\.4\.2|cantus_version\": *\"0\.4\.[01]\"" README.md README.zhTW.md docs/protocols/serve.md` returns no matches. The grep deliberately targets the specific stale forms, NOT the bare `0.4.2` substring, because the README Upgrade Guides list legitimately contains `v0.4.1 → v0.4.2` / `v0.4.2 → v0.4.3` MIGRATION links; cookbook `>=0.4.x` minimums and "introduced-in vX" annotations are likewise out of scope per Non-Goals. Confirms Decisions 2/3/4 fully applied.

## 8. Final apply report

- [x] 8.1 Apply summary report records: `git diff --stat main` for the three doc files, the §1.2 baseline-vs-current counts for the removed `release-v0.4.2` badge and the refreshed version literals, and the four smoke results (§6.1 badge, §7.1 version, §3.1 two-README install diff empty, §5.1 analyze+validate clean) — giving a single-glance confirmation that every Implementation Contract item holds before commit + PR.
