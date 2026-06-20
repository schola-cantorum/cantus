# Cookbook：把 Telegram bot 接上 cantus（echo bot）

這份教學帶你從零開始，把一個 Telegram bot 串進 `cantus serve`。整體流程跟 [LINE cookbook](./line.md) 幾乎一樣，只有一個差別：Telegram 不用 HMAC 簽章。它改用你在 `setWebhook` 時自己挑的 `secret_token`，把這個字串原封不動回傳給你，cantus 再拿來逐字比對 header。

## 0. 你會用到的東西

- 一個 Telegram 帳號（用 App 登入即可）。
- 已經裝好 `cantus-agent[serve]>=0.4.5` 與 `cloudflared`。

## 1. 跟 `@BotFather` 申請一個 bot

1. 在 Telegram 搜尋 `@BotFather`，按 **Start**。
2. 傳 `/newbot`，照著提示給 bot 一個 display name，再給它一個唯一的 `@username`（結尾一定要是 `bot`）。
3. `@BotFather` 會回你一個 **bot token**（長得像 `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ_aBC123-Def`）。這就是你的 `CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN`，千萬別外流。
4. 可做可不做、但很方便的一步：對 `@BotFather` 跑 `/setprivacy`，選 **Disable**，這樣 bot 在群組裡就能收到每一則訊息，而不是只收 `/command`。如果你只打算跑一對一的 echo，這步可以跳過。

## 2. 自己想一個 secret_token

這個字串是你在 `setWebhook` 時自己挑的。從此之後，Telegram 每次送來的 POST 都會把它放在 `X-Telegram-Bot-Api-Secret-Token` header 裡，cantus 在接受請求前會用一次 `hmac.compare_digest` 把這個 header 比對掉。

```bash
export CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN="<bot token from BotFather>"
export CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN="$(openssl rand -hex 32)"
```

`openssl rand -hex 32` 會給你一串 64 個字元的 hex string。Telegram 規定 secret_token 要落在 1–256 個字元、只能用 `A-Z a-z 0-9 _ -` 這些字元，所以 hex string 完全合法。

## 3. 寫 `myskills/app.py`

```python
# myskills/app.py
from cantus.core.registry import Registry
from cantus.protocols.skill import register_skill
from cantus.serve import TelegramWebhookChannel

registry = Registry()

@register_skill
def echo(text: str) -> str:
    """Echo back whatever the user said."""
    return text

registry.register("skill", echo)

# Secrets come from env vars (CANTUS_SERVE_CHANNEL_TELEGRAM_*).
telegram_channel = TelegramWebhookChannel()
```

## 4. 啟動 cantus serve

```bash
cantus serve \
  --host 127.0.0.1 \
  --port 8765 \
  --registry-import myskills.app:registry \
  --channels myskills.app:telegram_channel
```

## 5. Cloudflare Tunnel

另開一個 shell：

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

你會拿到一個 `https://<slug>.trycloudflare.com` 的 URL。

## 6. 把 webhook URL 註冊給 Telegram

Telegram 沒有 web console，所以直接打 Bot API：

```bash
BOT_TOKEN="$CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN"
SECRET_TOKEN="$CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN"
WEBHOOK_URL="https://<slug>.trycloudflare.com/channels/telegram"

curl -i -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"${WEBHOOK_URL}\",\"secret_token\":\"${SECRET_TOKEN}\"}"
```

正常的話會回 `{"ok":true,"result":true,"description":"Webhook was set"}`。

如果你跑了兩次想換 URL，卻忘了 `setWebhook` 會直接蓋掉上一次的設定，可以先用 `deleteWebhook` 清掉：

```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"
```

## 7. 跑 worker loop

```python
# scripts/worker.py
import asyncio
from myskills.app import telegram_channel

async def main():
    while True:
        try:
            update = telegram_channel.receive()
        except IndexError:
            await asyncio.sleep(0.1)
            continue
        message = update.get("message")
        if not message or "text" not in message:
            continue
        chat_id = message["chat"]["id"]
        user_text = message["text"]
        await telegram_channel.send(
            {"chat_id": chat_id, "text": f"echo: {user_text}"}
        )

if __name__ == "__main__":
    asyncio.run(main())
```

```bash
python scripts/worker.py
```

打開 Telegram App，對 `@<your_bot_username>` 發一則訊息，幾秒內你就會收到 `echo: <你剛剛打的字>`。

## 8. 用 curl 自我測試

```bash
curl -i -X POST http://127.0.0.1:8765/channels/telegram \
  -H "X-Telegram-Bot-Api-Secret-Token: $CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"update_id":1,"message":{"chat":{"id":123},"text":"hi"}}'
```

正常會看到 `HTTP/1.1 200 OK` 加上 `{"ok":true}`。如果你故意帶錯的 secret token，就會拿到 `HTTP/1.1 401 Unauthorized` 與 `{"detail":"Authentication required"}`。

## 9. 常見地雷

- **`setWebhook` 回 `"SSL error"`**：Telegram 規定 webhook 一定要走 HTTPS。Cloudflare Tunnel 預設就是 HTTPS，所以這通常代表你不小心把 URL 填成了 `http://...`。
- **bot 完全沒反應**：去 `https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo` 看一下 `last_error_date` / `last_error_message`。最常見的是 `Wrong response from the webhook: 401 Unauthorized`，意思就是 `secret_token` 對不上。
- **訊息只進來一次就不動了**：你的 worker loop 拋了一個沒被 `try/except` 接住的例外，把整個 loop 拖垮了。把處理邏輯包進 `try / except Exception`，並把錯誤 log 出來。
- **`ChannelSendError: telegram send failed: HTTP 403 ...bot was blocked by the user`**：使用者把 bot 封鎖了。把這個 chat_id 從你的活躍清單裡拿掉就好，這不是 bug。

## 下一步

- 把 worker 包進一個 cantus Workflow，讓 LLM 來產生回覆。
- 接 LINE：[LINE cookbook](./line.md)。
