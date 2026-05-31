<!--
Tasks below align to MODIFIED Requirement "Required English canonical docs SHALL exist and be English-only"
in capability cantus-i18n-docs (delta in specs/cantus-i18n-docs/spec.md).
Two new scenarios are exercised by the verification tasks (5, 6, 7):
  - Upgrade-guide list contains every released MIGRATION
  - CHANGELOG release entry references its MIGRATION
-->

## 1. Pre-flight & baseline snapshot

- [x] 1.1 Working tree is clean and on a dedicated branch: `git status --short` outputs no lines and `git branch --show-current` is not `main`. Captures starting state so any apply-time edit is attributable to this change.
- [x] 1.2 Every target MIGRATION file exists under `docs/migrations/`: for each of `MIGRATION_v0.4.2_to_v0.4.3.md`, `MIGRATION_v0.4.3_to_v0.4.4.md`, `MIGRATION_v0.4.4_to_v0.4.5.md`, `MIGRATION_v0.4.5_to_v0.4.6.md`, `MIGRATION_v0.4.6_to_v0.4.7.md`, `MIGRATION_v0.4.7_to_v0.5.0.md` plus any older ones, `test -f docs/migrations/<file>` returns 0. Confirms the link targets are real before any link is added.
- [x] 1.3 Baseline link-count snapshot captured: run `grep -c "docs/migrations/MIGRATION_v" README.md README.zhTW.md CHANGELOG.md` and store the per-file counts in the task notes — these counts MUST strictly increase by 6, 6, and ≥2 respectively when verification runs in §5–§7. (Baseline 2026-05-31: README.md=10, README.zhTW.md=10, CHANGELOG.md=9; 16 MIGRATION files total, so 10+6=16 full coverage.)

## 2. README.md Upgrade Guides list

- [x] 2.1 [P] `README.md` Upgrade Guides section lists every adjacent-release MIGRATION file from `v0.4.2 → v0.4.3` through `v0.4.7 → v0.5.0` (6 transitions) as a Markdown link with URL `./docs/migrations/MIGRATION_v<A>.<B>_to_v<X>.<Y>.md` and link text `v<A>.<B> → v<X>.<Y>`. Insertion point is immediately after the existing `v0.4.1 → v0.4.2` line, preserving the existing v0.3 short-form prefix unchanged. Verified by `grep -c "docs/migrations/MIGRATION_v" README.md` increasing by exactly 6 from the §1.3 baseline AND visual confirmation that the section now ends with the `v0.4.7 → v0.5.0` entry.

## 3. README.zhTW.md 升版指南清單

- [x] 3.1 [P] `README.zhTW.md` 升版指南 section lists the same 6 entries with byte-identical URLs and link text as §2.1, preserving the Two-README install-instructions sync contract. Verified by `grep -c "docs/migrations/MIGRATION_v" README.zhTW.md` increasing by exactly 6 from the §1.3 baseline AND `diff <(sed -n '/### 升版指南/,/^##/p' README.zhTW.md | grep -oE 'MIGRATION_v[^)]*') <(sed -n '/### Upgrade Guides/,/^##/p' README.md | grep -oE 'MIGRATION_v[^)]*')` produces an empty diff (same MIGRATION filenames in same order).

## 4. CHANGELOG.md release-entry MIGRATION references

- [x] 4.1 [P] `CHANGELOG.md` `## ✨ [0.5.0]` opening blockquote SHALL end with a Markdown link to `docs/migrations/MIGRATION_v0.4.7_to_v0.5.0.md`; `## [0.4.7]` release-summary paragraph SHALL end with a Markdown link to `docs/migrations/MIGRATION_v0.4.6_to_v0.4.7.md`. Link prose style MUST match the existing `[0.4.6]`/`[0.4.5]`/`[0.4.4]` precedent (`See [\`MIGRATION_v*\`](docs/migrations/MIGRATION_v*) ...`). Verified by `grep -c "docs/migrations/MIGRATION_v0\.\(4\.7\|5\.0\)" CHANGELOG.md` returning at least 2 AND visual confirmation that no other paragraph or heading inside those two entries was edited.

## 5. Upgrade-guide coverage smoke for Requirement "Required English canonical docs SHALL exist and be English-only"

- [x] 5.1 Run a shell loop asserting every `docs/migrations/MIGRATION_v*.md` file appears as a substring in BOTH `README.md` AND `README.zhTW.md`: `for f in docs/migrations/MIGRATION_v*.md; do n=$(basename "$f"); grep -q "$n" README.md && grep -q "$n" README.zhTW.md && echo "OK $n" || { echo "MISS $n"; exit 1; }; done`. The loop SHALL exit 0 and print one `OK <name>` line per file (16 lines expected). Directly verifies the new "Upgrade-guide list contains every released MIGRATION" scenario under the MODIFIED Requirement "Required English canonical docs SHALL exist and be English-only".

## 6. CHANGELOG body-link smoke

- [x] 6.1 `grep -E '\[\`MIGRATION_v0\.4\.7_to_v0\.5\.0\.md\`\]\(docs/migrations/MIGRATION_v0\.4\.7_to_v0\.5\.0\.md\)' CHANGELOG.md` returns at least 1 match AND `grep -E '\[\`MIGRATION_v0\.4\.6_to_v0\.4\.7\.md\`\]\(docs/migrations/MIGRATION_v0\.4\.6_to_v0\.4\.7\.md\)' CHANGELOG.md` returns at least 1 match. Directly verifies the new "CHANGELOG release entry references its MIGRATION" scenario for the two latest releases.

## 7. Markdown link target existence smoke

- [x] 7.1 Every new Markdown link added by §2, §3, §4 resolves to an existing file: extract URLs from the new lines via `grep -oE 'docs/migrations/MIGRATION_v[0-9.]+_to_v[0-9.]+\.md' README.md README.zhTW.md CHANGELOG.md | sort -u | while read p; do test -f "$p" || { echo "BROKEN $p"; exit 1; }; done`. Loop SHALL exit 0 with no `BROKEN` lines. Catches typos in version numbers before review.

## 8. Two-README install-section non-divergence

- [x] 8.1 The "Install" / "Quickstart" sections of `README.md` and `README.zhTW.md` were not touched by this change: `git diff --unified=0 main -- README.md README.zhTW.md | grep -E '^[+-]' | grep -v '^[+-][+-][+-]' | grep -vE 'MIGRATION_v|升版指南|Upgrade Guides|→' | wc -l` returns 0. Honors the existing `cantus-i18n-docs` "Two-README divergence policy" scenario (install-instructions must stay in sync; any drift fails this check).

## 9. Final apply report

- [x] 9.1 Apply task summary report includes: per-file modified-line count (`git diff --stat main -- README.md README.zhTW.md CHANGELOG.md`), the §1.3 baseline vs current link-count delta, and the four smoke-script exit codes (§5.1, §6.1, §7.1, §8.1) all 0. Hands off to commit + PR with a single-glance confirmation that every contract item from the MODIFIED Requirement is satisfied.
