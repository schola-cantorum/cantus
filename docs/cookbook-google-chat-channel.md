# Cookbook：用 cantus 接 Google Chat（透過 Cloud Pub/Sub，無需公開 HTTPS）

這份 walkthrough 帶你從零把一個 Google Chat app 接到 `cantus serve`，跑通 echo bot（成員在 space 講話 → bot 回訊息）。Google Chat 比 LINE / Telegram / Discord 多了一點 GCP 設定，但**少了一件大事**：因為走 Cloud Pub/Sub pull，你的筆電**不需要對外 HTTPS 端點**（不用 Cloudflare Tunnel），只要 service account 有權限就行。

> 設計取捨：Google Chat 也有 HTTPS webhook 模式（RS256 JWT 簽章），但 cantus 不支援那條路徑。原因是 RS256 + JWKS 公鑰輪替會把 `pyjwt`、`cryptography` 拉進 `cantus[serve]`，且仍然需要公開端點。Pub/Sub pull 用 IAM service account 認證，學生情境（筆電 + NAT）剛好走得通。

## 0. 你會用到的東西

- 一個 [Google Cloud](https://console.cloud.google.com/) 帳號（用 Google Workspace 或一般 Gmail 都行）。
- 一個你能管理的 [Google Chat space](https://chat.google.com/) 作為測試目標。
- 已安裝 `cantus-agent[serve]>=0.4.7`。
- 一台筆電，OS 不重要 ── `google-cloud-pubsub` 與其遞移依賴 `grpcio` 在 Linux x86_64 / macOS arm64+x86_64 / Windows AMD64 都有 prebuilt wheel。
- **不需要** `cloudflared`、`ngrok` 或任何 tunnel。

## 1. 在 Google Cloud Console 開 GCP project + 啟用 API

1. 進 [Google Cloud Console](https://console.cloud.google.com/) → **Select a project** → **New Project**。取個名字（例如 `cantus-chatbot`）。
2. 進到該 project 的 **APIs & Services** → **Library**，啟用以下 API：
   - **Google Chat API**
   - **Cloud Pub/Sub API**
   - **Google Workspace Events API**
3. 抄下 **Project ID**（不是 Project Number，是字串形式的 ID，例如 `cantus-chatbot-2026`）。

## 2. 開 service account + 下載 SA JSON 金鑰

1. **IAM & Admin** → **Service Accounts** → **Create Service Account**。取個名字（例如 `cantus-chatbot-sa`）。
2. 給予角色：
   - **Pub/Sub Subscriber**（讀 Pub/Sub topic）
3. 在 service account 詳細頁 → **Keys** tab → **Add Key** → **Create new key** → **JSON** → 下載。
4. 把下載的 JSON 檔放到本機安全位置（**不要 commit 進 git**），例如 `~/.cantus/sa.json`，並 `chmod 600 ~/.cantus/sa.json`。
5. 在 [Google Chat admin / API console](https://developers.google.com/workspace/chat/configure-app) 把該 service account 的 email 加為 Chat app 的 service account。

## 3. 開 Pub/Sub topic + subscription

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud pubsub topics create cantus-chat-events
gcloud pubsub subscriptions create cantus-chat-sub --topic=cantus-chat-events
```

兩個關鍵字串會用到：
- **Topic**：`projects/YOUR_PROJECT_ID/topics/cantus-chat-events`
- **Subscription**：`projects/YOUR_PROJECT_ID/subscriptions/cantus-chat-sub`

讓 Chat-events publisher（Google 內部 service account）可以發布到你的 topic：

```bash
gcloud pubsub topics add-iam-policy-binding cantus-chat-events \
  --member='serviceAccount:chat-api-push@system.gserviceaccount.com' \
  --role='roles/pubsub.publisher'
```

## 4. 在 Google Workspace Events API 訂閱 Chat events

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

`YOUR_SPACE_ID` 來自你想要 bot 監聽的 Chat space URL（例如 `https://chat.google.com/room/AAAA...` 裡的 `AAAA...`）。

## 5. 寫 `myskills/app.py`

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

# 三個值都從 CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_* env vars 拿
# （建構子也可以直接吃參數，但別把 SA 路徑寫進原始碼以免不同部署混淆）。
google_chat_channel = GoogleChatPubSubChannel()
```

## 6. 把 SA 路徑與訂閱資訊放進 shell

```bash
export CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH=$HOME/.cantus/sa.json
export CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SUBSCRIPTION=projects/YOUR_PROJECT_ID/subscriptions/cantus-chat-sub
export CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SPACE=spaces/YOUR_SPACE_ID
```

> **不是 secret 的**：`CREDENTIALS_PATH` 只是檔案路徑，`SUBSCRIPTION` 與 `SPACE` 是 Google 公開識別子。**真正的 secret 是 SA JSON 檔案的內容** ── 那檔案不要 commit 進 git，且 `chmod 600` 保護讀取權限。

## 7. 跑 `cantus serve`

```bash
cantus serve \
  --registry-import myskills.app:registry \
  --channels myskills.app:google_chat_channel
```

預期 log（前面省略 cantus 啟動訊息）：

```
INFO cantus.serve.channels GoogleChatPubSubChannel connected: projects/.../subscriptions/cantus-chat-sub
```

## 8. 手動 smoke：在 Chat space 講一句話

到你的 Google Chat space 講 `hello`，cantus 應該：

1. 從 Pub/Sub pull 收到 `google.workspace.chat.message.v1.created` 事件。
2. 把事件放進內部 queue（你的 skill 可以 receive 出來處理）。
3. 假設 skill 呼叫 `channel.send({"data": {"text": "hello back"}})`，bot 會在同一 space 回覆 `hello back`。

如果沒看到事件進來，依序檢查：
- `gcloud pubsub subscriptions pull cantus-chat-sub --auto-ack --limit=10` 看 topic 是否真的有訊息 ── 沒有的話 Workspace Events API 訂閱可能失敗。
- SA 是否有 `roles/pubsub.subscriber` 在那條 subscription 上。
- `cantus serve` log 是否出現 backoff 重試 ── 連續 10 次失敗會把 `self.last_error` 記下並安靜停止重連（不會 crash lifespan）。

## 9. 關閉

`Ctrl+C` 停掉 `cantus serve`。lifespan 會：
1. 呼叫 `channel.disconnect()` cancel Pub/Sub pull。
2. 關閉 app-scoped `httpx.AsyncClient`（這順序很重要 ── 出站 send 要在 disconnect 之前還可用）。

清理 Pub/Sub 資源（可選）：

```bash
gcloud pubsub subscriptions delete cantus-chat-sub
gcloud pubsub topics delete cantus-chat-events
```

## 安全提醒

- **SA JSON 檔絕不要 commit**。`.gitignore` 加 `*sa.json` / `*service-account*.json` 之類的 pattern。
- 部署到正式環境時用 [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation) 取代靜態 SA key，能避免長期金鑰外洩風險。
- `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH` 沒設時，cantus 會回退到 `GOOGLE_APPLICATION_CREDENTIALS`（Google 官方 ADC 標準），所以兩個都不設就會在 channel 建構時直接 fail-fast，錯誤訊息固定字串、不 echo 任何輸入值。
- `cantus serve --auth-mode bearer` 或 `--auth-mode api-key` 對 Skill HTTP endpoint 加 auth；channel inbound 走 Pub/Sub pull，沒有 HTTP route 需要 protect。
