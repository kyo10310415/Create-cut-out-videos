# Renderデプロイメントガイド

このガイドでは、YouTube切り抜き動画自動生成システムをRenderにデプロイする手順を説明します。

## 📋 事前準備

### 1. 必要なアカウント

- ✅ GitHubアカウント
- ✅ Renderアカウント（https://render.com/）
- ✅ Google CloudアカウントとYouTube API認証情報

### 2. 準備済みの情報

- YouTube API Key
- 対象チャンネルID（2つ）:
  - `UCrzO_hsFW8vLLy8xFBADfqQ`
  - `UC3NYX0zN6GySr_hzJHU4tog`

## 🚀 デプロイ手順

### ステップ1: GitHubリポジトリの作成

1. **GitHub認証の設定**
   - サンドボックス環境の#githubタブに移動
   - GitHub App認証を完了させる
   - OAuth認証も設定する

2. **リポジトリにプッシュ**
   ```bash
   # ✅ すでに完了しています！
   # リポジトリURL: https://github.com/kyo10310415/Create-cut-out-videos
   
   # 追加の変更がある場合:
   cd /home/user/webapp
   git add .
   git commit -m "変更内容"
   git push origin main
   ```

### ステップ2: Renderでサービスを作成

#### A. Webサービス（ダッシュボード）の作成

1. Renderダッシュボードにログイン
2. "New +" ボタンをクリック → "Web Service"を選択
3. GitHubリポジトリを接続
4. 以下の設定を入力:

| 項目 | 値 |
|-----|---|
| **Name** | youtube-clipper-dashboard |
| **Region** | Oregon (または最寄りのリージョン) |
| **Branch** | main |
| **Runtime** | Python 3 |
| **Build Command** | `apt-get update && apt-get install -y ffmpeg && pip install --upgrade pip && pip install -r requirements.txt` |
| **Start Command** | `python app.py` |
| **Plan** | Starter ($7/月) または Standard ($25/月) |

5. 環境変数を追加:

| Key | Value |
|-----|-------|
| `YOUTUBE_API_KEY` | あなたのYouTube APIキー |
| `YOUTUBE_CLIENT_ID` | YouTube Client ID（OAuth用） |
| `YOUTUBE_CLIENT_SECRET` | YouTube Client Secret（OAuth用） |
| `TARGET_CHANNEL_IDS` | `UCrzO_hsFW8vLLy8xFBADfqQ,UC3NYX0zN6GySr_hzJHU4tog` |
| `PORT` | `10000` |
| `CLIP_DURATION_TARGET` | `600` |
| `MIN_HIGHLIGHT_SCORE` | `0.7` |
| `JUMP_CUT_ENABLED` | `true` |
| `SUBTITLE_FONT_SIZE` | `48` |
| `SUBTITLE_COLOR` | `white` |
| `SUBTITLE_OUTLINE_COLOR` | `black` |
| `SUBTITLE_OUTLINE_WIDTH` | `3` |

6. "Create Web Service"をクリック

#### B. Cron Job（定期実行）の作成

1. "New +" ボタンをクリック → "Cron Job"を選択
2. GitHubリポジトリを接続
3. 以下の設定を入力:

| 項目 | 値 |
|-----|---|
| **Name** | youtube-clipper-daily |
| **Region** | Oregon |
| **Branch** | main |
| **Runtime** | Python 3 |
| **Build Command** | `apt-get update && apt-get install -y ffmpeg && pip install --upgrade pip && pip install -r requirements.txt` |
| **Command** | `python run_processor.py` |
| **Schedule** | `0 2 * * *` (毎日午前2時) |
| **Plan** | Starter ($7/月) |

4. 同じ環境変数を追加（Webサービスと同じ）

5. "Create Cron Job"をクリック

### ステップ3: デプロイの確認

#### Webサービス

1. Renderダッシュボードで"youtube-clipper-dashboard"を開く
2. "Logs"タブで起動ログを確認
3. デプロイ完了後、URLをクリックしてダッシュボードにアクセス
4. ダッシュボードが正常に表示されることを確認

#### Cron Job

1. "youtube-clipper-daily"を開く
2. "Logs"タブで実行ログを確認
3. 手動実行ボタンでテスト実行
4. ログに処理内容が表示されることを確認

## 🔧 トラブルシューティング

### ビルドエラー

**問題**: FFmpegのインストールが失敗する

**解決策**:
```bash
# Build Commandを以下に変更:
apt-get update && apt-get install -y ffmpeg libavcodec-extra && pip install --upgrade pip && pip install -r requirements.txt
```

### メモリエラー

**問題**: Whisperの音声認識でメモリ不足エラー

**解決策**:
- Standardプラン（2GB RAM）にアップグレード
- または`.env`で軽量モデルを使用:
  ```
  WHISPER_MODEL=tiny  # デフォルトはbase
  ```

### YouTube APIエラー

**問題**: API認証エラー

**解決策**:
1. Google Cloud Consoleで以下を確認:
   - プロジェクトが作成されている
   - YouTube Data API v3が有効化されている
   - APIキーが正しくコピーされている
2. Renderの環境変数を確認:
   - `YOUTUBE_API_KEY`が正しく設定されている
   - スペースや改行が入っていない

### ダウンロードエラー

**問題**: yt-dlpで動画ダウンロードが失敗する

**解決策**:
```bash
# requirements.txtを最新版に更新:
yt-dlp==2024.01.01  # 最新バージョンを確認
```

## 📊 モニタリング

### ダッシュボードでの確認

1. WebブラウザでRenderのURLにアクセス
2. 処理済み動画数を確認
3. 対象チャンネルの状態を確認
4. ログ出力を確認

### Renderダッシュボードでの確認

1. "Metrics"タブ:
   - CPU使用率
   - メモリ使用率
   - リクエスト数

2. "Logs"タブ:
   - 実行ログ
   - エラーログ
   - デバッグ情報

## 💰 コスト管理

### 推奨プラン構成

#### 週1回処理の場合（約$30/月）

- Webサービス: Starter ($7/月)
- Cron Job: Starter ($7/月)
- 実行時間課金: 約$15/月

**Cron Schedule**: `0 2 * * 0` (毎週日曜午前2時)

#### 毎日処理の場合（約$50/月）

- Webサービス: Standard ($25/月)
- Cron Job: Starter ($7/月)
- 実行時間課金: 約$20/月

**Cron Schedule**: `0 2 * * *` (毎日午前2時)

### コスト削減のヒント

1. **処理頻度を調整**: 週1回または週2回に変更
2. **動画数を制限**: `max_videos`を3本から1本に変更
3. **軽量モデル使用**: WhisperをtinyモデルにReduction
4. **不要な処理をスキップ**: ジャンプカットや字幕を無効化

## 🔄 更新手順

### コードの更新

1. ローカルで変更を加える
2. Gitにコミット:
   ```bash
   git add .
   git commit -m "更新内容"
   git push origin main
   ```
3. Renderが自動的に再デプロイを実行

### 環境変数の更新

1. Renderダッシュボードを開く
2. サービスを選択
3. "Environment"タブを開く
4. 環境変数を編集
5. "Save Changes"をクリック
6. サービスが自動的に再起動

## 📝 次のステップ

デプロイ完了後、以下を実行してください:

1. ✅ ダッシュボードにアクセスして動作確認
2. ✅ 手動で処理を実行してテスト
3. ✅ 出力動画の品質を確認
4. ✅ Cron Jobの初回実行を確認
5. ✅ ログを確認してエラーがないことを確認

## 🆘 サポート

問題が発生した場合:

1. Renderのログを確認
2. GitHubのIssueを作成
3. エラーメッセージをコピーして報告

---

**最終更新**: 2026-01-18  
**ステータス**: ✅ デプロイ準備完了
