# YouTube 切り抜き動画自動生成システム

YouTubeの配信動画から見どころを自動検出し、10分程度のハイライト動画を生成するシステムです。

## 📋 プロジェクト概要

- **プロジェクト名**: YouTube Clipper
- **目的**: YouTubeライブ配信の切り抜き動画を自動生成
- **処理時間**: 1時間の配信から10分の切り抜き動画を生成（約30-60分）

## ✨ 主な機能

### 1. 見どころ自動検出
- ✅ **AI powered分析（Gemini API）**: AIが動画内容、コメント、視聴維持率を総合的に分析
- ✅ コメント密度分析
- ✅ 同接数推定
- ✅ 視聴維持率スコアリング
- ✅ 総合スコアによる見どころ判定
- 🔄 **フォールバック対応**: Gemini APIが利用不可の場合は従来の方法で検出

### 2. 動画編集（Lesson 5準拠）
- ✅ セグメント切り抜きと結合
- ✅ ジャンプカット（無音部分の自動削除）
- ✅ テンポ＆リズム調整（7秒ルール準拠）
- ✅ BGM追加（オプション）

### 3. テロップ生成（Lesson 4準拠）
- ✅ Whisperによる音声認識
- ✅ 自動字幕生成
- ✅ 可読性原則に基づくデザイン
  - 白文字 + 黒縁取り（明暗差最大化）
  - 半透明黒背景（ベース）
  - 大きめフォント（48px）

### 4. YouTube連携
- ✅ YouTube Data API v3による情報取得
- ✅ YouTube Analytics API v2による視聴維持率取得
- ✅ コメント・統計データの取得
- ✅ 動画ダウンロード（yt-dlp）

## 🏗️ システムアーキテクチャ

```
【認証情報の分離】
ユーザーA（チャンネル所有者）
    ↓ OAuth認証情報
ユーザーB（システム管理者）の環境
    ↓
GitHub (コード管理)
    ↓
Render (デプロイ & 実行)
    ├─ Web Service (ダッシュボード)
    ├─ Background Worker (動画処理)
    └─ Environment Variables
        ├─ YOUTUBE_OAUTH_CREDENTIALS (ユーザーA)
        ├─ YOUTUBE_OAUTH_TOKEN (ユーザーA)
        └─ GEMINI_API_KEY (ユーザーB) ← 料金はユーザーB持ち
    ↓
YouTube API (データ取得 - ユーザーAの権限で実行)
    ↓
Gemini API (AI分析 - ユーザーBのAPIキーで実行)
    ↓
FFmpeg (動画編集)
    ↓
Whisper (音声認識)
    ↓
出力動画 (output/)
```

### コスト構造
- **YouTube API**: 無料（ユーザーAのチャンネルデータを取得）
- **Gemini API**: ユーザーB（システム管理者）のAPIキーで課金
  - Gemini 1.5 Flash: 非常に安価（多くの場合、無料枠内）
  - 料金はすべてユーザーBに紐づく

## 📁 プロジェクト構造

```
youtube-clipper/
├── src/
│   ├── api/
│   │   └── youtube_api.py          # YouTube API連携
│   ├── processor/
│   │   └── analytics.py             # アナリティクス分析
│   ├── editor/
│   │   └── video_editor.py          # FFmpeg動画編集
│   ├── subtitle/
│   │   └── subtitle_generator.py    # 字幕生成
│   ├── ai/
│   │   └── gemini_client.py         # 🆕 Gemini API統合
│   └── utils/
│       └── helpers.py               # ユーティリティ
├── app.py                           # Flaskダッシュボード
├── run_processor.py                 # メイン処理スクリプト
├── requirements.txt                 # Python依存関係
├── render.yaml                      # Renderデプロイ設定
├── .env.example                     # 環境変数サンプル
├── .gitignore                       # Git除外設定
└── README.md                        # このファイル
```

## 🚀 セットアップ手順

### 1. Google Cloud Consoleの設定

#### YouTube API v3の設定
1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. YouTube Data API v3を有効化
3. YouTube Analytics API v2を有効化（視聴維持率データの取得に必要）
4. OAuth 2.0 認証情報を作成
   - アプリケーション種類: デスクトップアプリ
   - `credentials.json`をダウンロード

#### Gemini APIの設定（オプションだが推奨）
1. [Google AI Studio](https://aistudio.google.com/)にアクセス
2. **Get API Key**をクリック
3. APIキーをコピー
4. 料金プラン:
   - **Gemini 1.5 Flash**: 非常に安価、無料枠あり
   - 詳細: https://ai.google.dev/pricing

**注意**: Gemini APIキーは**ユーザーB（システム管理者）**のアカウントで取得してください。YouTube APIはユーザーA（チャンネル所有者）の権限で実行されますが、Gemini APIの料金はユーザーBに課金されます。

### 2. ローカル環境のセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/kyo10310415/Create-cut-out-videos.git
cd Create-cut-out-videos

# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt

# FFmpegをインストール（システム要件）
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# macOS:
brew install ffmpeg

# Windows:
# https://ffmpeg.org/download.html からダウンロード

# 環境変数を設定
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

### 3. OAuth認証の設定（ユーザーA: チャンネル所有者が実行）

**重要**: この手順は**チャンネル所有者（ユーザーA）**が自分のパソコンで実行してください。

#### 手順1: OAuth認証を実行

```bash
# ユーザーAのパソコンで実行
python authenticate_oauth.py
```

1. ブラウザが開きます
2. **ユーザーA（チャンネル所有者）のGoogleアカウント**でログイン
3. 権限を承認:
   - YouTube アカウントの表示
   - YouTube Analytics レポートの閲覧
4. 「認証されていません」と表示された場合:
   - **詳細**をクリック
   - **（unsafe）に移動**をクリック
5. すべての権限を**許可**
6. 認証完了後、`token.pickle`ファイルが生成されます

#### 手順2: Base64エンコード（改行なし）

**Windows (PowerShell)**:
```powershell
# credentials.json
$bytes = [System.IO.File]::ReadAllBytes("credentials.json")
$base64 = [System.Convert]::ToBase64String($bytes)
$base64 | Out-File -FilePath credentials_base64.txt -NoNewline

# token.pickle
$bytes = [System.IO.File]::ReadAllBytes("token.pickle")
$base64 = [System.Convert]::ToBase64String($bytes)
$base64 | Out-File -FilePath token_base64.txt -NoNewline
```

**Mac/Linux**:
```bash
# credentials.json
base64 -w 0 credentials.json > credentials_base64.txt

# token.pickle
base64 -w 0 token.pickle > token_base64.txt
```

#### 手順3: ファイルをユーザーBに送信

- `credentials_base64.txt`
- `token_base64.txt`

**注意**: これらのファイルには認証情報が含まれています。安全な方法で送信してください。

### 4. 環境変数の設定（ユーザーB: システム管理者が実行）

`.env`ファイルを編集：

```env
# YouTube API認証情報（ユーザーA: チャンネル所有者）
YOUTUBE_API_KEY=your_api_key_here
YOUTUBE_OAUTH_CREDENTIALS=base64_encoded_credentials_json
YOUTUBE_OAUTH_TOKEN=base64_encoded_token_pickle

# Gemini API認証情報（ユーザーB: システム管理者）
GEMINI_API_KEY=your_gemini_api_key_here

# 対象チャンネルID（カンマ区切り）
TARGET_CHANNEL_IDS=UCrzO_hsFW8vLLy8xFBADfqQ

# 処理設定
CLIP_DURATION_TARGET=600           # 10分
MIN_HIGHLIGHT_SCORE=0.7            # 見どころ閾値
JUMP_CUT_ENABLED=true              # ジャンプカット有効化

# 字幕設定（Lesson 4準拠）
SUBTITLE_FONT_SIZE=48
SUBTITLE_COLOR=white
SUBTITLE_OUTLINE_COLOR=black
SUBTITLE_OUTLINE_WIDTH=3
```

## 💻 使用方法

### ローカルで実行

#### 1. ダッシュボードを起動

```bash
python app.py
```

ブラウザで `http://localhost:10000` にアクセス

#### 2. コマンドラインで実行

```bash
# 全チャンネルを処理
python run_processor.py
```

### Renderにデプロイ

#### 1. GitHubリポジトリにプッシュ

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

#### 2. Renderで新しいサービスを作成

1. [Render](https://render.com/)にログイン
2. "New +" → "Web Service"を選択
3. GitHubリポジトリを接続
4. 設定:
   - **Build Command**: `apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Plan**: Standard ($25/月) 推奨

#### 3. 環境変数を設定

Renderのダッシュボードで以下の環境変数を追加：

**YouTube API（ユーザーA: チャンネル所有者の認証情報）**:
- `YOUTUBE_API_KEY`
- `YOUTUBE_OAUTH_CREDENTIALS` ← `credentials_base64.txt`の内容
- `YOUTUBE_OAUTH_TOKEN` ← `token_base64.txt`の内容
- `TARGET_CHANNEL_IDS`

**Gemini API（ユーザーB: システム管理者の認証情報）**:
- `GEMINI_API_KEY` ← Google AI Studioで取得したAPIキー

**処理設定**:
- `CLIP_DURATION_TARGET=600`
- `MIN_HIGHLIGHT_SCORE=0.7`
- その他必要な設定

#### 4. Cron Jobを設定（定期実行）

1. "New +" → "Cron Job"を選択
2. 設定:
   - **Command**: `python run_processor.py`
   - **Schedule**: `0 2 * * *` (毎日午前2時)

## 💰 コスト試算

### Render料金（ユーザーB持ち）

| 処理頻度 | プラン | 月額 |
|---------|--------|------|
| 週1回 | Standard | $30 |
| 毎日 | Standard | $50 |

### YouTube API（無料）

- 無料枠: 10,000 units/日
- 本システムの使用量: 約1,000-2,000 units/日
- **コスト**: 無料枠内で運用可能
- **認証**: ユーザーA（チャンネル所有者）の権限で実行

### Gemini API（ユーザーB持ち）

**Gemini 1.5 Flash**（推奨）:
- 入力: 無料枠（1分あたり15リクエスト、1日100万トークン）
- 出力: 無料枠（1日200万トークン）
- 本システムの使用量: 約10,000-50,000トークン/動画
- **コスト**: ほとんどの場合、無料枠内で運用可能

**無料枠を超えた場合**:
- 入力: $0.075 / 100万トークン
- 出力: $0.30 / 100万トークン
- 月間100動画処理: 約$1-5/月

詳細: https://ai.google.dev/pricing

### 合計（ユーザーB持ち）

- **週1回**: 約$30/月（Render） + 無料（Gemini）
- **毎日**: 約$50/月（Render） + 無料〜$5/月（Gemini）

## 📊 処理フロー

```
1. YouTube API → 配信情報取得（ユーザーAの権限）
   ├─ 動画情報（タイトル、長さ、統計）
   ├─ コメント取得
   └─ 視聴維持率データ取得（Analytics API v2）
   ↓
2. Gemini API → AI powered見どころ分析（ユーザーBのAPIキー）
   ├─ 動画内容の理解
   ├─ コメント感情分析
   ├─ 視聴維持率パターン認識
   └─ 総合的な見どころ判定
   ↓
   （Gemini API利用不可時は従来の方法にフォールバック）
   ├─ コメント密度分析
   ├─ 同接数推定
   └─ 視聴維持率スコアリング
   ↓
3. 動画ダウンロード (yt-dlp)
   ↓
4. セグメント抽出 (FFmpeg)
   ↓
5. ジャンプカット (Lesson 5)
   ↓
6. 動画結合
   ↓
7. 音声認識 (Whisper)
   ↓
8. 字幕焼き込み (Lesson 4)
   ↓
9. 出力完了
```

## 🎓 教材準拠

### Lesson 4: テロップ設計と読みやすさ

- ✅ 可読性の原則（背景との明暗差）
- ✅ フォント設計（ゴシック体、48px）
- ✅ 色彩設計（白文字、黒縁取り、半透明背景）
- ✅ 視線誘導（下部中央配置）

### Lesson 5: テンポ＆リズム演出

- ✅ ジャンプカット（無音部分削除）
- ✅ 7秒ルール（視覚変化）
- ✅ 視聴維持率40%目標
- ✅ 間の詰め方（0.3秒以上の沈黙をカット）

## 🔧 トラブルシューティング

### FFmpegエラー

```bash
# FFmpegが見つからない場合
which ffmpeg  # パスを確認
sudo apt-get install ffmpeg  # 再インストール
```

### Whisperエラー

```bash
# メモリ不足の場合
# .envでモデルサイズを変更
WHISPER_MODEL=tiny  # または base (デフォルト: base)
```

### YouTube APIエラー

- APIキーが正しいか確認
- API有効化を確認
- クォータ制限を確認（無料枠: 10,000 units/日）

## 🔒 セキュリティ

- ✅ `.env`ファイルをGit管理外に設定
- ✅ APIキーはRenderの環境変数で管理
- ✅ ダウンロード動画は一時ファイルとして処理後削除
- ✅ ログに機密情報を出力しない

## 📝 今後の改善予定

- [ ] YouTube自動アップロード機能
- [ ] リアルタイム同接数取得（Analytics API）
- [ ] BGM自動追加機能
- [ ] サムネイル自動生成
- [ ] Discord/Slack通知機能
- [ ] Web UIでの設定変更機能
- [ ] 複数動画の一括処理最適化

## 📞 サポート

問題が発生した場合は、GitHubのIssueを作成してください。

## 📄 ライセンス

MIT License

## 🙏 謝辞

- YouTube Data API v3
- OpenAI Whisper
- FFmpeg
- yt-dlp

---

**作成日**: 2026-01-18  
**最終更新**: 2026-01-18  
**ステータス**: ✅ 開発完了
