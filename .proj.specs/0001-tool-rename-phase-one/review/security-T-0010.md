# Security review：T-0010（Wire format and grammar speak Tool）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0010/wire-format-and-grammar`。
- Base（`main`）與 merge-base：`7208bba`；HEAD：`3e35059`。審查對象是 committed 層（三個 commit：`83599f8`、`a9df926`、`3e35059`；21 個檔，+1445／−233）；staged、unstaged、untracked 層都是空的。
- 審查對象的 `branch.diff` SHA-256：`78fe456e9c34c97319c8d90209d00966b5019d222a6114e5657efc9caca8c9b7`。本報告之後的修正（commit `c7a4888`：stage 6 的測試與 docstring）沒有再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾；reviewer 只讀檔，所有結論都是讀程式碼推理，沒有執行驗證。
- 信任邊界：model 輸出與 HTTP 呼叫者不可信；寫 Python 的學生與設定 warning filter 的維運者對自己的 process 可信；model 輸出會被解析成 action 並 dispatch 工具，解析錯誤的文字（含 model 自己的輸出）會回饋給 model。
- 本次變更的攻擊面：兩個解析器的取名規則（`tool_name` 優先、舊 key 退用並發 W13）；回饋給 model 的錯誤文字；`build_schema`；grammar 函式在 `registry is None` 時退回全域 registry（W12）；class decorator 新增的 property setter。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（判定的信心） | 處置 |
|---|---|---|---|---|---|
| SEC-T0010-01 | `cantus/grammar/tool_call.py`（`_action_name` 的優先序） | parser differential | low／0.35 | 不成立（0.88） | 未確認為缺陷。兩個 key 都有時改用 `tool_name` 是 TR-83 規定的行為；兩個解析器共用同一條規則，名稱仍受 registry 檢查。只看原始 JSON 裡 `skill_name` 的外部過濾器在升級後要更新，記給 T-0019。 |
| SEC-T0010-02 | `cantus/grammar/tool_call.py`（W13 在 error filter 下被吞掉） | logging / detection gap | low／0.3 | 不成立（0.9） | 未確認為缺陷。TR-85 規定 W13 不得逸出；不留痕跡是使用者核准的讀法（D10）。記給 T-0019。 |
| SEC-T0010-03 | `cantus/grammar/tool_call.py`（model 可觸發 W13 的發送） | availability / log flooding | low／0.3 | 不成立（0.9） | 未確認為安全缺陷。每個舊 key 的輸出一則警告，數量受 `max_iterations` 限制；自訂的 `showwarning` 若丟出其他例外屬宿主自己的設定。 |
| SEC-T0010-04 | `cantus/grammar/tool_call.py`（W12 在 error filter 下丟出） | availability | low／0.25 | 不成立（0.95） | 未確認為缺陷。只有 W13 免於升級是 spec 的規定（AC-19、AC-22）；`cantus/` 內沒有不帶 `registry` 的呼叫點。 |
| SEC-T0010-05 | `cantus/grammar/tool_call.py`（未註冊訊息以字面引號放入 model 控制的名稱） | injection into feedback | low／0.2 | 不成立（0.9） | 非本次變更引入（v0.6 相同的寫法，D7 核准維持）；`GrammarError` 不會回饋給 model，agent 端用 `repr`。 |

## 涵蓋範圍的限制

- 沒有做的：相依套件掃描、可用性與速率限制的系統性檢查、低嚴重度強化的全面盤點。
- Colab 上的實際模型行為（AC-40）不在本報告範圍。
- 跨票的 chain analysis 不在本階段，於 epic close-out 進行。
- 零 finding 表示在上述範圍內沒有發現可利用的缺陷，不代表整個專案安全。
