# 07. Docker コンテナ設計仕様書 【堅牢化・確定版】

本ドキュメントは、`antigravity-gateway` を安全に Docker コンテナとして構築・起動・運用するための詳細設計書です。
CIS Docker Benchmark に準拠したコンテナ堅牢化（Container Hardening）およびリソース上限管理を定義します。

---

## 1. コンテナアーキテクチャ概要

* **ベースイメージ**: `python:3.11-slim` (軽量・セキュアなDebianベース)
* **パッケージマネージャー**: `uv` (高速ビルド)
* **実行形態**: `docker compose up -d` による常駐サービス
* **ネットワーク**: 外向き WebSocket 通信（フェーズ1ではインバウンドポート開放不要）

---

## 2. ボリュームマウント & 永続化設計

| ホスト側パス | コンテナ内パス | 権限 | 目的 |
| :--- | :--- | :---: | :--- |
| `${TARGET_WORKSPACE_PATH}` | `/workspace` | `rw` | Antigravity が操作する対象リポジトリ |
| `./artifacts` | `/app/artifacts` | `rw` | 生成された Plan / Diff 等の成果物永続化 |
| `./logs` | `/app/logs` | `rw` | セキュリティ監査ログ・実行ログの永続化 |
| `~/.gemini` (任意) | `/root/.gemini` | `ro` | Google / Antigravity のローカル認証情報 (読取専用) |

---

## 3. Dockerfile 設計

```dockerfile
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

# 環境変数の初期値
ENV PYTHONUNBUFFERED=1 \
    TARGET_WORKSPACE_PATH=/workspace \
    LOG_LEVEL=INFO

# 起動コマンド
CMD ["python", "src/main.py"]
```

---

## 4. docker-compose.yml 設計（堅牢化設定込み）

```yaml
version: '3.8'

services:
  gateway:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: antigravity-gateway
    restart: unless-stopped
    
    # 1. 非rootユーザーで実行
    user: "1000:1000"
    
    # 2. Linux Capabilities (特権) 全剥奪
    cap_drop:
      - ALL
      
    # 3. 特権昇格の完全禁止
    security_opt:
      - no-new-privileges:true
      
    # 4. ルートファイルシステムの読み取り専用化 (改ざん防止)
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid
      
    # 5. リソース上限設定 (ホストPCクラッシュ・暴走防止)
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2048M
        reservations:
          cpus: '0.2'
          memory: 256M

    env_file:
      - .env
    environment:
      - PYTHONUNBUFFERED=1
      - TARGET_WORKSPACE_PATH=/workspace
    volumes:
      # 操作対象のコードリポジトリ
      - ${TARGET_WORKSPACE_PATH:-.}:/workspace:rw
      # 成果物とログの永続化
      - ./artifacts:/app/artifacts:rw
      - ./logs:/app/logs:rw
      # Antigravity 認証情報 (必要な場合)
      - ~/.gemini:/home/appuser/.gemini:ro
```

---

## 5. 運用コマンド仕様

### 起動・停止
```bash
# ビルドしてバックグラウンド起動
docker compose up -d --build

# リアルタイムログ確認
docker compose logs -f

# 停止
docker compose down
```
