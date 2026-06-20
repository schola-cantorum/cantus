# Cookbook：把 cantus 接上 Google Chat（透過 Cloud Pub/Sub，不需要公開 HTTPS）

這份教學會帶你從零開始，把一個 Google Chat app 接到 `cantus serve`，做出一個能跑的 echo bot：space 裡的成員講一句話，bot 就回一句。Google Chat 要的 GCP 設定，確實比 LINE、Telegram、Discord 都多一些；但它也少掉那三個都需要的東西：因為 cantus 是用 pull 的方式去 Cloud Pub/Sub 拿資料，你的筆電完全不需要對外的 HTTPS 端點，所以也就不必額外跑一個 Cloudflare Tunnel。只要有一個帶 Pub/Sub Subscriber 權限的 service account 就夠了。

> 設計取捨：Google Chat 其實也有一條走 HTTPS webhook、用 RS256 JWT 簽章的模式，但 cantus 並不支援那條路。原因是 RS256 加上 JWKS 公鑰輪替，會把 `pyjwt` 和 `cryptography` 拉進 `cantus[serve]`，而且這樣還是得有一個公開端點。相對地，Pub/Sub pull 用 IAM service account 來認證，剛好能漂亮地對上學生的情境（一台躲在 NAT 後面的筆電）。

## 0. 你會用到的東西

- 一個 [Google Cloud](https://console.cloud.google.com/) 帳號（Google Workspace 或一般 Gmail 帳號都可以）。
- 一個你能管理的 [Google Chat space](https://chat.google.com/)，拿來當測試目標。
- 已安裝 `cantus-agent[serve]>=0.4.7`。
- 一台筆電，什麼作業系統都行。`google-cloud-pubsub` 和它連帶會裝進來的依賴 `grpcio`，在 Linux x86_64、macOS arm64 與 x86_64、Windows AMD64 上都有預先編好的 wheel。
- **不需要** `cloudflared`、`ngrok` 或任何 tunnel。

## 1. 在 Google Cloud Console 建立 GCP project 並啟用 API

1. 打開 [Google Cloud Console](https://console.cloud.google.com/)，按 **Select a project** -> **New Project**。取個名字，例如 `cantus-chatbot`。
2. 進到這個 project 的 **APIs & Services** -> **Library**，啟用下面這些 API：
   - **Google Chat API**
   - **Cloud Pub/Sub API**
   - **Google Workspace Events API**
3. 把 **Project ID** 記下來（要的是字串形式的 ID，不是 Project Number），例如 `cantus-chatbot-2026`。

## 2. 建立 service account 並下載它的 JSON 金鑰

1. 進 **IAM & Admin** -> **Service Accounts** -> **Create Service Account**。取個名字，例如 `cantus-chatbot-sa`。
2. 給它這個角色：
   - **Pub/Sub Subscriber**（用來讀取 Pub/Sub topic）
3. 在 service account 的詳細頁，打開 **Keys** 分頁 -> **Add Key** -> **Create new key** -> **JSON** -> 下載。
4. 把下載下來的 JSON 檔放到本機一個安全的位置（**不要 commit 進 git**），例如 `~/.cantus/sa.json`，然後執行 `chmod 600 ~/.cantus/sa.json`。
5. 到 [Google Chat admin / API console](https://developers.google.com/workspace/chat/configure-app)，把這個 service account 的 email 設成 Chat app 的 service account。

## 3. 建立 Pub/Sub topic 與 subscription

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud pubsub topics create cantus-chat-events
gcloud pubsub subscriptions create cantus-chat-sub --topic=cantus-chat-events
```

有兩個字串等一下會用到：
- **Topic**：`projects/YOUR_PROJECT_ID/topics/cantus-chat-events`
- **Subscription**：`projects/YOUR_PROJECT_ID/subscriptions/cantus-chat-sub`

接著放行 Chat-events 的發布者（一個 Google 內部的 service account），讓它能發布訊息到你的 topic：

```bash
gcloud pubsub topics add-iam-policy-binding cantus-chat-events \
  --member='serviceAccount:chat-api-push@system.gserviceaccount.com' \
  --role='roles/pubsub.publisher'
```

## 4. 透過 Google Workspace Events API 訂閱 Chat 事件

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

`YOUR_SPACE_ID` 來自你想讓 bot 監聽的那個 Chat space 的網址（例如 `https://chat.google.com/room/AAAA...` 裡的 `AAAA...` 這一段）。

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

# 這三個值都從 CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_* 這組環境變數讀進來。
# （建構子其實也能直接吃這些參數，但把 SA 路徑留在原始碼之外，
#  不同的部署環境才不會互相搞混。）
google_chat_channel = GoogleChatPubSubChannel()
```

## 6. 把 SA 路徑與訂閱資訊放進 shell

```bash
export CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH=$HOME/.cantus/sa.json
export CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SUBSCRIPTION=projects/YOUR_PROJECT_ID/subscriptions/cantus-chat-sub
export CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SPACE=spaces/YOUR_SPACE_ID
```

> **這些都不是 secret**：`CREDENTIALS_PATH` 只是一個檔案路徑，`SUBSCRIPTION` 和 `SPACE` 則是 Google 的公開識別字串。**真正的 secret，是那個 SA JSON 檔的內容。** 把那個檔案擋在 git 之外，並用 `chmod 600` 鎖住讀取權限。

## 7. 執行 `cantus serve`

```bash
cantus serve \
  --registry-import myskills.app:registry \
  --channels myskills.app:google_chat_channel
```

預期會看到的 log（上面 cantus 啟動的那幾行先省略）：

```
INFO cantus.serve.channels GoogleChatPubSubChannel connected: projects/.../subscriptions/cantus-chat-sub
```

## 8. 手動 smoke test：在 Chat space 裡講一句話

到你的 Google Chat space，打一句 `hello`。這時 cantus 應該會：

1. 從 Pub/Sub pull 出一個 `google.workspace.chat.message.v1.created` 事件。
2. 把這個事件放進內部的 queue（你的 skill 可以用 `receive` 把它拿出來處理）。
3. 假設 skill 呼叫了 `channel.send({"data": {"text": "hello back"}})`，bot 就會在同一個 space 裡回你 `hello back`。

如果遲遲沒有事件進來，照這個順序檢查：
- 執行 `gcloud pubsub subscriptions pull cantus-chat-sub --auto-ack --limit=10`，看看這條 subscription 裡到底有沒有訊息在排隊。如果是空的，多半是 Workspace Events API 的訂閱沒設成功。
- 確認那個 SA 在這條 subscription 上有 `roles/pubsub.subscriber`。
- 看看 `cantus serve` 的 log 有沒有出現 backoff 重試。連續失敗 10 次之後，它會把 `self.last_error` 記下來、停止重連，但伺服器其他部分還是照常運作——這個 channel 是安靜地放棄，不會把整個 lifespan 拖垮。

## 9. 關閉

按 `Ctrl+C` 停掉 `cantus serve`。接著 lifespan 會：
1. 呼叫 `channel.disconnect()`，取消 Pub/Sub pull。
2. 關掉 app 層級的 `httpx.AsyncClient`。這個順序很重要：出站的 `send` 必須在 `disconnect` 跑之前都還能用。

清理 Pub/Sub 資源（這步是選用的）：

```bash
gcloud pubsub subscriptions delete cantus-chat-sub
gcloud pubsub topics delete cantus-chat-events
```

## 安全注意事項

- **絕對不要把 SA JSON 檔 commit 進去。** 在 `.gitignore` 裡加上 `*sa.json`、`*service-account*.json` 這類 pattern。
- 上正式環境時，把靜態的 SA key 換成 [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)，這樣可以避開長期金鑰外洩的風險。
- 當 `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH` 沒設定時，cantus 會回退去找 `GOOGLE_APPLICATION_CREDENTIALS`（Google 標準的 ADC 變數）。所以如果兩個都沒設，這個 channel 會在建構的當下就直接 fail-fast，丟出一個固定的錯誤字串，而且不會把你輸入的任何值回傳出來。
- `cantus serve --auth-mode bearer` 或 `--auth-mode api-key` 會替 Skill 的 HTTP 端點加上認證。Channel 的 inbound 流量是走 Pub/Sub pull，所以那邊沒有 HTTP route 需要保護。
