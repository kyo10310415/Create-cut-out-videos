# 🔧 テストモード トラブルシューティング

## 問題: ボタンをクリックしても反応しない

### 修正内容

**問題**: JavaScriptの関数重複エラー
- `updateLog`関数が2回定義されていた
- これによりJavaScriptエラーが発生し、ボタンが機能しなかった

**修正**: 
- ✅ 重複した`updateLog`関数を削除
- ✅ デバッグ用のconsole.logを追加
- ✅ エラーハンドリングを強化

### 確認方法

#### 1. ブラウザのデベロッパーツールで確認

**Chrome/Edge/Firefox**:
1. F12キーを押す
2. 「Console」タブを開く
3. ボタンをクリック
4. 以下のようなログが表示されるはず:
   ```
   testSingleVideo called
   Video ID: i4FJ6hhguis
   Processing video: i4FJ6hhguis
   Response status: 200
   Response data: {success: true, ...}
   ```

#### 2. エラーがある場合

**赤いエラーメッセージが表示される場合**:
```
Uncaught ReferenceError: testSingleVideo is not defined
```
→ ページをリロード（Ctrl+F5で強制リロード）

```
Failed to fetch
```
→ Renderがデプロイ中、またはサービスが停止している

### 動作確認手順

1. **ページリロード**
   - Ctrl+F5（強制リロード）
   - キャッシュをクリア

2. **動画IDを入力**
   ```
   i4FJ6hhguis
   ```

3. **ボタンをクリック**
   - 「🎬 この動画を処理」をクリック

4. **確認ダイアログが表示される**
   ```
   動画ID: i4FJ6hhguis
   この動画を処理しますか？テストのため時間がかかります。
   ```

5. **「OK」をクリック**
   - ローディング表示が出る
   - 処理が開始される

## デバッグ方法

### ステップ1: Renderのログを確認

```bash
# Renderダッシュボード → サービス選択 → Logs
```

以下のようなログが表示されるはず:
```
127.0.0.1 - - [18/Jan/2026 10:40:05] "POST /api/test-video HTTP/1.1" 200 -
2026-01-18 10:40:05 - youtube_clipper - INFO - 動画処理開始: i4FJ6hhguis
```

### ステップ2: JavaScriptコンソールを確認

ブラウザのコンソール（F12）で以下を実行:

```javascript
// 関数が定義されているか確認
typeof testSingleVideo
// 結果: "function" であればOK

// 要素が存在するか確認
document.getElementById('test-video-id')
// 結果: <input...> であればOK

// 手動で関数を呼び出し
testSingleVideo()
```

### ステップ3: ネットワークタブを確認

1. F12 → Network タブ
2. ボタンをクリック
3. `/api/test-video` のリクエストを確認
4. Status が 200 であればOK

## よくある問題と解決策

### 問題1: 「動画IDを入力してください」と表示される

**原因**: 入力欄が空

**解決策**:
- 動画IDを正しく入力する
- 例: `i4FJ6hhguis`（11文字）

### 問題2: ボタンクリック後、何も起こらない

**原因**: JavaScriptエラー

**解決策**:
1. ページをリロード（Ctrl+F5）
2. ブラウザのキャッシュをクリア
3. F12でコンソールエラーを確認

### 問題3: 「Failed to fetch」エラー

**原因**: サーバーに接続できない

**解決策**:
1. Renderのサービスが起動しているか確認
2. URLが正しいか確認（https://create-cut-out-videos.onrender.com）
3. Renderのログでエラーを確認

### 問題4: 処理が開始されるが、すぐにエラー

**原因**: APIキーが設定されていない

**解決策**:
1. Renderの環境変数を確認
2. `YOUTUBE_API_KEY`が設定されているか確認
3. APIキーが有効か確認

### 問題5: ローディング表示が消えない

**原因**: サーバー側で処理が失敗している

**解決策**:
1. Renderのログを確認
2. エラーメッセージを探す
3. タイムアウトの可能性（Standardプランにアップグレード）

## 再デプロイ後の確認

GitHubにプッシュ後、Renderが自動的に再デプロイします。

### 確認手順

1. **Renderダッシュボードを開く**
   - サービス: youtube-clipper
   - Events タブで「Deploy succeeded」を確認

2. **URLにアクセス**
   ```
   https://create-cut-out-videos.onrender.com
   ```

3. **ページを強制リロード**
   - Ctrl+F5（Windows/Linux）
   - Cmd+Shift+R（Mac）

4. **F12でコンソールを開く**
   - エラーがないことを確認

5. **テスト実行**
   - 動画ID入力
   - ボタンクリック
   - コンソールログを確認

## テストに使える動画ID

### 短い動画（テスト推奨）

```
i4FJ6hhguis  # 約10分
dQw4w9WgXcQ  # 約4分（有名な動画）
```

### 実際の配信動画

「最近の配信から選択」ボタンで取得できます。

## サポート

問題が解決しない場合:

1. **Renderのログ全文を確認**
2. **ブラウザのコンソールのエラーをコピー**
3. **再現手順を記録**

---

**最終更新**: 2026-01-18  
**修正内容**: updateLog関数の重複削除、デバッグログ追加
