# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:latest AS uv_bin
FROM python:3.11-slim

# 必須ツールのインストール (git, curl, ca-certificates)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 非root実行ユーザー (appuser: UID 1000) の作成
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

# uv のコピー
COPY --from=uv_bin /uv /uvx /bin/

# アプリケーションディレクトリ
WORKDIR /app

# 依存関係定義のコピーとインストール (キャッシュ最適化)
COPY pyproject.toml requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt

# ソースコードのコピー & 権限付与
COPY src/ ./src/
RUN mkdir -p /app/artifacts /app/logs && \
    chown -R appuser:appgroup /app

# 実行ユーザーの切り替え (非root)
USER appuser

# 環境変数の初期値 (PYTHONPATHを設定してsrcモジュールを解決)
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TARGET_WORKSPACE_PATH=/workspace \
    LOG_LEVEL=INFO

# 起動コマンド
CMD ["python", "src/main.py"]
