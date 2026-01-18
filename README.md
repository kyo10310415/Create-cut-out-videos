# YouTube 切り抜き動画自動生成システム

YouTubeの配信動画から見どころを自動検出し、10分程度のハイライト動画を生成するシステムです。

## 📋 プロジェクト概要

- **プロジェクト名**: YouTube Clipper
- **目的**: YouTubeライブ配信の切り抜き動画を自動生成
- **処理時間**: 1時間の配信から10分の切り抜き動画を生成（約30-60分）

## ✨ 主な機能

### 1. 見どころ自動検出
- ✅ コメント密度分析
- ✅ 同接数推定
- ✅ 視聴維持率スコアリング
- ✅ 総合スコアによる見どころ判定

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
- ✅ コメント・統計データの取得
- ✅ 動画ダウンロード（yt-dlp）

## 🏗️ システムアーキテクチャ

```
GitHub (コード管理)
    ↓
Render (デプロイ & 実行)
    ├─ Web Service (ダッシュボード)
    ├─ Background Worker (動画処理)
    └─ Cron Jobs (定期実行)
    ↓
YouTube API (データ取得)
    ↓
FFmpeg (動画編集)
    ↓
Whisper (音声認識)
    ↓
出力動画 (output/)
```

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

1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. YouTube Data API v3を有効化
3. APIキーまたはOAuth認証情報を取得

### 2. ローカル環境のセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/YOUR_USERNAME/youtube-clipper.git
cd youtube-clipper

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

### 3. 環境変数の設定

`.env`ファイルを編集：

```env
# YouTube API認証情報
YOUTUBE_API_KEY=your_api_key_here

# 対象チャンネルID（カンマ区切り）
TARGET_CHANNEL_IDS=UCrzO_hsFW8vLLy8xFBADfqQ,UC3NYX0zN6GySr_hzJHU4tog

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
- `YOUTUBE_API_KEY`
- `TARGET_CHANNEL_IDS`
- その他必要な設定

#### 4. Cron Jobを設定（定期実行）

1. "New +" → "Cron Job"を選択
2. 設定:
   - **Command**: `python run_processor.py`
   - **Schedule**: `0 2 * * *` (毎日午前2時)

## 💰 コスト試算

### Render料金

| 処理頻度 | プラン | 月額 |
|---------|--------|------|
| 週1回 | Standard | $30 |
| 毎日 | Standard | $50 |

### YouTube API

- 無料枠: 10,000 units/日
- 本システムの使用量: 約1,000-2,000 units/日
- **コスト**: 無料枠内で運用可能

### 合計

- **週1回**: 約$30/月
- **毎日**: 約$50/月

## 📊 処理フロー

```
1. YouTube API → 配信情報取得
   ↓
2. アナリティクス分析 → 見どころ検出
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
