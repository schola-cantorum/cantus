# Cantus 桌面版快速上手（Windows / macOS / Linux）

從乾淨的 `pip` 環境到你第一個 `Agent.run(...)` 回覆，只要五分鐘，過程中會用上一個以 API key 驗證的 chat model。如果你是第一次接觸 cantus，又是在桌機或筆電上跑（也就是 Google Colab 以外的任何地方），這份就是建議的入門起點。

如果你是在 Colab 裡跑、想從 Google Drive 載入 4-bit Gemma，請改看 [`quickstart.md`](./quickstart.md)。

## 需求

- Python 3.10 以上
- 裝好 [`uv`](https://docs.astral.sh/uv/)：macOS 上用 `brew install uv`，多數系統用 `pipx install uv`，或是走[官方安裝程式](https://docs.astral.sh/uv/getting-started/installation/)
- 一把來自 Chat Completions 供應商的 API key。這份教學用 OpenAI；Anthropic、Google、Groq 都是同一套用法，透過 `load_chat_model("<provider>/<model>")` 就行。

## 五分鐘走一遍

### 1. 安裝 cantus

```bash
uv pip install cantus-agent
```

`cantus-agent` 為 Linux、macOS、Windows 都發了 wheel。預設安裝只會拉進一個 runtime 相依套件（`pydantic`），不會拉 `bitsandbytes`——那個套件被 `sys_platform == 'linux'` 這個條件擋住，因為它的 4-bit 量化 kernel 是針對 CUDA 寫的，在 Linux + CUDA 以外的環境根本跑不動。

### 2. 提供 API key

```bash
# macOS / Linux
export OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."

# Windows cmd
set OPENAI_API_KEY=sk-...
```

### 3. 定義一個 skill

```python
from cantus import skill, Agent, load_chat_model

@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b
```

### 4. 載入 chat model

```python
model = load_chat_model("openai/gpt-4o-mini")
agent = Agent(model=model)
```

`load_chat_model("openai/gpt-4o-mini")` 會從環境變數讀取 `OPENAI_API_KEY`，再走 OpenAI Chat Completions API。同一個 factory 也吃 `"anthropic/claude-..."`、`"google/gemini-..."`、`"groq/..."`，前提是你裝好對應的 extras（`uv pip install "cantus-agent[anthropic,google,groq]"`）。

### 5. 跑這個 agent

```python
state = agent.run("What is 17 plus 25?")
final = state.stream[-1]
print(getattr(final, "answer", final))
```

你應該會看到 agent 呼叫 `add` 這個 skill，然後印出 `42`。

## 用 CLI 啟動服務

只要你的 `Registry` 在某個 module 裡以頂層名稱（top-level binding）曝露出來，就能直接從 shell 啟動 FastAPI 伺服器——不必自己寫 `import uvicorn`：

```bash
pip install cantus-agent[serve]
cantus serve --host 0.0.0.0 --port 8765 --registry-import myskills.app:registry
```

這個 CLI 接受幾種覆寫參數：`--host`、`--port`、`--auth-mode {none,bearer,api-key}`、`--dashboard` / `--no-dashboard`，以及一個或多個 `--channels DOTTED_PATH`。沒設定的旗標會往下退到 `CANTUS_SERVE_*` 環境變數，最後再退到 `Settings` 預設值；按 `Ctrl-C` 就能讓 uvicorn 優雅關機。

## 透過 Cloudflare Tunnel 對外曝露

只要 `cantus serve` 跑在 `127.0.0.1` 上，一行 `cloudflared` 指令就能給你一個公開的 HTTPS URL，可以直接拿去掛 webhook（LINE、Discord、Telegram、Google Chat），完全不用開任何對內的防火牆 port。先從 [Cloudflare 官方下載頁](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)裝好 `cloudflared`，然後另開一個 shell：

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

`cloudflared` 會印出一個隨機指派的 `https://<slug>.trycloudflare.com` URL。按 `Ctrl-C` 就能把 tunnel 收掉——那個 URL 會立刻失效、解析不到。

**安全提醒：** 這種 quick-tunnel 模式沒有任何驗證，任何人只要拿到 URL，就能直接打你的 FastAPI app。把它搭配 `cantus serve --auth-mode bearer` 一起用，這樣呼叫方就得帶上 token 才行，而且記得每次 session 之間都把 token 換掉。唯讀的 `/introspection` 端點也是同一回事：它們預設就開著，從 tunnel 一樣打得到——`cantus serve --auth-mode bearer` 會跟 `/skills` 一起把它們保護起來（若是 `auth_mode=none`，伺服器啟動時會印出一行警告，提醒你 `/introspection` 正開著沒擋）。quick-tunnel 模式不會把任何 token 寫到硬碟上；之後如果你升級成 named tunnel，產生出來的 `cert.pem` 千萬不要 commit 進版控（它是你整個 tunnel namespace 的長期憑證）。

## 用 `cantus tui` 觀測

`cantus tui` 是一個唯讀的終端機儀表板，掛在某台執行中伺服器的 `/introspection` 與 `/health` 端點之上。裝好 `tui` 這個 extra，再把它指向同一台伺服器（本機或走 tunnel 的都行）：

```bash
pip install cantus-agent[tui]
cantus tui --url http://127.0.0.1:8765
```

它會開出五個分頁——**Dashboard**、**Skills**、**Permissions**、**Dataflow**、**Inspector**——用按鍵 `1`–`5` 切換；在 Sessions 清單的某一列上按 `Enter`，就能跳到那次執行的 step trace（在 Inspector 裡看）。`--auth-mode` 要跟伺服器對上：用 `--auth-mode bearer` 時，它會從環境變數讀 `CANTUS_SERVE_BEARER_TOKEN`；用 `--auth-mode api-key` 時則讀 `CANTUS_SERVE_API_KEY`——兩者都當成機密看待，絕對別記進 log，也別分享出去。workflow 的 step trace 只會顯示去敏化後的摘要（skill 名稱、參數的 key 名稱，以及結果／例外的型別名稱，永遠不會是它們的值），所以就算對方是走 tunnel 的伺服器，觀測起來也很安全。完整的 pane 說明請見 [`docs/tui.md`](./tui.md)。

## 透過 Ollama 跑本機 LLM

`load_chat_model("ollama/...")` 會接上本機的 [Ollama](https://ollama.com/download) daemon，在 macOS、Linux、Windows 上都能跑，不需要 CUDA 也不需要 `bitsandbytes`。那條 Linux 限定的 4-bit Gemma 路徑（`LocalEnvironment.prepare_model`）在支援的環境下還是可以用，但 Ollama 才是我們建議的跨平台本機 LLM 選項。

從 [https://ollama.com/download](https://ollama.com/download) 裝好 daemon 之後，先 pull 一個模型：

```bash
ollama pull gemma3:4b
```

接著在 Python 裡用它，就跟其他任何供應商一模一樣：

```python
from cantus import Agent, Message, load_chat_model

chat = load_chat_model("ollama/gemma3:4b")
response = chat.chat([Message(role="user", content="hi")])
print(response.message.content)
```

能不能用 tool-use 要看模型本身：`OllamaChatModel.supports_tool_use` 是 `True`（從 `OpenAIChatModel` 繼承而來），但某個特定的 Ollama 模型究竟支不支援 OpenAI 風格的 function calling，得看那個模型怎麼訓練的。正式依賴它之前，先寫一個小小的 `@skill` 驗證一下。

## 透過 MLX 跑本機 LLM（Apple Silicon）

`load_chat_model("mlx/...")` 會透過 Apple 的 [`mlx-lm`](https://github.com/ml-explore/mlx-lm)——M 系列晶片的原生推論框架——**在 process 內（in-process）**直接跑模型：不需要另外的 daemon 或伺服器，載入更快，在 Mac 上的記憶體用量也比 Ollama 採用的 llama.cpp 後端更省。和 Ollama 那條路徑不同，`MLXChatModel` 並非 OpenAI 相容；它用 `mlx_lm.load` 載入權重，再用 `mlx_lm.generate` / `mlx_lm.stream_generate` 生成。

> **只限 Apple Silicon：** 這個供應商只支援 Apple Silicon（macOS arm64）。在其他平台上，`mlx` 這個 extras 群組會解析成空的，import 這個 adapter 時就會丟出 `ImportError`，明白告訴你 MLX 需要 Apple Silicon。安裝方式：

```bash
pip install cantus[mlx]
```

接著把 `load_chat_model` 指向任何一個 Hugging Face / MLX 的 model id（這得你自己提供；cantus 不會幫你下載權重）：

```python
from cantus import Message, load_chat_model

chat = load_chat_model("mlx/mlx-community/Mistral-7B-Instruct-v0.3-4bit")
response = chat.chat([Message(role="user", content="hi")])
print(response.message.content)
```

> **這個版本不支援 tool use：** `MLXChatModel.supports_tool_use` 是 `False`。mlx-lm 沒有原生的結構化 tool-call 輸出，所以你一旦把非空的 `tools` 參數傳給 `chat()` / `stream()`，它會直接丟出 `NotImplementedError`，而不是悄悄忽略掉。需要 function calling 時，請改走 Ollama 路徑，或乾脆用雲端供應商。

## 透過 omlx 跑本機 LLM（MLX 伺服器）

`load_chat_model("omlx/...")` 會跟一台**本機、OpenAI 相容的 MLX 伺服器**對話，這台伺服器在 Apple Silicon 上以獨立 process 執行——可以是 [`omlx`](https://omlx.ai)（預設 `http://localhost:8000/v1`），也可以是 [`mlx-omni-server`](https://github.com/madroidmaq/mlx-omni-server)（預設 `http://localhost:10240/v1`）。和上面那條 in-process 的 MLX 路徑不同，`OmlxChatModel` 只是 `OpenAIChatModel` 的一層薄薄子類別，所以它直接跑在 openai SDK 上，**不需要任何新的相依套件**——裝（或沿用）openai 的 extras 就好：

```bash
pip install cantus[openai]
```

啟動你選的那台伺服器，再把 `load_chat_model` 指向它的 `/v1` 端點。**`base_url` 是必填的**——omlx 和 mlx-omni-server 監聽的 port 不一樣，沒有哪個單一預設值說得通，所以你得明講是哪一台：

```python
from cantus import Message, load_chat_model

# omlx defaults to :8000/v1; pass http://localhost:10240/v1 for mlx-omni-server
chat = load_chat_model("omlx/qwen2.5-coder-7b", base_url="http://localhost:8000/v1")
response = chat.chat([Message(role="user", content="hi")])
print(response.message.content)
```

> **這裡 function calling 是能用的：** 和 in-process 的 MLX 路徑不同，`OmlxChatModel.supports_tool_use` 是 `True`。這些伺服器有實作 OpenAI 風格的 function calling，所以你可以把 `tools=` 參數傳給 `chat()` / `stream()`。萬一伺服器沒在跑，`chat()` / `stream()` 會丟出一個點名 `base_url` 的 `ConnectionError`，不會甩你一大串原始的 httpx stack trace。

## 接下來往哪走

- [`quickstart.md`](./quickstart.md) — Colab 優先的快速上手，透過 Google Drive 快取載入 4-bit Gemma。
- [`cookbook/`](./cookbook/) — 一系列可直接跑的食譜，涵蓋 workflows、多供應商路由、retrieval，以及 `cantus.serve` 的 FastAPI app。
- `cantus-agent[serve]` — 把你的 agent 包進一個 FastAPI HTTP 端點背後（`from cantus import serve`）。
- [`docs/llm_wiki/research/cloudflare_tunnel_vs_ngrok.md`](./llm_wiki/research/cloudflare_tunnel_vs_ngrok.md) — 為什麼這份教學選了 `cloudflared` 而不是 `ngrok`（免費隨機子網域、不會留下 auth token、`Ctrl-C` 收得乾淨俐落）。
