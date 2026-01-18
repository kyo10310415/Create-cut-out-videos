"""
自動実行スケジューラー
前日の配信を自動的に切り抜き動画に変換
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from run_processor import YouTubeClipperPipeline
from src.utils.helpers import setup_logger


class AutoScheduler:
    """自動実行スケジューラー"""
    
    def __init__(self):
        """初期化"""
        load_dotenv()
        
        self.logger = setup_logger(
            'auto_scheduler',
            log_file='./logs/scheduler.log',
            level='INFO'
        )
        
        # 自動実行設定を読み込み
        self.enabled = self._load_auto_run_setting()
        self.pipeline = None
        
        self.logger.info(f"AutoScheduler初期化: 自動実行={'有効' if self.enabled else '無効'}")
    
    def _load_auto_run_setting(self) -> bool:
        """自動実行設定を読み込み"""
        # 環境変数から読み込み
        env_setting = os.getenv('AUTO_RUN_ENABLED', 'true').lower()
        
        # 設定ファイルから読み込み（環境変数より優先）
        setting_file = './config/auto_run.txt'
        if os.path.exists(setting_file):
            try:
                with open(setting_file, 'r') as f:
                    file_setting = f.read().strip().lower()
                    return file_setting == 'true' or file_setting == '1' or file_setting == 'on'
            except Exception as e:
                self.logger.warning(f"設定ファイル読み込みエラー: {e}")
        
        return env_setting == 'true'
    
    def _save_auto_run_setting(self, enabled: bool) -> None:
        """自動実行設定を保存"""
        setting_file = './config/auto_run.txt'
        os.makedirs(os.path.dirname(setting_file), exist_ok=True)
        
        try:
            with open(setting_file, 'w') as f:
                f.write('true' if enabled else 'false')
            self.logger.info(f"自動実行設定を保存: {'有効' if enabled else '無効'}")
        except Exception as e:
            self.logger.error(f"設定ファイル保存エラー: {e}")
    
    def set_auto_run(self, enabled: bool) -> bool:
        """
        自動実行のON/OFFを切り替え
        
        Args:
            enabled: Trueで有効、Falseで無効
            
        Returns:
            成功したかどうか
        """
        self.enabled = enabled
        self._save_auto_run_setting(enabled)
        return True
    
    def is_enabled(self) -> bool:
        """自動実行が有効かどうか"""
        return self._load_auto_run_setting()
    
    def load_settings(self) -> dict:
        """
        設定を読み込み（app.py互換性のため）
        
        Returns:
            設定辞書
        """
        return {
            'auto_run_enabled': self.is_enabled()
        }
    
    def enable(self) -> bool:
        """自動実行を有効化"""
        return self.set_auto_run(True)
    
    def disable(self) -> bool:
        """自動実行を無効化"""
        return self.set_auto_run(False)
    
    def get_yesterday_livestreams(self, channel_id: str) -> list:
        """
        前日の配信を取得
        
        Args:
            channel_id: YouTubeチャンネルID
            
        Returns:
            前日の配信動画リスト
        """
        if self.pipeline is None:
            self.pipeline = YouTubeClipperPipeline()
        
        # 前日の日付範囲を計算
        yesterday = datetime.now() - timedelta(days=1)
        start_of_yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_yesterday = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        self.logger.info(f"前日の配信を検索: {start_of_yesterday.date()} (チャンネル: {channel_id})")
        
        # YouTube APIで配信を検索
        all_livestreams = self.pipeline.youtube_api.get_recent_livestreams(
            channel_id,
            max_results=20,
            days_back=2  # 前日+当日
        )
        
        # 前日の配信のみフィルタ
        yesterday_streams = []
        for video in all_livestreams:
            try:
                # 公開日時を取得
                published_at = video['snippet']['publishedAt']
                published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                
                # 前日の配信かチェック
                if start_of_yesterday <= published_date <= end_of_yesterday:
                    yesterday_streams.append(video)
                    self.logger.info(f"  ✓ {video['snippet']['title']} ({published_date})")
            except Exception as e:
                self.logger.warning(f"日付解析エラー: {e}")
        
        self.logger.info(f"前日の配信: {len(yesterday_streams)}本")
        return yesterday_streams
    
    def process_yesterday_streams(self) -> dict:
        """
        前日の配信を全て処理
        
        Returns:
            処理結果のサマリー
        """
        # 自動実行が無効なら終了
        if not self.is_enabled():
            self.logger.info("自動実行が無効のため処理をスキップ")
            return {
                'status': 'skipped',
                'reason': '自動実行が無効',
                'total_processed': 0,
                'total_success': 0,
                'total_failed': 0
            }
        
        self.logger.info("=== 前日配信の自動処理を開始 ===")
        
        if self.pipeline is None:
            self.pipeline = YouTubeClipperPipeline()
        
        # 対象チャンネルを取得
        channel_ids = self.pipeline.config['target_channel_ids']
        
        all_results = []
        total_success = 0
        total_failed = 0
        
        for channel_id in channel_ids:
            if not channel_id.strip():
                continue
            
            self.logger.info(f"\n--- チャンネル: {channel_id} ---")
            
            # 前日の配信を取得
            yesterday_streams = self.get_yesterday_livestreams(channel_id.strip())
            
            if not yesterday_streams:
                self.logger.info(f"チャンネル {channel_id} の前日配信なし - スキップ")
                continue
            
            # 各配信を処理
            for i, video in enumerate(yesterday_streams, 1):
                video_id = video['id']
                video_title = video['snippet']['title']
                
                self.logger.info(f"\n処理中 ({i}/{len(yesterday_streams)}): {video_title}")
                
                # 動画を処理
                result = self.pipeline.process_video(video_id)
                result['channel_id'] = channel_id
                result['video_title'] = video_title
                all_results.append(result)
                
                if result.get('success'):
                    total_success += 1
                    self.logger.info(f"✓ 処理成功: {result.get('output_file')}")
                else:
                    total_failed += 1
                    self.logger.error(f"✗ 処理失敗: {result.get('error')}")
        
        # サマリーを作成
        summary = {
            'status': 'completed',
            'execution_time': datetime.now().isoformat(),
            'total_processed': len(all_results),
            'total_success': total_success,
            'total_failed': total_failed,
            'results': all_results
        }
        
        self.logger.info("\n=== 処理完了 ===")
        self.logger.info(f"処理済み: {len(all_results)}本")
        self.logger.info(f"成功: {total_success}本")
        self.logger.info(f"失敗: {total_failed}本")
        
        return summary


def main():
    """メイン関数"""
    scheduler = AutoScheduler()
    
    # コマンドライン引数を確認
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'enable':
            scheduler.set_auto_run(True)
            print("✓ 自動実行を有効にしました")
            return
        elif command == 'disable':
            scheduler.set_auto_run(False)
            print("✓ 自動実行を無効にしました")
            return
        elif command == 'status':
            enabled = scheduler.is_enabled()
            print(f"自動実行: {'有効' if enabled else '無効'}")
            return
    
    # 前日の配信を処理
    summary = scheduler.process_yesterday_streams()
    
    # 結果を表示
    print("\n=== 処理サマリー ===")
    print(f"ステータス: {summary['status']}")
    print(f"処理済み: {summary['total_processed']}本")
    print(f"成功: {summary['total_success']}本")
    print(f"失敗: {summary['total_failed']}本")


if __name__ == '__main__':
    main()
