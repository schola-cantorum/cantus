# Cookbook: connecting Discord with cantus (echo bot + slash command)

This walkthrough takes you from an empty Discord application to a working `cantus serve` deployment that runs an echo bot (a member types in a server, the bot replies) plus a `/ping` slash command. Discord carries one extra layer of complexity compared with LINE or Telegram: cantus needs both a **Gateway WebSocket** (a long-lived connection that streams events in) and an **Interactions HTTP** endpoint (Ed25519-signature verification for slash-command and button callbacks). Every command below assumes you have already worked through the "Serve via CLI" and "Expose via Cloudflare Tunnel" sections of [`docs/quickstart-desktop.md`](./quickstart-desktop.md).

## 0. What you'll need

- A [Discord Developer Portal](https://discord.com/developers/applications) account (your regular Discord account can sign in).
- A Discord server where you have administrator rights (a fresh server for testing is fine).
- `cantus-agent[serve]>=0.5.0` and `cloudflared` installed.
- A laptop on any OS. Both `pynacl` and `websockets` ship prebuilt wheels for Linux x86_64, macOS arm64 + x86_64, and Windows AMD64.

## 1. Create an application in the Discord Developer Portal

1. Open the [Discord Developer Portal](https://discord.com/developers/applications), click **New Application**, and give it a name (for example `cantus-echo-bot`).
2. On the application's detail page, note three values:
   - **Application ID** (the **General Information** tab). This becomes `CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID`. It is a **public value** that appears in the OAuth invite URL, so it is not a secret.
   - **Public Key** (a little further down the same page). A 64-character hex string. This becomes `CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY`; cantus uses it to verify the Ed25519 signature that Discord attaches to requests sent to `/channels/discord/interactions`.
3. Switch to the **Bot** tab:
   - Click **Reset Token** to obtain the bot token (shown only once; it disappears on refresh). This becomes `CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN`. It is the **real secret** — leaking it lets someone else act as your bot.
   - Under **Privileged Gateway Intents**, enable **MESSAGE CONTENT INTENT**. Without it, the `content` field arrives empty on every `MESSAGE_CREATE` event cantus receives. `GUILDS` and `GUILD_MESSAGES` are non-privileged and enabled by default.
4. Switch to **OAuth2** → **URL Generator**:
   - Under **Scopes**, check `bot` and `applications.commands`.
   - Under **Bot Permissions**, check `Send Messages`, `Read Message History`, and `Use Slash Commands`.
   - Copy the generated URL, paste it into your browser, and use it to add the bot to your test server.

## 2. Write `myskills/app.py`

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

# All three secrets come from the CANTUS_SERVE_CHANNEL_DISCORD_* env vars.
# (The constructor also accepts them as arguments, but never put secrets in source.)
discord_channel = DiscordRealtimeChannel()
```

## 3. Put the secrets in your shell (**not** in source)

```bash
export CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN="<bot token from step 1>"
export CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY="<public key hex string from step 1>"
export CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID="<application id from step 1>"
```

cantus v0.5.0 still does **not** read `.env` automatically. Either use `direnv` or `source` your own script.

## 4. Start cantus serve

```bash
cantus serve \
  --host 127.0.0.1 \
  --port 8765 \
  --registry-import myskills.app:registry \
  --channels myskills.app:discord_channel
```

Once it starts, cantus prints the Discord Gateway connection progress (IDENTIFY → READY), and the bot flips from offline to online in your Discord client. The FastAPI lifespan wraps `discord_channel.connect()` in an `asyncio.create_task` that runs in the background; `Ctrl-C` triggers the lifespan shutdown, cantus calls `discord_channel.disconnect()` to close cleanly (close code 1000), and the bot goes back to offline.

## 5. Expose the interactions URL with Cloudflare Tunnel

Slash-command and button events are pushed to cantus by Discord over HTTP, so you also need a public URL:

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

Your public interactions entry point is `https://<slug>.trycloudflare.com/channels/discord/interactions`.

## 6. Set the Interactions Endpoint URL in the Developer Portal

On the application's **General Information** tab:

1. Paste `https://<slug>.trycloudflare.com/channels/discord/interactions` into **Interactions Endpoint URL**.
2. Click **Save Changes**. Discord immediately sends a type=1 Ping interaction to validate the URL:
   - With a correct `X-Signature-Ed25519` and `X-Signature-Timestamp`, cantus replies `{"type":1}` (PONG) and the URL passes.
   - On a signature mismatch, cantus returns `401 {"detail":"Authentication required"}` and the Discord Console shows "validation failed". Almost every validation failure here is a pasted public key that doesn't match the application's, not a cantus bug — re-copy the Public Key from **General Information** before you suspect anything else.

## 7. Register a slash command by hand (cantus does not register it for you)

cantus deliberately does **not** call `PUT /applications/{id}/commands` on your behalf (the same discipline as the "we don't register your webhook URL" note in the LINE and Telegram cookbooks: the secret always stays in your hands). Register a `/ping` command yourself with `curl`:

```bash
APP_ID="$CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID"
BOT="$CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN"

curl -X POST "https://discord.com/api/v10/applications/$APP_ID/commands" \
  -H "Authorization: Bot $BOT" \
  -H "Content-Type: application/json" \
  -d '{"name":"ping","description":"Reply with pong","type":1}'
```

A few seconds later, type `/` in your test server and you'll see `/ping`.

## 8. Run the echo + ping loop

The Discord events cantus receives are pushed onto an internal queue inside `discord_channel`. Write a worker loop:

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

        # Two inbound paths: (a) a MESSAGE_CREATE pushed in by the Gateway;
        # (b) a slash command pushed in over the interactions HTTP endpoint.
        # Tell them apart by dict shape.
        if "interaction" in event:
            # Slash-command callback. Reply with type=4 (CHANNEL_MESSAGE_WITH_SOURCE).
            cmd = event["interaction"].get("data", {}).get("name")
            if cmd == "ping":
                await discord_channel.send({
                    "interaction": event["interaction"],
                    "data": {"type": 4, "data": {"content": "pong"}},
                })
        elif event.get("t") == "MESSAGE_CREATE":
            # Gateway MESSAGE_CREATE. Echo it back (skip the bot's own
            # messages to avoid an infinite loop).
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

In a third shell, run:

```bash
python scripts/worker.py
```

Say anything in your Discord server and you'll see `echo: <what you typed>` come back. Type `/ping` and you'll see `pong`.

## 9. Common pitfalls

- **The `content` of a MESSAGE_CREATE event is an empty string**: you forgot to enable MESSAGE CONTENT INTENT on the **Bot** tab of the Developer Portal.
- **The Discord Console shows "validation failed"**: check the public key first — `CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY` is usually short a character or is actually the client secret. If the key is right, the Cloudflare Tunnel probably isn't up yet.
- **`ChannelSendError: discord send failed: HTTP 403 Missing Permissions`**: the bot lacks `Send Messages` in that channel. Re-invite via OAuth, or add the permission in the channel settings.
- **`ChannelSendError: discord send failed: HTTP 401 Unauthorized`**: the bot token is invalid (you reset it but didn't update the env var).
- **The bot keeps reconnecting**: check the `last_error` that cantus logs. Discord enforces a 1000/24h rate limit on IDENTIFY; after 10 consecutive failures cantus stops reconnecting **without** crashing, but the bot stays offline. Confirm the token is correct before restarting cantus.
- **You accidentally committed the token**: go to the **Bot** tab of the Developer Portal and **Reset Token** right away; the old one is invalidated immediately. The public key can't be reset on its own — you'd have to recreate the application.

## Next steps

- Fold the worker loop into your Agent or Workflow so the LLM decides what to reply.
- Add more slash commands: copy the `curl` from step 7 and change `name` / `description` / `options`.
- Add components (buttons, select menus): add a `components` array to the `data` payload you `send` back. Discord pushes the user's click back as a type=3 interaction, which travels the same path as a slash command.
- Deploy for real: replace the Cloudflare Tunnel with a named tunnel that has a fixed hostname, or front cantus with your own reverse proxy. Manage the bot token and public key with your platform's secrets manager.
