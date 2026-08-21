# Issue #2: [Reliability] エージェント実行の最大タイムアウト処理の追加 (Hang防止)

## 📌 概要
`src/agent_runner.py` において、エージェントのプロンプト実行（`agent.chat`）に対するタイムアウトが設定されていないため、ネットワークハングや無限ループ時にプロセスが永久に待機状態になるリスクがある。

## 🎯 目的
エージェント実行に対して設定可能な最大タイムアウトを導入し、タイムアウト時には安全にユーザーへエラーを通知してプロセスリソースを解放する。

## 🔍 現状の課題
- 外部通信の遅延やLLM側のタイムアウト発生時、Slack のプレースホルダー（`🧠 思考中...`）が停止したままになり、スレッドがブロックされる可能性がある。

## 🛠️ 修正方針
1. `src/config.py` に `AGENT_TIMEOUT_SEC: int = 300`（デフォルト5分）を追加。
2. `src/agent_runner.py` の `execute_prompt` 内で `asyncio.wait_for(..., timeout=self.timeout_sec)` を適用。
3. `asyncio.TimeoutError` 発生時、分かりやすいエラーメッセージ（`⏱️ 処理がタイムアウトしました (制限時間: X秒)`）を返却。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] 設定可能なタイムアウト上限（`AGENT_TIMEOUT_SEC`）が追加されていること
- [ ] タイムアウト発生時に `TimeoutError` を適切にキャッチし、Slack に通知されること
- [ ] タイムアウト動作の単体テストが追加されていること
