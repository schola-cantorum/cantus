# Security review：T-0015（舊名稱的 surface 收尾）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0015/legacy-surface-closes`。
- Base（`main`）與 merge-base：`72250f1`；HEAD：`4101ec2`。審查對象是 committed 層（三個 commit：`2ac1a90`、`f6f192c`、`4101ec2`；4 個檔，+1123／−1）；staged、unstaged、untracked 層都是空的。**這個 diff 沒有動到 `cantus/` 底下任何檔案**，只新增測試與票的紀錄。
- 審查對象的 `branch.diff` SHA-256：`45b7c2e5d19893e210a80401dbae3315b5671be37bb7f7f25d37886ca69d5068`。本報告之後的修正只動三個測試模組（加強斷言、把 live server 測試的 loopback 請求改成不經環境的 proxy、拿掉一個 `-W` 參數），沒有再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻；它回報已讀過 skill 與 upstream 方法論全文），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾；reviewer 只讀檔，結論都是讀程式碼推理，沒有執行驗證。
- 信任邊界：cantus 是教學用的 agent 框架；模型輸出不可信；寫 Python 程式的學生對自己的 process 是可信的；測試在開發者的機器與 CI（GitHub Actions，來自本 repo 分支的 pull request）上執行。
- 本次變更的攻擊面：把產生的 Python 原始碼寫到 pytest 的 `tmp_path` 再 import 或執行的矩陣測試；把假的 SDK 模組裝進 `sys.modules` 的 fixture；以清理過的環境執行直譯器的子行程測試；在 `127.0.0.1` 的空閒 port 上啟動真的 `cantus serve`（auth mode none）並送兩個 HTTP 請求的測試；把 TUI app 的 `run` 換掉的測試。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（判定的信心） | 處置 |
|---|---|---|---|---|---|
| SEC-T0015-1 | `tests/test_internal_paths_silent.py`（live server 測試） | 測試期間有一個未驗證的 server 在 loopback 上 | low／0.3 | 不成立（0.92） | 未確認為缺陷：只綁 `127.0.0.1`、存活不到一秒、註冊的唯一工具只回傳整數；`tests/cli/test_signal_handling.py` 與 `tests/legacy/test_warning_visibility.py` 已有同樣的做法。 |
| SEC-T0015-2 | 同上（選 port 與綁 port 之間的競態） | TOCTOU | low／0.25 | 不成立（0.92） | 未確認為缺陷：搶到 port 的行程只能讓這個測試失敗或假綠，沒有機密或權限可得。 |
| SEC-T0015-3 | 同上（`urllib` 套用環境的 proxy 設定） | loopback 請求可能送到 proxy | low／0.35 | 不成立（0.93） | 未確認為安全缺陷（只會外洩 port、路徑與無敏感性的 body），但會讓測試在設了 proxy 的機器上不穩。已修正：兩個請求改用不帶 proxy 的 opener。 |
| SEC-T0015-4 | 同上（子行程繼承 `os.environ`，失敗訊息含 stderr） | 環境變數外洩到測試輸出 | low／0.15 | 不成立（0.93） | 未確認為缺陷：子行程執行的是 cantus 自己與測試寫的 script，不會印環境變數；repo 既有的子行程測試做法相同。 |
| SEC-T0015-5 | 同上與 `tests/legacy/support.py`（`tmp_path` 在 `sys.path` 最前面） | import 遮蔽 | low／0.1 | 不成立（0.95） | 未確認為缺陷：`tmp_path` 是 pytest 為每個測試建立的目錄，內容只有測試自己寫的檔案。 |
| SEC-T0015-6 | 同上（部分失敗路徑下 server 子行程可能殘留） | 殘留的行程 | low／0.3 | 不成立（0.93） | 未確認為缺陷：只有在 `Popen` 之後、`try` 之前啟動 thread 失敗時才會發生；殘留的是 loopback 上只回傳整數的 server。未修改。 |
| SEC-T0015-7 | `tests/legacy/test_matrix_w01_w18.py`（假 SDK 的 adapter 模組仍綁在 `cantus.adapters` 的屬性上） | 測試間的狀態殘留 | low／0.2 | 不成立（0.97） | 未確認為缺陷：T-0011 的 fixture 行為相同，`tests/adapters/test_huggingface_real_sdk.py` 已記錄並處理這個殘留；影響只在測試之間。 |

## 涵蓋範圍的限制

- 沒有做的：相依套件掃描、可用性與速率限制的系統性檢查、低嚴重度強化的全面盤點。
- 所有結論都是讀程式碼推理，沒有在共用的 CI runner 上實際驗證競態或 proxy 的情境。
- 本票不改產品程式碼，所以沒有新的產品攻擊面；先前各票記給 close-out 的項目不變。
- 跨票的 chain analysis 不在本階段，於 epic close-out 進行。
