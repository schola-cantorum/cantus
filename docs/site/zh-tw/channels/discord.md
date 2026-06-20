# Cookbook：用 cantus 接 Discord（echo bot + slash command）

這份 walkthrough 帶你從零把一個 Discord application 接到 `cantus serve`，跑通 echo bot（成員在 server 講話 → bot 回訊息）跟一個 `/ping` slash command。Discord 比 LINE / Telegram 多一層複雜度：cantus 同時需要 **Gateway WebSocket**（持續連線收事件）和 **Interactions HTTP**（Ed25519 簽章驗證 slash command / 按鈕回呼）。所有指令都假設你已經跑過 [`docs/quickstart-desktop.md`](../quickstart-desktop.md) 的「Serve via CLI」與「Expose via Cloudflare Tunnel」兩段。

## 0. 你會用到的東西

- 一個 [Discord Developer Portal](https://discord.com/developers/applications) 帳號（你的一般 Discord 帳號就可以登入）。
- 你自己擁有管理員權限的 Discord 伺服器（測試用，新開一個也行）。
- 已安裝 `cantus-agent[serve]>=0.5.0` 與 `cloudflared`。
- 一台筆電，OS 不重要 — `pynacl` 與 `websockets` 在 Linux x86_64 / macOS arm64+x86_64 / Windows AMD64 都有 prebuilt wheel。

## 1. 在 Discord Developer Portal 開一個 application

1. 進 [Discord Developer Portal](https://discord.com/developers/applications)，**New Application** → 取個名字（例如 `cantus-echo-bot`）。
2. 進到 application 詳細頁，記下三個值：
   - **Application ID**（**General Information** tab）── 這是 `CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID`。它是**公開值**，會出現在 OAuth invite URL 裡，不算 secret。
   - **Public Key**（同一頁稍下） ── 64 字元的 hex 字串。這是 `CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY`；cantus 會用它驗證 Discord 送進 `/channels/discord/interactions` 的 Ed25519 簽章。
3. 切到 **Bot** tab：
   - 點 **Reset Token** 拿到 bot token（只會顯示一次，重整就消失） ── 這是 `CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN`。**真正的 secret，外洩等於別人可以用你的 bot 身分。**
   - 在 **Privileged Gateway Intents** 區開啟 **MESSAGE CONTENT INTENT**。沒開的話 cantus 收到的 `MESSAGE_CREATE` 事件 `content` 欄位會是空字串。`GUILDS` 與 `GUILD_MESSAGES` 是非 privileged，預設就開。
4. 切到 **OAuth2** → **URL Generator**：
   - **Scopes** 勾 `bot` 與 `applications.commands`。
   - **Bot Permissions** 勾 `Send Messages`、`Read Message History`、`Use Slash Commands`。
   - 複製下面生成的 URL，貼到瀏覽器執行，把 bot 加進你的測試伺服器。

## 2. 寫 `myskills/app.py`

```python
# myskills/app.py
from cantus.core.registry import Registry
from cantus.protocols.skill import register_skill
from cantus.serve import DiscordRealtimeChannel

registry = Registry()

@register_skill
def echo(text: str) -> str:
    """Echo back whatever the user said."""
    return text

registry.register("skill", echo)

# 三個 secret 都從 CANTUS_SERVE_CHANNEL_DISCORD_* env vars 拿
# （建構子也可以直接吃參數，但別把 secret 寫進原始碼）。
discord_channel = DiscordRealtimeChannel()
```

## 3. 把 secrets 放進 shell（**不要**寫進 source）

```bash
export CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN="<bot token from step 1>"
export CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY="<public key hex string from step 1>"
export CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID="<application id from step 1>"
```

cantus v0.5.0 仍**不**自動讀 `.env`。要嘛用 `direnv`、要嘛 `source` 自己的腳本。

## 4. 啟動 cantus serve

```bash
cantus serve \
  --host 127.0.0.1 \
  --port 8765 \
  --registry-import myskills.app:registry \
  --channels myskills.app:discord_channel
```

啟動後會看到 cantus 印 Discord Gateway 連線狀態（IDENTIFY → READY），bot 在 Discord client 上的「online/offline」會切到 online。FastAPI lifespan 把 `discord_channel.connect()` 包成 `asyncio.create_task` 在背景跑；`Ctrl-C` 觸發 lifespan shutdown，cantus 呼叫 `discord_channel.disconnect()` 乾淨斷線（close code 1000），bot 切回 offline。

## 5. 用 Cloudflare Tunnel 暴露 interactions 公網 URL

Slash command / 按鈕的事件是 Discord 用 HTTP push 給 cantus，所以也需要公網 URL：

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

你的 interactions 公網入口是 `https://<slug>.trycloudflare.com/channels/discord/interactions`。

## 6. 回 Discord Developer Portal 設 Interactions Endpoint URL

在 application **General Information** tab：

1. **Interactions Endpoint URL** 貼上 `https://<slug>.trycloudflare.com/channels/discord/interactions`。
2. 點 **Save Changes**。Discord 會立刻送一個 type=1 的 Ping interaction 來驗 URL：
   - cantus 看到正確的 `X-Signature-Ed25519` + `X-Signature-Timestamp` 就回 `{"type":1}`（PONG），URL 通過。
   - 簽章對不上就回 401 `{"detail":"Authentication required"}`，Discord Console 顯示「validation failed」。這裡幾乎每一次驗證失敗，都是貼進去的 public key 跟 application 的對不上，而**不是** cantus 的 bug ── 在懷疑其他原因之前，先回 **General Information** 重新複製一次 Public Key。

## 7. 手動註冊一個 slash command（cantus 不代註冊）

cantus 故意**不**幫你自動呼叫 `PUT /applications/{id}/commands`（同 LINE / Telegram cookbook「不代註冊 webhook URL」的紀律：secret 永遠在你手上）。用 `curl` 自己註冊一個 `/ping`：

```bash
APP_ID="$CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID"
BOT="$CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN"

curl -X POST "https://discord.com/api/v10/applications/$APP_ID/commands" \
  -H "Authorization: Bot $BOT" \
  -H "Content-Type: application/json" \
  -d '{"name":"ping","description":"Reply with pong","type":1}'
```

幾秒後在 Discord 你的測試伺服器輸入 `/`，會看到 `/ping`。

## 8. 跑 echo + ping loop

cantus 收進來的 Discord event 會 push 到 `discord_channel` 的內部 queue。寫一個 worker loop：

```python
# scripts/worker.py
import asyncio
from myskills.app import discord_channel, registry

async def main():
    while True:
        try:
            event = discord_channel.receive()
        except IndexError:
            await asyncio.sleep(0.1)
            continue

        # 兩條入口：(a) Gateway 推進來的 MESSAGE_CREATE；(b) interactions HTTP 推進來的 slash command。
        # 用 dict shape 區分。
        if "interaction" in event:
            # Slash command callback。回 type=4 (CHANNEL_MESSAGE_WITH_SOURCE)
            cmd = event["interaction"].get("data", {}).get("name")
            if cmd == "ping":
                await discord_channel.send({
                    "interaction": event["interaction"],
                    "data": {"type": 4, "data": {"content": "pong"}},
                })
        elif event.get("t") == "MESSAGE_CREATE":
            # Gateway MESSAGE_CREATE。echo 回去（避開自己的訊息免得無限迴圈）。
            msg = event["d"]
            if msg.get("author", {}).get("bot"):
                continue
            await discord_channel.send({
                "channel_id": msg["channel_id"],
                "data": {"content": f"echo: {msg['content']}"},
            })

if __name__ == "__main__":
    asyncio.run(main())
```

第三個 shell 跑：

```bash
python scripts/worker.py
```

在 Discord 伺服器隨便講話 → 看到 `echo: <你打的字>` 回來。打 `/ping` → 看到 `pong`。

## 9. 常見坑

- **MESSAGE_CREATE event 的 `content` 是空字串**：你忘了在 Developer Portal **Bot** tab 開 MESSAGE CONTENT INTENT。
- **Discord Console 顯示「validation failed」**：先檢查 public key ── `CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY` 通常是少了一個字元，或根本是貼到了 client secret。如果 key 沒問題，那大概是 Cloudflare Tunnel 還沒起來。
- **`ChannelSendError: discord send failed: HTTP 403 Missing Permissions`**：bot 在那個頻道沒有 `Send Messages` 權限，回去 OAuth 重新邀請或在頻道設定加權限。
- **`ChannelSendError: discord send failed: HTTP 401 Unauthorized`**：bot token 失效（你 reset 了卻沒更新 env var）。
- **bot 一直 reconnect**：看 cantus log 印的 `last_error`。Discord 對 IDENTIFY 有 1000/24h rate limit，連續 10 次失敗 cantus 會 stop reconnect 而**不**會 crash，但 bot 會掛在 offline。重啟 cantus 前先確認 token 正確。
- **token 不小心 commit 出去**：立刻去 Developer Portal **Bot** tab **Reset Token**，舊的會立即失效。public key 不能單獨 reset，application 重建。

## 下一步

- 把 worker loop 包進你的 Agent / Workflow，讓 LLM 決定要回什麼。
- 加更多 slash command：複製第 7 步的 curl、改 `name` / `description` / `options`。
- 加 component（按鈕、select menu）：你 `send` 回去的 `data` payload 加 `components` array；Discord 把使用者點擊事件用 type=3 interaction 推回，跟 slash command 走同一條路徑。
- 上線部署：把 Cloudflare Tunnel 換成有固定 hostname 的 named tunnel，或直接部到自己的 reverse proxy。bot token / public key 用平台的 secrets manager 管理。
