# `cantus tui` — 終端機觀測儀表板

`cantus tui` 是一個**唯讀**的終端機儀表板（Textual TUI）。它透過 server 的 `/introspection` 與 `/health` endpoint，連到一個正在執行的 `cantus serve` 實例，把它當下的執行期狀態即時 render 出來。這個儀表板不會下任何指令，也不會更動 server 的任何狀態——所以你大可把它一直開著對著課堂上的 demo、或是一台行為怪怪的 server，完全不用擔心手一滑按到鍵就改壞了什麼。

想了解每個 endpoint 背後的資料契約，請看 [`docs/protocols/serve.md`](./protocols/serve.md#introspection-endpoints)。

## 安裝與啟動

`cantus tui` 需要 `tui` extra。Textual 這個相依藏在一道 lazy import gate 後面，所以如果你少裝了這個 extra，`cantus tui` 會直接提示你跑 `pip install cantus-agent[tui]`：

```bash
pip install cantus-agent[tui]
cantus tui --url http://127.0.0.1:8765
```

常用旗標：

| 旗標 | 預設值 | 用途 |
| --- | --- | --- |
| `--url` | `http://127.0.0.1:8765` | 目標 `cantus serve` 的 base URL（本機位址、或經由 tunnel 對外曝光的位址都行） |
| `--auth-mode` | `none` | 認證模式，三選一：`none` / `bearer` / `api-key`，必須跟 server 的 `auth_mode` 一致 |
| `--poll-interval` | `2.0` | 自動刷新間隔，單位是秒 |

## 五個分頁

一啟動，畫面就是一個帶五個分頁的 `TabbedContent`。按數字鍵 `1`–`5` 就能在它們之間切換：

| 鍵 | 分頁 | 顯示內容 |
| --- | --- | --- |
| `1` | **Dashboard** | 主總覽。左側是 Sessions 清單（最近被 dispatch 的那幾個 run），右側由上到下堆疊著 Queue（各 channel 的 queue 深度）與 Health（server 是否連得上，外加 `cantus_version`） |
| `2` | **Skills** | 列出每個已註冊 Skill 的 `name`、`description` 與 `args_schema`；若有 run 正在進行、且當下用到某個 skill，那個 skill 會被標記出來 |
| `3` | **Permissions** | 目前生效的認證設定：`auth_mode`、`dashboard_requires_auth` / `introspection_requires_auth` 這兩個 flag，以及被 auth gate 擋住的路徑清單。token 值**永遠不會**顯示 |
| `4` | **Dataflow** | 由 registry 與 channels 推導出來的靜態元件拓樸（節點與邊：serve、event stream、各個 skill、各個 channel） |
| `5` | **Inspector** | 單一 run 的 Action/Observation 步驟軌跡（從某一列 Sessions 鑽進去看，詳見下方） |

## 鍵位

| 鍵 | 動作 |
| --- | --- |
| `1`–`5` | 切換到對應分頁 |
| `Enter` | 在 Dashboard 的某一列 Sessions 上按 `Enter`，會跳到 **Inspector** 分頁、顯示那個 run 的步驟軌跡（移動高亮的那一列，Inspector 的內容也會跟著更新） |
| `r` | 立即刷新（不等自動 poll） |
| `p` | 暫停 / 恢復自動刷新（暫停時標題列顯示 `PAUSED`） |
| `q` | 離開 |

Inspector 裡顯示的 workflow 步驟 `summary` 是一份**結構投影**，而且 server 端早就先幫你去敏感過了。它只保留 skill 名稱、引數的**鍵名**，以及結果或例外的**型別名稱**；引數值、結果值、原始例外訊息則**一律不收**。也因為這樣，就算你連的是一台對外曝光的 server，Inspector 也不會把 secret 或 PII 漏出來。

## 三種認證模式

`--auth-mode` 必須跟 server 端的 `auth_mode` 對得起來。token 永遠是從**環境變數**讀進來的，不會經由命令列旗標傳入：

| `--auth-mode` | Header | Token 環境變數 |
| --- | --- | --- |
| `none`（預設） | （無） | — |
| `bearer` | `Authorization: Bearer <token>` | `CANTUS_SERVE_BEARER_TOKEN` |
| `api-key` | `X-API-Key: <token>` | `CANTUS_SERVE_API_KEY` |

舉個例子，連到一台以 bearer 模式保護的 server：

```bash
export CANTUS_SERVE_BEARER_TOKEN="<your-token>"
cantus tui --url https://<slug>.trycloudflare.com --auth-mode bearer
```

> ⚠️ **token 就是憑證。** 請把 `CANTUS_SERVE_BEARER_TOKEN` 與 `CANTUS_SERVE_API_KEY` 當成密碼一樣看待：別讓它們出現在原始碼、log、截圖或版本控制裡，一旦外洩就要立刻輪替。`cantus tui` 在內部會把 token 遮罩掉，所以任何一個分頁都不會印出它們的明文值。

## 與 serve 的關係

`cantus tui` 自己不會起任何 server，它純粹只是 `/introspection` 的 render 端。所以你得先在另一個 shell 把 `cantus serve` 跑起來（做法見 [`docs/quickstart-desktop.md`](./quickstart-desktop.md)），再把這個工具指過去連它。如果 server 是用 `auth_mode=none` 啟用 introspection 的，它會在啟動時印一則警告，提醒你 `/introspection` 目前不需要認證就能存取——等到要對外曝光時，記得改成 `bearer` 或 `api-key`。
