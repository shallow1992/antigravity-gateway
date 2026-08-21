# antigravity-gateway 🚀

**Google Antigravity (AGY)** を Slack から安全・快適に遠隔操作（Remote Control）するための公式ライクなゲートウェイシステムです。

自宅やオフィスのローカルPC（Mac/Linux）上で Docker コンテナとして常駐し、外出先やスマホの Slack からコード検索・ファイル編集・テスト実行・プラン作成などを自由自在に行えます。

---

## 🌟 主な特徴

- 🎮 **Claude Code 同等の Remote Control**: スマホの Slack からローカル PC 上のコードを直接編集・テスト実行・Git 操作。
- 💎 **Google Pro サブスクリプション完全対応**: 従量課金や厳しいレート制限のある API キーを廃止し、**Google Pro アカウントの権限で追加料金ゼロ・使い放題**。
- 🖥️ **Web 管理ダッシュボード (`http://localhost:8080`)**: ブラウザから **1 クリックで Google Pro 認証** を完了。ターミナルでの面倒な認証作業は不要。
- 🏛️ **Antigravity 全公式スラッシュコマンド網羅**: `/goal`, `/grill-me`, `/btw`, `/browser`, `/teamwork`, `/learn`, `/guide`, `/customs`, `/reset`, `/status`, `/help` に完全対応。
- 💡 **`/btw`（脇道質問）サポート**: メインの会話履歴を一切汚さずに、ちょっとした疑問を単発で確認。
- 🛡️ **堅牢な 5層防御セキュリティ**:
  - Slack ユーザー ID ホワイトリストによる厳格なアクセス制御
  - トークン・APIキーの自動マスキング (`[REDACTED_SECRET]`)
  - 機密ファイル (`.env`, `*.key`, `id_rsa`, `jetski-standalone-oauth-token`) へのアクセス完全遮断
  - **Docker 堅牢化**: 非root (`1000:1000`)、特権剥奪 (`cap_drop: ALL`)、ルートファイルシステム読取専用 (`read_only: true`)
  - **独立 Named Volume 隔離**: ホスト PC の `~/.gemini` には一切触れず、コンテナ専用ボリューム（`gemini_auth`）内で認証を隔離保持
  - **リソース上限管理**: メモリ上限 2GB / CPU 2コア設定により、ホスト PC の巻き添えクラッシュを物理的に防止
- 🔌 **ゼロコンフィグ接続 (Socket Mode)**: ポート開放や固定 IP、ドメイン設定が一切不要。
- 🎛️ **デュアルセッションモード**: スレッドごとに会話を分ける `thread` モードと、チャンネル直下で快適に対話する `channel` モードを自由に選択可能。
- 🤖 **Bot 自動参加**: パブリックチャンネルへの招待（`/invite`）の手間を完全自動化。

---

## 🛠️ セットアップ手順（6ステップ）

```mermaid
flowchart LR
    S1["1. Slack App 作成<br/>(マニフェスト登録)"] --> S2["2. Google Cloud で<br/>OAuth ID 発行"]
    S2 --> S3["3. .env 設定"]
    S3 --> S4["4. Docker 起動"]
    S4 --> S5["5. Web 画面で<br/>1-Click ログイン"]
    S5 --> S6["6. Slack から<br/>話しかけて完了！"]
```

---

### Step 1: Slack App の作成（マニフェスト登録）

1. ブラウザで **[Slack API: Your Apps](https://api.slack.com/apps)** を開きます。
2. **「Create New App」** をクリックします。
3. **「From an app manifest」** を選択し、インストール対象のワークスペースを選択して **「Next」** をクリックします。
4. **「JSON」** タブを選択し、以下の JSON をそのまま貼り付けて **「Next」** → **「Create」** をクリックします。

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

### Step 2: Slack トークンを 2つ 取得

1. **App-Level Token (`xapp-...`) の発行**:
   * 左メニュー **「Basic Information」** > **「App-Level Tokens」** で **「Generate Token and Scopes」** をクリック。
   * Token Name に `gateway-socket-token` と入力し、**「Add Scope」** で `connections:write` を追加して **「Generate」** をクリック。
   * 発行されたトークン（`xapp-...`）をコピーします。

2. **Bot Token (`xoxb-...`) の取得 & インストール**:
   * 左メニュー **「Install App」** を開き、**「Install to Workspace」** をクリックしてワークスペースに許可します。
   * 発行された **「Bot User OAuth Token」**（`xoxb-...`）をコピーします。

---

### Step 3: Google Cloud で OAuth クライアント ID を発行

Google Pro アカウントで Web 認証を行うための無料クライアント ID を作成します。

1. **[Google Cloud Console (認証情報画面)](https://console.cloud.google.com/apis/credentials)** を開きます。
2. 画面上部の **「+ 認証情報を作成」** ➔ **「OAuth クライアント ID」** をクリックします。
3. 以下の通り入力します：
   * **アプリケーションの種類**: **`ウェブ アプリケーション`**
   * **名前**: `Antigravity Gateway`（任意）
   * **承認済みのリダイレクト URI**: **「+ URI を追加」** を押し、以下を入力：
     ```text
     http://localhost:8080/auth/callback
     ```
4. **「作成」** をクリックし、表示された **「クライアント ID」** と **「クライアント シークレット」** をコピーします。

---

### Step 4: `.env` ファイルの設定

リポジトリ直下の [`.env`](.env) を開き、取得したトークンを設定します：

```bash
cp .env.example .env
```

```ini
# 1. Slack 認証情報 (Step 2 で取得)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-level-token

# 2. Google Pro OAuth 連携設定 (Step 3 で取得)
GOOGLE_OAUTH_CLIENT_ID=xxxxxxxxxxxx-xxxxxxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx

# 3. セキュリティ設定 (ご自身の Slack ユーザー ID、または全員許可 "*")
ALLOWED_USER_IDS=*
ALLOWED_CHANNEL_IDS=

# 4. 操作対象のリポジトリの絶対パス
TARGET_WORKSPACE_PATH=/Users/HirotakaAsako/Workspace/dev_angr

# 5. Remote Control 権限
ALLOW_FILE_READ=true
ALLOW_FILE_WRITE=true
ALLOW_RUN_COMMAND=true
```

---

### Step 5: Docker コンテナの起動

```bash
docker compose up -d --build
```

---

### Step 6: Web 管理ダッシュボードで 1-Click ログイン

1. ブラウザで **`http://localhost:8080`** を開きます。
2. **「Google アカウントでログイン (Pro 連携)」** ボタンをクリックします。
3. Google の画面で Pro アカウントを選択し、「許可」をクリックします。
4. 画面が **「🟢 Google Pro 連携中」** に切り替わればセットアップ完了です！

---

## 💬 使い方 & コマンドリファレンス

Slack の任意のチャンネル（または Bot の DM）でメンションまたはスラッシュコマンドで対話します。

### 1. 通常の対話（コード調査・質問）
```text
@Antigravity src/main.py の Graceful Shutdown の実装を説明して
```

### 2. 脇道質問（`/btw` - メイン会話履歴を汚さない）
メインタスクのコンテキストを維持したまま、単発の質問を行えます。
```text
/agy btw このリポジトリで使っている Python のバージョンは何？
```

### 3. 公式スラッシュコマンド体系一覧

| コマンド | 説明・活用例 |
| :--- | :--- |
| **`/agy <指示>`** | 通常のプロンプト送信 |
| **`/agy goal <目標>`** | **自律ゴール達成モード**: テストが通過するまで自律的に調査・修正・検証ループを実行 |
| **`/agy grill-me <テーマ>`** | **設計インタビューモード**: 実装前のプランや設計について逆質問・深掘り壁打ち |
| **`/agy btw <質問>`** | **会話履歴非汚染質問**: メインの対話履歴を汚さずに単発で質問・確認 |
| **`/agy browser <指示>`** | **ブラウザ調査モード**: Web サイトの調査・ドキュメント取得 |
| **`/agy teamwork <タスク>`** | **マルチエージェント協調**: 複数サブエージェントを立ち上げて並行分担 |
| **`/agy learn`** | **ルール学習**: 直近の成功や修正内容から再利用可能なルール・教訓を抽出 |
| **`/agy guide`** | **公式ガイド**: Antigravity の全体マニュアル・クイックリファレンス |
| **`/agy customs`** | **カスタマイズガイド**: スキル・ルール・MCP・設定ファイルの仕様表示 |
| **`/agy status`** | **稼働状況**: ワークスペース、Git ブランチ、実行権限カードの表示 |
| **`/agy reset` / `/agy clear`** | **セッション初期化**: 現在のスレッド/チャンネルの対話履歴をリセット |
| **`/agy help`** | **コマンドヘルプ**: 全コマンド一覧と説明の表示 |

---

## 🔒 セキュリティアーキテクチャ

本ゲートウェイは、ローカル PC の安全を確保するため **多層防御（5-Layer Defense）** を標準装備しています：

```text
[Slack] ➔ ① ユーザーホワイトリスト (ALLOWED_USER_IDS)
          ➔ ② コマンド・パストラバーサル検査 (Path.is_relative_to)
          ➔ ③ 認証トークン・シークレット完全マスキング ([REDACTED_...])
          ➔ ④ 独立 Docker Volume 隔離 (ホスト PC の ~/.gemini には一切触れない)
          ➔ ⑤ Docker 堅牢化 (非root, 特権剥奪 ALL, read_only, メモリ2GB / 2CPU上限)
```

---

## 📜 ライセンス

MIT License
