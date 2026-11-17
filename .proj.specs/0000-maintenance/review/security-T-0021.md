# Stage 7 安全審查：T-0021（openhands 群組認列 pillow 12.3.0 advisory）

- 日期：2026-11-17
- 分支：`tickets/T-0021/acknowledge-openhands-pillow-advisories`
- Base：`origin/main` = merge-base = `fa92292`（PR #47 merge 後）
- Worktree：`.claude/worktrees/zen-wilbur-0889c5`
- 審查方法：`.claude/skills/security-review/SKILL.md`

## 範圍

審查時所有變更都還沒 commit，沒有 committed diff：

| 狀態 | 檔案 |
|---|---|
| 已修改 | `.github/workflows/supply-chain.yml`：`openhands` matrix entry 新增 `acknowledged`（42 個 ID）與 `acknowledged_for`（`pillow==12.3.0`）；audit step 改由 `env:` 讀入這兩個欄位、組出 `--ignore-vuln` 參數，並在 audit 後檢查已安裝版本；更新兩段指引註解 |
| 未追蹤 | `.proj.tickets/0000-maintenance/T-0021-acknowledge-openhands-pillow-advisories.md`：新票 |
| 未追蹤 | 本報告 |

沒有改到 `cantus/`、`pyproject.toml` 或 guard script。

## 審查過程

1. **第一輪候選審查**（`harness-reviewer`，fresh context）：審最初的 diff，提出 F1–F5，全部 LOW。
2. **parent 查證與修正**：F1 用 OSV 逐一查證後排除；F2–F5 修正（見下表）。
3. **第二輪候選審查**（同一位 reviewer，只審修正後的新程式碼）：提出 R1–R3，全部 LOW，沒有找到注入、繞過或 fail-open 的路徑。
4. **假陽性過濾**：沒有任何候選達到 HIGH 或 MEDIUM，所以沒有另外派獨立 reviewer 做假陽性過濾，每個 LOW 候選都由 parent 對照證據處理。**這一步的獨立性因此降低。** reviewer 沒有 shell，Git 範圍由 parent 擷取。

## 結論

**沒有達到回報門檻的 finding。** 這次變更刻意讓 pip-audit 少報 42 筆，所以重點在「會不會多藏了什麼」：

- 認列只在 `openhands` 群組生效；`main`、`mlx` 拿到空字串，pillow 12.3.0 在那兩組仍會亮紅燈（本機重播確認）。
- 42 個 ID 在 OSV 上都是 Pillow 自身程式碼的 advisory。
- 已安裝的 pillow 只要不是 12.3.0，job 就會失敗，所以上游放寬 pin 後不會留下沒人清的 ignore。

## 候選的處置

| ID | 嚴重度／信心 | 內容 | 處置 |
|---|---|---|---|
| F1 | LOW／0.4 | pip-audit 依 ID 與 alias 跨所有套件比對；若某個 CVE 屬於 pillow 內嵌的原生函式庫（libtiff、libwebp 等），可能連帶蓋掉其他 wheel 的同一個 CVE | 排除。parent 逐一查 `api.osv.dev/v1/vulns/<id>`：22 個 CVE 的摘要都是「Pillow: …」，alias 為 `BIT-pillow-*` 或 GHSA，屬 Pillow 自身程式碼。workflow 註解已寫明比對規則 |
| F2 | LOW／0.7 | 上游放寬後沒有任何東西會提醒移除；pip-audit 不回報未使用的 ignore | 已修正。新增 `acknowledged_for`，版本不符時 job 失敗並提示刪除兩個欄位。另在註解附上 browser-use issue 4824 |
| F3 | LOW／0.5 | 「cantus/ 沒 import pillow」容易被讀成「使用者碰不到」，但 OpenHands browser tool 會用 pillow 解碼網頁截圖 | 已修正註解與票的措辭。使用者面向的公告（CHANGELOG／文件）沒有在本票處理，記在票的 Comments，發版時經 `/tw-emoji-release-note` 處理 |
| F4 | LOW／0.05 | `for id in $GROUP_ACKNOWLEDGED` 未加引號，會做 glob 展開 | 已修正，改用 `read -r -a`。值是 repo 內的靜態字串，原本也沒有跨越信任邊界 |
| F5 | LOW／0.4 | 指引註解只講共用清單，維護者可能把單一群組的 advisory 放進共用清單 | 已修正，註解寫明兩種機制及選用規則 |
| R1 | LOW／0.5 | `acknowledged_for` 只檢查版本，不檢查 ID 是否真屬於該套件 | 接受。目前 42 個 ID 已用 OSV 查證；之後新增 entry 由 review 把關。加 `-f json` 逐筆比對套件名屬於額外機制，不在本票範圍 |
| R2 | LOW／0.6 | `2>/dev/null` 會藏住版本查詢失敗的原因 | 已修正，保留 stderr；`|| echo none` 仍讓它 fail closed |
| R3 | LOW／0.4 | 版本檢查在 audit 前就 exit，pin 放寬那段期間看不到其他新 finding | 已修正。改成先跑完 pip-audit、記下結果，再因版本不符 exit 1 |

## 排除的候選

- **expression／script injection**：排除。`matrix.acknowledged`、`matrix.acknowledged_for` 只經 `env:` 進入腳本，沒有內插進 `run:`；`$pkg` 以 `sys.argv[1]` 傳給 Python，不進 `-c` 原始碼。fork PR 本來就能改整個 workflow，token 是 `contents: read`、沒有 secret。
- **`::error::` 文字的 workflow-command injection**：排除（信心 0.05）。內容來自靜態字串與套件自己的 Version metadata；能控制套件 metadata 的人在安裝時就已能執行任意程式碼。
- **`acknowledged_for` 解析邊界**：排除。空值、缺 `==`、`===`、多個 `==`、前後空白、短版本號或 local version 都會造成不符而失敗；Python 或 importlib 失敗得到 `none`，同樣失敗。
- **bash 3.2（macOS runner）**：排除。`read -a`、here-string、`+=()` 都支援；沒有 `-u`，空陣列展開沒問題。
- **guardrail 測試**：沒有加 `continue-on-error`，step 仍含 `pip-audit`，`tests/test_guardrail_config.py` 的檢查照常適用。

## 執行過的驗證

| 檢查 | 結果 |
|---|---|
| 從 YAML 抽出 audit step，以 `/bin/bash` 3.2 `-eo pipefail` 跑，pip-audit 改為 `-r <resolution> --no-deps --disable-pip`；resolution 是 `openhands` extra 在 x86_64 manylinux、Python 3.12、`--refresh` 的解析 | 版本相符：`No known vulnerabilities found, 42 ignored`，exit 0 |
| 同一份解析、兩個欄位皆空（`main`／`mlx` 拿到的值） | `Found 42 known vulnerabilities`，exit 1 |
| `acknowledged_for` 不符 | audit 照跑，接著 `::error::`，exit 1 |
| 不符，且少認列一個 ID | audit 列出 1 筆 finding，接著 `::error::`，exit 1 |
| `acknowledged_for` 指向未安裝套件 | `::error::`（`none is installed`），exit 1 |
| 42 個 ID 與 run 43872151231、43804092684 失敗 log 的 ID | 完全一致 |
| `actionlint` | 通過 |
| `tests/test_guardrail_config.py` | 64 passed |
| `scripts/check_no_dev_paths.sh` | 通過 |

本機重播用的是 requirements 模式，不是 CI 的已安裝環境模式。真正的驗收是 PR 上三個 `pip-audit` job 的結果。

## 涵蓋限制

- 依專案規則，沒有涵蓋：依賴掃描本身、DoS／rate limiting、低嚴重度 hardening。
- pillow 12.3.0 這 42 筆 advisory 本身對 `cantus[openhands]` 使用者的風險，是本票刻意認列的部分，不在本審查範圍。
- CI 裡的 pip-audit 沒有釘版本；本機為 2.10.1，假設比對規則相同。
- 本報告不代表整個專案是安全的。
