# 🚀 クイックスタートガイド - ハイブリッド構成

## 📋 目次
1. [システム概要](#システム概要)
2. [ローカルPC セットアップ](#ローカルpc-セットアップ)
3. [動作確認](#動作確認)
4. [トラブルシューティング](#トラブルシューティング)

---

## システム概要

```
┌─────────────── Render (クラウド) ───────────────┐
│ ✅ 24時間チャンネル監視                          │
│ ✅ 見どころ検出（Analytics API v2）              │
│ ✅ タスクキュー管理                              │
└──────────────┬──────────────────────────────────┘
               │ API通信
               ↓
┌─────────────── ローカルPC ──────────────────────┐
│ ✅ 動画ダウンロード                              │
│ ✅ 見どころクリップ作成                          │
│ ✅ 字幕生成                                      │
│ ✅ Google Driveアップロード                      │
└──────────────────────────────────────────────────┘
```

---

## ローカルPC セットアップ

### ステップ1: リポジトリをクローン

```bash
# Windows
cd C:\Users\PC_User\Documents
git clone https://github.com/kyo10310415/Create-cut-out-videos.git
cd Create-cut-out-videos

# Mac/Linux
cd ~/Documents
git clone https://github.com/kyo10310415/Create-cut-out-videos.git
cd Create-cut-out-videos
```

### ステップ2: FFmpegをインストール

#### Windows
1. https://www.gyan.dev/ffmpeg/builds/ からダウンロード
2. `ffmpeg-release-essentials.zip` を解凍
3. `bin` フォルダを `C:\ffmpeg\bin` に配置
4. 環境変数 PATH に `C:\ffmpeg\bin` を追加

確認:
```cmd
ffmpeg -version
```

#### Mac
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt install ffmpeg
```

### ステップ3: Python仮想環境をセットアップ

```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements_worker.txt

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_worker.txt
```

### ステップ4: 設定ファイルを作成

```bash
# .env.worker.example をコピー
copy .env.worker.example .env.worker  # Windows
cp .env.worker.example .env.worker    # Mac/Linux
```

`.env.worker` を編集（必要に応じて）:
```env
RENDER_API_URL=https://create-cut-out-videos.onrender.com
WORKER_ID=local-worker-1
POLLING_INTERVAL=30
```

### ステップ5: ワーカーを起動

```bash
# Windows
start_worker.bat

# Mac/Linux
chmod +x start_worker.sh
./start_worker.sh

# または直接実行
python local_worker.py  # Windows
python3 local_worker.py # Mac/Linux
```

---

## 動作確認

### テスト1: Renderでタスクを作成

1. https://create-cut-out-videos.onrender.com にアクセス
2. テストモードで動画IDを入力: `dQw4w9WgXcQ`
3. 「🎬 この動画を処理」をクリック
4. 「見どころを検出し、タスクを作成しました」と表示されればOK

### テスト2: ローカルワーカーのログを確認

ワーカーのコンソールに以下が表示されるはずです:

```
✅ 新しいタスク取得 (#1)
====================================================================
📋 タスク開始: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
🎬 動画: Rick Astley - Never Gonna Give You Up (Official Video)
📊 見どころ: 3個
====================================================================

📥 動画ダウンロード開始: Rick Astley - Never Gonna Give You Up...
✅ 動画ダウンロード完了

🎬 見どころクリップ作成中（3個）...
  📌 クリップ 1/3: 30秒 - 60秒
  📌 クリップ 2/3: 120秒 - 150秒
  📌 クリップ 3/3: 180秒 - 210秒
✅ 全クリップ作成完了（3個）

🔗 クリップ結合中...
✅ クリップ結合完了

📝 字幕生成中（Whisperを使用）...
✅ 文字起こし完了: 45セグメント
✅ 字幕生成完了

📤 完了通知送信中...

✅ タスク完了: dQw4w9WgXcQ_Rick_Astley_Never_Gonna_Give_You_Up_highlight.mp4
====================================================================
```

### テスト3: 完成動画を確認

```bash
# Windowsの場合
explorer output

# Macの場合
open output

# Linuxの場合
xdg-open output
```

`output` フォルダに `.mp4` ファイルが生成されているはずです！

---

## トラブルシューティング

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

### Q2: Whisperのインストールに失敗

**エラー**:
```
ERROR: Could not build wheels for openai-whisper
```

**解決**:
```bash
# PyTorchを先にインストール
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# その後Whisperをインストール
pip install openai-whisper
```

### Q3: タスクが取得できない

**症状**: ワーカーが「タスク待機中...」のまま

**確認事項**:
1. Renderのデプロイが完了しているか
   - https://dashboard.render.com で確認
2. RENDER_API_URLが正しいか
   - `.env.worker` の設定を確認
3. Renderでタスクが作成されているか
   - https://create-cut-out-videos.onrender.com/api/tasks/list にアクセス

### Q4: メモリ不足エラー

**エラー**:
```
RuntimeError: [enforce fail at alloc_cpu.cpp:114] data
```

**解決**:
- Whisperのモデルを小さくする:
  ```python
  # local_worker.py の 151行目あたり
  transcript = subtitle_gen.transcribe_audio(str(combined_path), model='tiny', language='ja')  # base → tiny
  ```

### Q5: ダウンロードが遅い/失敗する

**対策**:
1. yt-dlpを最新版に更新:
   ```bash
   pip install --upgrade yt-dlp
   ```

2. 別の動画でテスト:
   - 短い動画（3-5分）を選択

---

## 📊 ステータス確認

### タスク一覧を確認
```bash
curl https://create-cut-out-videos.onrender.com/api/tasks/list
```

### 統計情報を確認
```bash
curl https://create-cut-out-videos.onrender.com/api/status
```

---

## 🎯 次のステップ

- ✅ Phase 1: Renderタスク管理API → **完了**
- ✅ Phase 2: ローカルワーカーセットアップ → **このガイドを参照**
- ⏳ Phase 3: Google Drive連携 → 次回実装
- ⏳ Phase 4: 自動監視の設定

---

質問があれば、GitHub Issuesまたはサポートまでお問い合わせください！ 🚀
