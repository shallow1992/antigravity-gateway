# Issue #12: [Architecture & Security] Antigravity CLI (agy) ラッパーアーキテクチャ ＆ Web ダッシュボード認証への刷新

## 📌 概要
Google Pro サブスクリプションの権限（追加課金ゼロ・使い放題）を 100% 活用するため、従来の API キー依存を完全撤廃し、**Antigravity CLI（`agy` コマンド）を直接包むラッパーアーキテクチャ** に刷新する。
また、ホスト PC の機密情報から完全に切り離し、ブラウザ（`http://localhost:8080`）から **1 クリックで Google Pro 認証を完結できる Web 管理ダッシュボード** を新設する。

## 🎯 目的
1. **Antigravity CLI (`agy`) ラッパーアーキテクチャ**:
   - `GEMINI_API_KEY`（厳しいレート制限・従量課金）を完全撤廃。
   - Slack からの指示に応じて `agy --prompt ... --workspace /workspace` を安全に非同期サブプロセス実行。
   - `agy` の思考ログ・ツール実行ログをリアルタイムに Slack のメッセージへインプレース反映。
2. **直感的な Web 管理ダッシュボード (`http://localhost:8080`)**:
   - ブラウザで画面を開き、「Google アカウントでログイン」ボタンを押すだけで Google Pro 連携が自動完了。
   - 固定ポート `8080`（`/auth/callback`）でリダイレクトを直接受信し、トークンをコンテナ内ボリュームに自動保存。
3. **ホスト機密情報の完全隔離 (最高強度セキュリティ)**:
   - ホスト PC の `~/.gemini` を一切マウントせず、コンテナ専用の独立した Docker Named Volume (`gemini_auth`) 内でのみ認証情報を隔離保持。
4. **ピンポイント多層防御**:
   - `GEMINI.md` などのルールファイル読み込みは許可しつつ、認証トークンファイル（`jetski-standalone-oauth-token` 等）への直接アクセスは `SecurityGuard` でピンポイントに遮断する。

## 🛠️ 変更計画
1. **`src/web_server.py` [NEW]**:
   - `aiohttp.web` による管理ダッシュボード HTML、`/auth/login`、`/auth/callback`、`/auth/logout`、`/api/status`。
2. **`src/agent_runner.py` [MODIFY]**:
   - `AgyCliRunner` として刷新（`asyncio.create_subprocess_exec` による `agy` CLI 起動、ストリーミングログパース、タイムアウト処理）。
3. **`docker-compose.yml` [MODIFY]**:
   - ホストマウント `- ~/.gemini:...` を完全削除。
   - `127.0.0.1:8080:8080`（Web UI ポート）を開放。
   - Docker Named Volume `gemini_auth:/home/appuser/.gemini` を定義。
4. **`src/main.py` [MODIFY]**:
   - Slack Socket Mode と並行して Web サーバーを非同期起動。
5. **`src/security.py` [MODIFY]**:
   - `BLOCKED_FILE_PATTERNS` に `jetski-standalone-oauth-token`, `*token*`, `*oauth*`, `*credential*`, `*.key`, `*.pem` を登録（`GEMINI.md` は許可）。
   - `mask_secrets()` に OAuth トークンのマスキングを追加。
6. **`tests/test_web_server.py` [NEW]**:
   - Web サーバー、OAuth フロー、CSRF `state` 検証のテストスイートを追加。
7. **`tests/test_agent_runner.py` [MODIFY]**:
   - `agy` CLI サブプロセス実行とストリーミングのテストを追加。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] `http://localhost:8080` で Web 管理ダッシュボードが表示されること
- [ ] 「Google アカウントでログイン」からワンクリックで OAuth 連携が完了すること
- [ ] `agy` CLI が Google Pro 認証で起動し、Slack にリアルタイム進捗と結果が返ること
- [ ] ホストの `~/.gemini` をマウントせず Named Volume `gemini_auth` で認証が保持されること
- [ ] `GEMINI.md` などの指示書は読めるが、認証トークンファイルへのアクセスはブロックされること
- [ ] 全テストスイートおよび GitHub Actions CI が PASS すること
