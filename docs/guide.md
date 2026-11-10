# 協作指南

在專案目錄開啟 Claude Code 或 Codex，從目前的 spec、ticket 與驗證紀錄接續工作。

> **cantus 的在地規則**：Charter 已填寫，round 0 由既有程式碼滿足，不建立 walking skeleton（ADR-0010）；不改 `cantus/` 執行行為、也不動公開 API 的變更走輕量路徑（ADR-0012）；agent 可以在 ticket branch 或 epic 的 `specs/` branch 上 commit，但合併進 `main` 每次都要你核准（ADR-0014）；發版前要過 release gate（ADR-0013）。遷移前的舊 ticket 凍結在 `.proj.tickets/_legacy/`。

## 開始一段工作

告訴開發助理這次要完成的事，以及相關文件或 ticket 路徑。專案目的與流程以 [AGENTS.md](../AGENTS.md) 為準；執行細節見[交付流程](agents/workflow.md)。

| 操作 | Claude Code | Codex |
| --- | --- | --- |
| 定義需求與 Charter | `/grill-with-docs` | `$grill-with-docs` |
| 查看 skills | `/skills` | `/skills` |
| 審查變更 | `/code-review` | `$code-review` |
| 顯式診斷文件與實作差異 | `/egm-drift-report` | `$egm-drift-report` |
| 保存交接紀錄 | `/handoff` | `$handoff` |

Codex 專案設定需在自己的環境信任這個 checkout 後才會套用。帳號、API keys 與信任設定留在本機。完成設定或更新 skills 後，開啟新 session 檢查清單，避免沿用舊的載入結果。

## 找到適合的 skill

cantus 有 33 個 skills：範本的 33 個拿掉 archify，再加上 cantus 自有的 `eli5`。請以 `python3 scripts/verify-project.py` 檢查數量與結構。

| 工作 | Skills |
| --- | --- |
| 環境與工具設定 | `setup-matt-pocock-skills`、`wizard`、`tune-skills`（依使用者的模型重新調校自己 runtime 的 skills，手動觸發） |
| 需求與決策 | `grilling`、`grill-me`、`grill-with-docs`、`wayfinder`、`to-questionnaire` |
| 規格與實作 | `to-spec`、`to-tickets`、`implement`、`tdd`、`prototype` |
| 架構與診斷 | `codebase-design`、`domain-modeling`、`diagnosing-bugs`、`improve-codebase-architecture`、`egm-drift-report`（手動觸發） |
| 審查與驗證 | `code-review`、`security-review`、`agent-browser`、`evidence-report` |
| Git 文案與協作 | `tw-emoji-commit`、`tw-emoji-pr-note`、`tw-emoji-release-note`、`resolving-merge-conflicts`、`handoff` |
| 解說（cantus 自有） | `eli5` |
| 研究與知識傳遞 | `research`、`teach`、`writing-for-agents`、`wait-what`、`i-have-adhd` |

這份專案已設定 `.proj.specs/` 與 `.proj.tickets/`。需要更換 tracker 時才使用 `setup-matt-pocock-skills` 調整，避免重新套入通用 `.scratch/` 預設。標示為手動觸發的 skills 需明確呼叫，包含 `i-have-adhd`。

Claude Code 有同名的原生 `/security-review`。要使用專案版本，可明確要求「讀取並執行 `.claude/skills/security-review/SKILL.md`」；Codex 使用 `$security-review` 選擇專案版本。

## 診斷文件與實作差異

明確叫用 `egm-drift-report`，提供文件檔案／目錄與對應實作範圍。開發助理會逐份核對來源，區分確認差異、待確認事項與預期差異，只建立新的 Markdown 診斷報告。

範本維護報告放在 `.tmpl.docs/research/drift-reports/`；採用後放在既有 epic 的 `reports/`，或 `.proj.specs/_reports/`。來源不足、未查完或期間有變更時，報告會明列 partial、blocked 或 stale，不能解讀成無差異。詳細輸入與報告規則見[診斷契約](agents/drift-report.md)。

這是本機改編的 EGM 診斷能力，需顯式叫用，不會在每張 ticket、一般進度查詢或其他 pipeline 操作中自動執行。報告提供後續修正的證據；需求、spec、traceability、ticket 狀態與既有 gates 仍依現行流程處理。

## 兩套工具如何共用工作

`AGENTS.md` 是共用規範；`CLAUDE.md` 匯入它。skills 依工具分開保存：Claude Code 使用 `.claude/skills/`，Codex 使用 `.agents/skills/`。Anthropic 與 OpenAI 的 prompt 撰寫建議不同，同名 skill 可以各自調整措辭。Codex 的 reviewer／researcher 預設繼承當前 session 的模型與 reasoning effort；Claude 的 researcher 繼承 session，reviewer 則使用角色指定的模型與 effort。Claude 其他角色與完整分工見[模型協作規則](agents/claude-orchestration.md)。

切換工具前，使用 `handoff` 保存工作目標、spec／ticket 路徑、branch／HEAD、未提交變更、驗證結果與下一步。交接文件存放在 `.proj.handoffs/`，不進版控，frontmatter 標註以 session 數或時間計算的到期條件。接手者先確認文件未過期，再確認 Git 狀態後繼續。同一張 ticket 維持一位寫入者；並行實作使用不同 worktree。完整對應見 [runtime.md](agents/runtime.md)。

## 更新與搬移 skills

依要調整的工具修改對應目錄：Claude Code 改 `.claude/skills/`，Codex 改 `.agents/skills/`。兩邊內容不會自動同步；行為層面的修改（流程、輸出位置、gate）需要兩邊都套用時，逐一移植並依各自的官方建議調整措辭。改完後執行：

```bash
python3 scripts/verify-project.py
```

驗證會確認兩邊都有必要 skills、同名 skill 的觸發政策一致，且各自只保留自己工具的設定檔。

## 升級或降級範本

建立專案時，`docs/agents/template-source.json` 會記錄範本版本、建立時的名稱、描述與日期，以及每個範本檔的 SHA-256。`harness-agile migrate` 依這份紀錄，把專案移到**執行中那個版本**的範本內容：要升級就執行較新的版本，要降級就執行較舊的版本。0.4.0 以前的版本沒有這個指令；要降到這些版本，用較新的版本執行 `migrate . --source <該版的未初始化範本 checkout>`。

先 commit 或 stash 所有變更，再預覽計畫（`X.Y.Z` 換成目標版本）：

```bash
uvx --from 'harness-agile==X.Y.Z' harness-agile migrate .
```

```bash
npx --yes --package='create-harness-agile@X.Y.Z' create-harness-agile migrate .
```

確認計畫後，加上 `--apply` 寫入。migrate 不會 commit；完成後檢查 `git diff`，再用 `tw-emoji-commit` 提交。

| 檔案狀況 | migrate 的處理 |
| --- | --- |
| 範本檔沒有改過 | 換成目標版本內容；目標版本已移除的檔案會刪除 |
| 範本檔改過，目標版本也不同 | 保留你的版本，目標版本內容寫入 `<檔名>.harness-new` |
| 你刪除的範本檔 | 不重建 |
| 你改過、但目標版本沒變的範本檔 | 保留，不產生旁置檔 |
| `README.md`、`.gitignore`、`.gitattributes`、`.proj.*`、Git 未追蹤的本機檔 | 不同步。必要的結構調整（例如在 `.gitignore` 加一行）由 migration step 處理，降級時只還原 migrate 自己加入的內容 |
| 路徑上有 symlink 或 junction | 整次中止，不寫入任何檔案 |

出現 `.harness-new` 時，把需要的內容合併進原檔，再刪除旁置檔。處理完之前，`verify-project.py` 會失敗，migrate 也不會再次執行。填寫 Project Charter 之後，只要範本更新了 `AGENTS.md`，就會產生它的旁置檔；合併時保留你的 Charter。

專案沒有這份紀錄，或紀錄是舊格式時，第一次執行要加上 `--adopt --name … --one-liner … --date <建立日期>`。與目標版本不同的檔案都會先寫成旁置檔；若手邊有建立時那一版的未初始化範本 checkout，加上 `--baseline-source PATH`，就能分辨哪些檔案真的改過。

`--name`、`--one-liner`、`--date` 與 `--baseline-source` 只能搭配 `--adopt`。不在 Git 工作區時必須加 `--allow-no-git`，並自行備份。`--json` 會列出每個有動作的檔案分類，方便開發助理檢查。

寫入途中失敗（例如檔案被其他程式鎖住）時，專案可能停在一半。先用 `git status` 確認，再用 `git restore` 與 `git clean` 回到執行前的 commit，排除原因後重跑。

**cantus 升級時要注意**（採用時的狀態見 `docs/agents/template-source.json`）：

- **ADR 編號**：範本的 ADR 在 cantus 改號為 0005–0009。範本若新增 ADR，migrate 會用範本的編號把它加進 `docs/adr/`，跟 cantus 的編號重複；`tests/test_collaboration_workflow.py` 會在 CI 擋下重複編號。請改號接在 cantus 最新 ADR 之後、補上控制項或 `enforcement: manual`，並刪掉原檔。
- **被跳過的範本更新**：migrate 計畫裡列在 `skipped_deleted` 的檔案（範本的 `docs/adr/0001`～`0005`、`skills-lock.json`、archify），範本就算改了也**不會**產生旁置檔。每次升級都要拿範本的新版跟 cantus 的 `docs/adr/0005`～`0009` 手動比對，需要的修改自己合併進來。
- **不帶的檔案**：cantus 不帶 archify 和它的安全說明。範本若新增 `.claude/skills/archify/`、`.agents/skills/archify/` 或 `docs/security/` 底下的檔案，migrate 會把它們加回來；同一個測試會擋下，刪掉即可。
- **授權與導覽**：`LICENSE`、`docs/README.md`、`THIRD_PARTY_NOTICES.md` 是 cantus 自己的版本（ECL-2.0、產品文件導覽）。出現 `LICENSE.harness-new` 時直接刪除；另外兩份只合併跟 skill 授權有關的段落。
- **改過的範本檔**：`AGENTS.md`、`docs/agents/workflow.md`、`issue-tracker.md`、`runtime.md`、`language.md`、`skill-sources.json`、`docs/guide.md` 等出現旁置檔時，保留〈cantus〉段落與 ADR-0010～0014 的規則。

## 規格審查需要獨立上下文

Stage 3 的四軸 review，每個軸與每一輪都使用沒有前面對話的全新子代理。主助理提供當輪 spec、traceability、固定的審查 prompt 與必要專案規範，記錄版本與完成狀態；審查者依這些可見證據找問題。

四軸有效完成且零 P0 才能往拆票前進。第一輪就零 P0 可以通過；最多兩輪，第二輪仍有 P0 就拆分 epic、重新收斂需求。若工具無法建立獨立上下文、某軸失敗、缺檔或版本變動，結果是「未完成」；主助理可以提供診斷，但不能用它當作 gate 通過。不同軸意見衝突時，仍由你裁決。

實際對話隔離與工具權限需各別驗證；角色設定或靜態結構檢查不等於模型行為已通過。完整程序見[審查規則](agents/review.md)，這項要求適用於 Stage 3。

## 確認工作真的完成

結構檢查需要 Python 3.11+：

```bash
python3 scripts/verify-project.py
```

這會檢查共用入口、兩套 skills 目錄、觸發政策、sanitizer、來源 checksum 與角色設定。它驗證協作設定；cantus 產品的 build／test 命令見 `AGENTS.md`〈Build and test commands〉。

瀏覽器功能可用 `agent-browser`，或宿主提供且符合驗證需求的瀏覽器工具；原生應用程式、CLI 與 daemon 需要對應的 e2e harness。GitHub／GitLab CLI、MCP 連線與服務登入按需設定。回報結果時，說明實際驗證了哪個介面。

每次 `git commit`（含 amend）都使用專案的 `tw-emoji-commit` 產生並清理訊息；PR 與 release 文案使用對應的 `tw-emoji-*` skill。若 skill 不可用，停止該動作並回報。沒有 remote 時可在本機合併，有 remote 時依所在平台的流程交付；在 cantus，合併進 `main` 每次都要你核准（ADR-0014）。

