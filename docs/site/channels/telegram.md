# Cookbook: Connect a Telegram bot to cantus (echo bot)

This walkthrough takes you from zero to a Telegram bot wired into `cantus serve`. The flow mirrors the [LINE cookbook](./line.md), with one difference: Telegram does not sign requests with HMAC. Instead, it echoes back the `secret_token` you choose at `setWebhook` time, and cantus compares that header for equality.

## 0. What you'll need

- A Telegram account (signed in through the app).
- `cantus-agent[serve]>=0.4.5` and `cloudflared` installed.

## 1. Register a bot with `@BotFather`

1. Search for `@BotFather` in Telegram and tap **Start**.
2. Send `/newbot` and follow the prompts to give your bot a display name and a unique `@username` (it must end in `bot`).
3. `@BotFather` replies with a **bot token** (it looks like `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ_aBC123-Def`). This is your `CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN`. Never share it.
4. Optional but handy: run `/setprivacy` against `@BotFather` and choose **Disable** so the bot receives every message in a group, not only `/command` messages. You can skip this if you only run a one-on-one echo.

## 2. Make up your own secret_token

You pick this string yourself at `setWebhook` time. From then on, every POST Telegram sends carries it in the `X-Telegram-Bot-Api-Secret-Token` header, and cantus checks that header with a single `hmac.compare_digest` call before accepting the request.

```bash
export CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN="<bot token from BotFather>"
export CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN="$(openssl rand -hex 32)"
```

`openssl rand -hex 32` gives you a 64-character hex string. Telegram requires the secret_token to be 1–256 characters drawn from `A-Z a-z 0-9 _ -`, so a hex string is perfectly valid.

## 3. Write `myskills/app.py`

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

## 4. Start cantus serve

```bash
cantus serve \
  --host 127.0.0.1 \
  --port 8765 \
  --registry-import myskills.app:registry \
  --channels myskills.app:telegram_channel
```

## 5. Cloudflare Tunnel

In a second shell:

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

You'll get a `https://<slug>.trycloudflare.com` URL.

## 6. Register the webhook URL with Telegram

Telegram has no web console, so call the Bot API directly:

```bash
BOT_TOKEN="$CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN"
SECRET_TOKEN="$CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN"
WEBHOOK_URL="https://<slug>.trycloudflare.com/channels/telegram"

curl -i -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"${WEBHOOK_URL}\",\"secret_token\":\"${SECRET_TOKEN}\"}"
```

Expect `{"ok":true,"result":true,"description":"Webhook was set"}` in return.

If you run this twice to swap URLs but forget that `setWebhook` overwrites the previous one, you can clear it first with `deleteWebhook`:

```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"
```

## 7. Run the worker loop

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

Message your bot at `@<your_bot_username>` from the Telegram app, and within a few seconds you'll get `echo: <whatever you typed>` back.

## 8. Self-test with curl

```bash
curl -i -X POST http://127.0.0.1:8765/channels/telegram \
  -H "X-Telegram-Bot-Api-Secret-Token: $CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"update_id":1,"message":{"chat":{"id":123},"text":"hi"}}'
```

Expect `HTTP/1.1 200 OK` with `{"ok":true}`. Send the wrong secret token and you'll get `HTTP/1.1 401 Unauthorized` with `{"detail":"Authentication required"}`.

## 9. Common pitfalls

- **`setWebhook` returns `"SSL error"`**: Telegram requires HTTPS for webhooks. Cloudflare Tunnel is HTTPS by default, so this usually means you accidentally filled in `http://...`.
- **The bot doesn't respond at all**: check `https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo` for `last_error_date` / `last_error_message`. The most common one is `Wrong response from the webhook: 401 Unauthorized`, which means the `secret_token` doesn't match.
- **Messages come in once, then stop**: your worker loop raised an exception that wasn't caught by `try/except`, taking the whole loop down. Wrap the handler body in `try / except Exception` and log it.
- **`ChannelSendError: telegram send failed: HTTP 403 ...bot was blocked by the user`**: the user blocked the bot. Drop that chat_id from your active list; this is not a bug.

## Next steps

- Wrap the worker in a cantus Workflow and let an LLM generate the replies.
- Connect LINE: [LINE cookbook](./line.md).
