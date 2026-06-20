# Cookbook: connect cantus to the LINE Messaging API (echo bot)

This walkthrough takes you from zero to a LINE official account wired into `cantus serve`, running an echo bot: a student sends a message, the bot sends one back. Every command assumes you have already worked through the "Serve via CLI" and "Expose via Cloudflare Tunnel" sections of [`docs/quickstart-desktop.md`](./quickstart-desktop.md).

## 0. What you'll need

- A [LINE Developers Console](https://developers.line.biz/console/) account (sign in with the LINE app).
- `cantus-agent[serve]>=0.4.5` and `cloudflared` installed.
- A laptop. The OS doesn't matter.

## 1. Create a Messaging API channel in the LINE Developers Console

1. Open the LINE Developers Console and create a new Provider (or reuse one you already have).
2. Under that Provider, choose **Create a new channel** and pick **Messaging API**.
3. Fill in the basics (channel name, icon, category) and submit. You'll land on the channel's detail page.
4. Open the **Messaging API** tab and note two tokens:
   - **Channel secret** (on the **Basic settings** tab) — this becomes `CANTUS_SERVE_CHANNEL_LINE_SECRET`.
   - **Channel access token (long-lived)** — issue one near the bottom of the **Messaging API** tab. This becomes `CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN`.

Both tokens are plain strings. Do **not** paste them into chat messages, commits, or issues.

## 2. Write `myskills/app.py`

Keep the channel object and the registry as module-level variables. The cantus CLI resolves the `--channels` argument by dotted path, so they have to be importable:

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

## 3. Put the secrets in your shell (do **not** write them into source)

```bash
export CANTUS_SERVE_CHANNEL_LINE_SECRET="<channel secret from step 1>"
export CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN="<channel access token from step 1>"
```

If you prefer a `.env` file, add it to `.gitignore`. cantus itself does **not** read `.env` automatically, so you'll need `direnv` or a manual `source`.

## 4. Start cantus serve

```bash
cantus serve \
  --host 127.0.0.1 \
  --port 8765 \
  --registry-import myskills.app:registry \
  --channels myskills.app:line_channel
```

After the CLI parses your arguments, it pushes `line_channel` onto `app.state.channels`. `serve()` then calls `mount(app)` on it, which registers the `POST /channels/line` route. The FastAPI lifespan opens an app-scoped `httpx.AsyncClient` for outbound replies. `Ctrl-C` shuts everything down cleanly.

## 5. Expose a public URL with Cloudflare Tunnel

Open a second shell:

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

`cloudflared` prints a temporary URL like `https://<slug>.trycloudflare.com`. Copy it. Your public webhook entry point is `https://<slug>.trycloudflare.com/channels/line`.

## 6. Set the webhook URL back in the LINE Developers Console

On the channel's **Messaging API** tab:

1. Paste `https://<slug>.trycloudflare.com/channels/line` into **Webhook URL**.
2. Click **Update**, then **Verify**. LINE sends an empty verification event.
   - When cantus sees a correct `X-Line-Signature` it returns 200; when the header is missing or doesn't match it returns 401 with `{"detail": "Authentication required"}`. A passing Verify means your secret is correct.
3. Toggle **Use webhook** to ON.
4. Further down the same page, turn off **Auto-reply messages** and **Greeting messages**. Otherwise LINE replies on your bot's behalf and overrides your echo logic.
5. Add the channel as a friend from your phone (the QR code is near the bottom of the **Messaging API** tab).

## 7. Run the echo loop

cantus pushes each incoming webhook payload onto `line_channel`'s internal queue. One payload can carry several events, so `receive()` hands you the whole envelope and your loop walks the `events` array. You supply the worker loop that drains the queue. Here's a minimal version:

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

Run it in a third shell:

```bash
python scripts/worker.py
```

Message the bot from the LINE app on your phone and within a few seconds you'll see `echo: <whatever you typed>` come back.

## 8. Self-test with curl (no phone needed)

To confirm the `cantus serve` side works without depending on LINE, poke the webhook directly with `curl`:

```bash
SECRET="$CANTUS_SERVE_CHANNEL_LINE_SECRET"
BODY='{"events":[{"type":"message","replyToken":"fake-token","message":{"type":"text","text":"hi"}}],"destination":"U-test"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -binary | base64)

curl -i -X POST http://127.0.0.1:8765/channels/line \
  -H "X-Line-Signature: $SIG" \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

You should get `HTTP/1.1 200 OK` with the body `{"ok":true}`. Corrupt `SIG` and you'll get `HTTP/1.1 401 Unauthorized` with `{"detail":"Authentication required"}` instead.

## 9. Common pitfalls

- **Verify fails in the LINE Console**: 90% of the time `CANTUS_SERVE_CHANNEL_LINE_SECRET` doesn't match the channel secret. The other 10% is a Cloudflare Tunnel that hasn't come up yet.
- **The bot is friended but doesn't respond**: first check that the worker loop is running, then check that Auto-reply and Greeting are both off in the LINE Console.
- **`ChannelSendError: line send failed: HTTP 400 Invalid reply token`**: a reply token is valid for only about 30 seconds. If your loop sleeps too long it expires. Reply as soon as the event arrives.
- **You committed a token by accident**: go to the LINE Developers Console and **Issue a new channel access token** right away, which revokes the old one. A channel secret can't be reissued on its own; you have to rebuild the whole channel.

## Next steps

- Wrap the worker loop in an Agent or Workflow so the LLM decides how to reply.
- Connect a Telegram bot: see [`docs/cookbook-telegram-channel.md`](./cookbook-telegram-channel.md).
