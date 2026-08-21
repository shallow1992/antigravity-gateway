# AI Agent Guidelines (AGENTS.md) - Antigravity Gateway

本プロジェクト（`antigravity-gateway`）における開発指針、設計思想、セキュリティ防壁、および AI エージェントの行動・運用ルールです。

---

## 1. 永続コンテキスト・設計書の管理 (`docs/`)

- **設計書・仕様書の配置場所**:
  - プロジェクトの設計思想、アーキテクチャ、機能要件、および**「なぜそのように設計したのか（意図・Why）」**はすべて **`docs/`** 配下に Markdown ドキュメントとして永続化する。
  - 主なドキュメント体系:
    - [`docs/01_discussion_and_decisions.md`](./docs/01_discussion_and_decisions.md): 検討記録・技術比較・意思決定理由
    - [`docs/02_architecture.md`](./docs/02_architecture.md): 全体アーキテクチャ・データフロー
    - [`docs/03_security_and_permissions.md`](./docs/03_security_and_permissions.md): 5層防御セキュリティ仕様
    - [`docs/04_roadmap_and_phases.md`](./docs/04_roadmap_and_phases.md): フェーズ1〜3の開発ロードマップ
    - [`docs/05_artifacts_and_ux.md`](./docs/05_artifacts_and_ux.md): Markdown 変換・Webビューワー仕様
    - [`docs/06_detailed_design_phase1.md`](./docs/06_detailed_design_phase1.md): フェーズ1詳細設計書（確定版）
    - [`docs/07_docker_design.md`](./docs/07_docker_design.md): Docker 堅牢化・リソース上限設計
    - [`docs/08_setup_guide.md`](./docs/08_setup_guide.md): セットアップ＆運用手順書
    - [`docs/09_refactoring_backlog.md`](./docs/09_refactoring_backlog.md): 改善バックログ・GitHub Issue 管理
- **エージェントの行動指針**:
  - 新機能の追加、仕様変更、リファクタリングを行う際は、必ず `docs/` 配下の設計書を参照し、整合性を保つこと。
  - 機能や設計に変更があった場合は、コードだけでなく `docs/` 配下の設計ドキュメントも同時に更新して永続的な記憶として残すこと。

---

## 2. 開発環境・Docker 隔離 ＆ Git Worktree 運用ルール (重要)

- **ホスト環境の保護 (Docker 実行)**:
  - ホスト PC の環境を汚さないため、本番コンテナの実行は **Docker Compose（`docker compose up -d --build`）** で行う。
  - コンテナは非rootユーザー（`UID 1000:1000`）、`read_only: true`（ルートファイルシステム読取専用）、`cap_drop: [ALL]`（全Linux特権剥奪）、メモリ上限 2GB / CPU 2コア設定で運用する。
- **1 Issue = 1 Git Worktree / ブランチ開発の原則 (最重要)**:
  - 機能追加やバグ修正を行う際は、**GitHub Issue を作成・確認した上で専用ブランチまたは git worktree を作成して開発を進める**。
  - 各作業単位で独立してテスト・コミット・PR/Issue クローズを行い、`main` ブランチの履歴を常にクリーンに保つ。
- **PR マージ / 完了後の必須クリーンアップ手順**:
  - 作業完了時は、必ず以下のクリーンアップを実行すること：
    1. **メインブランチの最新化**: `git pull origin main` を実行してリモートの変更をローカル `main` に反映する。
    2. **作業ブランチ/Worktree の整理**: マージ済みのローカルブランチを削除し、必要に応じて `git fetch --prune` を実行する。
- **コーディング・設計**:
  - ソースコード（Python）の編集やドキュメントの更新はホスト側で直接行い、高速にイテレーションを回す。

---

## 3. コア技術・アーキテクチャ・コーディング規約

- **技術スタック**:
  - 言語: **Python 3.11+**
  - Slack フレームワーク: **`slack-bolt` (AsyncApp / Socket Mode)**
  - 設定管理: **`pydantic-settings`**（環境変数バリデーション）
  - AI エージェント基盤: **`google-antigravity` SDK** (`Agent`, `LocalAgentConfig`, `CapabilitiesConfig`)
  - パッケージ管理 / Linter: **`uv`**, **`ruff`**
  - テストフレームワーク: **`unittest` / `pytest`** (`pytest-asyncio`)
- **疎結合設計（モジュール責務分離）**:
  - `src/config.py`: 設定定義とバリデーション
  - `src/security.py`: 認可チェック、パストラバーサル防止、シークレット自動マスキング、監査ログ
  - `src/session.py`: セッション管理（スレッド/チャンネル）、TTL、FIFO 履歴トリミング
  - `src/converter.py`: GFM（GitHub Flavored Markdown）から Slack `mrkdwn` への変換
  - `src/commands.py`: Antigravity スラッシュコマンドのパース・ディスパッチ・カード生成
  - `src/agent_runner.py`: SDK 呼び出し、思考ストリーミング、スロットリング、タイムアウト管理
  - `src/bot.py`: Slack Bolt イベントルーティング専従
  - `src/main.py`: Socket Mode 起動、自動入室、Graceful Shutdown

---

## 4. CI/CD & GitHub 連携 ＆ コミット・Issue 運用ルール (重要)

- **コミットメッセージ規約 (Conventional Commits)**:
  - コミットおよび PR タイトルは以下のプレフィックスを厳守し、意図を明確にする：
    - `feat:` (新機能の追加)
    - `fix:` (バグ修正)
    - `refactor:` (リファクタリング・コード改善)
    - `docs:` (ドキュメントの追加・更新)
    - `test:` (テストの追加・修正)
    - `ci:` (CI/CD 設定・GitHub Actions ワークフロー)
    - `chore:` (依存関係・環境設定)
- **リモート CI (GitHub Actions) の自動検証義務 (最重要)**:
  - GitHub へのプッシュ（`git push`）を行った際、エージェントは必ず GitHub CLI（`gh run list` や `gh run view <run-id>`）を用いて、**GitHub Actions CI ワークフロー（Ruff Lint & Test Suite）の実行結果を確認**すること。
  - CI が `success`（All Green）になることを見届け、テスト失敗や Linter エラーが検知された場合は即座に原因を修正して再プッシュすること。

---

## 5. セキュリティ・プライバシー保護 ＆ 5層防御ルール (最重要)

- **第1層: 厳格なアクセス制御 (User Whitelist)**:
  - `ALLOWED_USER_IDS` に登録された Slack ユーザーのみが Bot を操作可能。未認可ユーザーには即座に拒否通知。
- **第2層: 機密情報（シークレット）の完全自動マスキング**:
  - Slack トークン（`xoxb-`, `xapp-`, `xoxp-`）、Gemini API キー（`AIza...`）、GitHub トークン（`ghp_...`）、OpenAI キー（`sk-...`）、Anthropic キー（`sk-ant-...`）、Bearer トークン、AWS キー等は、Slack 送信前に `SecurityGuard.mask_secrets()` で **`[REDACTED_...]` に自動置換**する。
- **第3層: パストラバーサル＆機密ファイル保護**:
  - `is_safe_file_path()` には Python 3.9+ の **`Path.is_relative_to()`** を使用し、境界プレフィックスのすり抜けを物理的に防止する。
  - `.env*`, `*.key`, `*.pem`, `id_rsa*`, `credentials.json` へのアクセスは即座にブロックする。
- **第4層: 危険コマンド遮断 (Command Blacklist)**:
  - `rm -rf /`, `mkfs`, `sudo`, フォークボム等の破壊的コマンドは実行前に遮断する。
- **第5層: Docker コンテナ完全隔離**:
  - 非root、特権剥奪（`cap_drop: ALL`）、ルートファイルシステム読取専用（`read_only: true`）、リソース上限（2GB RAM / 2 CPUs）によりホスト環境の安全を物理的に保証する。
- **環境固有情報・個人情報の混入禁止**:
  - コミット・ドキュメント・Issue に、ホスト固有の絶対パスや実トークンを混入させない。ダミー値は文字列結合などで Push Protection の誤検知を回避する。

---

## 6. Antigravity コマンド体系 ＆ UX 設計のベストプラクティス

- **公式スラッシュコマンドの完全マッピング**:
  - `/goal <目標>`: 自律ゴール達成モード（テスト通過まで自律ループ）
  - `/grill-me <テーマ>`: 設計・プラン壁打ちインタビューモード
  - `/btw <質問>`: **メインの会話履歴を一切汚さない単発質問（Ephemeral/インライン）**
  - `/browser <指示>`: ブラウザ自動化・Web調査
  - `/teamwork <タスク>`: 複数サブエージェント協調実行
  - `/schedule <指示>`: タイマー・定期実行タスク登録
  - `/learn`: 成功・修正内容からルールを抽出して永続化
  - `/guide`, `/customs`: 公式ガイド・カスタマイズ仕様の表示
  - `/reset`, `/clear`: 会話セッション初期化
  - `/status`: 稼働状況、Gitブランチ、実行権限のカード表示
  - `/help`: コマンド一覧ヘルプの表示
- **`/btw` のセッション履歴非汚染（厳守）**:
  - `/btw` コマンドのプロンプトおよび回答は、`ConversationSession.history` に追加してはならない。メインタスクのコンテキスト汚染を防ぐ。
- **進捗表示のインプレース編集 UX**:
  - 処理開始時にプレースホルダー（`🧠 *考え中...*`）を投稿し、思考・ツール実行イベントに合わせて**同一メッセージをリアルタイム編集更新**する。
  - Slack API レートリミット（Tier 3）保護のため、**最低 0.8 秒以上のデバウンス（スロットリング）** を厳守する。
- **デュアルセッションモード**:
  - `SESSION_MODE=thread`（スレッド分離対話）と `SESSION_MODE=channel`（チャンネル直下タイムライン）を `.env` で切り替え可能にする。
- **パブリックチャンネル自動参加**:
  - `AUTO_JOIN_CHANNELS=true` により、起動時に全パブリックチャンネルを自動走査して入室し、未参加チャンネルでのメンション時も自律入室する。

---

## 7. ディスカッション・意思決定 ＆ エージェントの行動規範 (重要)

- **ディスカッション・合意先行の原則 (先走り実装の禁止)**:
  - ユーザーから指示や相談を受けた際、**意図や設計思想を確認せずに勝手にコード変更に着手してはならない**。
  - まずはディスカッションを行い、選択肢・メリット・デメリット・設計方針を提示して、ユーザーの合意を得てから実装に進むこと。
- **Issue 駆動開発の徹底**:
  - 発見された課題や改善項目は、まず GitHub Issue として目的・現状・修正方針・完了条件を定義し、Issue 単位で着実に対応・検証・クローズすること。
- **デッドコードの完全除去**:
  - リファクタリングや仕様変更に伴い不要となったコード、未使用の import、古い設定は即座に完全削除し、常にクリーンな状態を保つ。
