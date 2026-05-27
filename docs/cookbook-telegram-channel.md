# Cookbook：用 cantus 接 Telegram Bot API（echo bot）

這份 walkthrough 帶你從零把一個 Telegram bot 接到 `cantus serve`。流程與 [`cookbook-line-channel.md`](./cookbook-line-channel.md) 對稱，只是 Telegram 不用 HMAC，改用 `setWebhook` 時設定的 `secret_token` 做 header 等值比對。

## 0. 你會用到的東西

- 一個 Telegram 帳號（用 App 登入）。
- 已安裝 `cantus-agent[serve]>=0.4.5` 與 `cloudflared`。

## 1. 跟 `@BotFather` 申請 bot

1. 在 Telegram 搜尋 `@BotFather`，按 **Start**。
2. 傳 `/newbot`，依照提示給 bot 一個 display name 與一個唯一的 `@username`（必須以 `bot` 結尾）。
3. `@BotFather` 會回你一個 **bot token**（長得像 `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ_aBC123-Def`）── 這是 `CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN`，**絕對不要**外流。
4. 額外推薦：對 `@BotFather` 跑 `/setprivacy` → **Disable** 讓 bot 在 group 也能收到所有訊息（不是只有 `/command`）；如果只跑 1-on-1 echo 可以略過。

## 2. 自己想一個 secret_token

Telegram 的 webhook 驗證不是 HMAC，而是 `setWebhook` 時你**自己**指定的一個靜態字串。Telegram 之後每個 POST 都會在 `X-Telegram-Bot-Api-Secret-Token` header 帶這個字串；cantus 收到後 `hmac.compare_digest` 一比就知道是不是真的來自 Telegram。

```bash
export CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN="<bot token from BotFather>"
export CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN="$(openssl rand -hex 32)"
```

`openssl rand -hex 32` 給你 64 字 hex string；Telegram 限制 secret_token 必須是 `A-Z a-z 0-9 _ -` 且 1–256 字，hex string 完全合法。

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

另開 shell：

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

得到 `https://<slug>.trycloudflare.com`。

## 6. 把 webhook URL 註冊給 Telegram

Telegram 沒有 web console，直接打 Bot API：

```bash
BOT_TOKEN="$CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN"
SECRET_TOKEN="$CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN"
WEBHOOK_URL="https://<slug>.trycloudflare.com/channels/telegram"

curl -i -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"${WEBHOOK_URL}\",\"secret_token\":\"${SECRET_TOKEN}\"}"
```

預期回 `{"ok":true,"result":true,"description":"Webhook was set"}`。

如果跑兩次想換 URL 但忘了 `setWebhook` 的覆蓋語意，可以先 `deleteWebhook`：

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

在 Telegram App 對 bot `@<your_bot_username>` 發訊息，幾秒內就會收到 `echo: <你打的字>`。

## 8. curl 自我測試

```bash
curl -i -X POST http://127.0.0.1:8765/channels/telegram \
  -H "X-Telegram-Bot-Api-Secret-Token: $CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"update_id":1,"message":{"chat":{"id":123},"text":"hi"}}'
```

預期 `HTTP/1.1 200 OK` 與 `{"ok":true}`。換錯 secret token 會收到 `HTTP/1.1 401 Unauthorized` 與 `{"detail":"Authentication required"}`。

## 9. 常見坑

- **`setWebhook` 回 `"SSL error"`**：Telegram 強制 webhook 要 HTTPS。Cloudflare Tunnel 預設就是 HTTPS，所以這通常意味你不小心填了 `http://...`。
- **bot 完全沒反應**：先用 `https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo` 看 `last_error_date` / `last_error_message`，最常見是 `Wrong response from the webhook: 401 Unauthorized` ── 代表 `secret_token` 對不上。
- **訊息只進來一次就停了**：worker loop 拋 exception 沒被 `try/except` 包住，整個 loop 掛掉；把處理邏輯包進 `try / except Exception` 並 log 出來。
- **`ChannelSendError: telegram send failed: HTTP 403 ...bot was blocked by the user`**：使用者把 bot block 了。把 chat_id 從你的活躍清單移除即可，這不是 bug。

## 下一步

- 把 worker 包進 cantus Workflow，餵 LLM 自動回。
- 接 LINE：[`docs/cookbook-line-channel.md`](./cookbook-line-channel.md)。
