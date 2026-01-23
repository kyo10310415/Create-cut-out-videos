# Gemini API セットアップガイド

## 🔴 現在のエラー

```
404 Client Error: Not Found for url: 
https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent
```

**原因**: Generative Language API が有効化されていない

---

## ✅ 解決手順

### **方法1：Google AI Studio（推奨・簡単）**

1. **Google AI Studioにアクセス**
   ```
   https://aistudio.google.com/app/apikey
   ```

2. **APIキーを作成**
   - 「Create API key」をクリック
   - プロジェクトを選択（または新規作成）
   - APIキーをコピー

3. **重要：APIが自動的に有効化される**
   - Google AI Studioでキーを作成すると、Generative Language APIが自動的に有効化されます

---

### **方法2：Google Cloud Console（詳細設定）**

1. **Google Cloud Consoleにアクセス**
   ```
   https://console.cloud.google.com
   ```

2. **プロジェクトを選択**
   - 既存：`create-cut-out-videos`
   - または新規作成

3. **APIを有効化**
   - 左メニュー → 「APIとサービス」 → 「ライブラリ」
   - 検索: "Generative Language API"
   - 「有効にする」をクリック

4. **APIキーを作成**
   - 「認証情報」タブ
   - 「認証情報を作成」 → 「APIキー」
   - キーをコピー

5. **APIキーを制限（セキュリティ向上）**
   - キーを編集
   - 「APIの制限」 → 「キーを制限」
   - 「Generative Language API」のみを選択
   - 保存

---

## 🔧 Renderの環境変数を更新

1. **Renderダッシュボードを開く**
   ```
   https://dashboard.render.com
   ```

2. **サービスを選択**
   - `Create-cut-out-videos`

3. **Environment タブ**
   - `GEMINI_API_KEY` を探す
   - 新しいAPIキーに更新
   - **Save Changes** をクリック

4. **自動再起動を待つ**
   - 約1-2分で再起動完了

---

## ✅ 動作確認

### **期待されるログ**

```
✓ Gemini API初期化完了
🤖 Gemini APIで見どころを分析中...
✓ Gemini APIから 10 個の見どころを取得
```

### **エラーが消えること**

```
⚠️ Gemini API使用エラー: 404 Client Error  ← これが消える
```

---

## 💡 トラブルシューティング

### **エラー: 403 Forbidden**
- **原因**: APIキーの権限不足
- **解決**: APIキーの制限を確認、Generative Language APIが許可されているか

### **エラー: 429 Too Many Requests**
- **原因**: レート制限超過
- **解決**: 無料枠は15リクエスト/分、有料プランを検討

### **エラー: 400 Bad Request**
- **原因**: リクエスト形式が間違っている
- **解決**: コードを確認（通常は発生しない）

---

## 📊 料金について

### **無料枠（推奨）**

| モデル | 無料枠 | 超過後の料金 |
|--------|--------|--------------|
| **Gemini 1.5 Flash** | 15 RPM | $0.075/1M入力トークン |
| | 1M トークン/日 | $0.30/1M出力トークン |

### **使用量の目安**

- 1動画の分析: 約5,000-10,000トークン
- 月間100動画: 約500,000-1,000,000トークン
- **月間コスト**: 無料枠内の可能性が高い

---

## 🎯 次のステップ

1. ✅ 新しいAPIキーを取得
2. ✅ Renderの環境変数を更新
3. ✅ サービス再起動を待つ
4. ✅ テスト動画で動作確認
5. ✅ ログでエラーが消えたことを確認

---

## 📞 サポート

- Google AI Studio: https://aistudio.google.com
- Gemini API ドキュメント: https://ai.google.dev/docs
- Google Cloud Console: https://console.cloud.google.com
