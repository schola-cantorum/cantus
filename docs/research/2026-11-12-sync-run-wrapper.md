# 研究筆記：同步 `run()` 包裝 async 核心，能不能取代 nest_asyncio

- **查證日期**：2026-11-12
- **問題**：cantus 決定把 agent 核心改成 async（`Agent.arun`），保留同步的 `Agent.run()` 給入門使用。Colab 和 Jupyter 的 main thread 已經有正在執行的 event loop，在裡面呼叫 `asyncio.run()` 會拋出 `RuntimeError`。以往的解法是 `nest_asyncio`。我們要確認的是：改用「在背景 thread 的新 loop 上執行」能不能做到同樣的事？
- **方法**：用 multi-agent workflow 平行研究五條線：主流函式庫原始碼、nest_asyncio 與 Jupyter／Colab 的事實、thread 做法的陷阱、本機原型實測、cantus 程式碼盤點。每條線都再經過一輪反駁式審查，最後做完整性檢查。實測用 nbclient／jupyter_client 驅動真正的 ipykernel，涵蓋三組環境：Colab 鎖定的組合（ipykernel 6.17.1、IPython 7.34、tornado 6.6）、Python 3.10 上的 ipykernel 7.3.0、Python 3.12／3.13 上的 ipykernel 7.4.0。中斷相關測試另外涵蓋 Python 3.10–3.14。
- **標記**：【驗】表示看過一手來源或實際跑過；【推】表示推論。原型程式沒有放進 repo，關鍵行為都記錄在下文。
- **採用的決定**：[ADR-0016](../adr/0016-async-core-with-sync-run-wrapper.md)

## 結論

**做得到，但不能用「每次呼叫開一個新 thread、新 loop」的寫法。** 要改成「全行程單一、常駐的背景 loop thread」，加上主動取消與 SIGINT 串接。

- 機制本身已經驗證【驗】。在真 kernel 的 cell 裡，裸呼叫 `asyncio.run` 會拋出 RuntimeError；改走 thread 加新 loop 之後，下列行為都正常：
  - 回傳值正確
  - 例外以原型別重新拋出，traceback 帶有 `arun` 的 frame
  - worker 的 `print` 出現在同一個 cell
  - 搭配 `copy_context()` 時 contextvar 會傳進去
  - 可以巢狀呼叫
  - top-level `await` 不受影響
  - 已經 `nest_asyncio.apply()` 的環境也照樣能跑

  每次呼叫多出約 0.6–0.74 ms。
- Colab 雲端本身沒有實測【推】。推論依據：Colab 的 kernel 是 `ipykernel.ipkernel.IPythonKernel` 的子類別（colabtools `google/colab/_kernel.py:20,25`），而且在 `_kernel.py`、`_shell.py` 裡都找不到 asyncio 相關的客製。

## 陷阱（依嚴重度排序）

| 嚴重度 | 陷阱 | 證據 |
|---|---|---|
| P0 | **每次開新 thread 的寫法，按中斷沒有作用。** `with ThreadPoolExecutor` 離開時會等 worker 跑完，KeyboardInterrupt 要等 `arun` 結束才浮出來；就算拿掉 `with`，worker 也會變成孤兒，繼續呼叫 LLM | 【驗】中斷點在 1.0 s，cell 到 4.0 s 以上才結束；拿掉 `with` 後例外 0.2–0.5 s 就浮出，但 worker 仍繼續執行後續步驟（持續呼叫 LLM）。CPython `concurrent.futures` 文件的 `Executor.shutdown` 段落 |
| P0 | **呼叫端是 `asyncio.run` 或 `asyncio.Runner`（Python ≥3.11）時，第一次 Ctrl-C 會被 Runner 的 SIGINT handler 吃掉。** 那個 handler 只取消 main task、不拋例外，所以 wrapper 收不到中斷。若在阻塞期間直接把 handler 換成 default，script 正常了，uvicorn 卻會壞（關機卡住超過 10 s）；改用「先取消 task、再呼叫原本的 handler」的串接寫法，兩邊都正常 | 【驗】3.12／3.13 跑完 30 步、過了 3 s 才收到中斷，3.10 只要 0.5 s；串接版在 3.10／3.12／3.13 都是 0.5 s，uvicorn 0.2 s 正常結束。CPython `Lib/asyncio/runners.py:102-107`；https://docs.python.org/3/library/asyncio-runner.html#handling-keyboard-interruption |
| P0 | **每次開新 loop，跨呼叫重用的 loop-bound 物件會壞。** 快取在物件上的 `httpx.AsyncClient`、`AsyncOpenAI`，第二次 `run()` 就拋出 `Event loop is closed`；一般 script 也一樣，因為每次 `asyncio.run` 都是新 loop。只有「全行程單一 loop」能在 script → loop 內 → script 的呼叫順序下全部成功 | 【驗】httpx 0.28.1、openai `AsyncOpenAI`，Python 3.10／3.12／3.13／3.14。https://github.com/encode/httpx/issues/2473 |
| P0 | **MLX 的亂數狀態是 thread-local，而且每個新 thread 都從同一個初始值開始。** 在每個新 thread 裡，temp>0 的 `mlx_lm.generate` 產生完全相同的文字；notebook 裡呼叫的 `mx.random.seed()` 對 worker 沒有作用。改用常駐 thread 就恢復正常 | 【驗】mlx 0.31.2（cantus 的 venv）與 0.32.4 都重現。`mlx_lm/sample_utils.py:271-272`。亂數狀態是 thread-local：https://github.com/ml-explore/mlx/issues/4234 。注意：mlx 0.32.0 有一個回歸問題，如果 compiled sampler 是在別的 thread（例如 notebook 的 main thread）載入模型時建立的，連常駐 worker 也會每次取樣都一樣；0.32.1 起修好（https://github.com/ml-explore/mlx/pull/3828 ）。所以專屬 thread 也要負責載入模型和設定 seed |
| P1 | **Python 3.10–3.12 的 `Thread.join()` 被中斷後，`is_alive()` 會誤報 False**，所以不能拿它判斷 worker 是否已停止 | 【驗】3.10／3.11／3.12 皆重現，3.13 起修好。https://github.com/python/cpython/issues/90882 |
| P1 | **阻塞期間，呼叫端的 loop 完全凍結。** notebook loop 上的 task 一次都不會被排程。已經綁在 notebook loop 上的 Lock、Event、Queue、Future、aiohttp session、grpc.aio channel、已有連線的 httpx client，拿到 worker 裡用會拋出 RuntimeError；未競爭的 Lock 是延遲綁定，所以這類錯誤會間歇出現 | 【驗】凍結期間 0 次排程（nest_asyncio 是 25–28 次）；`bound to a different event loop`。CPython `Lib/asyncio/mixins.py:12-21`。ipywidgets 也會凍結是【推】 |
| P1 | **同步阻塞的呼叫無法中途取消。** cantus 目前的 provider 全是同步的，取消要等到下一個 `await` 才生效；OpenAI 和 Anthropic SDK 的預設 timeout 都是 600 s。若 `arun` 裡有同步呼叫沒包 `to_thread`，會拖住共用的 loop【推】 | 【驗】openai `_constants.py:7`、anthropic `_constants.py:10` |
| P1 | **Windows 上 Python <3.14 的 `Thread.join()` 無法被 Ctrl-C 中斷**（lock 等待是否有同樣的版本界線，沒有找到來源）。Jupyter 在 Windows 透過 `interrupt_main()` 送中斷 | 【推】沒有在 Windows 實測。`join` 的部分見 https://github.com/python/cpython/issues/139689 ；lock 等待見相關的 https://github.com/python/cpython/issues/74157 |
| P1 | **在 FastAPI 的 `async def` handler 裡呼叫 `run()` 會卡住整個 uvicorn loop**；在 `def` handler 裡呼叫則沒有影響 | 【驗】`/ping` 的回應從 0.01 s 變成 0.82 s |
| P2 | contextvars 必須用 `copy_context()` 帶進 worker；worker 內做的修改不會傳回呼叫端，這和 `asyncio.run` 的語意一致 | 【驗】 |
| P2 | cell 結束時還沒停的 worker，輸出可能跑到錯的 cell（ipykernel 6.17.1 會送到下一個 cell）。只要取消做對就不會發生 | 【驗】ipykernel changelog 7.1.0 #1451 |
| P2 | Colab 的 `_message.blocking_request`（`userdata.get`、`drive.mount` 都用它）不是 thread-safe；單一 worker 循序呼叫應該沒有問題 | 【推】colabtools `_message.py:108,154-159` |
| P2 | 在無 loop 的情況下跑完 `asyncio.run` 後，main thread 就沒有 current loop，之後呼叫 `asyncio.get_event_loop()` 會出錯；常駐 loop 的設計沒有這個副作用 | 【驗】Python 3.10–3.14 |
| P2 | coroutine 要在決定好要用哪個 loop 之後才建立，否則會出現「never awaited」警告 | 【驗】 |

## 與替代方案比較

- **nest_asyncio 1.6.0**【驗】
  - 維護狀態：repo 已於 2024-03-06 封存，最後一版發於 2024-01-21（https://github.com/erdewit/nest_asyncio 、https://pypi.org/pypi/nest_asyncio/json ）。
  - 運作方式：對整個行程做 monkey-patch，把 Task 和 Future 換成純 Python 實作，連 tornado 也一起 patch。
  - 相容性：遇到 uvloop 會拋出 ValueError；在 3.12–3.14 上，`apply()` 之後任何帶 `loop_factory` 的 `asyncio.run` 都會拋出 TypeError。
  - 優點：notebook loop 不會凍結。
  - Colab 預裝 1.6.0。jupyter_client 7.x 用它，8.x 已經拿掉。
- **nest-asyncio2**（維護中的 fork）【驗】：修了 3.12 以上的問題，但仍然是全域 patch。ipykernel 7.x 只在 Tk 事件迴圈的分支用到它。
- **anyio `start_blocking_portal`**【驗】：在 running loop 裡也能用，loop 可以跨呼叫保留。anyio 是 httpx 的直接相依套件；安裝 serve、tui 或 provider 等 extras 時，cantus 就已經間接裝了它（核心安裝不含）。但從 Python 3.14 起，portal thread 用的是全新的 `Context()`，contextvars 不會自動帶過去；中斷行為沒有實測。
- **直接報錯，要求使用者改用 `await arun()`**【驗】：OpenAI Agents SDK 的 `run_sync` 就是這樣，偵測到 running loop 就拒絕執行（openai-agents v0.24.0 `agents/run.py:2574-2577`）。Pydantic AI 沒有事先檢查，而是在目前的 loop 上呼叫 `run_until_complete`，所以在 running loop 裡會失敗；官方文件建議改用 top-level await。代價是 cantus 現有的 notebook 和 quickstart 全都呼叫 `agent.run()`。
- **同步、非同步各寫一份**（httpx、LangChain）：沒有上面這些陷阱，但要維護兩份程式碼。

## 以背景 thread 包裝同步呼叫的既有函式庫【驗，讀過原始碼】

**常駐 loop thread（與 ADR-0016 的設計相同）**：
- **Prefect 3.9.2 `run_coro_as_sync`**：全域常駐的 loop thread，目的就是共用 async httpx client；遇到 KeyboardInterrupt 會取消 task。
- **unsync 1.4.0**：常駐 daemon loop thread。
- **jupyter_core 5.9.1 `run_sync`**（`utils/__init__.py:98-171`）：沒有 running loop 時，直接在呼叫端 thread 的 loop 上 `run_until_complete`；有 running loop 時（也就是 Jupyter 的情境），改用常駐的 daemon loop，每個呼叫端 thread 一個。nbclient 和 jupyter_client 8.x 都用它取代 nest_asyncio。

**每次呼叫都開新 loop（供比較；正是前面列為 P0 的做法）**：
- **Google ADK 2.14.0 `Runner.run`**（`google/adk/runners.py:1003-1122`）：每次呼叫都開新 thread 跑 `asyncio.run`；會 copy context，用 `call_soon_threadsafe(task.cancel)` 取消。後兩點值得借鏡。
- **langchain_core 1.8.0**（`callbacks/manager.py:352-388`）：有 running loop 時，丟到共用的 thread pool，在 `copy_context()` 裡用 `asyncio.Runner` 執行，每批都是新的 loop。

## cantus 盤點結果（2026-11-12 的 main）

- Agent 目前完全同步：`cantus/core/agent.py:94` 呼叫 `self.model.generate(prompt)`；`:97-179` 的 `run` 是一般的 for 迴圈。
- 所有 provider 都是同步的。遠端和 OpenAI 相容的 provider 把 client 快取在 `self._client`（`cantus/model/providers/openai.py:41-52`），MLX 則把模型和 tokenizer 快取在 `self._model`／`self._tokenizer`。如果之後改成 async provider 並沿用「快取在 self」的寫法，在「每次開新 loop」的設計下就會中第三個 P0 陷阱。
- `cantus/serve/app.py:237-246`：在 `async def` endpoint 裡直接呼叫同步的 `Skill.run`（改名後即 Tool），現在就會卡住 uvicorn。
- channel cookbook（`docs/site/channels/line.md:117`，Telegram、Discord 兩頁和 zh-tw 版本同樣如此）的 worker 跑在 `asyncio.run(main())` 底下，目前只回 echo，還沒有 agent。學生依照「下一步」把 `agent.run()` 加進去時，就會同時碰到 SIGINT 被吃掉和 loop 凍結這兩個陷阱。
- MCP adapter（`cantus/adapters/mcp.py`）跟 MCP SDK v1.x 不相容，任何環境都會壞，跟 event loop 無關。這點已用真正的 stdio MCP server 重現；修正列為 async 核心 epic 的一張票，排在背景 loop runner 之後（見 ADR-0016）。
- `cantus/` 裡沒有任何直接呼叫 `asyncio.run` 或 `nest_asyncio` 的地方。
- 測試缺口：沒有任何測試走「已經有 running loop」的分支；docs harness 每頁都在子行程執行；CI 不會執行 notebook。

## 建議的 `run()` 設計

已經寫進 [ADR-0016](../adr/0016-async-core-with-sync-run-wrapper.md) 的「Required behaviour of run()」：

- 全行程單一常駐的背景 loop。
- 用 `copy_context()` 送出工作。
- 用短 timeout 輪詢等待。
- 呼叫端被中斷時主動取消 task。
- 串接 SIGINT handler。
- 重入時拋出錯誤。
- 同步工作一律包 `to_thread`；MLX 用專屬的單一 thread，並在那條 thread 上載入模型、設定 seed。
- 不依賴 nest_asyncio，但相容於已經 apply 過的環境。
- 待 epic 決定：worker 自己拋出、而不是呼叫端要求的 `CancelledError` 要怎麼呈現。ADK 的做法是包成 `RuntimeError`。

**測試必須涵蓋**：
1. 無 loop 的情況。
2. 在 running loop 裡呼叫。
3. 用 nbclient 驅動真正的 kernel，ipykernel 版本矩陣包含 6.17.1（Colab 鎖定版本）和 7.x。
4. 快取的 async client 在 script → loop 內 → script 的順序下連續使用。
5. contextvar 的傳遞方向。
6. 中斷（Python 3.10–3.14，包含 `asyncio.run` 的 main 和 `interrupt_kernel`）。
7. 不依賴 `is_alive`。
8. thread 不洩漏、程式結束時不會卡住。
9. 已經 apply nest_asyncio 的環境。
10. `get_event_loop()` 不受影響。
11. 不出現「never awaited」警告。
12. 重入時拋出錯誤。
13. MLX 兩次輸出不同：先在 main thread 載入模型，再呼叫兩次（只在 Apple Silicon 上跑）。
14. FastAPI 的 `def` handler 不阻塞。
15. stage 8 手動驗證：Colab 雲端（含停止鍵），以及 Windows 上的 Jupyter 中斷。

## 未解問題

1. 真正的 Colab 雲端沒有實測：前端按中斷是否同樣以 SIGINT 送到 kernel 的 main thread、Linux 加 Python 3.13 的環境、`blocking_request` 在 worker thread 的實際行為。
2. Windows 沒有實測：`interrupt_main` 的中斷路徑、`signal.signal` 串接的語意。
3. ipywidgets 在阻塞期間凍結，屬於推論。
4. anyio portal 和 Prefect 的中斷行為沒有實測。
5. 常駐 loop 被同步呼叫卡住時會拖住所有並行的 `run()`，屬於推論。
