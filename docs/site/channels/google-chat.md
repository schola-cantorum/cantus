# Cookbook: Connect cantus to Google Chat (over Cloud Pub/Sub, no public HTTPS)

This walkthrough takes a Google Chat app from zero to a working echo bot on `cantus serve`: a member says something in a space, and the bot replies. Google Chat asks for more GCP setup than LINE, Telegram, or Discord, but it drops the requirement those three share: because cantus pulls from Cloud Pub/Sub, your laptop never needs a public HTTPS endpoint, so there is no Cloudflare Tunnel to run. A service account with Pub/Sub Subscriber access is enough.

> Design tradeoff: Google Chat also offers an HTTPS webhook mode with RS256 JWT signing, but cantus does not support that path. RS256 plus JWKS public-key rotation would pull `pyjwt` and `cryptography` into `cantus[serve]`, and it would still need a public endpoint. Pub/Sub pull authenticates with an IAM service account, which fits the student scenario (a laptop behind NAT) cleanly.

## 0. What you'll need

- A [Google Cloud](https://console.cloud.google.com/) account (Google Workspace or a regular Gmail account both work).
- A [Google Chat space](https://chat.google.com/) you can administer, to use as the test target.
- `cantus-agent[serve]>=0.4.7` installed.
- A laptop on any OS. `google-cloud-pubsub` and its transitive dependency `grpcio` ship prebuilt wheels for Linux x86_64, macOS arm64 and x86_64, and Windows AMD64.
- **No** `cloudflared`, `ngrok`, or any tunnel.

## 1. Create a GCP project and enable APIs in the Google Cloud Console

1. Open the [Google Cloud Console](https://console.cloud.google.com/), then **Select a project** -> **New Project**. Give it a name, for example `cantus-chatbot`.
2. In that project, go to **APIs & Services** -> **Library** and enable these APIs:
   - **Google Chat API**
   - **Cloud Pub/Sub API**
   - **Google Workspace Events API**
3. Note the **Project ID** (the string-form ID, not the Project Number), for example `cantus-chatbot-2026`.

## 2. Create a service account and download its JSON key

1. Go to **IAM & Admin** -> **Service Accounts** -> **Create Service Account**. Give it a name, for example `cantus-chatbot-sa`.
2. Grant it the role:
   - **Pub/Sub Subscriber** (to read the Pub/Sub topic)
3. On the service account detail page, open the **Keys** tab -> **Add Key** -> **Create new key** -> **JSON** -> download.
4. Put the downloaded JSON file somewhere safe on your machine (**do not commit it to git**), for example `~/.cantus/sa.json`, and run `chmod 600 ~/.cantus/sa.json`.
5. In the [Google Chat admin / API console](https://developers.google.com/workspace/chat/configure-app), add this service account's email as the Chat app's service account.

## 3. Create a Pub/Sub topic and subscription

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud pubsub topics create cantus-chat-events
gcloud pubsub subscriptions create cantus-chat-sub --topic=cantus-chat-events
```

Two strings you'll use later:
- **Topic**: `projects/YOUR_PROJECT_ID/topics/cantus-chat-events`
- **Subscription**: `projects/YOUR_PROJECT_ID/subscriptions/cantus-chat-sub`

Let the Chat-events publisher (an internal Google service account) publish to your topic:

```bash
gcloud pubsub topics add-iam-policy-binding cantus-chat-events \
  --member='serviceAccount:chat-api-push@system.gserviceaccount.com' \
  --role='roles/pubsub.publisher'
```

## 4. Subscribe to Chat events through the Google Workspace Events API

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  https://workspaceevents.googleapis.com/v1/subscriptions \
  -d '{
    "target_resource": "//chat.googleapis.com/spaces/YOUR_SPACE_ID",
    "event_types": ["google.workspace.chat.message.v1.created"],
    "notification_endpoint": {
      "pubsub_topic": "projects/YOUR_PROJECT_ID/topics/cantus-chat-events"
    },
    "payload_options": {"include_resource": true}
  }'
```

`YOUR_SPACE_ID` comes from the URL of the Chat space you want the bot to listen to (for example the `AAAA...` part in `https://chat.google.com/room/AAAA...`).

## 5. Write `myskills/app.py`

```python
# myskills/app.py
from cantus.core.registry import Registry
from cantus.protocols.skill import register_skill
from cantus.serve import GoogleChatPubSubChannel

registry = Registry()

@register_skill
def echo(text: str) -> str:
    """Echo back whatever the user said."""
    return text

registry.register("skill", echo)

# All three values come from CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_* env vars.
# (The constructor accepts them directly too, but keep the SA path out of
# source code so different deployments don't get crossed.)
google_chat_channel = GoogleChatPubSubChannel()
```

## 6. Put the SA path and subscription details in your shell

```bash
export CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH=$HOME/.cantus/sa.json
export CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SUBSCRIPTION=projects/YOUR_PROJECT_ID/subscriptions/cantus-chat-sub
export CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SPACE=spaces/YOUR_SPACE_ID
```

> **Not secrets**: `CREDENTIALS_PATH` is just a file path, and `SUBSCRIPTION` and `SPACE` are public Google identifiers. **The real secret is the contents of the SA JSON file.** Keep that file out of git and protect read access with `chmod 600`.

## 7. Run `cantus serve`

```bash
cantus serve \
  --registry-import myskills.app:registry \
  --channels myskills.app:google_chat_channel
```

Expected log (cantus startup lines omitted above it):

```
INFO cantus.serve.channels GoogleChatPubSubChannel connected: projects/.../subscriptions/cantus-chat-sub
```

## 8. Manual smoke test: say something in the Chat space

Go to your Google Chat space and say `hello`. cantus should:

1. Pull a `google.workspace.chat.message.v1.created` event from Pub/Sub.
2. Put the event on an internal queue (your skill can `receive` it for processing).
3. Assuming the skill calls `channel.send({"data": {"text": "hello back"}})`, the bot replies `hello back` in the same space.

If no events arrive, check in order:
- `gcloud pubsub subscriptions pull cantus-chat-sub --auto-ack --limit=10` to see whether the topic actually has messages. If not, the Workspace Events API subscription may have failed.
- Whether the SA has `roles/pubsub.subscriber` on that subscription.
- Whether the `cantus serve` log shows backoff retries. After 10 consecutive failures it records `self.last_error` and stops reconnecting, but the rest of the server keeps running — the channel gives up without crashing the lifespan.

## 9. Shutdown

`Ctrl+C` stops `cantus serve`. The lifespan then:
1. Calls `channel.disconnect()` to cancel the Pub/Sub pull.
2. Closes the app-scoped `httpx.AsyncClient`. The order matters: outbound `send` must still work before `disconnect` runs.

Clean up the Pub/Sub resources (optional):

```bash
gcloud pubsub subscriptions delete cantus-chat-sub
gcloud pubsub topics delete cantus-chat-events
```

## Security notes

- **Never commit the SA JSON file.** Add patterns like `*sa.json` and `*service-account*.json` to `.gitignore`.
- For production, replace the static SA key with [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation) to avoid the risk of leaking long-lived keys.
- When `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH` is unset, cantus falls back to `GOOGLE_APPLICATION_CREDENTIALS` (Google's standard ADC variable). So if neither is set, the channel fails fast at construction time with a fixed error string that does not echo any input value.
- `cantus serve --auth-mode bearer` or `--auth-mode api-key` adds auth to the Skill HTTP endpoints. Channel inbound traffic goes over Pub/Sub pull, so there is no HTTP route to protect there.
