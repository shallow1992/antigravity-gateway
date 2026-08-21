# 05. Artifacts と UI/UX 設計仕様（Webビューワー）

Antigravity の最大の特徴である「構造化された設計書（Implementation Plan）」「変更記録（Walkthrough）」「コード差分（Diff）」「構成図（Mermaid）」を、チャットツールの制限を受けずに快適に閲覧するための設計仕様です。

---

## 1. チャットと Web ビューワーの責務分離

| コンポーネント | チャット (Slack / Discord) | Web ビューワー (FastAPI + Browser) |
| :--- | :--- | :--- |
| **主な役割** | **通知・指示・短い会話・進捗確認** | **設計書・Diff・ダイアグラムの閲覧・承認** |
| **表示内容** | • 要約・サマリー<br>• Thinking / Tool 実行ログ<br>• Webビューワーへのアクセスリンク<br>• 短い回答やコードスニペット | • 完全な `implementation_plan.md`<br>• 完全な `walkthrough.md`<br>• Mermaid 構成図のレンダリング<br>• シンタックスハイライト付きコード Diff |
| **インタラクション** | メンション、スレッド返信、絵文字リアクション | 「承認して実行 (Approve)」/「差し戻し (Reject)」ボタン |

---

## 2. Web ビューワーのアーキテクチャ (フェーズ2)

```mermaid
flowchart LR
    subgraph AntigravityBot [Bot サーバー]
        Runner[Agent Runner] -->|プラン生成| Disk[(./artifacts/plan_123.md)]
        Web[FastAPI Web Server<br/>(Port 8000)]
        Disk --> Web
    end

    subgraph TunnelProvider [セキュアトンネル (無料)]
        CFTunnel[Cloudflare Tunnel / ngrok]
    end

    Web <--> CFTunnel
    CFTunnel <--> ExternalURL[https://agy-xxxx.trycloudflare.com/artifacts/123]
    
    AntigravityBot -->|Slack に URL を送信| SlackUser([Slack ユーザー])
    SlackUser -->|スマホ / PC ブラウザで開く| ExternalURL
```

---

## 3. Web ビューワーの画面設計イメージ

* **UIフレームワーク**: 軽量なダークテーマ Markdown ビューワー（HTML/CSS + KaTeX + Mermaid.js + Prism.js / Highlight.js）。
* **機能**:
  1. **TOC (目次)**: 長文プランの素早いナビゲーション。
  2. **Mermaid 図の自動描画**: アーキテクチャ図やシーケンス図のビジュアル化。
  3. **Diff 表示**: `+`（緑）/ `-`（赤）の直感的な差分表示。
  4. **アクションバー**: 画面上部に「Approve（実行許可）」ボタンを配置。クリックすると Bot に webhook を送信し、Slack スレッドに「✅ ユーザーがプランを承認しました」と通知して実行に移る。

---

## 4. Markdown コンバーター（Slack 用）の変換ルール

`src/converter.py` で行う主な変換ルール:

| GFM (標準Markdown) | 変換後 (Slack mrkdwn) | 備考 |
| :--- | :--- | :--- |
| `**太字**` | `*太字*` | Slack はアスタリスク1個 |
| `*斜体*` | `_斜体_` | Slack はアンダースコア |
| `~~打消し~~` | `~打消し~` | Slack はチルダ1個 |
| `[タイトル](URL)` | `<URL\|タイトル>` | Slack 専用リンク形式 |
| `# 見出し` / `## 見出し` | `*見出し*` (太字) または Block Kit Header | Slack は `#` 非対応 |
| `\| 表 \| 表 \|` | ` ```\n\| 表 \| 表 \|\n``` ` | 等幅フォントで崩れを防止 |
| ` ```diff ... ``` ` | ` ```diff ... ``` ` | コードブロックを維持 |
