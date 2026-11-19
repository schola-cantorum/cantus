# Security review：T-0019（v0.6.0 → v0.7.0 遷移指南與 CHANGELOG）

- 範圍：分支 `tickets/T-0019/migration-guide-and-changelog`，base `4bad046`（= merge-base），審查的 HEAD 為 `c753ba8`（committed 層，3 個檔案：新增的 `docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md`、`CHANGELOG.md` 的 `[Unreleased]` 條目與票；diff SHA-256 `a4b70bb1b338e4a5e4cf1008d4336a753c81b5b35133826c5ca5954320a553e5`）。審查後的修正 commit `73fd75c`（指南）與 `b994485`（重新產生的 CHANGELOG）只改文件；下表標「採用」的項目是誤報過濾後仍採用的文件建議，沒有另外再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 依 upstream 方法論列出所有候選（不套用門檻），它回報完整讀了 `SKILL.md` 與 `references/upstream-security-review.md`；每個候選再交給一個獨立的 `harness-reviewer` 做誤報過濾，十一位都回報讀了 upstream 的誤報準則。所有結論都是讀程式碼與文件推論；reviewer 沒有 shell，只引用了 harness 留下的 `cantus serve` 執行紀錄（`server.stderr`）。
- 信任邊界：cantus 是教學用的 agent 框架。模型輸出不可信（決定呼叫哪個 tool 與引數）；`cantus serve` 的 HTTP 用戶端在未認證時不可信；寫 Python 的學生對自己的 process 是可信的；升級伺服器的 operator 會照這份指南做，所以指南的建議算在攻擊面內。
- 本次變更的攻擊面：只有文件。deny-list 與 proxy 的路徑建議（X11、R2-6，兩個方向）、`cantus serve` 的範例（loopback、auth mode none、範例模組與 curl）、舊路由與新路由的認證對等（R7）、`gated_routes`（R8）、第一次使用的 log 會被掃描器用掉（R7）、關掉與升級警告的建議（V1、V9）、`_dispatch_skill` 覆寫的防護與其缺口（X8）、HTTP 呼叫不跑 hook 與 `validate_args`（V6）、CHANGELOG 條目與外部連結。`cantus/` 套件程式碼、測試、workflow 與產生器都沒有改動。

## 結果

達到報告門檻（HIGH／MEDIUM 且信心 ≥ 0.8）的 finding：**0**。十一個候選都被獨立過濾判定為不成立（不是本次變更新增、可被攻擊者利用的缺陷）；其中七個指出的文件不精確仍被採用為文件修正。

| id | 位置（審查時的 HEAD） | 類別 | 候選嚴重度／信心 | 過濾結果 | 處置 |
|---|---|---|---|---|---|
| SEC-T0019-1 | 指南 X8（1240 行） | 文件／缺少警告 | low／0.5 | 不成立（0.85）：`serve()` 只收 `Registry`，HTTP 路由從來不經過 `Agent._dispatch_*`，這在 v0.6 就是如此；指南沒有教讀者把 HTTP 當成受 dispatch 保護 | 採用：X8 補一句「`cantus serve` 直接呼叫 tool（V6）」（`73fd75c`） |
| SEC-T0019-2 | 指南 X8（1243 行） | 文件／防護缺口清單 | low／0.55 | 不成立（0.85）：行為正確但不是本次新增的缺陷，屬缺口清單少列一項 | 採用：補上「指派到 instance 的方法」（`73fd75c`） |
| SEC-T0019-3 | 指南 V1（1732 行） | 文件／強化建議 | low／0.45 | 不成立（0.85）：v0.6 根本沒有警告；V1 只過濾 `CantusDeprecationWarning`，不會藏起 serve 的未認證 `UserWarning` | 採用：V1 說明整類關掉也會藏起 W11，建議改用 `message=` 過濾單一訊息（`73fd75c`） |
| SEC-T0019-4 | 指南 R8（891 行） | 文件／安全相關描述 | low／0.6 | 不成立（0.85）：描述不精確會造成稽核誤報，不會造成放行 | 採用：R8 改為實際列出的路徑與各自的 auth 條件（`73fd75c`） |
| SEC-T0019-5 | `CHANGELOG.md:14` | 文件／存取控制建議 | low／0.6 | 不成立（0.85）：CHANGELOG 只摘要，完整的兩個方向寫在指南 X11 | 採用：重新產生的條目寫出兩個方向（`b994485`） |
| SEC-T0019-6 | 指南 Checklist（1877 行） | 文件／存取控制建議 | low／0.55 | 不成立（0.85）：升級者手上的規則是寫給 `/skills` 的，照做會兩邊都擋 | 採用：Checklist 第 6 項寫出兩個方向（`73fd75c`） |
| SEC-T0019-7 | 指南 A5（1707 行） | 文件／模型輸出過濾 | low／0.45 | 不成立（0.85）：`tool_name` 優先是凍結 spec 的決定，由先前的票實作；指南如實記錄 | 採用：A5 補上「改檢查 parse 後的 `tool_name`，或兩個 key 都檢查」（`73fd75c`） |
| SEC-T0019-8 | 指南 X11（1345 行） | 文件／路徑正規化 | low／0.3 | 不成立（0.85）：percent-encoding 是所有放在 proxy 後的路由都有的性質，與這次改名無關 | 不改 |
| SEC-T0019-9 | 指南 R0（779 行） | 文件／不安全範例 | low／0.3 | 不成立（0.9）：指令沿用 CLI 預設（`127.0.0.1`、auth none），沒有新增不安全設定 | 採用：R0 說明範例沒有認證，升級真正的伺服器時保留原本的 `--host` 與認證設定（`73fd75c`） |
| SEC-T0019-10 | 指南 R5、R7（878 行） | 文件／監控 | low／0.3 | 不成立（0.93）：「每個 template 只 log 一次」是 T-0012 的既有設計（D3），指南如實說明 | 不改 |
| SEC-T0019-11 | 指南 R0（779 行） | 文件／模組遮蔽 | low／0.15 | 不成立（0.92）：學生對自己的資料夾是可信的；`PYTHONPATH=.` 是 `cantus serve` 匯入本地模組的方式 | 不改 |

## 給 epic close-out chain analysis 的輸入

- SEC-T0019-5、-6 與 R2-6、X11、SEC-T0017-1、SEC-T0018-1／-2 同族：兩組路由並存期間，只寫一組路徑的規則會漏掉另一組。這張票在指南、Checklist 與 CHANGELOG 都寫出兩個方向。
- SEC-T0019-1 與 R2-5、SEC-T0012-2、SEC-T0016-5、SEC-T0018-5 同族：`cantus serve` 直接呼叫 tool，不跑 dispatch 覆寫、hook 與 `validate_args`。
- SEC-T0019-3 與 W11 的設計同族：W11 是 agent 用到函式庫註冊的 tool 的唯一訊號，整類關掉警告會一併藏起來。
- SEC-T0019-7 與凍結 spec 的 `_action_name` 規則同族：只看 `skill_name` 的外部過濾器在 `tool_name` 優先後會被繞過。

## 涵蓋範圍的限制

- 沒有執行任何攻擊或 HTTP 請求；路由與認證以讀 `cantus/serve/` 原始碼為準。這張票的 harness 在真實 `cantus serve` 上跑了指南的 curl 與 httpx 範例，並比對了三條舊路由的 header（stage 5 與 stage 8 的紀錄），但沒有測試認證模式。
- 未涵蓋：相依套件掃描、可用性與流量限制、percent-encoding 等 proxy 端的路徑正規化、Windows shell。
- 本報告不代表整個專案是安全的。
