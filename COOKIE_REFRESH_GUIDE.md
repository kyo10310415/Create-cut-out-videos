# YouTube Cookie 再取得ガイド

## 🔴 HTTP 403 Forbidden エラーの解決

現在、以下のエラーが発生しています：

```
✓ YouTubeのCookieを読み込みました
ERROR: unable to download video data: HTTP Error 403: Forbidden
```

これは**Cookieの有効期限切れ**または**YouTubeの仕様変更**が原因です。

---

## ✅ 解決手順

### **ステップ1: YouTubeに再ログイン**

1. **YouTubeにアクセス**: https://www.youtube.com
2. **ログアウト**して**再ログイン**
   - これにより新しいCookieが生成されます
3. ログイン後、**動画を1つ視聴**
   - これでCookieが完全にアクティブになります

---

### **ステップ2: Cookieを再エクスポート**

#### **Chromeの場合**
1. Chrome拡張機能「**Get cookies.txt LOCALLY**」を開く
2. YouTubeページで拡張機能アイコンをクリック
3. 「**Export**」をクリック
4. 新しい `cookies.txt` がダウンロードされます

#### **Firefoxの場合**
1. アドオン「**cookies.txt**」を開く
2. YouTubeページでアドオンアイコンをクリック
3. 「**Export**」をクリック
4. 新しい `cookies.txt` がダウンロードされます

---

### **ステップ3: Base64エンコード（再実行）**

```powershell
cd C:\Users\PC_User\Documents\Create-cut-out-videos

# 最新コードを取得
git pull origin main

# 新しいcookies.txtをエンコード
$cookiesPath = "C:\Users\PC_User\Downloads\cookies.txt"
$base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($cookiesPath))
$base64 = $base64 -replace "`r`n", "" -replace "`n", ""
$base64 | Set-Clipboard

Write-Host "✅ 新しいCookieをエンコードしました" -ForegroundColor Green
Write-Host "✅ クリップボードにコピーしました" -ForegroundColor Green
Write-Host ""
Write-Host "次: Renderの環境変数 YOUTUBE_COOKIES を更新してください" -ForegroundColor Cyan
```

---

### **ステップ4: Renderの環境変数を更新**

1. **Renderダッシュボード**: https://dashboard.render.com
2. **youtube-clipper**サービスを選択
3. **Environment**タブをクリック
4. **YOUTUBE_COOKIES**の値を更新：
   - 既存の値を削除
   - クリップボードの新しい値をペースト
5. **Save Changes**をクリック

Renderが自動的に再デプロイします（約5-10分）。

---

## 🔍 **Cookie有効性の確認方法**

### **確認ポイント**

Cookieファイルの内容を確認（メモ帳で開く）：

```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1748025600	YSC	xxxxx
.youtube.com	TRUE	/	FALSE	1748025600	VISITOR_INFO1_LIVE	xxxxx
.youtube.com	TRUE	/	TRUE	1748025600	LOGIN_INFO	xxxxx
```

重要なCookie：
- **LOGIN_INFO**: ログイン情報（必須）
- **VISITOR_INFO1_LIVE**: 訪問者情報
- **PREF**: 設定情報
- **SID**: セッションID

これらが存在しない場合、ログインが不完全です。

---

## 💡 **追加のトラブルシューティング**

### **問題A: Cookieエクスポート後も403エラー**

**原因**: YouTubeアカウントが制限されている

**解決方法**:
1. **別のYouTubeアカウント**でログイン
2. そのアカウントのCookieをエクスポート
3. Renderに設定

---

### **問題B: 「This action is not supported」エラー**

**原因**: Cookieファイルの形式が間違っている

**解決方法**:
1. Chrome拡張機能を**最新版**にアップデート
2. Cookieを再エクスポート
3. ファイルの最初の行が `# Netscape HTTP Cookie File` であることを確認

---

### **問題C: 特定の動画だけダウンロードできない**

**原因**: 動画に年齢制限や地域制限がある

**解決方法**:
1. **別の動画**でテスト（例: `dQw4w9WgXcQ`）
2. 制限のない動画を選択

---

## 🎯 **期待される結果**

Cookie更新後、Renderログで以下が表示されるはずです：

```
✓ YouTubeのCookieを読み込みました
動画ダウンロード開始: https://www.youtube.com/watch?v=xxxxx
動画ダウンロード完了: /tmp/.../xxxxx.mp4  ← 成功！
🎵 音声を解析して盛り上がりを検出します
🎵 音声解析完了: XX 個の区間を分析
✅ 検出された見どころ: X個
```

---

## 📝 **まとめ**

1. ✅ **YouTubeに再ログイン**
2. ✅ **Cookieを再エクスポート**
3. ✅ **Base64エンコード**
4. ✅ **Renderの環境変数を更新**
5. ✅ **再デプロイ後テスト**

---

これで403エラーが解消されるはずです！ 🚀
