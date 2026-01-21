# 「ダウンロードファイルが空」エラーの解決方法

## 🔴 現在の問題

```
✓ YouTubeのCookieを読み込みました
動画ダウンロード開始: https://www.youtube.com/watch?v=5Myn7tCKGVs
ERROR: The downloaded file is empty
```

ダウンロードは開始されるが、ファイルが空のまま完了します。

---

## 🔍 **原因の可能性**

### **1. この動画に制限がある**
- 年齢制限
- 地域制限（日本国外からのアクセス制限）
- プライベート/限定公開設定
- Cookie認証が不十分

### **2. yt-dlpの設定問題**
- フォーマット選択が動画と互換性なし
- タイムアウトが短すぎる
- バッファサイズが小さすぎる

### **3. ネットワーク問題**
- Renderサーバーの帯域幅制限
- YouTubeからのレート制限
- ダウンロード中断

---

## ✅ **解決手順**

### **ステップ1: 別の動画でテスト（最優先）**

この動画（`5Myn7tCKGVs`）に問題がある可能性が高いです。

**推奨テスト動画**:
- 動画ID: `dQw4w9WgXcQ`
- タイトル: Rick Astley - Never Gonna Give You Up
- 特徴: 制限なし、高画質、安定

**テスト手順**:
1. https://create-cut-out-videos.onrender.com にアクセス
2. 動画ID: `dQw4w9WgXcQ` を入力
3. 「🎬 この動画を処理」をクリック
4. Renderログを確認

**期待される結果**:
```
✓ YouTubeのCookieを読み込みました
動画ダウンロード開始: https://www.youtube.com/watch?v=dQw4w9WgXcQ
動画ダウンロード完了: /tmp/.../dQw4w9WgXcQ.mp4  ← 成功！
```

---

### **ステップ2: Cookieを最新化（重要）**

現在のCookieが**動画アクセス権限を持っていない**可能性があります。

#### **2-1: YouTubeで動画を視聴**
1. https://www.youtube.com にアクセス
2. テストする動画を**実際に視聴**（`5Myn7tCKGVs`）
   - これでCookieに動画アクセス履歴が追加されます
3. 動画を**最後まで視聴**（少なくとも1分以上）

#### **2-2: Cookieを再エクスポート**
1. Chrome拡張機能「Get cookies.txt LOCALLY」を開く
2. YouTubeページで「Export」をクリック
3. 新しい `cookies.txt` をダウンロード

#### **2-3: Base64エンコード & Render設定**
```powershell
cd C:\Users\PC_User\Documents\Create-cut-out-videos
git pull origin main

$cookiesPath = "C:\Users\PC_User\Downloads\cookies.txt"
$base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($cookiesPath))
$base64 = $base64 -replace "`r`n", "" -replace "`n", ""
$base64 | Set-Clipboard

Write-Host "✅ 新しいCookieをエンコードしました" -ForegroundColor Green
```

Renderの環境変数 `YOUTUBE_COOKIES` を更新してSave Changes。

---

### **ステップ3: コード改善を適用（自動デプロイ中）**

以下の改善を実装しました：

#### **フォーマット選択を簡素化**
```python
# 変更前
'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

# 変更後（より互換性が高い）
'format': 'best[ext=mp4]/best'
```

#### **タイムアウトとバッファを増強**
```python
'socket_timeout': 60,  # 30 → 60秒
'buffersize': 1024 * 1024,  # 1MB
'http_chunk_size': 10485760,  # 10MB
'retries': 20,  # 10 → 20
```

#### **デバッグログを有効化**
```python
'verbose': True,  # 詳細ログ出力
```

これで、Renderログにyt-dlpの詳細な動作が表示されます。

---

## 🧪 **テスト計画**

### **テスト1: 人気動画（制限なし）**
- 動画ID: `dQw4w9WgXcQ`
- 期待: ✅ ダウンロード成功

### **テスト2: 元の動画（再試行）**
- 動画ID: `5Myn7tCKGVs`
- Cookie更新後に再テスト
- 期待: ✅ ダウンロード成功（Cookie更新により）

### **テスト3: 別の配信動画**
- 「最近の配信から選択」で別の動画を選択
- 期待: ✅ ダウンロード成功

---

## 📊 **判定基準**

### **シナリオA: テスト1が成功**
→ **元の動画に問題がある**
- 解決策: 別の動画を使用するか、Cookie更新

### **シナリオB: テスト1も失敗**
→ **Cookie またはネットワークに問題がある**
- 解決策: Cookie再取得、またはRenderサポートに連絡

### **シナリオC: テスト2が成功（Cookie更新後）**
→ **Cookieの動画アクセス権限が不足していた**
- 解決策: 今後は対象動画を視聴してからCookie取得

---

## 🔍 **デバッグ情報の確認**

Renderログで以下を確認してください：

### **成功時のログ**
```
[download] Destination: /tmp/.../xxxxx.mp4
[download] 100% of 234.56MiB in 01:23
動画ダウンロード完了: /tmp/.../xxxxx.mp4
```

### **失敗時のログ（詳細）**
```
[youtube] Extracting URL: https://www.youtube.com/watch?v=xxxxx
[youtube] xxxxx: Downloading webpage
[youtube] xxxxx: Downloading android player API JSON
ERROR: The downloaded file is empty
```

エラーメッセージの直前に表示される詳細情報を共有してください。

---

## 🎯 **推奨アクション（優先順）**

1. ✅ **今すぐ**: `dQw4w9WgXcQ` でテスト
2. ⚠️ **失敗した場合**: Cookie を再取得
3. 🔄 **Cookie更新後**: `5Myn7tCKGVs` を再テスト
4. 📝 **結果を報告**: 成功/失敗とログを共有

---

## 💡 **補足情報**

### **なぜ6分もかかる？**
- 動画が1時間53分と長い
- Renderサーバーの帯域幅制限
- YouTubeからのダウンロード速度制限

### **空ファイルになる理由**
- ダウンロード途中で中断
- Cookie認証が途中で失効
- YouTubeが大容量ダウンロードを検知してブロック

---

まずは `dQw4w9WgXcQ` でテストして、結果を教えてください！ 🚀
