# 🔐 OAuth認証 - 簡単セットアップガイド

## 📋 概要

**ユーザーA（チャンネル所有者）がブラウザで簡単に認証できる**Webベースの認証システムを実装しました。

### メリット
- ✅ ユーザーAのパソコンに Python不要
- ✅ ブラウザだけで完結
- ✅ 自動的にBase64エンコード
- ✅ コピー＆ペーストだけで設定完了

---

## 🚀 セットアップ手順

### ステップ1: OAuth設定アプリをRenderにデプロイ

#### 1-1. 新しいWebサービスを作成

1. [Render](https://render.com/)にログイン
2. "New +" → "Web Service"を選択
3. GitHubリポジトリ `Create-cut-out-videos` を選択

#### 1-2. サービス設定

| 項目 | 値 |
|-----|-----|
| **Name** | `youtube-clipper-oauth-setup` |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python oauth_setup.py` |
| **Instance Type** | Free |

#### 1-3. 環境変数を設定

| 環境変数名 | 値 | 説明 |
|-----------|-----|------|
| `OAUTH_REDIRECT_URI` | `https://youtube-clipper-oauth-setup.onrender.com/oauth2callback` | OAuth リダイレクトURI |

**注意**: `youtube-clipper-oauth-setup` の部分は実際のサービス名に置き換えてください。

#### 1-4. credentials.jsonをアップロード

1. Renderのダッシュボード → `youtube-clipper-oauth-setup` サービス
2. **Files** タブ（または **Shell** タブ）
3. `credentials.json` をアップロード（または内容をペースト）

**方法A: Shellでアップロード**:
```bash
# Renderのシェルを開く
cat > credentials.json << 'EOF'
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "youtube-clipper",
    ...
  }
}
EOF
```

**方法B: 環境変数で設定**:
```bash
# credentials.jsonをBase64エンコード（ローカルPC）
base64 -w 0 credentials.json > credentials_base64.txt

# Renderの環境変数に追加
GOOGLE_OAUTH_CREDENTIALS=<credentials_base64.txtの内容>
```

そして `oauth_setup.py` を修正:
```python
# credentials.jsonを環境変数から復元
if os.getenv('GOOGLE_OAUTH_CREDENTIALS'):
    credentials_base64 = os.getenv('GOOGLE_OAUTH_CREDENTIALS')
    credentials_bytes = base64.b64decode(credentials_base64)
    with open(CREDENTIALS_FILE, 'wb') as f:
        f.write(credentials_bytes)
```

---

### ステップ2: Google Cloud Consoleでリダイレクト URIを追加

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクトを選択
3. **APIとサービス** → **認証情報**
4. OAuth 2.0 クライアントIDをクリック
5. **承認済みのリダイレクト URI** に追加:
   ```
   https://youtube-clipper-oauth-setup.onrender.com/oauth2callback
   ```
6. **保存**

---

### ステップ3: ユーザーAに認証URLを送信

#### URLを送信
```
https://youtube-clipper-oauth-setup.onrender.com
```

#### ユーザーAへのメッセージ例
```
【YouTube Clipper OAuth認証のお願い】

以下のURLにアクセスして、認証を完了してください：
https://youtube-clipper-oauth-setup.onrender.com

手順:
1. 「認証を開始」ボタンをクリック
2. あなたのGoogleアカウントでログイン
3. すべての権限を許可
4. 画面に表示される2つのコードをコピー
5. 私（ユーザーB）に送信

所要時間: 約3分
```

---

### ステップ4: 認証情報をRenderに設定（ユーザーBが実行）

ユーザーAから送られてきた2つのBase64コードを使用：

1. Renderダッシュボード: https://dashboard.render.com
2. `youtube-clipper` サービス → **Environment** タブ
3. 以下の環境変数を追加:

| 環境変数名 | 値 |
|-----------|-----|
| `YOUTUBE_OAUTH_CREDENTIALS` | ユーザーAから受け取ったコード1 |
| `YOUTUBE_OAUTH_TOKEN` | ユーザーAから受け取ったコード2 |
| `GEMINI_API_KEY` | あなたのGemini APIキー |

4. **Save Changes** → **Restart Service**

---

### ステップ5: テスト

1. `youtube-clipper` サービスのログを確認:
   ```
   ✓ credentials.json を環境変数から復元しました
   ✓ OAuth トークンを環境変数から復元しました
   ✓ YouTube Analytics API v2 が初期化されました
   ✓ Gemini API初期化完了
   ```

2. 動画IDで見どころ検出をテスト:
   ```
   動画ID: 5Myn7tCKGVs
   期待結果: 🤖 Gemini APIで見どころを分析中...
   ```

---

## 🔧 トラブルシューティング

### エラー: credentials.json が見つかりません

**原因**: `credentials.json` がRenderにアップロードされていない

**対処**:
1. Renderのシェルを開く
2. `ls -la` で確認
3. ファイルがない場合は、上記の方法でアップロード

### エラー: redirect_uri_mismatch

**原因**: Google Cloud Consoleのリダイレクト URIが間違っている

**対処**:
1. Google Cloud Console → 認証情報
2. リダイレクト URIを確認:
   ```
   https://youtube-clipper-oauth-setup.onrender.com/oauth2callback
   ```
3. 正確に一致しているか確認（末尾の `/` に注意）

### エラー: セッションのstateが見つかりません

**原因**: Renderの複数インスタンスでセッションが共有されていない

**対処**:
1. Render の Instance Type を **Free** または **Starter** に設定
2. 複数インスタンスを使わない

---

## 💡 代替方法: APIキーのみで運用

視聴維持率データが不要な場合は、**APIキーのみで運用**することも可能です。

### メリット
- ✅ OAuth認証不要
- ✅ セットアップが簡単

### デメリット
- ❌ 視聴維持率データが取得できない
- ❌ 見どころ検出の精度が低い

### 実装方法

環境変数を変更:
```env
# OAuth認証情報を削除
# YOUTUBE_OAUTH_CREDENTIALS=...
# YOUTUBE_OAUTH_TOKEN=...

# APIキーのみで運用
YOUTUBE_API_KEY=your_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Gemini APIに視聴維持率なしで分析させる
USE_GEMINI_WITHOUT_ANALYTICS=true
```

コードを修正:
```python
# run_processor.py
if os.getenv('USE_GEMINI_WITHOUT_ANALYTICS') == 'true':
    # 視聴維持率データなしでGemini APIを使用
    retention_data = None
else:
    # 通常の処理
    retention_data = self.youtube_api.get_audience_retention(video_id)
```

---

## 🎯 推奨アプローチ

### 最もおすすめ: Webベースの認証（本ガイド）

- ✅ ユーザーAの手間が最小
- ✅ ブラウザだけで完結
- ✅ 視聴維持率データが取得できる
- ✅ 見どころ検出の精度が高い

### 次点: APIキーのみ（簡易版）

- ✅ セットアップが簡単
- ⚠️ 視聴維持率データなし
- ⚠️ 精度は中程度

---

## 質問

1. **Webベースの認証を実装しますか？**
2. **それとも、APIキーのみで運用しますか？**

どちらがいいですか？ 🚀
