# Issue #11: [Bug & Docker] requirements.txt への pydantic-settings 不足による ModuleNotFoundError の修正

## 📌 概要
Docker コンテナ起動時に `ModuleNotFoundError: No module named 'pydantic_settings'` が発生してプロセスが異常終了する。

## 🎯 目的
`requirements.txt` と `pyproject.toml` の依存パッケージ定義の不整合を解消し、Docker イメージビルド時に `pydantic-settings` が確実にインストールされるようにする。

## 🔍 原因分析
- `src/config.py` において `from pydantic_settings import BaseSettings, SettingsConfigDict` を使用している。
- `pyproject.toml` には `pydantic-settings>=2.2.0` が記述されていたが、`requirements.txt` には `pydantic>=2.0.0` のみが記載されており、`pydantic-settings` が欠落していた。
- `Dockerfile` が `RUN uv pip install --system --no-cache -r requirements.txt` を実行しているため、コンテナ環境内に `pydantic-settings` パッケージがインストールされず、インポートエラーが発生した。

## 🛠️ 修正方針
1. **`requirements.txt` の修正**:
   - `pydantic-settings>=2.2.0` を明示的に追加。
   - `pyproject.toml` の `dependencies` と完全同期させる。
2. **依存関係の整合性確認**:
   - `slack-bolt`, `slack-sdk`, `pydantic`, `pydantic-settings`, `aiohttp`, `google-antigravity` の全リストを再検証。
3. **CI 検証**:
   - GitHub Actions CI ワークフローで `requirements.txt` からのインストールと全テスト（32件）がパスすることを確認。

## ✅ 完了条件 (Acceptance Criteria)
- [ ] `requirements.txt` に `pydantic-settings>=2.2.0` が含まれていること
- [ ] `pyproject.toml` と `requirements.txt` の依存関係が一致していること
- [ ] Docker ビルド時に `pydantic-settings` が正常にインストールされること
- [ ] GitHub Actions CI が PASS すること
