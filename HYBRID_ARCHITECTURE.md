# ハイブリッド構成実装ガイド

> 認証更新（SEC-006）：以下の旧サンプルの匿名GET pollingは使用できません。実装済みの`local_worker.py`とREADMEの認証設定を使用してください。取得はBearer認証付きPOST、完了・失敗も同じworker専用鍵が必要です。
# 複数チャンネル監視 + ローカル動画処理

## 🎯 **目標**
複数のYouTubeチャンネルの配信を自動監視し、見どころを検出して切り抜き動画を生成する。

---

## 📐 **システム構成**

### **Render (クラウド側) - 監視・検出**
- ✅ 複数チャンネルの配信を24時間監視
- ✅ YouTube Data API v3で動画情報・コメントを取得
- ✅ Analytics API v2で視聴維持率を取得
- ✅ 見どころのタイムスタンプを検出
- ✅ タスクキューに処理依頼を追加
- ✅ Webhookでローカルに通知

### **ローカルPC - 動画処理**
- ✅ Webhookを受信してタスクを取得
- ✅ yt-dlpで動画をダウンロード
- ✅ FFmpegで見どころクリップを作成
- ✅ Whisperで字幕を生成
- ✅ 切り抜き動画を結合・編集
- ✅ 完成動画をクラウドストレージにアップロード
- ✅ Renderに処理完了を通知

---

## 🚀 **実装ステップ**

### **ステップ1: Renderでタスクキューを実装** ✅ 既に実装済み

現在のコードには以下が既にあります：
- `job_queue`: タスクキュー
- `job_results`: 処理結果の保存
- `/api/test-video`: 動画処理API

これを拡張して、**タスクを外部に通知**する機能を追加します。

---

### **ステップ2: ローカルワーカーを作成** ← 新規実装

ローカルPCで動作する「ワーカー」プログラムを作成します。

#### **ワーカーの役割**
1. Renderからタスクを定期的に取得（ポーリング）
2. 動画をダウンロード
3. 見どころクリップを作成
4. 完成動画をアップロード
5. Renderに完了通知

#### **ワーカーのコード例**

```python
# local_worker.py

import time
import requests
import os
from pathlib import Path
from src.utils.helpers import download_video
from src.editor.video_editor import VideoEditor
from src.subtitle.subtitle_generator import SubtitleGenerator

# Renderの API URL
RENDER_API_URL = "https://create-cut-out-videos.onrender.com"
WORKER_ID = "local-worker-1"

# ローカルディレクトリ
DOWNLOAD_DIR = Path("./downloads")
OUTPUT_DIR = Path("./output")
TEMP_DIR = Path("./temp")

# ディレクトリ作成
DOWNLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

def get_pending_task():
    """Renderから処理待ちタスクを取得"""
    try:
        response = requests.get(f"{RENDER_API_URL}/api/tasks/pending")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"タスク取得エラー: {e}")
        return None

def process_task(task):
    """タスクを処理"""
    try:
        video_id = task['video_id']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        highlights = task['highlights']  # Renderで検出された見どころ
        
        print(f"処理開始: {video_id}")
        
        # 1. 動画ダウンロード
        download_path = DOWNLOAD_DIR / f"{video_id}.mp4"
        print("動画ダウンロード中...")
        downloaded_file = download_video(video_url, str(download_path))
        
        if not downloaded_file:
            raise Exception("動画ダウンロード失敗")
        
        # 2. 見どころクリップを作成
        video_editor = VideoEditor(
            output_dir=str(OUTPUT_DIR),
            temp_dir=str(TEMP_DIR)
        )
        
        clips = []
        for i, highlight in enumerate(highlights):
            start = highlight['start']
            end = highlight['end']
            clip_path = TEMP_DIR / f"{video_id}_clip_{i}.mp4"
            
            print(f"クリップ作成: {start}秒 - {end}秒")
            video_editor.extract_clip(downloaded_file, str(clip_path), start, end)
            clips.append(str(clip_path))
        
        # 3. クリップを結合
        combined_path = TEMP_DIR / f"{video_id}_combined.mp4"
        print("クリップ結合中...")
        video_editor.concatenate_videos(clips, str(combined_path))
        
        # 4. 字幕生成
        subtitle_gen = SubtitleGenerator()
        output_path = OUTPUT_DIR / f"{video_id}_highlight.mp4"
        
        print("字幕生成中...")
        transcript = subtitle_gen.transcribe_audio(str(combined_path))
        result = subtitle_gen.apply_subtitle_effects(
            str(combined_path),
            transcript,
            str(output_path)
        )
        
        if not result:
            raise Exception("字幕生成失敗")
        
        print(f"処理完了: {output_path}")
        
        # 5. Renderに完了通知
        notify_completion(task['task_id'], str(output_path))
        
        # 6. 一時ファイル削除
        cleanup_temp_files([downloaded_file, str(combined_path)] + clips)
        
        return True
        
    except Exception as e:
        print(f"処理エラー: {e}")
        notify_error(task['task_id'], str(e))
        return False

def notify_completion(task_id, output_file):
    """Renderに完了通知"""
    try:
        data = {
            'task_id': task_id,
            'status': 'completed',
            'output_file': output_file,
            'worker_id': WORKER_ID
        }
        response = requests.post(f"{RENDER_API_URL}/api/tasks/complete", json=data)
        print(f"完了通知送信: {response.status_code}")
    except Exception as e:
        print(f"完了通知エラー: {e}")

def notify_error(task_id, error_message):
    """Renderにエラー通知"""
    try:
        data = {
            'task_id': task_id,
            'status': 'failed',
            'error': error_message,
            'worker_id': WORKER_ID
        }
        response = requests.post(f"{RENDER_API_URL}/api/tasks/error", json=data)
        print(f"エラー通知送信: {response.status_code}")
    except Exception as e:
        print(f"エラー通知送信失敗: {e}")

def cleanup_temp_files(files):
    """一時ファイルを削除"""
    for file in files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"削除: {file}")
        except Exception as e:
            print(f"削除エラー: {e}")

def main():
    """メインループ"""
    print(f"ワーカー起動: {WORKER_ID}")
    print(f"Render API: {RENDER_API_URL}")
    print("タスク待機中...")
    
    while True:
        try:
            # タスクを取得
            task = get_pending_task()
            
            if task:
                print(f"\n新しいタスク: {task['video_id']}")
                process_task(task)
            else:
                # タスクがない場合は30秒待機
                time.sleep(30)
                
        except KeyboardInterrupt:
            print("\nワーカーを停止します")
            break
        except Exception as e:
            print(f"エラー: {e}")
            time.sleep(60)  # エラー時は1分待機

if __name__ == "__main__":
    main()
```

---

### **ステップ3: Renderにタスク管理APIを追加**

Renderに以下のAPIエンドポイントを追加します：

1. `GET /api/tasks/pending` - 処理待ちタスクを取得
2. `POST /api/tasks/complete` - タスク完了通知
3. `POST /api/tasks/error` - タスクエラー通知

---

### **ステップ4: 動作フロー**

```
1. Render: 新しい配信を検出
   ↓
2. Render: 見どころを分析（コメント + 視聴維持率）
   ↓
3. Render: タスクキューに追加
   ↓
4. ローカルワーカー: タスクを取得
   ↓
5. ローカルワーカー: 動画をダウンロード
   ↓
6. ローカルワーカー: 見どころクリップを作成
   ↓
7. ローカルワーカー: 字幕を生成
   ↓
8. ローカルワーカー: Renderに完了通知
   ↓
9. Render: ダッシュボードに結果を表示
```

---

## 💡 **メリット**

### **Render側**
- ✅ 24時間自動監視
- ✅ Cookie問題なし（ダウンロードしないため）
- ✅ Analytics API v2で高精度な見どころ検出
- ✅ 無料プランで運用可能

### **ローカル側**
- ✅ Cookie問題なし（ローカルIPから）
- ✅ 高速処理（CPUリソース制限なし）
- ✅ yt-dlp安定動作
- ✅ FFmpeg高速編集

---

## 📋 **必要な環境**

### **ローカルPC要件**
- Python 3.9+
- FFmpeg
- yt-dlp
- 50GB以上の空きディスクスペース
- 安定したインターネット接続

### **Render側**
- 現在の環境そのまま
- 新しいAPIエンドポイントを追加するのみ

---

## 🎯 **次のステップ**

1. ✅ この構成で進めるか確認
2. ✅ Renderにタスク管理APIを実装
3. ✅ ローカルワーカーのセットアップスクリプトを作成
4. ✅ テスト実行

---

この構成であれば、YouTube の制限を回避しつつ、複数チャンネルの自動監視と切り抜き動画生成が実現できます。

どうでしょうか？この方向で進めますか？ 🚀
