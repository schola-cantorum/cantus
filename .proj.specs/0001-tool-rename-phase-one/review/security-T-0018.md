# Security review：T-0018（文件網站其餘頁面）

- 範圍：分支 `tickets/T-0018/remaining-site-pages`，base `567dcb0`（= merge-base），審查的 HEAD 為 `f770c78`（committed 層，43 個檔案：17 頁英文、17 頁 zh-tw、8 個 `docs/api` 產生檔與票；diff SHA-256 `9f8ad1aae072fdc93237452fc34cedede77e05a1d8e0df80895f0fc0a962b2f4`）。審查後的修正 commit `04d108e` 只改文件與產生的 `docs/api`；其中與下表有關的三處（SEC-T0018-3、-4、-7）是採用誤報過濾 reviewer 的非安全建議，沒有另外再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 依 upstream 方法論列出所有候選（不套用門檻），它回報完整讀了 `SKILL.md` 與 `references/upstream-security-review.md`；每個候選再交給一個獨立的 `harness-reviewer` 做誤報過濾，八位都回報讀了 upstream 的誤報準則。所有結論都是讀程式碼與文件推論，沒有執行驗證；reviewer 沒有 Bash，base 的文字取自 diff 的刪除行。
- 信任邊界：cantus 是教學用的 agent 框架。模型輸出不可信（決定呼叫哪個 tool 與引數）；tool 回傳值可能帶有模型或先前使用者寫入的文字；`cantus serve` 的 HTTP 用戶端與聊天平台的發訊者在未認證、未驗簽時不可信；寫 Python 的學生對自己的 process 是可信的；文件教的寫法會被學生照抄，所以文件的教學內容算在攻擊面內。
- 本次變更的攻擊面：只有文件。channel 四頁（`mytools/app.py` 由 `cantus serve` 掛載、secret 放環境變數、webhook 驗簽、curl 自測、版本下限）、quickstart-desktop（`0.0.0.0` 上的 `cantus serve`、Cloudflare tunnel、認證模式、introspection、`/tools` 路由）、TUI 頁（token、去敏摘要）、cookbook（hook、validator、tips §7 共用的 `Registry`）、core/agent（沒給 `tools=` 時退回全域 registry）。`cantus/` 套件程式碼、測試與產生器都沒有改動。

## 結果

達到報告門檻（HIGH／MEDIUM 且信心 ≥ 0.8）的 finding：**0**。八個候選都被獨立過濾判定為不成立（不是本次變更新增、可被攻擊者利用的缺陷）。

| id | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果 | 處置 |
|---|---|---|---|---|---|
| SEC-T0018-1 | `docs/site/quickstart-desktop.md:93` | 文件／存取控制描述 | low／0.45 | 不成立（0.85）：`--auth-mode bearer` 對 `/tools` 與 `/skills` 兩組路由套用同一組 dependencies；只寫 `/tools` 的 proxy 規則是頁面沒教的做法，base 寫 `/skills` 時也有對稱的缺口 | 不改（R15：舊路由只寫在 Tool 頁的 legacy 段落） |
| SEC-T0018-2 | `docs/site/channels/google-chat.md:147` | 文件／存取控制描述 | low／0.35 | 不成立（0.85）：伺服器的認證範圍沒有改；這頁沒有教 proxy 或 WAF 規則 | 不改 |
| SEC-T0018-3 | `docs/site/cookbook/tips.md:138` | 文件／共用狀態 | medium／0.5 | 不成立（0.8）：`Registry` 直接共用的語意在 base 已存在，base 的全域 registry 範圍更大；要讓攻擊者碰到高權限 tool，學生得先做出文件沒教的設定 | 採用非安全建議：§7 示範 `agent.registry is reg`，並說明之後加入的 tool 會傳到每個拿著它的 agent（`04d108e`） |
| SEC-T0018-4 | `docs/site/core/agent.md:16` | 文件／授權範圍描述 | low／0.4 | 不成立（0.85）：全域 registry 只由學生 process 裡的程式碼填入，屬可信範圍；fallback 是既有行為 | 採用非安全建議：句子對齊 Tool 頁（可能由函式庫填入、之後註冊的 tool 也看得到）（`04d108e`） |
| SEC-T0018-5 | `docs/site/channels/line.md:62` | 文件／暴露面說明不足 | low／0.55 | 不成立（0.85）：registry 裡的 tool 和 webhook 一起在 tunnel 上公開、channel 頁的指令沒有 `--auth-mode`，這在 base（`/skills/echo`）就一樣；本次只改模組寫法 | 不改；選用的文件建議（說明 registry 的 tool 也會公開成 HTTP 路由、建議加 `--auth-mode bearer`）列給使用者 |
| SEC-T0018-6 | `docs/site/channels/line.md:8` | 文件／版本下限 | low／0.15 | 不成立（0.95）：只有專案擁有者能發佈 0.7.0；發佈前照做只會讓 pip 報錯 | 不改（R16） |
| SEC-T0018-7 | `docs/site/quickstart-agent.md:175` | 文件／防護範圍描述 | low／0.25 | 不成立（0.9）：句子範圍正確；validator 檢查的是菜單，不是安全控制 | 採用非安全建議：補一句「在它之前建立的 agent 仍用沒有防護的 tool」（`04d108e`） |
| SEC-T0018-8 | `docs/site/cookbook/tips.md:72` | 文件／同名取代 | low／0.2 | 不成立（0.9）：範例是只有一個 tool 的新 `Registry`；`register_skill` 在 base 也是同樣的取代語意 | 不改 |

## 給 epic close-out chain analysis 的輸入

- SEC-T0018-1、-2 與 R2-6、X11、SEC-T0017-1 同族：兩組路由並存期間，文件只寫一組路徑時，照文件寫的外部規則會漏掉另一組。
- SEC-T0018-3 與 R2-15、SEC-T0017-5 同族：交給多個 agent 的 `Registry` 是同一個物件，之後加入或取代的 tool 會傳到全部。
- SEC-T0018-5 與 R2-5、SEC-T0012-2、SEC-T0016-5 同族：`cantus serve` 在 auth mode none 時，registry 裡的每個 tool 都對能連到埠的人開放，且不跑 hook 與 `validate_args`。

## 涵蓋範圍的限制

- 沒有執行任何攻擊或 HTTP 請求；路由與認證行為以讀 `cantus/serve/` 原始碼為準（T-0012 的 stage 8 已在真實 `cantus serve` 上驗過路由與 header）。
- 未涵蓋：相依套件掃描、可用性與流量限制、低嚴重度的強化建議（只列給使用者）、channel worker 的行為（OQ-011）、`/docs` 與 `/openapi.json` 不受認證保護（既有）。
- 本報告不代表整個專案是安全的。
