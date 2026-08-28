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

> **注意**：上面的 SPECTRA 區塊由 `spectra update` 自動重寫，**不要在裡面編輯**。它描述的
> 「每件變更都走 propose→apply→archive」已不是本專案的預設路徑——實際規則見下面〈工作流〉。
> 本檔案 SPECTRA 區塊**以外**的所有段落都不會被 `spectra update` 動到。

---

## Agent skills

### Issue tracker

Tickets 與 spec 以版控 markdown 存放於 `.proj.tickets/`（狀態即目錄）與 `.proj.spec/`；無遠端 tracker。見 `docs/agents/issue-tracker.md`。

### Domain docs

單一 context：repo 根目錄的 `CONTEXT.md` 加 `docs/adr/`，兩者皆由 `/domain-modeling` 在術語或決策真正成形時才建立。見 `docs/agents/domain.md`。

（未安裝 `triage` skill，因此沒有 triage 標籤詞彙，也不要套用任何標籤。）

---

## 工作流：一條主線，兩條例外路徑

### 主線 —— 日常變更

```
grill-with-docs → to-spec → to-tickets → implement → code-review → 你 commit
                （撞牆才升 wayfinder）
```

- `to-spec` 只在「跨多個 session」時才值得跑；單 session 的變更直接 `grill-with-docs → implement`。
- 規劃深度預設用 `grill-with-docs`（單 session）。只有當工作**確實一個 session 裝不下**時才考慮升級 `wayfinder`（目前未安裝）。

### 例外路徑 A —— 契約變動

**判準：變更動到公開 API 表面**——新增／改名／移除 public 符號、CLI flag、HTTP endpoint、或設定欄位。

符合判準時走 Spectra：`spectra-propose` → 實作 → `spectra-archive`，把 spec delta 套進 `openspec/specs/`。不符合判準的變更不要碰 `openspec/`。

### 例外路徑 B —— 發版

`spectra-audit` + Gate A/B/C 雙閘，然後 release。這條不因主線改動而改變。

### 兩個叫「spec」的地方，不可混用

| 路徑 | 是什麼 |
| --- | --- |
| `openspec/specs/` | **契約帳本**，現行真相來源。只透過 Spectra 變更，且只在動到公開 API 表面時。 |
| `.proj.spec/` | `to-spec` 產出的**拋棄式快照**，供「跨 session 但不動公開 API」的工作使用。無同步機制。 |

不得引用 `.proj.spec/` 當作需求依據；`to-spec` 也不得改寫 `openspec/specs/`。

---

## Skill 叫用規則

### `implement` 不得自行 commit

`implement` 的 `SKILL.md` 結尾寫著 `Commit your work to the current branch.`——**在本專案不適用**。跑到該 commit 時停手，把變更交回使用者，由使用者依全域規則走 `/tw-emoji-commit`。這同時也是一個人工驗收點。

（`implement` 中段的 `use /code-review` 照常執行，它會命中本 repo 的 `code-review` skill。）

### `spectra-*` 僅限手動叫用

12 個 `spectra-*` skill 一律**只在使用者明確點名時**才執行，不得自動觸發。Spectra 已是例外路徑，不該自己跳出來。

實作上這由各 `SKILL.md` 的 `disable-model-invocation: true` 保證，但 `.claude/` 在 `.gitignore` 內、且 `spectra update` / `spectra init` 會重寫那些檔案。**因此：每當 `.claude/skills/spectra-*` 有任何變動（跑過 `spectra update`、`spectra init`、或版本升級），必須檢查全部 12 個 `SKILL.md` 的 frontmatter 是否仍帶 `disable-model-invocation: true`，缺的補回。** 本節是該設定的真相來源。

### `diagnosing-bugs` 不得自動觸發

同樣以 frontmatter 加 `disable-model-invocation: true` 實作。它會在使用者只是隨口描述問題時就啟動完整重現流程。需要它時使用者會點名。`.agents/` 在版控內，被 `npx skills update` 覆蓋時 diff 看得到。

### `code-review` 的 sub-agent 不得再委派

`code-review` 第 4 步的兩個 sub-agent brief 末尾都必須帶「直接執行本次審查，不得再呼叫 `/code-review` 或衍生其他 agent」。缺這一句時 sub-agent 會重新發現此 skill 並再度扇出。被 `npx skills update` 覆蓋後依此重建。

---

## Archive 的地位：歷史紀錄，不是現行契約

`openspec/changes/archive/` 底下的所有文件（`proposal.md`、`design.md`、`tasks.md`、以及各 change 自帶的 spec delta）**一律視為過去的決策歷程**，不是現行需求。

- **現行真相來源只有 `openspec/specs/`**。archive 內的 spec delta 在 archive 當下就已套進 `openspec/specs/`，那份副本是歷史快照。
- **不得**把 archived 文件當成需求依據來做規範稽核、推導驗收條件、或當待辦清單。archived `tasks.md` 裡未勾選的項目**不是** backlog；archived `proposal.md` 裡的約束若與現行 spec 衝突，**以現行 spec 為準**。
- 何時該翻閱：想了解「當初為什麼這樣決定」、追溯某條需求的由來、或比對 spec 演進時。

### 兩個例外（archive 仍在範圍內）

1. **機械性 repo-hygiene 掃描不排除 archive**。`scripts/check_no_dev_paths.sh` 以 `git grep -- .` 掃**全部 git-tracked 檔案**，archive 也算；這是 `cantus-distribution` 規範「CI enforces no development-environment path leakage」的實作。archived 文件若含開發環境絕對路徑／密鑰，照樣要修。同理適用於未來任何 secret／授權掃描。
2. **spec 對帳與回溯修復可讀 archive**。archive 內留有各 change 的 spec delta 與 `@trace` 標註，是 archive 過程吃掉 `@trace`、或懷疑 spec drift 時的比對來源。這屬於「回溯」而非「以 archive 為需求依據」。

---

## Roadmap／架構視覺化產物（不進版控）

`cantus-roadmap.html`、`cantus-explorer.html` 等路線圖與架構視覺化 HTML 屬於本地工程輔助檔（engineering artifacts），**不納入版本控制**。若要產生或更新這類產物，一律輸出到 **`.spectra/roadmap/`**（`.spectra/` 已列入 `.gitignore`，不會進版控）：

- `.spectra/roadmap/cantus-roadmap.html` — 決策稽核／時間軸／進度儀表板
- `.spectra/roadmap/cantus-explorer.html` — 互動式分層架構 + 各情境資料流模擬

兩檔以相對路徑互相連結，必須放在同一資料夾。**請勿**在 repo root 產生這類 HTML，也不要 `git add` 它們（產生後它們會自動被 `.spectra/` 的 ignore 規則蓋住）。
