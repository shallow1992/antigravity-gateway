# Issue #10: [Bug & Docker] Docker起動時の ModuleNotFoundError (src) 解消と Compose 構文警告の修正

## 📌 概要
Docker Compose 上で `docker compose up -d --build` を実行した際、コンテナ起動時に `ModuleNotFoundError: No module named 'src'` が発生してプロセスがクラッシュする問題、および `docker-compose.yml` における `the attribute 'version' is obsolete` 警告を解消する。

## 🎯 目的
Docker コンテナ環境において `src` パッケージが確実に解決され、警告なしでクリーンに起動できるようにする。

## 🔍 原因分析
1. **`ModuleNotFoundError: No module named 'src'`**:
   - `Dockerfile` の `WORKDIR /app` に対して `CMD ["python", "src/main.py"]` で実行した際、Python の `sys.path[0]` がスクリプト配置先 `/app/src` に設定され、プロジェクトルート `/app` が検索パスに含まれていなかった。
2. **`the attribute 'version' is obsolete`**:
   - Docker Compose v2 以降ではトップレベルの `version: '3.8'` 属性が非推奨（不要）となり、指定があると警告が出力される仕様になっていた。

## 🛠️ 修正内容
1. **`Dockerfile`**:
   - `ENV PYTHONPATH=/app` を追加し、コンテナ内全体でルートパッケージが参照できるように設定。
2. **`docker-compose.yml`**:
   - トップレベルの `version: '3.8'` を削除。
   - `environment:` に `- PYTHONPATH=/app` を明示的に追加。
3. **`src/main.py`**:
   - 先頭に `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))` を追加し、ローカル直接実行やあらゆる環境でのインポート安全性を二重に担保。

## ✅ 完了条件 (Acceptance Criteria)
- [x] `Dockerfile` および `docker-compose.yml` に `PYTHONPATH=/app` が設定されていること
- [x] `docker-compose.yml` から不要な `version` 属性が削除されていること
- [x] `src/main.py` に `sys.path` 安全策が追加されていること
- [x] GitHub Actions CI が PASS すること
