# 09. リファクタリング & 改善バックログ (Issues)

本ドキュメントは、コードレビューにより洗い出された品質改善・保守性向上・セキュリティ強化のための GitHub Issue 一覧です。
1つずつの Issue を順次対応・検証して進めます。

---

## 📋 Issue 一覧と進捗管理

| Issue ID | 種別 | タイトル | 優先度 | 状態 | 詳細ファイル |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Issue #1** | Refactor | コマンドディスパッチャの分離と重複コード排除 (DRY) | High | 📝 準備完了 | [issues/issue_01_command_dispatcher.md](../issues/issue_01_command_dispatcher.md) |
| **Issue #2** | Reliability | エージェント実行の最大タイムアウト処理の追加 (Hang防止) | High | 📝 準備完了 | [issues/issue_02_agent_timeout.md](../issues/issue_02_agent_timeout.md) |
| **Issue #3** | Memory | セッション会話履歴の最大件数制限 (FIFOローテーション) | Medium | 📝 準備完了 | [issues/issue_03_session_history_limit.md](../issues/issue_03_session_history_limit.md) |
| **Issue #4** | Security | シークレットスキャナーのパターン拡充 (OpenAI / Anthropic / JWT等) | High | 📝 準備完了 | [issues/issue_04_secret_redaction_patterns.md](../issues/issue_04_secret_redaction_patterns.md) |
| **Issue #5** | Security | パストラバーサル判定の厳密化 (Path.is_relative_to) | High | 📝 準備完了 | [issues/issue_05_path_traversal_refinement.md](../issues/issue_05_path_traversal_refinement.md) |
| **Issue #6** | Operations | バックグラウンドタスクの安全な終了管理 (Graceful Shutdown改善) | Medium | 📝 準備完了 | [issues/issue_06_graceful_shutdown_tasks.md](../issues/issue_06_graceful_shutdown_tasks.md) |

---

## 🚀 推奨の対応順序

1. **Issue #4 & Issue #5（セキュリティ強化）**: 最重要の防壁を即座に引き締め。
2. **Issue #1（DRY・構造整理）**: コマンド処理を綺麗に切り離してコードをスッキリ化。
3. **Issue #2 & Issue #3（信頼性・メモリ安全）**: タイムアウトと履歴ローテーションで長期稼働を安定化。
4. **Issue #6（Graceful Shutdown）**: コンテナ終了シーケンスの完全化。
