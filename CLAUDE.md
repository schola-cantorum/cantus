> **遷移中**：本專案正從 Spectra＋mattpocock skills 遷移到 harness-agile 範本（分三個 PR）。
> Spectra 與 `openspec/` 已移除，舊內容保存在 Git tag `pre-harness-migration`。
> 遷移完成前，以本檔為準。

---

## Agent skills

### Issue tracker

Tickets 與 spec 以版控 markdown 存放於 `.proj.tickets/`（狀態即目錄）與 `.proj.spec/`；無遠端 tracker。見 `docs/agents/issue-tracker.md`。

### Domain docs

單一 context：repo 根目錄的 `CONTEXT.md` 加 `docs/adr/`，兩者皆由 `/domain-modeling` 在術語或決策真正成形時才建立。見 `docs/agents/domain.md`。

（未安裝 `triage` skill，因此沒有 triage 標籤詞彙，也不要套用任何標籤。）

---

## 工作流：一條主線，遷移期間暫停的兩條路徑

### 主線 —— 日常變更

```
grill-with-docs → to-spec → to-tickets → implement → code-review → 你 commit
                （撞牆才升 wayfinder）
```

- `to-spec` 只在「跨多個 session」時才值得跑；單 session 的變更直接 `grill-with-docs → implement`。
- 規劃深度預設用 `grill-with-docs`（單 session）。只有當工作**確實一個 session 裝不下**時才考慮升級 `wayfinder`（目前未安裝）。

### 遷移期間暫停 —— 契約變動與發版

原本的「例外路徑 A（契約變動走 Spectra）」與「例外路徑 B（`spectra-audit` + Gate A/B/C 後發版）」
隨 Spectra 一起移除。遷移完成前：

- **動到公開 API 表面的變更暫緩**（新增／改名／移除 public 符號、CLI flag、HTTP endpoint、設定欄位）。
- **暫停發版**。新的 release gate 由遷移 PR ② 的 ADR 定義。

### `.proj.spec/`

`to-spec` 產出的**拋棄式快照**，無同步機制，不得引用為需求依據。

---

## Skill 叫用規則

### `implement` 不得自行 commit

`implement` 的 `SKILL.md` 結尾寫著 `Commit your work to the current branch.`——**在本專案不適用**。跑到該 commit 時停手，把變更交回使用者，由使用者依全域規則走 `/tw-emoji-commit`。這同時也是一個人工驗收點。

（`implement` 中段的 `use /code-review` 照常執行，它會命中本 repo 的 `code-review` skill。）

### `diagnosing-bugs` 不得自動觸發

同樣以 frontmatter 加 `disable-model-invocation: true` 實作。它會在使用者只是隨口描述問題時就啟動完整重現流程。需要它時使用者會點名。`.agents/` 在版控內，被 `npx skills update` 覆蓋時 diff 看得到。

### `code-review` 的 sub-agent 不得再委派

`code-review` 第 4 步的兩個 sub-agent brief 末尾都必須帶「直接執行本次審查，不得再呼叫 `/code-review` 或衍生其他 agent」。缺這一句時 sub-agent 會重新發現此 skill 並再度扇出。被 `npx skills update` 覆蓋後依此重建。

---

## Roadmap／架構視覺化產物（不進版控）

`cantus-roadmap.html`、`cantus-explorer.html` 等路線圖與架構視覺化 HTML 屬於本地工程輔助檔（engineering artifacts），**不納入版本控制**。若要產生或更新這類產物，一律輸出到 **`.scratch/roadmap/`**（`.scratch/` 已列入 `.gitignore`，不會進版控）：

- `.scratch/roadmap/cantus-roadmap.html` — 決策稽核／時間軸／進度儀表板
- `.scratch/roadmap/cantus-explorer.html` — 互動式分層架構 + 各情境資料流模擬

兩檔以相對路徑互相連結，必須放在同一資料夾。**請勿**在 repo root 產生這類 HTML，也不要 `git add` 它們（產生後它們會自動被 `.scratch/` 的 ignore 規則蓋住）。
