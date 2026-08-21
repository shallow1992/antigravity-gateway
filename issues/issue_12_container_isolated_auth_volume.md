# Issue #12: [Architecture & Security] Dev Container型コンテナ内独立認証ボリュームへの移行 (APIキー不要化 & ホスト完全隔離)

## 📌 概要
ホスト PC の `~/.gemini` ディレクトリを直接マウントする方式を廃止し、VS Code Dev Container と同様にコンテナ専用の独立した Docker Named Volume (`gemini-auth`) を用いて Google Pro 認証をコンテナ内部で完結・保持するアーキテクチャに刷新する。

## 🎯 目的
1. **API キーの完全撤廃 (従量課金ゼロ & Pro サブスク活用)**:
   - 厳しいレート制限や従量課金が発生する `GEMINI_API_KEY` を廃止し、Google Pro サブスクリプションの認証で無制限に動作させる。
2. **ホスト機密情報の完全隔離 (最高強度のセキュリティ)**:
   - ホスト PC の `~/.gemini` や認証情報に一切アクセスさせず、コンテナ専用ボリューム内で安全に認証情報を隔離・永続化する。
3. **エージェントからのトークン保護 (多層防御)**:
   - コンテナ内ボリュームであっても、AI エージェントがファイル検索・読み取りツールで認証トークンファイル（`jetski-standalone-oauth-token` 等）を覗き見できないよう、`src/security.py` でピンポイントに遮断する。

## 🛠️ 変更計画
1. **`docker-compose.yml`**:
   - ホストマウント `- ~/.gemini:/home/appuser/.gemini:ro` を削除。
   - Docker Named Volume `gemini_auth:/home/appuser/.gemini` を定義してコンテナ内でのみ永続化。
2. **`src/config.py`**:
   - `GEMINI_API_KEY` を必須項目から完全撤廃（ローカル/コンテナ内認証をデフォルト化）。
3. **`src/security.py`**:
   - `BLOCKED_FILE_PATTERNS` に `*token*`, `*oauth*`, `*jetski*`, `*.key` 等の機密認証パターンを登録し、`GEMINI.md` などのルールファイル読み込みは許可しつつ認証ファイルのみを厳格ブロック。
4. **`src/agent_runner.py`**:
   - コンテナ内 `/home/appuser/.gemini` の認証情報を自動検知してエージェントを実行。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] `docker-compose.yml` がホストの `~/.gemini` をマウントせず Named Volume `gemini_auth` を使用していること
- [ ] `GEMINI_API_KEY` がなくても Google Pro 認証でエージェントが動作すること
- [ ] `GEMINI.md` などの指示書は読めるが、認証トークンファイルへのアクセスは `SecurityGuard` でブロックされること
- [ ] 全 32 件の単体・結合テストスイートおよび GitHub Actions CI が PASS すること
