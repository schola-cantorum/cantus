# Cookbook：用 cantus 接 LINE Messaging API（echo bot）

這份 walkthrough 帶你從零把一個 LINE 官方帳號接到 `cantus serve`，跑通 echo bot（學生發訊息→bot 回訊息）。所有指令都假設你已經跑過 [`docs/quickstart-desktop.md`](./quickstart-desktop.md) 的「Serve via CLI」與「Expose via Cloudflare Tunnel」兩段。

## 0. 你會用到的東西

- 一個 [LINE Developers Console](https://developers.line.biz/console/) 帳號（用 LINE App 登入即可）。
- 已安裝 `cantus-agent[serve]>=0.4.5` 與 `cloudflared`。
- 一台筆電，OS 不重要。

## 1. 在 LINE Developers Console 開一個 Messaging API channel

1. 進 LINE Developers Console，建一個新 Provider（沒有就建一個）。
2. 在這個 Provider 底下 **Create a new channel** → 選 **Messaging API**。
3. 填完基本資料（channel name、icon、category）後送出，進到該 channel 的詳細頁。
4. 切到 **Messaging API** tab，記下兩個 token：
   - **Channel secret**（在 **Basic settings** tab）── 這是 `CANTUS_SERVE_CHANNEL_LINE_SECRET`。
   - **Channel access token (long-lived)** ── 在 **Messaging API** tab 下方 **Issue** 一個，這是 `CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN`。

兩個 token 都是純字串，**不要**貼到聊天訊息、commit、或 issue 裡。

## 2. 寫 `myskills/app.py`

把 channel 物件與 registry 都放在 module top-level 變數裡，cantus CLI 的 `--channels` 參數靠 dotted path 解析：

```python
# myskills/app.py
from cantus.core.registry import Registry
from cantus.protocols.skill import register_skill
from cantus.serve import LineWebhookChannel

registry = Registry()

@register_skill
def echo(text: str) -> str:
    """Echo back whatever the user said."""
    return text

registry.register("skill", echo)

# Channel secrets come from CANTUS_SERVE_CHANNEL_LINE_SECRET and
# CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN env vars (no constructor args).
line_channel = LineWebhookChannel()
```

## 3. 把 secrets 放進 shell（**不要**寫進 source）

```bash
export CANTUS_SERVE_CHANNEL_LINE_SECRET="<channel secret from step 1>"
export CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN="<channel access token from step 1>"
```

如果你習慣 `.env` 檔，記得把它加到 `.gitignore`；cantus 本身 v0.4.5 仍**不**自動讀 `.env`，需要 `direnv` 或自己 source。

## 4. 啟動 cantus serve

```bash
cantus serve \
  --host 127.0.0.1 \
  --port 8765 \
  --registry-import myskills.app:registry \
  --channels myskills.app:line_channel
```

CLI 解析後會把 `line_channel` 推到 `app.state.channels`、`serve()` 對它呼叫 `mount(app)` 註冊 `POST /channels/line`、FastAPI lifespan 起一個 app-scoped `httpx.AsyncClient`。`Ctrl-C` 乾淨關閉。

## 5. 用 Cloudflare Tunnel 暴露公網 URL

另開一個 shell：

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

`cloudflared` 會印出 `https://<slug>.trycloudflare.com` 這種臨時 URL；複製起來，你的 webhook 公網入口就是 `https://<slug>.trycloudflare.com/channels/line`。

## 6. 回 LINE Developers Console 設 webhook URL

在 channel 的 **Messaging API** tab：

1. **Webhook URL** 貼上 `https://<slug>.trycloudflare.com/channels/line`。
2. 點 **Update**，再點 **Verify** ── LINE 會發一個空的 verification event 給你。
   - cantus 看到正確的 `X-Line-Signature` 就回 200，看不到或對不上就回 401 `{"detail": "Authentication required"}`。Verify 通過代表 secret 對了。
3. **Use webhook** 撥到 ON。
4. 同一頁更下面，把 **Auto-reply messages** 與 **Greeting messages** 關掉（不然 LINE 會替你的 bot 自動回，蓋掉你的 echo 邏輯）。
5. 用手機加這個 channel 為好友（QR code 在 **Messaging API** tab 下方）。

## 7. 跑 echo loop

cantus 收進來的 LINE event 會 push 到 `line_channel` 的內部 queue。需要你寫一個 worker loop（最小範例）：

```python
# scripts/worker.py
import asyncio
from myskills.app import line_channel, registry

async def main():
    while True:
        try:
            event_envelope = line_channel.receive()
        except IndexError:
            await asyncio.sleep(0.1)
            continue
        for ev in event_envelope.get("events", []):
            if ev.get("type") != "message" or ev["message"].get("type") != "text":
                continue
            reply_token = ev["replyToken"]
            user_text = ev["message"]["text"]
            await line_channel.send(
                {
                    "replyToken": reply_token,
                    "messages": [{"type": "text", "text": f"echo: {user_text}"}],
                }
            )

if __name__ == "__main__":
    asyncio.run(main())
```

第三個 shell 跑：

```bash
python scripts/worker.py
```

用手機在 LINE App 對這個 bot 講話，幾秒內就會看到 `echo: <你打的字>` 回來。

## 8. curl 自我測試（不靠手機）

想驗證 `cantus serve` 那邊沒問題、不依賴 LINE 端，可以用 `curl` 直接戳 webhook：

```bash
SECRET="$CANTUS_SERVE_CHANNEL_LINE_SECRET"
BODY='{"events":[{"type":"message","replyToken":"fake-token","message":{"type":"text","text":"hi"}}],"destination":"U-test"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -binary | base64)

curl -i -X POST http://127.0.0.1:8765/channels/line \
  -H "X-Line-Signature: $SIG" \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

預期回 `HTTP/1.1 200 OK` 與 body `{"ok":true}`。把 `SIG` 改錯，回的是 `HTTP/1.1 401 Unauthorized` 與 `{"detail":"Authentication required"}`。

## 9. 常見坑

- **Verify 在 LINE Console 失敗**：90% 是 `CANTUS_SERVE_CHANNEL_LINE_SECRET` 與 channel secret 不一致；剩下 10% 是 Cloudflare Tunnel 還沒起來。
- **bot 已加好友但發訊息沒反應**：先確認 worker loop 有跑、再確認 LINE Console 的 Auto-reply / Greeting 都已關閉。
- **`ChannelSendError: line send failed: HTTP 400 Invalid reply token`**：reply token 只有約 30 秒效期，被你 sleep 卡太久就過期；echo bot 收到 event 後請立刻回。
- **token 不小心 commit 出去**：立刻去 LINE Developers Console **Issue a new channel access token**，舊的會 revoke；channel secret 不能單獨重新發，整個 channel 重建。

## 下一步

- 把 worker loop 包進你的 Agent / Workflow，讓 LLM 來決定怎麼回。
- 接 Telegram bot：見 [`docs/cookbook-telegram-channel.md`](./cookbook-telegram-channel.md)。
