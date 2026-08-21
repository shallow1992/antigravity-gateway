# Issue #9: [Test & CI] 設定バリデーションテストおよび GitHub Actions 自動テスト CI の構築 (test_config.py & CI)

## 📌 概要
`src/config.py` に対する設定バリデーションテスト（`tests/test_config.py`）を追加し、さらに GitHub へのプッシュやプルリクエスト時に自動でテスト・Linter（`ruff`）を実行する GitHub Actions ワークフロー（`.github/workflows/test.yml`）を構築する。

## 🎯 目的
環境変数の設定不備を起動前に確実に検知できることを保証し、GitHub 上で自動テスト（CI）による品質ゲートを確立する。

## 🔍 テスト対象シナリオ
1. **必須設定の欠落検知**:
   - `SLACK_BOT_TOKEN` や `SLACK_APP_TOKEN` が未設定の場合にバリデーションエラーとなること。
2. **ホワイトリストのパース**:
   - `ALLOWED_USER_IDS=" U123 , U456 "` の前後の空白がトリムされ、綺麗なセット型になること。
3. **不正なセッションモードの検知**:
   - `SESSION_MODE="invalid"` が設定された場合にエラーとなること。
4. **GitHub Actions CI ワークフロー**:
   - `ubuntu-latest`, Python 3.11 環境で `uv` を用いて高速にテストと `ruff check` が実行されること。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] `tests/test_config.py` が作成され、全エッジケースが検証されていること
- [ ] `.github/workflows/test.yml` が追加され、CI が実行可能であること
