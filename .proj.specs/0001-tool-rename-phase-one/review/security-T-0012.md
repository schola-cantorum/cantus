# Security review：T-0012（cantus serve 的 /tools 路由與 /skills alias）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0012/serve-tool-routes`。
- Base（`main`）與 merge-base：`b17cf2f`；HEAD：`ee63c0c`。審查對象是 committed 層（三個 commit：`65b63d1`、`bc31af3`、`ee63c0c`；20 個檔）；staged、unstaged、untracked 層都是空的。
- 審查對象的 `branch.diff` SHA-256：`47c19eeedcaf06c52b9de852f973e0346b71ce9bc775c561597a3e3610a08d2e`。本報告之後的修正（commit `29e017f`：`CantusFastAPI` 自己建立 `AliasState`、docstring、型別 import 改名、補測試）沒有再審；它沒有改動路由的註冊、dependency 或 wrapper 的行為。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾；reviewer 只讀檔，結論都是讀程式碼推理，沒有執行驗證。stage 8 另在真的 `cantus serve` 行程上量過 auth none 與 bearer 下兩個路由家族的狀態與 header（見票的 Comments）。
- 信任邊界：沒有帶設定憑證的 HTTP client 不可信；auth mode none 時所有路由開放是營運者的選擇；寫 registry 模組、決定 tool 名稱並啟動行程的學生或營運者可信；introspection 不得露出引數值、結果、例外訊息或 token。
- 本次變更的攻擊面：新增 primary 路由 `/tools/{name}`、`/tools`、`/introspection/tools`；v0.6 路由改由 `add_alias_route` 以同一個 handler 與 dependency list 註冊；包住整個 middleware stack 的 wrapper 依 `scope["route"]` 替 alias 的回應附加兩個常數 header，並在每個樣板第一次使用時寫一筆 log（401、405、500 也算）；保留名稱加入 `tools`；introspection 值改名；snapshot 的 `tools` 欄位與鏡像 validator；模組 `__getattr__` 的舊名；TUI 來源前綴的過渡橋接。票指定 stage 7 要看 alias 路由的 auth 對等與 header 的位置。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（判定的信心） | 處置 |
|---|---|---|---|---|---|
| SEC-T0012-1 | `cantus/serve/_aliases.py`（`AliasState` 以 `id(route)` 為鍵） | route misidentification | low／0.35 | 不成立（0.88） | 未確認為缺陷。路由物件一直被 `app.router.routes` 持有，id 不會被重用；只有 host 事後移除路由才可能發生，而 host 是可信的一方，後果也只是多一個常數 header。 |
| SEC-T0012-2 | `_aliases.py`（未認證的 401／405 會用掉該樣板唯一的一筆記錄） | audit-signal integrity | low／0.6 | 不成立（0.88） | 未確認為缺陷。這是使用者核准的讀法 D3；記錄的文字是固定樣板，每個 app 最多三筆。已知的缺點（掃描器可能先用掉記錄、記錄分不出觸發者）記給 T-0019 的遷移指南。 |
| SEC-T0012-3 | `_aliases.py`（401／405／500 也帶 `Link`，URL 含 `v0.7.0`） | information disclosure | low／0.4 | 不成立（0.85） | 未確認為缺陷。header 是常數；`/tools` 路由是否存在本身就能分辨版本，`/health` 在 v0.6 已回傳版本。 |
| SEC-T0012-4 | `_aliases.py`（`add_alias_route` 的 dependency 由呼叫端傳入） | authorization（defense in depth） | low／0.3 | 不成立（0.93） | 未確認為缺陷。三個註冊點都傳入與 primary 相同的 list；測試對三條 alias、三種 auth 模式、兩個 `*_requires_auth` 旗標逐一比對，mutation check 也確認拿掉任一處的 dependency 會被測試抓到。stage 6 另有同一點的設計建議（S6-19），未採納，列給使用者。 |
| SEC-T0012-5 | `_aliases.py`（假設剛註冊的路由是 `routes[-1]`） | route misidentification | low／0.2 | 不成立（0.95） | 未確認為缺陷。FastAPI 的 `add_api_route` 以 append 加入；若未來改變，後果是標記錯誤（正確性），會被 header 的測試抓到。 |
| SEC-T0012-6 | `_aliases.py`（wrapper 在最外層，host 的 middleware 無法改寫這兩個 header） | middleware composition | low／0.3 | 不成立（0.93） | 未確認為缺陷。附加的是常數 header，沒有攻擊者可控的位元組。最外層是使用者核准的 D1，寫進 T-0019。 |
| SEC-T0012-7 | `_aliases.py`（寫 log 發生在送出回應的路徑上） | availability | low／0.2 | 不成立（0.9） | 未確認為缺陷。每個樣板每個 app 只有一次 logging 呼叫；會丟例外的 logging handler 只能由 host 設定。 |
| SEC-T0012-8 | `cantus/serve/app.py`（tool 名稱不檢查路徑語法） | input validation | low／0.25 | 不成立（0.9） | 未確認為缺陷。v0.6 的 `/skills/{name}` 已是同樣情況；名稱由 registry 的擁有者決定。可另開維護票加名稱白名單，記給 close-out 的 chain analysis。 |
| SEC-T0012-9 | `tests/legacy/test_w06_w16_serve.py`（CLI 測試在行為退化時會短暫啟動 auth none 的 server） | test hygiene | low／0.2 | 不成立（0.95） | 未確認為缺陷。綁在 `127.0.0.1`，環境已去掉 `CANTUS_SERVE_*`；修正後 timeout 縮為 30 秒並明確失敗。 |
| SEC-T0012-10 | `_aliases.py`（`CantusFastAPI` 依賴 `serve()` 事後設定狀態） | availability | low／0.15 | 不成立（0.95） | 未確認為缺陷，但已在 `29e017f` 改成由 `CantusFastAPI.__init__` 建立狀態（stage 6 的 S6-17 也提出同一點）。 |

## 涵蓋範圍的限制

- 沒有做的：相依套件掃描、可用性與速率限制的系統性檢查、低嚴重度強化的全面盤點。
- reviewer 的結論來自讀程式碼；`scope["route"]` 在各 FastAPI／Starlette 版本的行為由主 session 的原型（FastAPI 0.115.0、0.120.0、0.136.1、0.163.2）與測試量測，不是 reviewer 驗證的。
- HTTP 呼叫不執行 hook 與 `validate_args`（R2-5）是 v0.6 的行為，本票只寫成測試，沒有改；它對 ludus 的影響屬於 T-0016／T-0019 的文件與 close-out 的 chain analysis。
- 跨票的 chain analysis 不在本階段，於 epic close-out 進行。
