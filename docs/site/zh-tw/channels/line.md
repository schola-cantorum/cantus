# Cookbook：把 cantus 接上 LINE Messaging API（echo bot）

這份教學帶你從零開始，把一個 LINE 官方帳號接到 `cantus serve`，跑出一個 echo bot：學生丟一句話進來，bot 就原封不動回一句。每一道指令都假設你已經做完 [`docs/quickstart-desktop.md`](../quickstart-desktop.md) 裡的「Serve via CLI」與「Expose via Cloudflare Tunnel」兩節，所以這裡不會再重講那兩段。

## 0. 你會用到的東西

- 一個 [LINE Developers Console](https://developers.line.biz/console/) 帳號（直接用 LINE App 登入就行）。
- 裝好 `cantus-agent[serve]>=0.4.5` 和 `cloudflared`。
- 一台筆電。是 macOS、Windows 還是 Linux 都沒差。

## 1. 在 LINE Developers Console 開一個 Messaging API channel

1. 打開 LINE Developers Console，建一個新的 Provider（如果你手邊已經有一個，拿來重用也可以）。
2. 在這個 Provider 底下選 **Create a new channel**，channel 類型挑 **Messaging API**。
3. 把基本欄位填一填（channel name、icon、category）後送出，畫面會帶你到這個 channel 的詳細頁。
4. 切到 **Messaging API** 分頁，把兩個 token 記下來：
   - **Channel secret**（在 **Basic settings** 分頁）── 它對應到 `CANTUS_SERVE_CHANNEL_LINE_SECRET`。
   - **Channel access token (long-lived)** ── 在 **Messaging API** 分頁靠近底部的地方按 issue 發一個出來，它對應到 `CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN`。

這兩個 token 都只是普通字串。**千萬不要**把它們貼進聊天訊息、commit 或 issue 裡。

## 2. 寫 `myskills/app.py`

把 channel 物件和 registry 都放在 module 最外層當變數。cantus CLI 的 `--channels` 參數是靠 dotted path 去 import 的，所以這兩個東西一定要能被 import 到：

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

## 3. 把 secrets 放進 shell（**不要**寫死在程式碼裡）

```bash
export CANTUS_SERVE_CHANNEL_LINE_SECRET="<channel secret from step 1>"
export CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN="<channel access token from step 1>"
```

如果你比較習慣用 `.env` 檔，記得把它加進 `.gitignore`。cantus 本身**不會**自動去讀 `.env`，所以你得搭配 `direnv`，或是自己手動 `source` 一下。

## 4. 啟動 cantus serve

```bash
cantus serve \
  --host 127.0.0.1 \
  --port 8765 \
  --registry-import myskills.app:registry \
  --channels myskills.app:line_channel
```

CLI 解析完你的參數後，會把 `line_channel` 推進 `app.state.channels`。接著 `serve()` 會對它呼叫 `mount(app)`，註冊出 `POST /channels/line` 這條路由。FastAPI 的 lifespan 會開一個 app 等級的 `httpx.AsyncClient`，專門用來送回覆。按 `Ctrl-C` 就會把整套乾淨關掉。

## 5. 用 Cloudflare Tunnel 開一個對外網址

另外開一個 shell：

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

`cloudflared` 會印出一個像 `https://<slug>.trycloudflare.com` 的臨時網址，把它複製起來。你對外的 webhook 入口就是 `https://<slug>.trycloudflare.com/channels/line`。

## 6. 回 LINE Developers Console 設定 webhook URL

回到這個 channel 的 **Messaging API** 分頁：

1. 把 `https://<slug>.trycloudflare.com/channels/line` 貼進 **Webhook URL**。
2. 按 **Update**，再按 **Verify**。LINE 會丟一個空的 verification event 過來。
   - cantus 看到正確的 `X-Line-Signature` 就回 200；header 不見了或對不上，就回 401，body 是 `{"detail": "Authentication required"}`。Verify 過得了，就代表你的 secret 設對了。
3. 把 **Use webhook** 切到 ON。
4. 在同一頁再往下捲，把 **Auto-reply messages** 和 **Greeting messages** 都關掉。不然 LINE 會搶在你前面替 bot 自動回，把你的 echo 邏輯整個蓋掉。
5. 用手機把這個 channel 加為好友（QR code 就在 **Messaging API** 分頁靠近底部的地方）。

## 7. 跑起 echo loop

每收到一筆 webhook，cantus 就會把整包 payload 推進 `line_channel` 的內部 queue。一筆 payload 裡可能裝了好幾個 event，所以 `receive()` 是把整個信封交給你，要由你的 loop 自己去走 `events` 這個陣列。把 queue 抽乾的 worker loop 得你自己寫，下面是一個最精簡的版本：

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

開第三個 shell 把它跑起來：

```bash
python scripts/worker.py
```

接著用手機上的 LINE App 對這個 bot 說句話，幾秒之內你就會看到 `echo: <你剛剛打的字>` 跳回來。

## 8. 用 curl 自我測試（不用手機也行）

想確認 `cantus serve` 這一側本身沒問題、又不想牽扯到 LINE 那邊，可以用 `curl` 直接戳 webhook：

```bash
SECRET="$CANTUS_SERVE_CHANNEL_LINE_SECRET"
BODY='{"events":[{"type":"message","replyToken":"fake-token","message":{"type":"text","text":"hi"}}],"destination":"U-test"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -binary | base64)

curl -i -X POST http://127.0.0.1:8765/channels/line \
  -H "X-Line-Signature: $SIG" \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

你應該會拿到 `HTTP/1.1 200 OK`，body 是 `{"ok":true}`。試著把 `SIG` 改壞，這次回的就是 `HTTP/1.1 401 Unauthorized`，body 是 `{"detail":"Authentication required"}`。

## 9. 常見的坑

- **在 LINE Console 按 Verify 失敗**：十次有九次是 `CANTUS_SERVE_CHANNEL_LINE_SECRET` 跟 channel secret 對不起來，剩下那一成是 Cloudflare Tunnel 還沒起來。
- **bot 加了好友卻不回話**：先確認 worker loop 真的有在跑，再回去確認 LINE Console 裡的 Auto-reply 和 Greeting 兩個都關掉了。
- **`ChannelSendError: line send failed: HTTP 400 Invalid reply token`**：reply token 大概只有 30 秒效期，你的 loop 要是睡太久它就過期了。Event 一進來就要趕快回。
- **不小心把 token commit 出去了**：馬上回 LINE Developers Console 按 **Issue a new channel access token**，這個動作會把舊的作廢。Channel secret 沒辦法單獨重發，真的外洩就只能把整個 channel 重建一次。

## 下一步

- 把 worker loop 包進一個 Agent 或 Workflow，改讓 LLM 來決定要怎麼回。
- 接一個 Telegram bot：看 [`docs/cookbook-telegram-channel.md`](./telegram.md)。
