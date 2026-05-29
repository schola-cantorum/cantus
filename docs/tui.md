# `cantus tui` — 終端機觀測儀表板

`cantus tui` 是一個**唯讀**的終端機儀表板（Textual TUI），連到一個正在執行的 `cantus serve` 實例的 `/introspection` 與 `/health` endpoint，把 server 當下的執行期狀態即時 render 出來。它只讀資料、不下任何指令，也不變更 server 的任何狀態，適合在教學或除錯時即時觀察 agent / skill / channel 的運行情況。

各 endpoint 的資料契約見 [`docs/protocols/serve.md`](./protocols/serve.md#introspection-endpoints)。

## 安裝與啟動

`cantus tui` 需要 `tui` extra（Textual 相依走 lazy import gate，未裝時 `cantus tui` 會提示 `pip install cantus-agent[tui]`）：

```bash
pip install cantus-agent[tui]
cantus tui --url http://127.0.0.1:8765
```

常用旗標：

| 旗標 | 預設值 | 用途 |
| --- | --- | --- |
| `--url` | `http://127.0.0.1:8765` | 目標 `cantus serve` 的 base URL（本機或經 tunnel 對外的 URL 皆可） |
| `--auth-mode` | `none` | 認證模式，三選一：`none` / `bearer` / `api-key`，須與 server 的 `auth_mode` 一致 |
| `--poll-interval` | `2.0` | 自動刷新間隔（秒） |

## 五個分頁

啟動後畫面是一個 `TabbedContent`，共五個分頁，按數字鍵 `1`–`5` 切換：

| 鍵 | 分頁 | 顯示內容 |
| --- | --- | --- |
| `1` | **Dashboard** | 主總覽：左側為 Sessions 清單（最近被 dispatch 的 run），右側上下堆疊 Queue（各 channel 的 queue 深度）與 Health（server 是否可達 + `cantus_version`） |
| `2` | **Skills** | 每個註冊 Skill 的 `name` / `description` / `args_schema`；目前有 run 正在使用的 skill 會被標記 |
| `3` | **Permissions** | 生效的認證設定：`auth_mode`、`dashboard_requires_auth` / `introspection_requires_auth` 兩個 flag、被 auth gate 的路徑清單。**永遠不顯示** token 值 |
| `4` | **Dataflow** | 由 registry + channels 推導的靜態元件拓樸（nodes + edges：serve、event stream、各 skill、各 channel） |
| `5` | **Inspector** | 單一 run 的 Action/Observation 步驟軌跡（從 Sessions 列鑽取，見下方） |

## 鍵位

| 鍵 | 動作 |
| --- | --- |
| `1`–`5` | 切換到對應分頁 |
| `Enter` | 在 Dashboard 的 Sessions 列上按 `Enter`，跳到 **Inspector** 分頁顯示該 run 的步驟軌跡（移動高亮列也會同步更新 Inspector 內容） |
| `r` | 立即刷新（不等自動 poll） |
| `p` | 暫停 / 恢復自動刷新（暫停時標題列顯示 `PAUSED`） |
| `q` | 離開 |

Inspector 顯示的 workflow 步驟 `summary` 是 server 端去敏感後的**結構投影**——只含 skill 名稱、引數**鍵名**、結果 / 例外**型別名稱**，**絕不含**引數值、結果值或原始例外訊息。因此即使連到對外曝光的 server，Inspector 也不會把 secret / PII 顯示出來。

## 三種認證模式

`--auth-mode` 必須與 server 端的 `auth_mode` 一致；token 一律從**環境變數**讀取，不經由命令列旗標傳入：

| `--auth-mode` | Header | Token 環境變數 |
| --- | --- | --- |
| `none`（預設） | （無） | — |
| `bearer` | `Authorization: Bearer <token>` | `CANTUS_SERVE_BEARER_TOKEN` |
| `api-key` | `X-API-Key: <token>` | `CANTUS_SERVE_API_KEY` |

範例：連到一個以 bearer 模式保護的 server：

```bash
export CANTUS_SERVE_BEARER_TOKEN="<your-token>"
cantus tui --url https://<slug>.trycloudflare.com --auth-mode bearer
```

> ⚠️ **token 是敏感值**：`CANTUS_SERVE_BEARER_TOKEN` 與 `CANTUS_SERVE_API_KEY` 都是高敏感憑證，請勿寫進原始碼、log、截圖或版本控制；session 之間請定期輪替。`cantus tui` 內部以遮罩方式處理 token，畫面上的任何分頁都不會顯示其明文值。

## 與 serve 的關係

`cantus tui` 不會自己起 server——它只是 `/introspection` 的 render 端。請先在另一個 shell 啟動 `cantus serve`（見 [`docs/quickstart-desktop.md`](./quickstart-desktop.md)），再用本工具連上去。若 server 以 `auth_mode=none` 啟用 introspection，server 會在啟動時印一則警告提醒 `/introspection` 目前無需認證即可存取——一旦對外曝光，請改用 `bearer` 或 `api-key`。
