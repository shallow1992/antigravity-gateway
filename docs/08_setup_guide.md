# 08. セットアップ＆運用手順書 (Slack App & Docker)

本ドキュメントは、`antigravity-gateway` をゼロからセットアップし、Docker 上で安全に起動・運用するための手順書です。

---

## 📋 前提条件
- **Docker Desktop** または **Docker Engine** がインストールされていること
- **Slack ワークスペース** の管理者権限またはアプリインストール権限があること
- **Python 3.11+** および **`uv`**（ローカル開発・テストを行う場合）

---

## 🛠️ Step 1: Slack App の作成とトークン取得

### 1.1 App の新規作成
1. ブラウザで [Slack API: Your Apps](https://api.slack.com/apps) を開きます。
2. **「Create New App」** をクリックします。
3. **「From an app manifest」** を選択し、インストール対象のワークスペースを選択して **「Next」** をクリックします。

### 1.2 マニフェストの貼り付け
**「JSON」** タブを選択し、以下の JSON をそのまま貼り付けて **「Next」** → **「Create」** をクリックします。
（※ 全公式コマンド `/agy` および自動参加 `channels:join` が設定されています）

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

### 1.3 App-Level Token (`xapp-...`) の生成
1. 左メニュー **「Basic Information」** を開きます。
2. **「App-Level Tokens」** セクションにある **「Generate Token and Scopes」** をクリックします。
3. Token Name に `gateway-socket-token` と入力します。
4. **「Add Scope」** をクリックし、`connections:write` を選択します。
5. **「Generate」** をクリックし、生成されたトークン（`xapp-...`）をコピーして控えます。

### 1.4 ワークスペースへのインストール & Bot Token (`xoxb-...`) の取得
1. 左メニュー **「Install App」** を開きます。
2. **「Install to Workspace」** をクリックし、権限リクエストを許可します。
3. 表示された **「Bot User OAuth Token」**（`xoxb-...`）をコピーして控えます。

---

## ⚙️ Step 2: 環境変数の設定 (`.env`)

リポジトリ直下に `.env` ファイルを作成し、取得したトークンと設定値を入力します。

```bash
cp .env.example .env
```

```ini
# Slack 認証情報
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_APP_TOKEN=xapp-1-xxxxxxxxxxx-xxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# セッションモード & 自動参加設定
SESSION_MODE=thread          # 'thread' (スレッドごと) または 'channel' (チャンネル直下)
AUTO_JOIN_CHANNELS=true      # パブリックチャンネルへの一括自動参加

# セキュリティ設定
ALLOWED_USER_IDS=U0123456789
ALLOWED_CHANNEL_IDS=C0123456789

# 操作対象リポジトリのパス
TARGET_WORKSPACE_PATH=/Users/username/Workspace/your-repo

# Remote Control 権限
ALLOW_FILE_READ=true
ALLOW_FILE_WRITE=true
ALLOW_RUN_COMMAND=true
```

---

## 🚀 Step 3: Docker での起動と確認

### 起動コマンド
```bash
docker compose up -d --build
```

### ログ確認
```bash
docker compose logs -f
```

---

## 💬 Step 4: Slack での使い方一覧

### 1. 公式スラッシュコマンド
* `/agy goal このテストをすべて通るように修正して`（自律ゴール達成）
* `/agy grill-me 認証基盤のリファクタリング設計`（設計壁打ちインタビュー）
* `/agy btw この関数の型定義は何？`（メイン履歴を汚さない単発質問）
* `/agy browser https://docs.example.com の内容を要約して`（Web調査）
* `/agy teamwork 全モジュールのリファクタリングを分担実行`（協調実行）
* `/agy learn`（直前の修正からルールを学習）
* `/agy status`（稼働状況・権限・リポジトリ表示）
* `/agy reset`（会話セッションの初期化）
* `/agy help`（ヘルプ表示）

### 2. チャット対話（スレッド / チャンネル）
* `@Antigravity 〇〇をして` と話しかけて対話開始。
* 2回目以降はメンション不要で会話を継続。
