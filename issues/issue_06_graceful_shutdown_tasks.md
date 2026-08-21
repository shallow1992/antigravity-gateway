# Issue #6: [Operations] バックグラウンドタスクの安全な終了管理 (Graceful Shutdown改善)

## 📌 概要
`src/main.py` において、`auto_join_public_channels` などのバックグラウンド非同期タスクが、コンテナ停止（`SIGINT`/`SIGTERM`）時に明示的にキャンセル・待機されていないため、完全な Graceful Shutdown パイプラインを整備する。

## 🎯 目的
コンテナ停止時にすべての非同期タスクが安全かつ綺麗に終了し、未完了の通信や警告ログを出さずにシャットダウンできるようにする。

## 🔍 現状の課題
- `auto_join_public_channels` が `asyncio.create_task` で起動されたまま参照が保持されていないため、停止時に `Task was destroyed but it is pending!` のような警告が発生する可能性がある。

## 🛠️ 修正方針
1. `src/main.py` でバックグラウンドタスクの参照を `background_tasks: Set[asyncio.Task]` で保持。
2. シャットダウンシーケンスで、保持している全タスクを `task.cancel()` して `asyncio.gather(..., return_exceptions=True)` で待機。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] バックグラウンドタスクが追跡・管理されていること
- [ ] シャットダウン時にすべてのタスクが安全にクリーンアップされること
- [ ] 停止ログが正しく出力されること
