# Issue #3: [Memory] セッション会話履歴の最大件数制限 (FIFOローテーション)

## 📌 概要
`src/session.py` の `ConversationSession.history` は無制限に追加されるため、長時間の同一スレッド/チャンネル対話でメモリ消費およびコンテキストトークン数が肥大化するリスクがある。

## 🎯 目的
会話履歴に上限（最大ターン数）を設け、上限を超えた場合は古いメッセージから自動的に破棄（FIFO: First In First Out）するトリミング機構を実装する。

## 🔍 現状の課題
- 50ターン以上の対話が続くと、メモリフットプリントが増加し、エージェントに渡すコンテキストが過大になり推論速度や精度に悪影響を及ぼす。

## 🛠️ 修正方針
1. `src/config.py` に `MAX_HISTORY_TURNS: int = 20`（最新10往復分）を追加。
2. `src/session.py` の `add_user_message` / `add_assistant_message` において、`len(self.history) > max_turns` の場合に古い履歴をスライス（`self.history = self.history[-max_turns:]`）する。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] 履歴件数が `MAX_HISTORY_TURNS` を超えた際に、自動的に古い順に切り詰められること
- [ ] 切り詰め後も最新の対話文脈が正常に保持されること
- [ ] 単体テストで履歴トリミングの動作が検証されていること
