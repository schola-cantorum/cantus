# Security review：T-0020（根目錄文件、notebook、CI install smoke 與 rename sweep 測試）

- 範圍：分支 `tickets/T-0020/root-docs-notebooks-and-sweep`，base `13ddcbc`（= main，= merge-base），審查的 HEAD 為 `dccb737`（committed 層，18 個檔案：`.github/workflows/cross-platform-install.yml` 的 import smoke、`scripts/smoke_install.sh`、新增的 `tests/test_rename_sweep.py`、三個既有測試的範例或路徑、根目錄文件 8 個、兩本 notebook、`pyproject.toml` 的一行註解與票）。`cantus/` 沒有改動。審查後的修正 commit `5791a62`（sweep 測試的配對語意、測試缺口與 Git 環境隔離）與 `fc3be11`（文件與 notebook 的句子）沒有再送 reviewer；它們沒有改動 workflow 與 script，下表標「採用」的是誤報過濾後仍採用的建議。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 依 upstream 方法論列出所有候選（不套用門檻），它回報完整讀了 `SKILL.md`（73 行）與 `references/upstream-security-review.md`（191 行）；每個候選再交給一個獨立的 `harness-reviewer` 做誤報過濾，九位都回報讀了 upstream 的誤報準則。所有結論都是讀程式碼與文件推論；reviewer 沒有 shell，也沒有執行任何東西。
- 信任邊界：cantus 是教學用的 agent 框架。模型輸出不可信（決定呼叫哪個 tool 與引數）；`cantus serve` 的 HTTP 用戶端在未認證時不可信；寫 Python 的學生對自己的 process 是可信的；pull request 的作者對 CI 而言不可信。文件與 notebook 教的寫法會被讀者照抄，所以算在攻擊面內。
- 本次變更的攻擊面：
  - CI：`cross-platform-install.yml` 的 import smoke（PR 觸發、權限）。
  - `smoke_install.sh`：參數會進 pip 的 requirement 字串；`uv pip install --system`。
  - 在每個 PR 的 CI 執行的 sweep 測試：呼叫 git 的子程序、讀取掃描集合內每個被追蹤的檔案、在 `tmp_path` 建立暫存 Git repository。
  - 學生與 operator 會照抄的文件與 notebook：`llms.txt`（貼給外部 LLM 產生程式碼）、README、根目錄 quickstart 的 tunnel 與 auth 說明、notebook 的 `%pip install` 與新的 `cantus_version` 說明。

## 結果

達到報告門檻（HIGH／MEDIUM 且信心 ≥ 0.8）的 finding：**0**。九個候選都被獨立過濾判定為不成立：它們都不是本次變更新增、可被攻擊者利用的缺陷。其中三個指出的穩健性或文件問題仍被採用為修正。

| id | 位置（審查時的 HEAD） | 類別 | 候選嚴重度／信心 | 過濾結果 | 處置 |
|---|---|---|---|---|---|
| SEC-T0020-1 | `tests/test_rename_sweep.py:176` | 資訊揭露（跟隨 symlink） | low／0.2 | 不成立（0.92）：PR 作者本來就能在 CI 裡印出任何檔案；外洩內容只限含舊名稱的行 | 不改；記為已知（symlink 讀到目標檔，見票的 coverage report） |
| SEC-T0020-2 | `tests/test_rename_sweep.py:189` | 完整性（繼承 `GIT_*` 環境變數） | low／0.25 | 不成立（0.9）：沒有權限跨越，只在 git hook 內跑 pytest 時可能誤改 index；base 的 `tests/test_check_no_dev_paths.py` 也是同樣寫法 | 採用為穩健性修正：git 子程序不繼承 `GIT_*`，暫存 repository 忽略 global／system 設定（`5791a62`） |
| SEC-T0020-3 | `.github/workflows/cross-platform-install.yml:27` | CI 強化（checkout 沒有 `persist-credentials: false`） | low／0.15 | 不成立（0.95）：既有狀態，本 diff 只改 import 那一行；沒有具體攻擊路徑 | 不改；可另開 CI 強化的維護票 |
| SEC-T0020-4 | `notebooks/task_template.ipynb:69` | 供應鏈（引導學生安裝會移動的 `main`） | low／0.3 | 不成立（0.9）：從同一個受信任的 repo 安裝，信任來源不變；spec D7 的釘選維持 v0.6.0 | 不改（說明是核准的 N3；`fc3be11` 只補了切換 runtime 的步驟） |
| SEC-T0020-5 | `llms.txt:199` | 文件（serve 範例公開帶 hook 的 tool、沒提 auth） | low／0.3 | 不成立（0.88）：base 已有同樣的範例，這次範圍反而收斂；hook 不是存取控制 | 部分採用：hook 段落寫明 workflow step 與 `cantus serve` 都不跑 hook（`fc3be11`） |
| SEC-T0020-6 | `docs/quickstart-desktop.md:72` | 文件（`--host 0.0.0.0` 且沒有 auth） | low／0.3 | 不成立（0.85）：既有內容，本票依 D15 只改舊名稱 | 不改；建議另開文件票，根目錄與網站頁一起修 |
| SEC-T0020-7 | `docs/quickstart-desktop.md:87` | 文件（安全提醒只寫 `/tools`，沒寫仍會回應的 `/skills`） | low／0.2 | 不成立（0.9）：教的是啟用 bearer，兩組路由都受保護；與 T-0018 R15 的處置一致 | 不改 |
| SEC-T0020-8 | `scripts/smoke_install.sh:33` | 驗證完整性（`python -c` 在 repository 根目錄 import 原始碼樹） | low／0.15 | 不成立（0.9）：沒有攻擊者，是驗證可信度的問題，而且是既有狀態 | 不改；記為已知，stage 8 在樹外執行 PyPI 模式 |
| SEC-T0020-9 | `llms.txt:148` | 文件（AutoMemory 交出全部四個 tool） | low／0.15 | 不成立（0.92）：與 base 相同；`delete` 只計數、`str_replace` 保留原本的 turn | 採用為文件修正：寫明交給 agent 的方式，並改正 `delete` 與 `str_replace` 的說法（`fc3be11`） |

## 給 epic close-out chain analysis 的輸入

- SEC-T0020-6、-7 與 R2-5、SEC-T0012-2、SEC-T0016-5、SEC-T0018-5、SEC-T0019-1、-9 同族：範例的 `cantus serve` 沒有認證，HTTP 呼叫不跑 hook 與 `validate_args`；根目錄 quickstart 的 `--host 0.0.0.0` 沒有改。
- SEC-T0020-7 與 R2-6、X11、SEC-T0017-1、SEC-T0018-1／-2、SEC-T0019-5／-6 同族：alias 期間有兩組路由，只寫一組的說明或規則可能漏掉另一組。
- SEC-T0020-3、-8：CI 與 install smoke 的驗證可信度（checkout 保留憑證、smoke 在樹內 import 原始碼）。
- SEC-T0020-9 與 SEC-T0014-2、-4 同族：`view` 讀回的記憶不可信，`str_replace` 會寫入。
- 本票讓幾個既有 finding 變好：README、根目錄 quickstart 與兩本 notebook 改成明確的 `tools=`（T0008 的 fallback 族）；`llms.txt` 改教 `tool_name`，並寫明 hook 只在 agent 呼叫時執行（SEC-T0010-01／SEC-T0019-7、SEC-T0019-1 族）。

## 涵蓋範圍的限制

- 沒有執行任何攻擊；所有結論來自閱讀程式碼與文件。stage 8 另外在真實的 `cantus serve` 上驗證了兩種認證模式下兩組路由的狀態碼（見票的 stage 8 紀錄）。
- 未涵蓋：相依套件掃描、可用性與流量限制（例如很大的檔案拖慢 sweep，只影響 PR 自己的 CI）、Windows shell。
- reviewer 只讀了先前各票 security 報告的候選表，沒有逐份讀完內文。
- 本報告不代表整個專案是安全的。
