# YouTube Analytics API v2 セットアップガイド（簡易版）

## 🎯 完了した作業

✅ credentials.jsonのダウンロード完了

## 📋 次のステップ

### ステップ1: ローカル環境でOAuth認証

**前提条件:**
- credentials.jsonをプロジェクトルートに配置
- .envファイルにYOUTUBE_API_KEYが設定されている

**実行方法:**

```bash
# 1. プロジェクトディレクトリに移動
cd /path/to/Create-cut-out-videos

# 2. credentials.jsonを配置
# （ダウンロードしたファイルをプロジェクトルートにコピー）

# 3. 認証スクリプトを実行
python authenticate_oauth.py
```

**認証フロー:**
1. ブラウザが自動的に開きます
2. **API設定アカウント**（現在のYouTube API KEYを設定したアカウント）でログイン
3. 「このアプリは確認されていません」と表示される場合:
   - 「詳細」をクリック
   - 「（アプリ名）に移動（安全ではないページ）」をクリック
4. 権限リクエストを確認して「**許可**」をクリック

**成功すると:**
- `token.pickle` ファイルが生成されます
- テストとして視聴維持率データを取得します

---

### ステップ2: token.pickleをBase64エンコード

```bash
# Macの場合
base64 token.pickle

# Linuxの場合
base64 token.pickle

# Windowsの場合
certutil -encode token.pickle token_base64.txt
# token_base64.txtの内容をコピー
```

出力された文字列を**すべてコピー**（改行を含む）

---

### ステップ3: Renderに環境変数を設定

Renderダッシュボードで以下を設定:

```bash
# 1. credentials.jsonをBase64エンコード
base64 credentials.json

# 2. Renderの環境変数に追加
YOUTUBE_OAUTH_CREDENTIALS=<credentials.jsonのBase64>
YOUTUBE_OAUTH_TOKEN=<token.pickleのBase64>
```

**設定方法:**
1. https://dashboard.render.com にアクセス
2. `youtube-clipper` サービスを選択
3. Environment → Add Environment Variable
4. 上記2つの環境変数を追加
5. Save Changes

---

### ステップ4: GitHubにプッシュ

```bash
cd /path/to/Create-cut-out-videos
git pull origin main
git add .
git commit -m "Add YouTube Analytics API v2 integration"
git push origin main
```

Renderが自動的に再デプロイを開始します（約5-10分）

---

### ステップ5: 動作確認

デプロイ完了後、テストモードで確認:

```
1. https://create-cut-out-videos.onrender.com にアクセス
2. 動画IDを入力（前回と同じでOK）
3. 「🎬 この動画を処理」をクリック
4. ログを確認:
   ✓ YouTube Analytics API v2 が初期化されました
   ✓ 視聴維持率データを取得: XX ポイント
   ✓ 視聴維持率データを統合します
   ✓ 検出された見どころ: X個（前回より増える）
```

---

## 🐛 トラブルシューティング

### 認証が失敗する

**エラー: "このアプリは確認されていません"**
→ 「詳細」→「（アプリ名）に移動」をクリックして続行

**エラー: "アクセスが拒否されました"**
→ YouTube Studioで権限が正しく付与されているか確認

### 視聴維持率データが取得できない

**原因1: OAuth認証が完了していない**
→ ローカルで `authenticate_oauth.py` を実行

**原因2: 動画が公開直後**
→ 数日経った配信で試す

**原因3: Analytics APIにアクセス権限がない**
→ YouTube Studioで「管理者（完全）」権限を確認

### Renderログの確認

```
Renderダッシュボード → youtube-clipper → Logs

確認すべきログ:
✓ credentials.json を環境変数から復元しました
✓ OAuth トークンを環境変数から復元しました
✓ YouTube Analytics API v2 が初期化されました
```

---

## 📊 期待される効果

### Before（修正前）
- ❌ 視聴維持率データなし
- ❌ コメント0件 → 見どころ検出失敗
- ⚠️ 音声解析のみで検出

### After（修正後）
- ✅ **視聴維持率データを使用**（最も正確）
- ✅ コメント + 音声 + **視聴維持率** で総合判定
- ✅ 検出精度が大幅向上

---

## 📞 サポート

問題が発生した場合は、以下の情報を共有してください:

1. **認証エラーのスクリーンショット**
2. **Renderログ**（最新50行）
3. **ローカルで実行した `authenticate_oauth.py` の出力**

---

**最終更新**: 2026-01-18  
**ステータス**: ✅ コード実装完了・認証待ち
