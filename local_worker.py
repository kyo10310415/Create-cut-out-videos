"""
ローカルワーカー - YouTube切り抜き動画生成
Renderからタスクを取得して、ローカルPCで動画処理を実行
"""

import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import logging

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.helpers import download_video, clean_filename, format_duration
from src.editor.video_editor import VideoEditor
from src.subtitle.subtitle_generator import SubtitleGenerator

# 環境変数をロード
load_dotenv('.env.worker')

# 設定
RENDER_API_URL = os.getenv('RENDER_API_URL', 'https://create-cut-out-videos.onrender.com')
WORKER_ID = os.getenv('WORKER_ID', 'local-worker-1')
WORKER_TOKEN = os.getenv('CLIPPER_WORKER_TOKEN', '')
if len(WORKER_TOKEN) < 32 or any(char.isspace() for char in WORKER_TOKEN):
    raise ValueError('CLIPPER_WORKER_TOKEN must be configured (at least 32 characters)')
from urllib.parse import urlsplit
_worker_origin = urlsplit(RENDER_API_URL)
if (_worker_origin.username or _worker_origin.password or _worker_origin.query or _worker_origin.fragment
        or _worker_origin.path not in ('', '/') or not _worker_origin.hostname
        or (_worker_origin.scheme != 'https' and not (_worker_origin.scheme == 'http'
            and _worker_origin.hostname in ('localhost', '127.0.0.1', '::1')))):
    raise ValueError('RENDER_API_URL must be an HTTPS origin')
WORKER_HEADERS = {'Authorization': 'Bearer ' + WORKER_TOKEN}
POLLING_INTERVAL = int(os.getenv('POLLING_INTERVAL', 30))
MAX_WORKERS = int(os.getenv('MAX_WORKERS', 1))

# ディレクトリ
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', './downloads'))
OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', './output'))
TEMP_DIR = Path(os.getenv('TEMP_DIR', './temp'))
LOG_DIR = Path('./logs')

# ディレクトリ作成
DOWNLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ロガーをセットアップ
logger = logging.getLogger('worker')
logger.setLevel(logging.INFO)

# ファイルハンドラ
log_file = LOG_DIR / f'worker_{datetime.now().strftime("%Y%m%d")}.log'
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# コンソールハンドラ
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)


def get_pending_task():
    """Renderから処理待ちタスクを取得"""
    try:
        url = f"{RENDER_API_URL}/api/tasks/pending"
        data = {'worker_id': WORKER_ID}
        response = requests.post(url, json=data, headers=WORKER_HEADERS, timeout=30, allow_redirects=False)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('task'):
                return data['task']
        
        return None
        
    except requests.exceptions.Timeout:
        logger.warning("タスク取得タイムアウト（30秒）")
        return None
    except Exception as e:
        logger.error(f"タスク取得エラー: {e}")
        return None


def process_task(task):
    """タスクを処理"""
    task_id = task['task_id']
    video_id = task['video_id']
    video_title = task['video_title']
    highlights = task['highlights']
    
    logger.info("=" * 60)
    logger.info(f"📋 タスク開始: {task_id}")
    logger.info(f"🎬 動画: {video_title}")
    logger.info(f"📊 見どころ: {len(highlights)}個")
    logger.info("=" * 60)
    
    try:
        # 1. 動画ダウンロード
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        download_path = DOWNLOAD_DIR / f"{video_id}.mp4"
        
        logger.info("📥 動画ダウンロード開始...")
        print(f"\n📥 動画ダウンロード開始: {video_title}")
        
        # Cookieファイルのパスを環境変数に設定（ローカル用）
        cookie_file = project_root / "cookies.txt"
        if cookie_file.exists():
            os.environ['YOUTUBE_COOKIES_FILE'] = str(cookie_file)
            logger.info(f"🍪 Cookieファイルを使用: {cookie_file}")
        else:
            logger.warning("⚠️ cookies.txt が見つかりません。YouTubeの認証エラーが発生する可能性があります。")
        
        downloaded_file = download_video(video_url, str(download_path), logger)
        
        if not downloaded_file:
            raise Exception("動画ダウンロード失敗")
        
        logger.info(f"✅ 動画ダウンロード完了: {downloaded_file}")
        print(f"✅ 動画ダウンロード完了")
        
        # 2. 動画編集の準備
        video_editor = VideoEditor(
            output_dir=str(OUTPUT_DIR),
            temp_dir=str(TEMP_DIR)
        )
        
        # 3. 見どころクリップを作成
        logger.info(f"🎬 見どころクリップ作成中（{len(highlights)}個）...")
        print(f"\n🎬 見どころクリップ作成中（{len(highlights)}個）...")
        
        clips = []
        for i, highlight in enumerate(highlights, 1):
            start = highlight['start']
            end = highlight['end']
            score = highlight.get('score', 0)
            
            clip_path = TEMP_DIR / f"{video_id}_clip_{i:02d}.mp4"
            
            logger.info(f"  クリップ {i}/{len(highlights)}: {start}秒 - {end}秒 (スコア: {score:.2f})")
            print(f"  📌 クリップ {i}/{len(highlights)}: {start}秒 - {end}秒")
            
            result = video_editor.extract_clip(downloaded_file, str(clip_path), start, end)
            
            if result:
                clips.append(str(clip_path))
                logger.info(f"  ✅ クリップ {i} 作成完了")
            else:
                logger.warning(f"  ⚠️ クリップ {i} 作成失敗")
        
        if not clips:
            raise Exception("クリップ作成に失敗しました")
        
        print(f"✅ 全クリップ作成完了（{len(clips)}個）")
        
        # 4. クリップを結合
        combined_path = TEMP_DIR / f"{video_id}_combined.mp4"
        
        logger.info("🔗 クリップ結合中...")
        print(f"\n🔗 クリップ結合中...")
        
        result = video_editor.concatenate_videos(clips, str(combined_path))
        
        if not result:
            raise Exception("クリップ結合に失敗しました")
        
        logger.info("✅ クリップ結合完了")
        print(f"✅ クリップ結合完了")
        
        # 5. 字幕生成
        clean_title = clean_filename(video_title)
        output_filename = f"{video_id}_{clean_title}_highlight.mp4"
        output_path = OUTPUT_DIR / output_filename
        
        logger.info("📝 字幕生成中...")
        print(f"\n📝 字幕生成中（Whisperを使用）...")
        
        subtitle_gen = SubtitleGenerator()
        
        # 音声を文字起こし
        transcript = subtitle_gen.transcribe_audio(str(combined_path), model='base', language='ja')
        
        if transcript:
            logger.info(f"✅ 文字起こし完了: {len(transcript)}セグメント")
            print(f"✅ 文字起こし完了: {len(transcript)}セグメント")
            
            # 字幕を動画に適用
            result = subtitle_gen.apply_subtitle_effects(
                str(combined_path),
                transcript,
                str(output_path)
            )
            
            if result:
                logger.info(f"✅ 字幕生成完了: {output_path}")
                print(f"✅ 字幕生成完了")
            else:
                # 字幕なしでも出力
                logger.warning("字幕生成失敗、字幕なしで出力")
                print(f"⚠️ 字幕生成失敗、字幕なしで出力")
                import shutil
                shutil.copy(combined_path, output_path)
        else:
            # 字幕なしで出力
            logger.warning("文字起こし失敗、字幕なしで出力")
            print(f"⚠️ 文字起こし失敗、字幕なしで出力")
            import shutil
            shutil.copy(combined_path, output_path)
        
        # 6. 完了通知
        logger.info("📤 完了通知送信中...")
        print(f"\n📤 完了通知送信中...")
        
        notify_completion(task_id, str(output_path))
        
        logger.info("✅ タスク完了")
        print(f"\n✅ タスク完了: {output_filename}")
        print("=" * 60)
        
        # 7. 一時ファイル削除
        cleanup_temp_files([downloaded_file, str(combined_path)] + clips)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 処理エラー: {e}", exc_info=True)
        print(f"\n❌ 処理エラー: {e}")
        print("=" * 60)
        
        notify_error(task_id, str(e))
        return False


def notify_completion(task_id, output_file):
    """Renderに完了通知"""
    try:
        url = f"{RENDER_API_URL}/api/tasks/complete"
        data = {
            'task_id': task_id,
            'output_file': output_file,
            'worker_id': WORKER_ID
        }
        response = requests.post(url, json=data, headers=WORKER_HEADERS, timeout=10, allow_redirects=False)
        
        if response.status_code == 200:
            logger.info(f"✅ 完了通知送信成功")
        else:
            logger.warning(f"⚠️ 完了通知送信失敗: {response.status_code}")
            
    except Exception as e:
        logger.error(f"完了通知エラー: {e}")


def notify_error(task_id, error_message):
    """Renderにエラー通知"""
    try:
        url = f"{RENDER_API_URL}/api/tasks/error"
        data = {
            'task_id': task_id,
            'error': error_message,
            'worker_id': WORKER_ID
        }
        response = requests.post(url, json=data, headers=WORKER_HEADERS, timeout=10, allow_redirects=False)
        
        if response.status_code == 200:
            logger.info(f"✅ エラー通知送信成功")
        else:
            logger.warning(f"⚠️ エラー通知送信失敗: {response.status_code}")
            
    except Exception as e:
        logger.error(f"エラー通知送信失敗: {e}")


def cleanup_temp_files(files):
    """一時ファイルを削除"""
    for file in files:
        try:
            if os.path.exists(file):
                os.remove(file)
                logger.info(f"🗑️ 削除: {file}")
        except Exception as e:
            logger.warning(f"削除エラー: {file} - {e}")


def print_banner():
    """起動バナーを表示"""
    banner = """
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║     🎬 YouTube Clipper - ローカルワーカー                  ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
"""
    print(banner)
    print(f"🆔 ワーカーID: {WORKER_ID}")
    print(f"📡 Render API: {RENDER_API_URL}")
    print(f"⏱️  ポーリング間隔: {POLLING_INTERVAL}秒")
    print(f"📂 出力ディレクトリ: {OUTPUT_DIR.absolute()}")
    print(f"📝 ログファイル: {log_file.absolute()}")
    print("=" * 60)


def main():
    """メインループ"""
    print_banner()
    logger.info(f"🚀 ワーカー起動: {WORKER_ID}")
    logger.info(f"📡 Render API: {RENDER_API_URL}")
    
    print(f"\n⏳ タスク待機中...\n")
    
    task_count = 0
    success_count = 0
    error_count = 0
    
    try:
        while True:
            try:
                # タスクを取得
                task = get_pending_task()
                
                if task:
                    task_count += 1
                    logger.info(f"\n✅ 新しいタスク取得 (#{task_count})")
                    print(f"\n✅ 新しいタスク取得 (#{task_count})")
                    
                    # タスクを処理
                    success = process_task(task)
                    
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                    
                    # 統計表示
                    print(f"\n📊 統計: 処理済み {task_count}件 (成功 {success_count}, 失敗 {error_count})")
                    print(f"⏳ 次のタスクを待機中...\n")
                    
                    # 短い待機
                    time.sleep(5)
                else:
                    # タスクがない場合は待機
                    time.sleep(POLLING_INTERVAL)
                    
            except KeyboardInterrupt:
                raise  # Ctrl+Cは外側でキャッチ
            except Exception as e:
                logger.error(f"ループエラー: {e}", exc_info=True)
                print(f"❌ エラー: {e}")
                time.sleep(60)  # エラー時は1分待機
                
    except KeyboardInterrupt:
        print("\n\n⏹️  ワーカーを停止します...")
        logger.info("⏹️  ワーカー停止")
        logger.info(f"📊 最終統計: 処理済み {task_count}件 (成功 {success_count}, 失敗 {error_count})")
        print(f"📊 最終統計: 処理済み {task_count}件 (成功 {success_count}, 失敗 {error_count})")
        print("👋 お疲れ様でした！")


if __name__ == "__main__":
    main()
