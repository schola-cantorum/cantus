# Stage 7 安全審查：T-0003（移除失效的 litellm ignore）

- 日期：2026-11-11
- 分支：`tickets/T-0003/remove-dead-litellm-ignores`
- Base：`origin/main` = merge-base = `8323be8`（PR #43 merge 後）
- Worktree：`.claude/worktrees/xenodochial-aryabhata-b94fb4`
- 審查方法：`.claude/skills/security-review/SKILL.md`

## 範圍

審查時所有變更都還沒 commit，沒有 committed diff：

| 狀態 | 檔案 |
|---|---|
| 已修改 | `.github/workflows/supply-chain.yml`：刪除 litellm 區塊（1 行註解、11 個 `--ignore-vuln`），拿掉新的最後一個參數結尾的 `\`，更新標頭註解 |
| 已修改 | `.proj.tickets/_legacy/pending/supply-chain-backlog/01-remediate-acknowledged-advisories.md`：新增一行 log |
| 未追蹤 | `.proj.tickets/0000-maintenance/T-0003-remove-dead-litellm-ignores.md`：新票 |
| 未追蹤 | 本報告 |

沒有改到 `cantus/`、`pyproject.toml` 或 guard script。

## 審查過程

1. **第一輪候選審查**（`harness-reviewer`）：審的是先前的方案，也就是新增 13 筆 ignore。這輪的候選 C1 發現 dspy 3.5.0 已把 litellm 改成選用依賴，parent 查證屬實，所以方案改成移除 11 筆，第一輪其他候選也隨之失效。
2. **第二輪候選審查**（`harness-reviewer`，fresh context）：審的是目前這份移除 diff。
3. **假陽性過濾**：沒有任何候選達到 HIGH 或 MEDIUM，所以沒有另外派獨立 reviewer 做假陽性過濾。下面每個 LOW 候選，都由 parent 直接對照證據處理。**這一步的獨立性因此降低。**

## 結論

**沒有達到回報門檻的 finding。** 移除 `--ignore-vuln` 只會讓 pip-audit 回報更多，不會更少。所以這次變更最壞的結果是 CI 亮紅燈（可用性問題），不會藏住漏洞。

## 候選的處置

| ID | 嚴重度／信心 | 內容 | 處置 |
|---|---|---|---|
| F1 | LOW／0.95 | 擷取的 diff 夾帶 T-0002 的檔案 | 屬實。原因是審查期間 origin/main 前進到 `8323be8`（PR #43）。分支已移到新 base，重新確認 `git diff origin/main --stat` 只剩本票的檔案 |
| F2 | LOW／0.85 | 本機重播用的是 darwin 解析，不是 CI 的 Linux | 已修正。main、openhands 改用 x86_64 manylinux 重新解析並重播，結果是 0 筆未列入 |
| F3 | LOW／0.5 | openhands 重播沒加 `--refresh` | 已修正。三個群組都用 `--refresh` 重新解析 |
| F4 | LOW／0.3 | 「6 ignored」和 4 個 ID 對不上 | 不是錯誤。pip-audit 把 diskcache 的 PYSEC-2026-2447 和 langchain-core 的 PYSEC-2026-2562 各列了兩次，4 個 ID 共比對到 6 筆。票上已寫明 |
| F5 | LOW／0.9 | 標頭註解「All 19」已過時 | 已補一句：目前剩 4 筆，移除紀錄在 backlog log |
| F6 | LOW／0.4 | 舊環境，或使用者自行在 `cantus[openai]` 旁加裝 litellm，仍可能拿到 1.80.x | 接受，不在本票處理。這個 audit 只檢查全新安裝的依賴閉包；advisory 都在 LiteLLM Proxy server，而 cantus 不會啟動 proxy（`cantus/` 沒有 import litellm，`cantus/adapters/dspy.py` 只用 `dspy.Tool`）。已記在票的 Comments |
| F7 | LOW／0.9 | 票的 slug 和內容意思相反 | 已修正。branch 還沒 push，已改名為 `remove-dead-litellm-ignores`，票的檔名也一起改 |
| F8 | LOW／0.7 | 票轉述 workflow 規則不精確 | 已改為引用原文，並說明這次是套件離開了依賴閉包 |

## 排除的候選

- **移除 ignore 會削弱 guardrail**：排除。三個群組共用同一份 ignore 清單，已逐一確認：
  - main 群組沒有 litellm。
  - openhands 群組是 litellm 1.109.0，不在 11 個 ID 的任何影響範圍內。
  - mlx 群組沒有 litellm。
- **shell／YAML 正確性**：排除。
  - 抽出 `run:` 區塊跑 `bash -n` 通過。
  - 剩下的 4 個 ID 都有傳進 pip-audit，最後一個參數沒有懸空的 `\`。
- **trigger／權限**：排除。`on:` 和 `permissions: contents: read` 都沒改。
- **機密或開發路徑外洩**：排除。`scripts/check_no_dev_paths.sh` 通過，新文字裡只有一個公開的 Actions run URL。
- **`tests/test_guardrail_config.py`**：排除。這些測試不解析 ignore 清單；本機跑 82 passed。

## 執行過的驗證

| 檢查 | 結果 |
|---|---|
| 用 workflow 的 audit 指令重播 main 群組（x86_64 manylinux、Python 3.12、`--refresh`） | dspy 3.5.0，沒有 litellm；`No known vulnerabilities found, 6 ignored` |
| 重播 openhands 群組（x86_64 manylinux） | litellm 1.109.0、openai 2.54.0；`No known vulnerabilities found` |
| 重播 mlx 群組（macOS 14 arm64） | mlx-lm 0.32.2，沒有 litellm；`No known vulnerabilities found` |
| `tests/test_guardrail_config.py` 加 `tests/test_collaboration_workflow.py` | 82 passed |

本機重播用的是 `pip-audit -r --no-deps --disable-pip`，不是 CI 的已安裝環境模式。真正的驗收是 PR 上三個 `pip-audit` job 的結果。

## 涵蓋限制

- 依專案規則，沒有涵蓋：依賴掃描本身、DoS／rate limiting、低嚴重度 hardening。
- 沒有跑 actionlint。
- 本報告不代表整個專案是安全的。
