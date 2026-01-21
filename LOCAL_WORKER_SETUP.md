# ローカルワーカーセットアップガイド

## 🎯 概要

このワーカーは、Render上のタスクキューから処理待ちタスクを取得し、ローカルPCで動画のダウンロード・編集・字幕生成を行います。

---

## 📋 前提条件

### 必須ソフトウェア
- Python 3.9以上
- FFmpeg
- Git

### 推奨スペック
- CPU: 4コア以上
- RAM: 8GB以上
- ディスク空き容量: 50GB以上

---

## 🚀 セットアップ手順

### ステップ1: リポジトリをクローン

```bash
# Windowsの場合
cd C:\Users\PC_User\Documents
git clone https://github.com/kyo10310415/Create-cut-out-videos.git
cd Create-cut-out-videos

# Mac/Linuxの場合
cd ~/Documents
git clone https://github.com/kyo10310415/Create-cut-out-videos.git
cd Create-cut-out-videos
```

### ステップ2: Python仮想環境を作成

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### ステップ3: 依存パッケージをインストール

```bash
pip install --upgrade pip
pip install -r requirements_worker.txt
```

### ステップ4: FFmpegをインストール

#### Windows
1. https://www.gyan.dev/ffmpeg/builds/ からダウンロード
2. `ffmpeg-release-essentials.zip` を解凍
3. `bin` フォルダを `C:\ffmpeg\bin` に配置
4. 環境変数 PATH に `C:\ffmpeg\bin` を追加

#### Mac
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt install ffmpeg
```

### ステップ5: 設定ファイルを作成

```.env.worker
# Render API URL
RENDER_API_URL=https://create-cut-out-videos.onrender.com

# ワーカーID（任意の名前）
WORKER_ID=local-worker-1

# ローカルディレクトリ
DOWNLOAD_DIR=./downloads
OUTPUT_DIR=./output
TEMP_DIR=./temp

# Google Drive設定（オプション）
GOOGLE_DRIVE_ENABLED=true
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here

# ポーリング間隔（秒）
POLLING_INTERVAL=30

# 並列処理数
MAX_WORKERS=1
```

### ステップ6: ワーカーを起動

```bash
# Windows
python local_worker.py

# Mac/Linux
python3 local_worker.py
```

---

## 📂 ディレクトリ構成

```
Create-cut-out-videos/
├── local_worker.py           # ワーカーメインスクリプト
├── requirements_worker.txt   # ワーカー専用の依存パッケージ
├── .env.worker               # ワーカー設定ファイル
├── downloads/                # 動画ダウンロード先
├── output/                   # 完成動画の出力先
├── temp/                     # 一時ファイル
└── logs/                     # ログファイル
```

---

## 🔍 動作確認

### 1. ワーカーが起動したか確認

コンソールに以下が表示されればOK：
```
🚀 ワーカー起動: local-worker-1
📡 Render API: https://create-cut-out-videos.onrender.com
⏳ タスク待機中...
```

### 2. Renderでテストタスクを作成

1. https://create-cut-out-videos.onrender.com にアクセス
2. 動画ID: `dQw4w9WgXcQ` を入力
3. 「🎬 この動画を処理」をクリック

### 3. ワーカーのログを確認

```
✅ 新しいタスク取得: dQw4w9WgXcQ
📥 動画ダウンロード開始...
✅ 動画ダウンロード完了
🎬 見どころクリップ作成中...
✅ クリップ作成完了: 3個
🔗 クリップ結合中...
✅ 結合完了
📝 字幕生成中...
✅ 字幕生成完了
✅ タスク完了通知送信
```

---

## 🛠️ トラブルシューティング

### Q1: FFmpegが見つからない

**エラー**:
```
FileNotFoundError: [WinError 2] The system cannot find the file specified: 'ffmpeg'
```

**解決**:
```bash
# FFmpegのインストールを確認
ffmpeg -version

# PATHが通っているか確認
where ffmpeg  # Windows
which ffmpeg  # Mac/Linux
```

### Q2: yt-dlpでダウンロードできない

**エラー**:
```
ERROR: unable to download video data: HTTP Error 403: Forbidden
```

**解決**:
1. yt-dlpを最新版に更新:
   ```bash
   pip install --upgrade yt-dlp
   ```

2. YouTubeにログインしてCookieを再取得（ローカルは通常不要）

### Q3: メモリ不足エラー

**エラー**:
```
MemoryError: Unable to allocate array
```

**解決**:
- 並列処理数を減らす: `.env.worker` の `MAX_WORKERS=1`
- 動画の解像度を下げる: 設定で `video_resolution=720p`

---

## 🔄 ワーカーの自動起動（オプション）

### Windows（タスクスケジューラ）

1. `start_worker.bat` を作成:
   ```bat
   @echo off
   cd C:\Users\PC_User\Documents\Create-cut-out-videos
   call venv\Scripts\activate
   python local_worker.py
   ```

2. タスクスケジューラでWindows起動時に実行

### Mac/Linux（systemd）

1. `/etc/systemd/system/youtube-clipper-worker.service` を作成:
   ```ini
   [Unit]
   Description=YouTube Clipper Worker
   After=network.target

   [Service]
   Type=simple
   User=your-username
   WorkingDirectory=/home/your-username/Documents/Create-cut-out-videos
   ExecStart=/home/your-username/Documents/Create-cut-out-videos/venv/bin/python3 local_worker.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. サービスを有効化:
   ```bash
   sudo systemctl enable youtube-clipper-worker
   sudo systemctl start youtube-clipper-worker
   ```

---

## 📊 監視とメンテナンス

### ログの確認
```bash
tail -f logs/worker.log
```

### タスク統計を表示
```bash
curl https://create-cut-out-videos.onrender.com/api/tasks/list?status=completed
```

### ディスク使用量の確認
```bash
# Windows
dir downloads /s
dir output /s

# Mac/Linux
du -sh downloads/
du -sh output/
```

---

## 🎯 次のステップ

- ✅ Phase 1: Renderタスク管理API → **完了**
- ✅ Phase 2: ローカルワーカーセットアップ → **このガイドを参照**
- ⏳ Phase 3: Google Drive連携
- ⏳ Phase 4: 動作確認とテスト

---

質問があれば、GitHub Issuesまたはサポートまでお問い合わせください！ 🚀
