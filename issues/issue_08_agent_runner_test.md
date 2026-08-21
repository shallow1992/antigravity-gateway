# Issue #8: [Test] エージェントランナー非同期実行・タイムアウト・進捗スロットリングのテスト追加 (test_agent_runner.py)

## 📌 概要
`src/agent_runner.py` に対する単体テストを追加し、プロンプト実行、タイムアウト（`asyncio.TimeoutError`）、思考ログの進捗コールバック（`on_progress`）、会話履歴コンテキストの結合処理を網羅的に検証する。

## 🎯 目的
エージェントのライフサイクル管理と例外処理（タイムアウト等）が意図通りに動作することを自動テストで保証する。

## 🔍 テスト対象シナリオ
1. **通常実行**:
   - `execute_prompt` が正常に応答テキストを返すこと。
2. **タイムアウト動作**:
   - `AGENT_TIMEOUT_SEC`（例: 0.1秒）を超過した場合に、タイムアウトメッセージが安全に返却されること。
3. **会話コンテキスト結合**:
   - `session.history` が存在する場合、`[Previous Conversation Context]` ブロックがプロンプトに付加されること。
4. **進捗通知コールバック**:
   - `on_progress` が正常に呼び出されること。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] `tests/test_agent_runner.py` が追加されていること
- [ ] タイムアウトおよびコンテキスト結合のテストが PASS すること
