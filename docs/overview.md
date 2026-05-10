# colab-llm-agent Framework Overview

`colab-llm-agent` 是一個**為 Google Colab + Gemma 4 量身設計的小型 agent framework**。它把 OpenHands 的 EventStream 心臟、smolagents 的 decorator 體驗、以及 LangGraph 的可觀測性結合成一個極簡核心，讓教學與研究都能在單一 Colab notebook 內完整跑完。

## 四層架構

```
+-----------------------------------------------------+
|  User Code        @skill / @workflow / @validator   |  <- decorator-first
+-----------------------------------------------------+
|  Protocols        skill | analyzer | validator |    |  <- 五件 protocol
|                   workflow | tool                   |
+-----------------------------------------------------+
|  Core Runtime     Agent / EventStream / Action /    |  <- bounded loop
|                   Observation / Registry / Result   |
+-----------------------------------------------------+
|  Substrate        ModelHandle (Gemma 4) / Drive /  |  <- Colab-native I/O
|                   Inspector                         |
+-----------------------------------------------------+
```

最上層是使用者程式碼，透過 decorator 把純 Python function 註冊成 protocol；中間兩層是 framework 提供的 runtime；最底層是 Colab 環境本身（model handle、Drive mount、stdout）。

## 五件 Protocol

| Protocol    | 角色                                       | 回傳型別          |
| ----------- | ------------------------------------------ | ----------------- |
| `skill`     | 一個原子能力，例如查表、呼叫 API           | 任意值            |
| `analyzer`  | 對輸入做純讀分析，產出結構化 insight       | dataclass / dict  |
| `validator` | 檢查上一步輸出是否合格，可觸發 retry       | `Result(ok, ...)` |
| `workflow`  | 把 skill / analyzer / validator 串成流程   | 任意值            |
| `tool`      | 對 LLM 公開的 function-call schema wrapper | 任意值            |

`skill` / `analyzer` / `validator` / `workflow` 都是 function-based，只需 decorator；`tool` 則是給 LLM function-calling 的對外介面。

## 與 OpenHands / smolagents 的關係

- **OpenHands**：我們完全沿用 `Action` / `Observation` / `EventStream` 的設計，並把錯誤包成 Observation，不讓 exception 跳出 loop。
- **smolagents**：decorator-first 的 ergonomic 來自這裡，但我們不採用 CodeAgent 直接 exec LLM 程式碼的設計，改走顯式 dispatch。
- **LangGraph**：我們不引入 graph 編譯期，但保留「可重播」這個核心承諾——`Inspector(stream).replay()` 隨時還原整段歷史。

整個 core runtime 約 500 行 Python，沒有額外執行期相依，適合直接 `pip install` 進 Colab。

## 文件樹結構

- `overview.md`（本檔）：四層架構、五件 protocol、相關專案比較
- `quickstart.md`：30 秒從 import 到第一次 agent run
- `protocols/{skill,analyzer,validator,workflow,memory,debug}.md`：每件 protocol 的三入口範例與常見錯誤
- `core/{agent,event-stream,inspector}.md`：runtime 內部資料結構
- `cookbook/{patterns,errors,tips}.md`：常見組合與排錯
- `llms-txt.md`：`docs/llms.txt` 是什麼、為何存在、如何用作老師端可行性測試
