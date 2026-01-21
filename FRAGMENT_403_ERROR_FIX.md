# フラグメントダウンロード 403エラーの解決方法

## 🔴 問題

```
[download] Got error: HTTP Error 403: Forbidden. Retrying fragment 33...
[download] fragment not found; Skipping fragment 33 ...
ERROR: The downloaded file is empty
```

動画のフラグメント（断片）のダウンロード途中で403エラーが発生し、ファイルが空になります。

---

## 🔍 **根本原因**

### **YouTube のフラグメント配信**
- YouTube は動画を複数の小さなフラグメント（通常5-10秒ごと）に分割
- 各フラグメントに対して認証チェックが行われる
- Cookie の認証が途中で切れると、残りのフラグメントがダウンロードできない

### **なぜCookieが途中で切れる？**
1. **Cookieの有効期限が短い**
   - 無料アカウントのCookieは短命
   - 長時間のダウンロードに耐えられない

2. **YouTubeのBot検出**
   - 連続ダウンロードを検知
   - 途中で認証を再要求

3. **IPアドレスのレート制限**
   - RenderサーバーIPが制限対象
   - 短時間に大量のリクエストを送信

---

## ✅ **解決策**

### **解決策1: Cookie を最新化してすぐに使用（推奨）**

Cookieをエクスポートした直後に、すぐにダウンロードを実行すると成功率が高まります。

#### **手順**
1. **YouTubeをログアウト→再ログイン**
   - https://www.youtube.com
   - 完全にログアウト
   - 再ログイン（新しいセッション）

2. **テスト動画を視聴**
   - `dQw4w9WgXcQ` の動画を開く
   - **最後まで視聴**（3分34秒）
   - これでCookieに視聴履歴が追加される

3. **Cookieをすぐにエクスポート**
   - Chrome拡張機能 →

 Export
   - `cookies.txt` をダウンロード

4. **5分以内にBase64エンコード & Render設定**
   ```powershell
   cd C:\Users\PC_User\Documents\Create-cut-out-videos
   git pull origin main
   
   $cookiesPath = "C:\Users\PC_User\Downloads\cookies.txt"
   $base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($cookiesPath))
   $base64 = $base64 -replace "`r`n", "" -replace "`n", ""
   $base64 | Set-Clipboard
   
   Write-Host "✅ 新しいCookieをエンコードしました" -ForegroundColor Green
   Write-Host "⚡ すぐにRenderに設定してください（5分以内）" -ForegroundColor Yellow
   ```

5. **Renderに設定してすぐにテスト**
   - Renderダッシュボード → youtube-clipper → Environment
   - `YOUTUBE_COOKIES` を更新 → Save Changes
   - 再デプロイ完了後、**すぐに**テスト実行

---

### **解決策2: yt-dlp の認証方式を変更**

フラグメントダウンロードのたびに認証を更新する方式に変更します。

#### **実装の変更**

現在の問題：
- Cookieファイルを最初に1回だけ読み込む
- フラグメントダウンロード中は同じ認証を使い続ける
- 途中で認証が切れても更新されない

改善案：
- OAuth 2.0トークンを使用
- または、yt-dlp の `--extractor-args` で認証を強化

---

### **解決策3: より短い動画でテスト**

長い動画ほどフラグメント数が多く、途中で認証が切れやすいです。

#### **推奨テスト動画**
- **30秒~2分の動画**を選択
- フラグメント数が少ないため、成功率が高い

例:
- YouTube公式の短い動画
- 広告なしの短いクリップ

---

### **解決策4: ytdl-patched を使用（代替ツール）**

yt-dlpの代わりに、より安定した `ytdl-patched` を使用する方法もあります。

---

## 🧪 **テスト計画（優先順）**

### **テスト1: Cookie を最新化してすぐに実行**
1. YouTube再ログイン
2. 動画を視聴
3. Cookie即座にエクスポート
4. 5分以内にRender設定
5. すぐにテスト実行

**期待**: ✅ フラグメント403エラーが消える

---

### **テスト2: 短い動画でテスト**
- 1-2分の動画を選択
- フラグメント数が少ない

**期待**: ✅ ダウンロード成功

---

### **テスト3: 別のアカウントのCookieを試す**
- 別のYouTubeアカウントでログイン
- そのアカウントのCookieをエクスポート

**期待**: ✅ 別アカウントで成功する可能性

---

## 📊 **技術的な詳細**

### **フラグメントダウンロードの仕組み**

```
動画URL
↓
プレイリスト取得（m3u8）
↓
フラグメントリスト
  - fragment_1.ts (0-5秒)
  - fragment_2.ts (5-10秒)
  - fragment_3.ts (10-15秒)
  ...
  - fragment_32.ts ← ここで403エラー
  - fragment_33.ts ← ダウンロードできない
```

### **ログから読み取れること**

```
[youtube] dQw4w9WgXcQ: Downloading m3u8 information
[info] dQw4w9WgXcQ: Downloading 1 format(s): 96
[download] Got error: HTTP Error 403: Forbidden. Retrying fragment 32...
```

- ✅ m3u8プレイリスト取得成功
- ✅ フォーマット選択成功
- ✅ 最初の31フラグメントダウンロード成功
- ❌ フラグメント32以降で認証エラー

---

## 💡 **なぜ最初は成功して途中で失敗する？**

1. **Cookieの短い有効期限**
   - 最初は有効
   - 数十秒後に期限切れ

2. **YouTubeの動的な認証チェック**
   - 最初は緩い
   - 途中から厳しくなる

3. **Bot検出のしきい値**
   - 最初のリクエストは許可
   - 連続リクエストがしきい値を超えると拒否

---

## 🎯 **推奨アクション（今すぐ）**

1. ✅ **YouTubeを再ログイン**
2. ✅ **テスト動画を最後まで視聴**
3. ✅ **Cookie をすぐにエクスポート**
4. ✅ **5分以内にRenderに設定**
5. ✅ **すぐにテスト実行**

**この手順で、Cookieが最も新鮮な状態で使用でき、成功率が最も高くなります。**

---

## 🔍 **代替アプローチ（高度）**

### **OAuth 2.0トークンを使用**
- YouTube Data API v3のOAuthトークン
- Cookieより長期間有効
- 実装が複雑

### **yt-dlp の代替ツール**
- `youtube-dl` (古いが安定)
- `ytdl-patched` (コミュニティパッチ版)
- `gallery-dl` (別アプローチ)

---

まずは**解決策1（Cookie最新化してすぐ使用）**を試してください！ 🚀
