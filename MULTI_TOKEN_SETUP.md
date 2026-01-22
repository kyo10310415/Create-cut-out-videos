# マルチトークン設定ガイド

複数のチャンネルで異なるGoogleアカウントを使用する場合の設定方法

---

## 📋 概要

このシステムは、**チャンネルごとに異なるOAuth認証**を使用できます。

### 使用例

- チャンネル1: `UCrzO_hsFW8vLLy8xFBADfqQ`（Googleアカウント A）
- チャンネル2: `UC3NYX0zN6GySr_hzJHU4tog`（Googleアカウント B）
- チャンネル3: `UChzVx-TG5UcoVJw3xvG_ggw`（Googleアカウント C - ぎょうへい先生）

---

## ステップ1: 各チャンネルでOAuth認証を実行

### 1-1: チャンネルオーナーに依頼

各チャンネルのオーナーに以下のメッセージを送信：

```
【YouTube Clipper】OAuth認証のお願い

お世話になっております。

あなたのYouTubeチャンネルから見どころを自動検出するシステムを構築中です。
以下の手順で認証をお願いいたします（所要時間：約3分）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
手順1: 認証ページにアクセス
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

https://youtube-clipper-oauth-v2.onrender.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
手順2: 認証を実行
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 「認証を開始」ボタンをクリック
2. あなたのGoogleアカウントでログイン
3. 権限の確認画面で「許可」をクリック

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
手順3: コードをコピーして送信
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

成功画面に表示される以下の情報を送ってください：

✓ チャンネル名
✓ チャンネルID
✓ YOUTUBE_OAUTH_CREDENTIALS (Base64) - 1つ目の「コピー」ボタン
✓ YOUTUBE_OAUTH_TOKEN (Base64) - 2つ目の「コピー」ボタン

よろしくお願いいたします。
```

### 1-2: 認証情報を収集

各チャンネルから以下の情報を収集：

| チャンネル | チャンネルID | YOUTUBE_OAUTH_TOKEN (Base64) |
|-----------|-------------|------------------------------|
| チャンネル1 | `UCrzO_hsFW8vLLy8xFBADfqQ` | `eyJ0b2tlbiI6...`（チャンネル1のトークン）|
| チャンネル2 | `UC3NYX0zN6GySr_hzJHU4tog` | `eyJ0b2tlbiI6...`（チャンネル2のトークン）|
| チャンネル3 | `UChzVx-TG5UcoVJw3xvG_ggw` | `eyJ0b2tlbiI6...`（チャンネル3のトークン）|

⚠️ **重要**: `YOUTUBE_OAUTH_CREDENTIALS` は全チャンネル共通で1つだけ設定します

---

## ステップ2: Render に環境変数を設定

### 2-1: Render ダッシュボードを開く

https://dashboard.render.com → `youtube-clipper` サービス → Environment タブ

### 2-2: 環境変数を追加

以下の環境変数を追加：

```bash
# 共通の認証情報（1つだけ）
YOUTUBE_OAUTH_CREDENTIALS=eyJ3ZWJi...（どのチャンネルの認証でも同じ）

# チャンネル1専用トークン
YOUTUBE_OAUTH_TOKEN_UCrzO_hsFW8vLLy8xFBADfqQ=eyJ0b2tlbiI6...（チャンネル1のトークン）

# チャンネル2専用トークン
YOUTUBE_OAUTH_TOKEN_UC3NYX0zN6GySr_hzJHU4tog=eyJ0b2tlbiI6...（チャンネル2のトークン）

# チャンネル3専用トークン（ぎょうへい先生）
YOUTUBE_OAUTH_TOKEN_UChzVx-TG5UcoVJw3xvG_ggw=eyJ0b2tlbiI6...（チャンネル3のトークン）

# デフォルトトークン（フォールバック用・任意）
YOUTUBE_OAUTH_TOKEN=eyJ0b2tlbiI6...（いずれかのトークン）

# 対象チャンネルID（カンマ区切り）
TARGET_CHANNEL_IDS=UCrzO_hsFW8vLLy8xFBADfqQ,UC3NYX0zN6GySr_hzJHU4tog,UChzVx-TG5UcoVJw3xvG_ggw
```

### 2-3: 保存して再起動

1. **Save Changes** をクリック
2. サービスが自動的に再起動します（約1-2分）

---

## ステップ3: 動作確認

### 3-1: ログを確認

Render ダッシュボード → Logs タブで以下を確認：

```
✓ credentials.json を環境変数から復元しました
✓ チャンネル専用トークンを使用: YOUTUBE_OAUTH_TOKEN_UCrzO_hsFW8vLLy8xFBADfqQ
✓ OAuth トークンを環境変数から復元しました（JSON形式）
✓ YouTube Analytics API v2 が初期化されました
```

### 3-2: Web UIでテスト

1. https://create-cut-out-videos.onrender.com を開く
2. 各チャンネルの動画IDを入力してテスト
3. 見どころが正常に検出されることを確認

---

## 環境変数の命名規則

```bash
# パターン
YOUTUBE_OAUTH_TOKEN_{CHANNEL_ID}

# 例
YOUTUBE_OAUTH_TOKEN_UCrzO_hsFW8vLLy8xFBADfqQ
YOUTUBE_OAUTH_TOKEN_UC3NYX0zN6GySr_hzJHU4tog
YOUTUBE_OAUTH_TOKEN_UChzVx-TG5UcoVJw3xvG_ggw
```

⚠️ **注意**: チャンネルIDは**ハイフン（-）を含む場合があります**が、環境変数名には**そのまま使用**してください。

---

## トラブルシューティング

### エラー1: チャンネル専用トークンが見つからない

```
⚠️ チャンネル専用トークン 'YOUTUBE_OAUTH_TOKEN_UCrzO...' が見つかりません
✓ デフォルトのOAuthトークンを使用
```

**原因**: 環境変数名が間違っているか、設定されていない

**解決策**:
1. 環境変数名を再確認（`YOUTUBE_OAUTH_TOKEN_` + チャンネルID）
2. チャンネルIDに間違いがないか確認
3. Save Changes 後にサービスを再起動

### エラー2: 視聴維持率データが取得できない

```
⚠️ 視聴維持率データが取得できませんでした（OAuth認証が必要）
```

**原因**: そのチャンネルのOAuthトークンが設定されていない

**解決策**:
1. 該当チャンネルのオーナーにOAuth認証を依頼
2. 取得したトークンを環境変数に追加

### エラー3: トークン復元エラー

```
⚠️ トークン復元エラー: ...
```

**原因**: Base64文字列に改行が含まれている

**解決策**:
1. Base64文字列から改行を削除
2. 1行になっていることを確認

---

## まとめ

| 項目 | 説明 |
|------|------|
| **環境変数** | `YOUTUBE_OAUTH_TOKEN_{CHANNEL_ID}` |
| **フォールバック** | `YOUTUBE_OAUTH_TOKEN` |
| **共通認証情報** | `YOUTUBE_OAUTH_CREDENTIALS` |
| **対象チャンネル** | `TARGET_CHANNEL_IDS` |

これで、複数のGoogleアカウントで管理されているチャンネルに対応できます！ 🎉
