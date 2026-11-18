# Security review：T-0016（ludus 遷移文件修正）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0016/ludus-migration-document`。
- Base（`main`）與 merge-base：`13b77ad`；HEAD：`befb5a7`。審查對象是 committed 層（四個 commit：`20bffd7`、`8ec20d4`、`48b8186`、`befb5a7`；2 個檔，+230／−50）；staged、unstaged、untracked 層都是空的。**這個 diff 沒有動到 `cantus/`、`tests/`、`docs/`、`scripts/` 或 `.github/`**，只改 `.proj.specs/0001-tool-rename-phase-one/ludus-migration.md` 與本票的票檔。
- 審查對象的 `branch.diff` SHA-256：`d1f0d8093e859824819ce51c3604838fd12c9afee64778fde27f11118d357fb9`。本報告之後，stage 6 的修正只改這兩個檔的文字（措辭、補充說明、prompt 的步驟順序與參數），沒有再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻；它回報已讀過 skill 與 upstream 方法論全文），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾（六個都回報已讀 upstream 方法論）。reviewer 只讀檔，結論都是讀文件與程式碼推理，沒有執行驗證。
- 信任邊界：cantus 是教學用的 agent 框架；模型輸出不可信；寫 Python 程式的學生、執行文件指令的 ludus 維護者，對自己的 process 是可信的。ludus 的 submit self-check 是教學閘門，不是認證邊界；broker 是可信的 gateway。
- 本次變更的攻擊面：給 ludus 維護者的 Markdown 文件，內含三段 shell 指令（`python -c` 設 warning filter 後以 `runpy` 執行測試、`env -u PYTHONWARNINGS -u PYTHONPATH python …`、`git grep --untracked …`），以及一段交給 coding agent、在 ludus repo 裡執行遷移的 prompt。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（判定的信心） | 處置 |
|---|---|---|---|---|---|
| SEC-T0016-1 | 文件 Verification 第 1 步 | 安裝名稱（`cantus` 與 PyPI 的 `cantus-agent`）混淆 | low／0.35 | 不成立（0.9） | 未確認為缺陷：文件其他地方與 ludus 的 extra 都寫 `cantus-agent`，同樣的措辭在 base 就有。stage 6 把第 1 步改成寫明「the PyPI package `cantus-agent`」（文件品質修正）。 |
| SEC-T0016-2 | 文件 agent prompt 的 Verify 段 | prompt 沒有限制安裝、push 與 repo 外的寫入 | low／0.4 | 不成立（0.9） | 未確認為缺陷：執行 prompt 的是維護者自己的 agent 與權限，prompt 不含不可信輸入；「Commit and open a PR only as the ludus maintainer's own rules allow」在 base 就有。D5 的限制只約束 cantus 自己 stage 8 的 subagent。未修改。 |
| SEC-T0016-3 | 文件 prompt 第 3 步與三項檢查 | agent 可能放寬 gate 判斷或加 warning filter，讓檢查通過 | low／0.45 | 不成立（0.85） | 未確認為缺陷：需要維護者自己的 agent 作弊且維護者審查失靈；被影響的是教學閘門與驗證可信度，不是安全邊界。這是使用者在 stage 5 決定的 D8（run 3 的名稱清單不擴充），由 stage 8 審 diff 把關。未修改。 |
| SEC-T0016-4 | 文件 check 1（`python -c` 從 ludus 根目錄執行） | 目前目錄排在 `sys.path` 前面，可能遮蔽已安裝的 cantus | low／0.3 | 不成立（0.9） | 未確認為缺陷：能放遮蔽檔的人本來就能直接改測試；`341769d` 的 ludus 根目錄沒有同名模組。未修改。 |
| SEC-T0016-5 | 文件 R2-5 一段 | 沒說 self-check 不是安全邊界，也沒提醒 `cantus serve` 不設 auth 會讓別人用學生的 broker session 操作 plot | low／0.35 | 不成立（0.9） | 未確認為缺陷：`cantus serve` 直接執行 `tool.run` 是本 diff 之前就有的行為，預設只綁 `127.0.0.1`，auth mode none 時 serve 會警告；本次只改文字。列入 close-out chain analysis 的輸入（見下）。未修改。 |
| SEC-T0016-6 | 文件 check 3（`git grep --untracked`） | 可能搜到 repo 內未被 ignore 的 venv 或本機檔案 | low／0.2 | 不成立（0.92） | 未確認為安全缺陷（輸出只回報給維護者本人）。stage 6 的 P-08 以文件品質處理：Verification 前言改成寫明 venv 建在 repo 外或命名為 `.venv`。 |

## 給 epic close-out chain analysis 的輸入

- SEC-T0016-5：ludus 的六個工具以 closure 綁住帶 session token 的 `LudusClient`；若有人把它們經 `cantus serve` 提供、又把 host 改成對外並維持 auth mode none，能連到該 port 的人就能以學生的 session 對其 plot 下動作，submit 前的 self-check 也不會執行（R2-5）。與既有的 R2-5、SEC-T0012-2、SEC-T0012-8 同屬「HTTP 介面繞過 agent loop 的保護」一族。

## 涵蓋範圍的限制

- 沒有做的：相依套件掃描、可用性與速率限制的系統性檢查、低嚴重度強化的全面盤點。
- 所有結論都是讀文件與程式碼推理；文件指令的實際行為由 stage 5 的 harness 與 stage 8 驗證，不在本報告範圍。
- 本票不改產品程式碼，沒有新的產品攻擊面。
- 跨票的 chain analysis 不在本階段，於 epic close-out 進行。
