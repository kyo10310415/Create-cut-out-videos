# YouTube Bot検証エラーの解決方法

## 🔴 問題

```
ERROR: [youtube] 5Myn7tCKGVs: Sign in to confirm you're not a bot. 
This helps protect our community. Learn more
```

RenderサーバーからのアクセスがYouTubeのBot保護によって遮断されています。

---

## ✅ 解決方法: YouTubeのCookieを使用

### **ステップ1: ブラウザからCookieをエクスポート**

#### **Chromeの場合**
1. Chrome拡張機能「**Get cookies.txt LOCALLY**」をインストール
   - https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
2. **YouTube**にログイン: https://www.youtube.com
3. 拡張機能アイコンをクリック
4. 「**Export**」をクリックして `cookies.txt` をダウンロード

#### **Firefoxの場合**
1. アドオン「**cookies.txt**」をインストール
   - https://addons.mozilla.org/firefox/addon/cookies-txt/
2. **YouTube**にログイン: https://www.youtube.com
3. アドオンアイコンをクリック
4. 「**Export**」をクリックして `cookies.txt` をダウンロード

---

### **ステップ2: cookies.txtをBase64エンコード**

#### **Windows PowerShell**
```powershell
cd C:\Users\PC_User\Documents\Create-cut-out-videos
.\encode_cookies.ps1
```

スクリプトが自動的に：
1. `cookies.txt` のパスを聞きます
2. Base64エンコードを実行
3. クリップボードにコピー

#### **Mac/Linux**
```bash
cd ~/Documents/Create-cut-out-videos
base64 cookies.txt | tr -d '\n' > cookies_base64.txt
cat cookies_base64.txt
```

---

### **ステップ3: Renderに環境変数を設定**

1. **Renderダッシュボード**にアクセス: https://dashboard.render.com
2. **youtube-clipper**サービスを選択
3. **Environment**タブをクリック
4. 新しい環境変数を追加：
   - **Key**: `YOUTUBE_COOKIES`
   - **Value**: Base64エンコードした文字列をペースト
5. **Save Changes**をクリック

Renderが自動的に再デプロイを開始します（約5-10分）。

---

### **ステップ4: 動作確認**

再デプロイ完了後、以下をテスト：

1. https://create-cut-out-videos.onrender.com にアクセス
2. 動画IDを入力（例: `5Myn7tCKGVs`）
3. 「🎬 この動画を処理」をクリック
4. **Renderログ**で確認：

```
✓ YouTubeのCookieを読み込みました
動画ダウンロード開始: https://www.youtube.com/watch?v=5Myn7tCKGVs
動画ダウンロード完了: /tmp/...
```

**Bot検証エラーが消えて、正常にダウンロードされるはずです！**

---

## 📝 トラブルシューティング

### **🔴 「Cookieファイルが無効です」エラー**

**原因**: Cookieの形式が間違っている、または期限切れ

**解決方法**:
1. 再度YouTubeにログイン
2. Cookieを再エクスポート
3. Base64エンコードを再実行
4. Renderの環境変数を更新

---

### **🔴 「依然としてBot検証エラーが出る」**

**原因**: Cookieが正しく読み込まれていない

**解決方法**:
1. Renderの**Logs**で以下を確認：
   ```
   ✓ YouTubeのCookieを読み込みました
   ```
2. このメッセージが出ない場合、環境変数 `YOUTUBE_COOKIES` が正しく設定されていません
3. Base64文字列に余分なスペースや改行がないか確認

---

### **🔴 「Cookie読み込みエラー（続行します）」**

**原因**: Base64デコードに失敗

**解決方法**:
1. Base64エンコード時に **BEGIN/END行を削除**したか確認
   - `certutil -encode` を使った場合、手動で削除が必要
   - `encode_cookies.ps1` スクリプトは自動的に処理します
2. 余分な改行やスペースがないか確認

---

## 🔒 セキュリティに関する注意事項

### **Cookieの取り扱い**
- Cookieには**ログイン情報**が含まれています
- 環境変数に設定することで、Render上でのみ使用されます
- GitHubには**絶対にコミットしないでください**
- `.gitignore` に `cookies.txt` を追加済み

### **Cookie の有効期限**
- YouTubeのCookieは通常**数週間～数ヶ月**有効です
- 期限切れの場合、再度エクスポートして設定してください

---

## 📚 技術詳細

### **実装内容**

`src/utils/helpers.py` の `download_video()` 関数を修正：

```python
# 環境変数からCookieを読み込む
youtube_cookies = os.getenv('YOUTUBE_COOKIES')
if youtube_cookies:
    # Base64デコード
    cookies_data = base64.b64decode(youtube_cookies)
    
    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
        f.write(cookies_data)
        cookies_file = f.name
    
    # yt-dlpにCookieファイルを指定
    ydl_opts['cookiefile'] = cookies_file
```

### **yt-dlp のCookieサポート**

yt-dlpは `--cookies` オプションで Netscape形式のCookieファイルをサポートしています：

```bash
yt-dlp --cookies cookies.txt https://www.youtube.com/watch?v=VIDEO_ID
```

このオプションにより、YouTubeはサーバーを**認証済みユーザー**として認識し、Bot検証をスキップします。

---

## 🎯 まとめ

1. ✅ **Cookie エクスポート**: ブラウザからYouTubeのCookieを取得
2. ✅ **Base64 エンコード**: PowerShellスクリプトで自動処理
3. ✅ **Render 設定**: 環境変数 `YOUTUBE_COOKIES` に設定
4. ✅ **再デプロイ**: Renderが自動的に再デプロイ
5. ✅ **テスト**: Bot検証エラーが解消されることを確認

---

## 📖 参考リンク

- **yt-dlp ドキュメント**: https://github.com/yt-dlp/yt-dlp#usage-and-options
- **Chrome拡張機能**: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
- **Firefox アドオン**: https://addons.mozilla.org/firefox/addon/cookies-txt/

---

質問があればお気軽にお問い合わせください！ 🚀
