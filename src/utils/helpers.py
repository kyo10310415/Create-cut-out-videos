"""
ユーティリティモジュール
共通機能とヘルパー関数
"""

import os
import logging
from datetime import datetime
from typing import Optional
import requests


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    ロガーをセットアップ
    
    Args:
        name: ロガー名
        log_file: ログファイルパス（オプション）
        level: ログレベル
        
    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラ（オプション）
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def download_video(
    video_url: str,
    output_path: str,
    logger: Optional[logging.Logger] = None
) -> Optional[str]:
    """
    YouTubeから動画をダウンロード（yt-dlp使用）
    
    Args:
        video_url: YouTube動画URL
        output_path: 出力ファイルパス
        logger: ロガー（オプション）
        
    Returns:
        ダウンロードしたファイルパスまたはNone
    """
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
        }
        
        if logger:
            logger.info(f"動画ダウンロード開始: {video_url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        if logger:
            logger.info(f"動画ダウンロード完了: {output_path}")
        
        return output_path
    except Exception as e:
        if logger:
            logger.error(f"動画ダウンロードエラー: {e}")
        return None


def format_duration(seconds: int) -> str:
    """
    秒数を読みやすい形式に変換
    
    Args:
        seconds: 秒数
        
    Returns:
        HH:MM:SS形式の文字列
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def get_video_id_from_url(url: str) -> Optional[str]:
    """
    YouTube URLから動画IDを抽出
    
    Args:
        url: YouTube URL
        
    Returns:
        動画IDまたはNone
    """
    import re
    
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def ensure_directory(directory: str) -> None:
    """
    ディレクトリが存在しない場合は作成
    
    Args:
        directory: ディレクトリパス
    """
    os.makedirs(directory, exist_ok=True)


def clean_filename(filename: str) -> str:
    """
    ファイル名から不正な文字を削除
    
    Args:
        filename: 元のファイル名
        
    Returns:
        クリーンなファイル名
    """
    import re
    
    # 不正な文字を削除
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # 空白を置換
    filename = filename.replace(' ', '_')
    
    # 長さ制限
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename


def get_file_size_mb(file_path: str) -> float:
    """
    ファイルサイズをMB単位で取得
    
    Args:
        file_path: ファイルパス
        
    Returns:
        ファイルサイズ（MB）
    """
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    return 0


def send_webhook_notification(
    webhook_url: str,
    message: str,
    title: str = "YouTube Clipper通知"
) -> bool:
    """
    Webhookで通知を送信（Discord, Slackなど）
    
    Args:
        webhook_url: Webhook URL
        message: メッセージ本文
        title: タイトル
        
    Returns:
        成功したかどうか
    """
    try:
        # Discord Webhook形式
        if 'discord.com' in webhook_url:
            payload = {
                'embeds': [{
                    'title': title,
                    'description': message,
                    'color': 3447003,
                    'timestamp': datetime.utcnow().isoformat()
                }]
            }
        # Slack Webhook形式
        elif 'slack.com' in webhook_url:
            payload = {
                'text': f"*{title}*\n{message}"
            }
        else:
            # 汎用形式
            payload = {
                'title': title,
                'message': message
            }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Webhook通知エラー: {e}")
        return False


def calculate_estimated_time(
    video_duration_seconds: int,
    num_segments: int
) -> int:
    """
    処理時間を推定
    
    Args:
        video_duration_seconds: 動画の長さ（秒）
        num_segments: セグメント数
        
    Returns:
        推定処理時間（秒）
    """
    # 経験則: 
    # - 動画ダウンロード: 動画長の0.1倍
    # - 音声認識: 動画長の0.5倍
    # - セグメント抽出: セグメント数 * 10秒
    # - 結合: セグメント数 * 5秒
    # - 字幕焼き込み: 動画長の0.3倍
    
    download_time = video_duration_seconds * 0.1
    transcribe_time = video_duration_seconds * 0.5
    extract_time = num_segments * 10
    concat_time = num_segments * 5
    subtitle_time = video_duration_seconds * 0.3
    
    total_time = download_time + transcribe_time + extract_time + concat_time + subtitle_time
    
    return int(total_time)


class ProgressTracker:
    """進捗追跡クラス"""
    
    def __init__(self, total_steps: int):
        """
        初期化
        
        Args:
            total_steps: 総ステップ数
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = datetime.now()
    
    def update(self, step_name: str) -> None:
        """
        進捗を更新
        
        Args:
            step_name: ステップ名
        """
        self.current_step += 1
        percentage = (self.current_step / self.total_steps) * 100
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print(f"[{self.current_step}/{self.total_steps}] ({percentage:.1f}%) {step_name} (経過時間: {elapsed:.1f}秒)")
    
    def complete(self) -> None:
        """処理完了"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print(f"\n処理完了！ 総処理時間: {format_duration(int(elapsed))}")


if __name__ == '__main__':
    # テスト実行
    logger = setup_logger('test', log_file='./logs/test.log')
    logger.info("ログテスト")
    
    # 進捗追跡テスト
    tracker = ProgressTracker(5)
    tracker.update("ステップ1")
    tracker.update("ステップ2")
    tracker.update("ステップ3")
    tracker.update("ステップ4")
    tracker.update("ステップ5")
    tracker.complete()
