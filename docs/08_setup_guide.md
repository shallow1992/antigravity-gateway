# 08. セットアップ＆運用手順書 (完全版)

本ドキュメントは、**Antigravity Gateway** をローカル環境（Docker）でセットアップし、Slack から Google Pro サブスクリプション権限で安全に遠隔操作を開始するための完全手順書です。

---

## 📋 全体フロー

```mermaid
flowchart LR
    S1["1. Slack App 作成<br/>(マニフェスト登録)"] --> S2["2. Slack トークン取得<br/>(xapp / xoxb)"]
    S2 --> S3["3. Google Cloud で<br/>OAuth ID 発行"]
    S3 --> S4["4. .env 設定"]
    S4 --> S5["5. Docker 起動"]
    S5 --> S6["6. Web 画面で<br/>1-Click ログイン"]
```

---

## Step 1: Slack App の作成 (Manifest 登録)

1. ブラウザで **[Slack API: Your Apps](https://api.slack.com/apps)** を開きます。
2. **「Create New App」** ➔ **「From an app manifest」** を選択します。
3. インストール先の Slack ワークスペースを選択して **「Next」** をクリックします。
4. **「JSON」** タブに以下のマニフェストを貼り付けて **「Next」** ➔ **「Create」** をクリックします。

```json
{
  "display_information": {
    "name": "Antigravity Gateway",
    "description": "Google Antigravity bridge for Slack"
  },
  "features": {
    "bot_user": {
      "display_name": "Antigravity",
      "always_online": true
    },
    "slash_commands": [
      {
        "command": "/agy",
        "description": "Execute Antigravity commands and workflows",
        "usage_hint": "[goal | schedule | browser | grill-me | teamwork | learn | btw | reset | status | help | <prompt>]",
        "should_escape": false
      },
      {
        "command": "/antigravity",
        "description": "Execute Antigravity commands and workflows",
        "usage_hint": "[goal | schedule | browser | grill-me | teamwork | learn | btw | reset | status | help | <prompt>]",
        "should_escape": false
      }
    ]
  },
  "oauth_config": {
    "scopes": {
      "bot": [
        "app_mentions:read",
        "chat:write",
        "channels:history",
        "channels:join",
        "channels:read",
        "commands",
        "groups:history",
        "im:history",
        "im:write",
        "reactions:read",
        "reactions:write"
      ]
    }
  },
  "settings": {
    "socket_mode_enabled": true,
    "event_subscriptions": {
      "bot_events": [
        "app_mention",
        "message.channels",
        "message.groups",
        "message.im"
      ]
    },
    "org_deploy_enabled": false
  }
}
```

---

## Step 2: Slack トークンの取得

1. **App-Level Token (`xapp-...`) の発行**:
   * 左メニュー **「Basic Information」** > **「App-Level Tokens」** で **「Generate Token and Scopes」** をクリック。
   * Token Name に `gateway-socket-token` と入力し、Scope に `connections:write` を追加して **「Generate」** をクリック。
   * 発行された `xapp-...` をコピーします。
2. **Bot Token (`xoxb-...`) の取得**:
   * 左メニュー **「Install App」** > **「Install to Workspace」** をクリックして許可します。
   * 発行された **「Bot User OAuth Token」**（`xoxb-...`）をコピーします。

---

## Step 3: Google Cloud で OAuth クライアント ID を発行

1. **[Google Cloud Console (認証情報画面)](https://console.cloud.google.com/apis/credentials)** を開きます。
2. **「+ 認証情報を作成」** ➔ **「OAuth クライアント ID」** をクリックします。
3. 以下の通り入力します：
   * **アプリケーションの種類**: `ウェブ アプリケーション`
   * **名前**: `Antigravity Gateway`
   * **承認済みのリダイレクト URI**: `http://localhost:8080/auth/callback` を追加
4. **「作成」** をクリックし、発行された **クライアント ID** と **クライアント シークレット** をコピーします。

---

## Step 4: `.env` ファイルの設定

```bash
cp .env.example .env
```

```ini
# Slack 認証情報
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_APP_TOKEN=xapp-1-xxxxxxxxxxxxxxxxxxxxxx

# Google Pro OAuth 連携設定
GOOGLE_OAUTH_CLIENT_ID=xxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxx

# セキュリティ (Slack ユーザーID / 全員許可は "*")
ALLOWED_USER_IDS=*
ALLOWED_CHANNEL_IDS=

# 操作対象ワークスペース
TARGET_WORKSPACE_PATH=/Users/HirotakaAsako/Workspace/dev_angr

# Remote Control 実行権限
ALLOW_FILE_READ=true
ALLOW_FILE_WRITE=true
ALLOW_RUN_COMMAND=true
```

---

## Step 5: Docker コンテナの起動

```bash
docker compose up -d --build
```

---

## Step 6: Web 管理画面で 1-Click Google Pro ログイン

1. ブラウザで **`http://localhost:8080`** を開きます。
2. **「Google アカウントでログイン (Pro 連携)」** ボタンをクリックします。
3. Google の画面で Pro アカウントを選択し、「許可」をクリックします。
4. **「🟢 Google Pro 連携中」** に切り替われば準備完了です！

---

## 💬 動作確認

Slack の任意のチャンネルで話しかけてみてください：
```text
@Antigravity 疎通確認です。現在のプロジェクトの概要を教えて
```
またはスラッシュコマンド：
```text
/agy status
```
