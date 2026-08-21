# Issue #1: [Refactor] コマンドディスパッチャの分離と重複コード排除 (DRY)

## 📌 概要
`src/bot.py` 内で、スラッシュコマンド（`_handle_slash_command_core`）と通常チャット対話（`_handle_user_prompt`）において、コマンド判定（`status`, `help`, `reset` 等）およびカード生成ロジックが二重に実装されており、DRY原則に反している。

## 🎯 目的
コマンドのパース、ディスパッチ、およびシステム応答の生成ロジックを専用モジュール（`src/commands.py`）に集約し、保守性とテスタビリティを向上させる。

## 🔍 現状の課題
- `status` や `help` などの変更時、2箇所のコードを修正する必要があり手戻りやバグの原因となる。
- `bot.py` のコード行数が肥大化し、ルーティングとビジネスロジックが密結合になっている。

## 🛠️ 修正方針
1. `src/commands.py` を新規作成し、以下を移行・集約：
   - `CommandDispatcher` クラスまたは関数群
   - `status`, `help`, `reset`, `btw`, `goal`, `grill-me` などのコマンドディスパッチ処理
   - ヘルプカード・ステータスカードの構築ロジック
2. `src/bot.py` は Slack Bolt のイベントルーティングに専念させ、コマンド処理は `CommandDispatcher` に委譲。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] `src/commands.py` が作成され、コマンド処理が一元化されていること
- [ ] スラッシュコマンド（`/agy ...`）と通常チャット入力（`/<command>`）の両方で同一のロジックが使われていること
- [ ] 既存の単体テストがすべて PASS すること
