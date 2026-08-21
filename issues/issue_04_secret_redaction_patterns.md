# Issue #4: [Security] シークレットスキャナーのパターン拡充 (OpenAI / Anthropic / JWT等)

## 📌 概要
`src/security.py` の `SECRET_PATTERNS` に、主要なAIプロバイダー（OpenAI, Anthropic）のAPIキーや、JWT Bearerトークンなどのパターンを追加し、機密情報の漏洩防御をより強固にする。

## 🎯 目的
万が一エージェントがプロジェクト内の環境変数や設定ファイルから他のAPIキーや認証ヘッダーを読み取ってしまっても、Slackへの返信時に自動的に `[REDACTED_SECRET]` にマスキングされる範囲を広げる。

## 🔍 現状の課題
- 現状は Slack Tokens, Gemini API Key, GitHub PAT, AWS Access Key に対応しているが、OpenAI（`sk-...`）や Anthropic（`sk-ant-...`）、Bearer トークンなどが未対応。

## 🛠️ 修正方針
1. `src/security.py` の `SECRET_PATTERNS` に以下の正規表現パターンを追加：
   - OpenAI API Key: `sk-[a-zA-Z0-9]{20,T3BlbkFJ[a-zA-Z0-9]{20,}}` / `sk-proj-[a-zA-Z0-9_-]{40,}`
   - Anthropic API Key: `sk-ant-[a-zA-Z0-9-_]{32,}`
   - Generic Bearer Token: `Bearer\s+[a-zA-Z0-9_\-\.]{20,}`
2. 単体テストに新しいキーパターンのマスキング検証を追加。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] OpenAI、Anthropic、Bearer トークンのマスキングパターンが追加されていること
- [ ] テストコードで新パターンのマスキングが検証され PASS すること
