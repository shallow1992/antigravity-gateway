# antigravity-gateway 🚀

**Google Antigravity (AGY)** を Slack から安全・快適に遠隔操作（Remote Control）するための公式ライクなゲートウェイシステムです。

自宅やオフィスのローカルPC（Mac/Linux）上で Docker コンテナとして常駐し、外出先やスマホの Slack からコード検索・ファイル編集・テスト実行・プラン作成などを自由自在に行えます。

---

## 🌟 主な特徴

- 🎮 **Claude Code 同等の Remote Control**: スマホの Slack からローカル PC 上のコードを直接編集・テスト実行・Git 操作。
- 🏛️ **Antigravity 全公式スラッシュコマンド網羅**: `/goal`, `/grill-me`, `/btw`, `/browser`, `/teamwork`, `/learn`, `/guide`, `/customs`, `/reset`, `/status`, `/help` に完全対応。
- 💡 **`/btw`（脇道質問）サポート**: メインの会話履歴を一切汚さずに、ちょっとした疑問を単発で確認。
- 🛡️ **堅牢な 5層防御セキュリティ**:
  - Slack ユーザー ID ホワイトリストによる厳格なアクセス制御
  - トークン・APIキーの自動マスキング (`[REDACTED_SECRET]`)
  - 機密ファイル (`.env`, `*.key`, `id_rsa`) へのアクセス遮断
  - **Docker 堅牢化**: 非root (`1000:1000`)、特権剥奪 (`cap_drop: ALL`)、ルートファイルシステム読取専用 (`read_only: true`)
  - **リソース上限管理**: メモリ上限 2GB / CPU 2コア設定により、ホスト PC の巻き添えクラッシュを物理的に防止
- 🔌 **ゼロコンフィグ接続 (Socket Mode)**: ポート開放や固定 IP、ドメイン設定が一切不要。
- 🎛️ **デュアルセッションモード**: スレッドごとに会話を分ける `thread` モードと、チャンネル直下で快適に対話する `channel` モードを自由に選択可能。
- 🤖 **Bot 自動参加**: パブリックチャンネルへの招待（`/invite`）の手間を完全自動化。

---

## 🛠️ セットアップ手順（5ステップ）

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

### Step 2: 2つのトークンを取得

1. **App-Level Token (`xapp-...`) の発行**:
   * 左メニュー **「Basic Information」** > **「App-Level Tokens」** で **「Generate Token and Scopes」** をクリック。
   * Token Name に `gateway-socket-token` と入力し、**「Add Scope」** で `connections:write` を追加して **「Generate」** をクリック。
   * 発行されたトークン（`xapp-...`）をコピーします。
2. **Bot User OAuth Token (`xoxb-...`) の取得**:
   * 左メニュー **「Install App」** > **「Install to Workspace」** をクリックして許可。
   * 表示された **「Bot User OAuth Token」**（`xoxb-...`）をコピーします。

---

### Step 3: 環境変数の設定 (`.env`)

リポジトリ直下で設定ファイルを作成します。

```bash
cd antigravity-gateway
cp .env.example .env
```

`.env` を開き、取得したトークンと設定を入力します：

```ini
# Slack 認証情報
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_APP_TOKEN=xapp-1-xxxxxxxxxxx-xxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# セッションモード & 自動参加
SESSION_MODE=thread          # 'thread' (スレッドごと) または 'channel' (チャンネル直下)
AUTO_JOIN_CHANNELS=true      # パブリックチャンネルへの一括自動参加

# セキュリティ設定
# 自分の Slack メンバーID (Slackのプロフィール画面 > 「...」 > 「メンバーIDをコピー」で取得)
ALLOWED_USER_IDS=U0123456789
ALLOWED_CHANNEL_IDS=C0123456789

# 操作対象リポジトリのパス
TARGET_WORKSPACE_PATH=/Users/username/Workspace/your-project

# Remote Control 権限
ALLOW_FILE_READ=true
ALLOW_FILE_WRITE=true        # ファイル編集を許可
ALLOW_RUN_COMMAND=true       # pytest や git などのコマンド実行を許可
```

---

### Step 4: Docker で起動

```bash
docker compose up -d --build
```

#### ログの確認（正常接続の確認）
```bash
docker compose logs -f
```

ログに `⚡️ Antigravity Gateway is connecting to Slack Socket Mode...` および `✨ Successfully auto-joined X public channel(s).` と表示されれば起動完了です！

---

### Step 5: Slack からの動作確認

Slack の任意のチャンネル（または Bot の DM）で以下を試してみましょう。

1. **ステータス確認**:
   ```text
   /agy status
   ```
2. **通常対話（コード調査・Remote Control）**:
   ```text
   @Antigravity src/auth.py の実装内容を教えて
   ```
3. **自律ゴール達成モード**:
   ```text
   /agy goal pytest tests/ を実行して、落ちているテストをすべて修正して
   ```
4. **脇道質問（会話履歴を汚さない）**:
   ```text
   /agy btw このプロジェクトの Python バージョンは何？
   ```

---

## 🏛️ Antigravity スラッシュコマンド一覧

| コマンド | 説明 |
| :--- | :--- |
| **`/agy goal <目標>`** | 目標達成・テスト通過までエージェントが自律ループ実行 |
| **`/agy grill-me <テーマ>`** | エージェントが人間に質問して設計の穴を詰める壁打ちモード |
| **`/agy btw <質問>`** | メインの会話履歴を一切汚さずに単発回答 |
| **`/agy browser <指示>`** | Webページ調査・ブラウザ自動化タスクを実行 |
| **`/agy teamwork <タスク>`** | 複数サブエージェントによる並行・分担タスク実行 |
| **`/agy schedule <指示>`** | タイマー・定期実行タスクの登録 |
| **`/agy learn`** | 直前の修正・対話からルールを学習して永続化提案 |
| **`/agy guide`** | Antigravity の公式ガイド・リファレンスを表示 |
| **`/agy customs`** | カスタマイズ仕様（Skills/Rules/Hooks）を表示 |
| **`/agy reset` / `clear`** | 現在の会話セッション履歴を初期化 |
| **`/agy status`** | ワークスペース、Gitブランチ、実行権限、稼働状況を表示 |
| **`/agy help`** | コマンド一覧と使い方をカード表示 |

_※ すべてのコマンドはチャットメッセージ内でそのまま `/goal ...` や `/btw ...` と入力しても同様に動作します。_

---

## 📂 ディレクトリ構成

```text
antigravity-gateway/
├── README.md                           # 本ドキュメント (セットアップ＆全体ガイド)
├── Dockerfile                          # 非root (UID 1000) + uv 高速マルチステージビルド
├── docker-compose.yml                  # 堅牢化設定 (cap_drop ALL, read_only, メモリ2GB上限)
├── .env.example                        # 環境変数ひな型
├── pyproject.toml                      # 依存パッケージ & ruff / pytest 設定
├── docs/                               # 体系化された設計ドキュメント
│   ├── 01_discussion_and_decisions.md  # 検討記録・技術比較・意思決定理由
│   ├── 02_architecture.md              # 全体アーキテクチャ・データフロー
│   ├── 03_security_and_permissions.md  # 5層防御セキュリティ仕様
│   ├── 04_roadmap_and_phases.md        # フェーズ1〜3のゴール・計画
│   ├── 05_artifacts_and_ux.md          # Webビューワー・Markdown変換仕様
│   ├── 06_detailed_design_phase1.md    # フェーズ1詳細設計書 (確定版)
│   ├── 07_docker_design.md             # Docker堅牢化・リソース上限設計
│   └── 08_setup_guide.md               # セットアップ＆運用手順書
├── src/                                # 実装コード
│   ├── config.py                       # 設定バリデーション
│   ├── security.py                     # 認可・シークレットマスキング
│   ├── session.py                      # セッション管理 & TTL
│   ├── converter.py                    # GFM -> Slack mrkdwn 変換
│   ├── agent_runner.py                 # Antigravity SDK 実行
│   ├── bot.py                          # Slack Bolt アプリ & コマンドルーティング
│   └── main.py                         # エントリーポイント & Socket Mode 起動
└── tests/                              # 単体テスト (18件 ALL PASS)
```
