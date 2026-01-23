"""
YouTube切り抜き動画自動生成メインスクリプト
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.youtube_api import YouTubeAPI
from src.processor.analytics import AnalyticsProcessor
from src.processor.audio_analyzer import AudioAnalyzer
from src.editor.video_editor import VideoEditor
from src.subtitle.subtitle_generator import SubtitleGenerator
from src.ai.gemini_client import GeminiClient
from src.utils.helpers import (
    setup_logger, download_video, get_video_id_from_url,
    ensure_directory, clean_filename, ProgressTracker,
    calculate_estimated_time, format_duration
)


class YouTubeClipperPipeline:
    """YouTube切り抜き動画生成パイプライン"""
    
    def __init__(self, config: dict = None):
        """
        初期化
        
        Args:
            config: 設定辞書（.envから読み込まれる）
        """
        # 環境変数をロード
        load_dotenv()
        
        # 設定
        self.config = config or self._load_config_from_env()
        
        # ロガー設定
        self.logger = setup_logger(
            'youtube_clipper',
            log_file='./logs/clipper.log',
            level=self.config.get('log_level', 'INFO')
        )
        
        # APIとプロセッサを初期化
        self.youtube_api = YouTubeAPI(api_key=self.config['youtube_api_key'])
        self.analytics_processor = AnalyticsProcessor(
            min_highlight_score=self.config['min_highlight_score']
        )
        self.audio_analyzer = AudioAnalyzer()  # 音声解析を追加
        
        # Gemini APIクライアントを初期化（環境変数にキーがある場合のみ）
        self.gemini_client = None
        try:
            self.gemini_client = GeminiClient()
            self.logger.info("✓ Gemini API初期化完了")
        except ValueError:
            self.logger.warning("⚠️ Gemini APIキーが設定されていません。従来の方法で見どころを検出します。")
        except Exception as e:
            self.logger.warning(f"⚠️ Gemini API初期化エラー: {e}")
        self.video_editor = VideoEditor(
            output_dir=self.config['output_dir'],
            temp_dir=self.config['temp_dir'],
            video_resolution=self.config['video_resolution'],
            video_fps=self.config['video_fps'],
            video_bitrate=self.config['video_bitrate']
        )
        self.subtitle_generator = SubtitleGenerator(
            font_size=self.config['subtitle_font_size'],
            font_color=self.config['subtitle_color'],
            outline_color=self.config['subtitle_outline_color'],
            outline_width=self.config['subtitle_outline_width'],
            bg_opacity=self.config['subtitle_bg_opacity']
        )
        
        # ディレクトリ作成
        ensure_directory(self.config['output_dir'])
        ensure_directory(self.config['temp_dir'])
        ensure_directory('./logs')
        ensure_directory('./downloads')
        
        self.logger.info("YouTube Clipper Pipeline初期化完了")
    
    def _load_config_from_env(self) -> dict:
        """環境変数から設定を読み込み"""
        return {
            'youtube_api_key': os.getenv('YOUTUBE_API_KEY'),
            'target_channel_ids': os.getenv('TARGET_CHANNEL_IDS', '').split(','),
            'clip_duration_target': int(os.getenv('CLIP_DURATION_TARGET', 600)),
            'min_highlight_score': float(os.getenv('MIN_HIGHLIGHT_SCORE', 0.7)),
            'output_dir': os.getenv('OUTPUT_DIR', './output'),
            'temp_dir': os.getenv('TEMP_DIR', './temp'),
            'video_resolution': os.getenv('VIDEO_RESOLUTION', '1920x1080'),
            'video_fps': int(os.getenv('VIDEO_FPS', 30)),
            'video_bitrate': os.getenv('VIDEO_BITRATE', '5000k'),
            'subtitle_font_size': int(os.getenv('SUBTITLE_FONT_SIZE', 48)),
            'subtitle_color': os.getenv('SUBTITLE_COLOR', 'white'),
            'subtitle_outline_color': os.getenv('SUBTITLE_OUTLINE_COLOR', 'black'),
            'subtitle_outline_width': int(os.getenv('SUBTITLE_OUTLINE_WIDTH', 3)),
            'subtitle_bg_opacity': float(os.getenv('SUBTITLE_BG_OPACITY', 0.7)),
            'jump_cut_enabled': os.getenv('JUMP_CUT_ENABLED', 'true').lower() == 'true',
            'silence_threshold': os.getenv('SILENCE_THRESHOLD', '-40dB'),
            'silence_min_duration': float(os.getenv('SILENCE_MIN_DURATION', 0.3)),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        }
    
    def _get_youtube_api_for_channel(self, channel_id: str) -> YouTubeAPI:
        """
        チャンネル専用のYouTubeAPIインスタンスを取得
        マルチトークン対応
        """
        return YouTubeAPI(
            api_key=self.config['youtube_api_key'],
            channel_id=channel_id
        )
    
    def process_video(self, video_id: str, channel_id: str = None) -> dict:
        """
        動画1本を処理
        
        Args:
            video_id: YouTube動画ID
            channel_id: チャンネルID（マルチトークン対応用）
            
        Returns:
            処理結果の辞書
        """
        self.logger.info(f"=== 動画処理開始: {video_id} ===")
        
        # チャンネル専用のAPIインスタンスを使用（指定された場合）
        youtube_api = self._get_youtube_api_for_channel(channel_id) if channel_id else self.youtube_api
        
        # 進捗トラッカー
        tracker = ProgressTracker(total_steps=8)
        
        try:
            # ステップ1: 動画情報取得
            tracker.update("動画情報取得")
            video_details = youtube_api.get_video_details(video_id)
            if not video_details:
                self.logger.error(f"動画情報取得失敗: {video_id}")
                return {'success': False, 'error': '動画情報取得失敗'}
            
            video_title = video_details['snippet']['title']
            video_duration = self._parse_duration(video_details['contentDetails']['duration'])
            self.logger.info(f"動画: {video_title} (長さ: {format_duration(video_duration)})")
            
            # ステップ2: コメント取得
            tracker.update("コメント取得")
            comments = youtube_api.get_video_comments(video_id, max_results=100)
            self.logger.info(f"コメント数: {len(comments)}")
            
            # ステップ3: アナリティクス分析
            tracker.update("アナリティクス分析")
            
            # コメント密度分析
            comment_scores = self.analytics_processor.analyze_comments(comments, video_duration)
            
            # 視聴維持率を取得（Analytics API v2）
            retention_data = None
            retention_scores = {}
            
            try:
                self.logger.info("📊 視聴維持率データを取得しています...")
                retention_data = youtube_api.get_audience_retention(video_id)
                
                if retention_data:
                    # 視聴維持率を30秒間隔のスコアに変換
                    timestamps = retention_data['timestamps']
                    rates = retention_data['retention_rates']
                    
                    for i, timestamp in enumerate(timestamps):
                        # 30秒間隔に丸める
                        rounded_timestamp = (timestamp // 30) * 30
                        retention_scores[rounded_timestamp] = rates[i]
                    
                    self.logger.info(f"✓ 視聴維持率データを取得: {len(retention_scores)} ポイント")
                else:
                    self.logger.info("⚠️ 視聴維持率データが取得できませんでした（OAuth認証が必要）")
            except Exception as e:
                self.logger.warning(f"視聴維持率取得エラー: {e}")
            
            # 同接数推定
            stats = youtube_api.get_video_statistics(video_id)
            viewer_scores = self.analytics_processor.estimate_concurrent_viewers(
                view_count=int(stats.get('viewCount', 0)),
                like_count=int(stats.get('likeCount', 0)),
                comment_count=int(stats.get('commentCount', 0)),
                video_duration_seconds=video_duration
            )
            
            # ステップ3.5: 動画ダウンロード（音声解析用に先に行う）
            self.logger.info("📥 音声解析のために動画を先にダウンロードします")
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            download_path = f"./downloads/{video_id}.mp4"
            
            downloaded_file = download_video(video_url, download_path, self.logger)
            if not downloaded_file:
                self.logger.error("動画ダウンロード失敗")
                # ダウンロード失敗時はコメントのみで見どころ検出
                audio_scores = {}
            else:
                # 音声解析を実行
                self.logger.info("🎵 音声を解析して盛り上がりを検出します")
                audio_features = self.audio_analyzer.analyze_audio_features(downloaded_file)
                
                # 音量スコアと活動スコアを統合
                audio_scores = {}
                for timestamp in audio_features.get('volume', {}).keys():
                    volume_score = audio_features['volume'].get(timestamp, 0)
                    activity_score = audio_features['activity'].get(timestamp, 0)
                    audio_scores[timestamp] = (volume_score + activity_score) / 2
            
            # 総合スコア計算（コメント、視聴者、音声、視聴維持率を統合）
            # 視聴維持率がある場合は重みを調整
            if retention_scores:
                self.logger.info("✓ 視聴維持率データを統合します")
                # 視聴維持率を最優先
                if audio_scores:
                    highlight_scores = self.analytics_processor.calculate_highlight_scores(
                        comment_scores, audio_scores, retention_scores
                    )
                else:
                    highlight_scores = self.analytics_processor.calculate_highlight_scores(
                        comment_scores, viewer_scores, retention_scores
                    )
            elif audio_scores:
                self.logger.info("✓ 音声解析データを統合します")
                # 音声スコアを追加（viewer_scoresの代わりに使用）
                highlight_scores = self.analytics_processor.calculate_highlight_scores(
                    comment_scores, audio_scores, retention_scores=None
                )
            else:
                # 音声スコアも視聴維持率もない場合は従来通り
                highlight_scores = self.analytics_processor.calculate_highlight_scores(
                    comment_scores, viewer_scores
                )
            
            # 見どころ検出
            skip_start_seconds = int(os.getenv('SKIP_START_SECONDS', '120'))  # デフォルト2分
            highlights = self.analytics_processor.detect_highlights(
                highlight_scores,
                target_duration=self.config['clip_duration_target'],
                skip_start_seconds=skip_start_seconds
            )
            
            self.logger.info(f"検出された見どころ: {len(highlights)}個")
            
            if not highlights:
                self.logger.warning("見どころが検出されませんでした")
                return {'success': False, 'error': '見どころなし'}
            
            # ステップ4: 動画ダウンロード（すでにダウンロード済みの場合はスキップ）
            tracker.update("動画ダウンロード")
            if not downloaded_file or not os.path.exists(downloaded_file):
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                download_path = f"./downloads/{video_id}.mp4"
                
                downloaded_file = download_video(video_url, download_path, self.logger)
                if not downloaded_file:
                    self.logger.error("動画ダウンロード失敗")
                    return {'success': False, 'error': '動画ダウンロード失敗'}
            
            # ステップ5: セグメント抽出
            tracker.update("セグメント抽出")
            segments = [(start, end) for start, end, _ in highlights]
            segment_files = self.video_editor.extract_segments(
                downloaded_file,
                segments,
                output_prefix=f'{video_id}_seg'
            )
            
            self.logger.info(f"抽出されたセグメント: {len(segment_files)}個")
            
            # ステップ6: 動画結合
            tracker.update("動画結合")
            clean_title = clean_filename(video_title)
            combined_file = os.path.join(
                self.config['temp_dir'],
                f'{video_id}_{clean_title}_combined.mp4'
            )
            
            combined = self.video_editor.concatenate_videos(
                segment_files,
                combined_file,
                add_transitions=False
            )
            
            if not combined:
                self.logger.error("動画結合失敗")
                return {'success': False, 'error': '動画結合失敗'}
            
            # ステップ7: ジャンプカット（無音削除）- Lesson 5準拠
            tracker.update("ジャンプカット適用")
            if self.config['jump_cut_enabled']:
                jumpcut_file = os.path.join(
                    self.config['temp_dir'],
                    f'{video_id}_{clean_title}_jumpcut.mp4'
                )
                
                jumpcut = self.video_editor.remove_silence(
                    combined,
                    jumpcut_file,
                    silence_threshold=self.config['silence_threshold'],
                    min_silence_duration=self.config['silence_min_duration']
                )
                
                if jumpcut:
                    combined = jumpcut
            
            # ステップ8: 字幕生成 - Lesson 4準拠
            tracker.update("字幕生成")
            output_file = os.path.join(
                self.config['output_dir'],
                f'{video_id}_{clean_title}_highlight.mp4'
            )
            
            # 音声認識
            transcript = self.subtitle_generator.transcribe_audio(combined, model='base', language='ja')
            
            if transcript:
                # 字幕焼き込み
                result = self.subtitle_generator.apply_subtitle_effects(
                    combined,
                    transcript,
                    output_file
                )
                
                if result:
                    self.logger.info(f"処理完了: {output_file}")
                    tracker.complete()
                    
                    return {
                        'success': True,
                        'output_file': output_file,
                        'video_id': video_id,
                        'video_title': video_title,
                        'highlights': highlights,
                        'duration': format_duration(video_duration)
                    }
            else:
                # 字幕なしで出力
                import shutil
                shutil.copy(combined, output_file)
                self.logger.info(f"処理完了（字幕なし）: {output_file}")
                tracker.complete()
                
                return {
                    'success': True,
                    'output_file': output_file,
                    'video_id': video_id,
                    'video_title': video_title,
                    'highlights': highlights,
                    'duration': format_duration(video_duration),
                    'note': '字幕生成スキップ'
                }
        
        except Exception as e:
            self.logger.error(f"処理エラー: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def detect_highlights_only(self, video_id: str) -> dict:
        """
        見どころ検出のみ実行（ダウンロード・編集はしない）
        ローカルワーカーに処理を委譲するための情報を返す
        
        Args:
            video_id: YouTube動画ID
            
        Returns:
            見どころ情報の辞書
        """
        self.logger.info(f"=== 見どころ検出開始: {video_id} ===")
        
        try:
            # ステップ1: 動画情報取得
            video_details = self.youtube_api.get_video_details(video_id)
            if not video_details:
                self.logger.error(f"動画情報取得失敗: {video_id}")
                return {'success': False, 'error': '動画情報取得失敗'}
            
            video_title = video_details['snippet']['title']
            video_duration = self._parse_duration(video_details['contentDetails']['duration'])
            channel_id = video_details['snippet'].get('channelId')
            
            self.logger.info(f"動画: {video_title} (長さ: {format_duration(video_duration)})")
            
            # ステップ2: コメント取得
            comments = self.youtube_api.get_video_comments(video_id, max_results=100)
            self.logger.info(f"コメント数: {len(comments)}")
            
            # ステップ3: アナリティクス分析
            
            # コメント密度分析
            comment_scores = self.analytics_processor.analyze_comments(comments, video_duration)
            
            # 視聴維持率を取得（Analytics API v2）
            retention_data = None
            retention_scores = {}
            
            try:
                self.logger.info("📊 視聴維持率データを取得しています...")
                retention_data = self.youtube_api.get_audience_retention(video_id)
                
                if retention_data and isinstance(retention_data, dict):
                    timestamps = retention_data.get('timestamps', [])
                    retention_rates = retention_data.get('retention_rates', [])
                    
                    data_points = len(timestamps)
                    print(f"✓ 視聴維持率データを取得: {data_points} ポイント")
                    self.logger.info(f"✓ 視聴維持率データを取得: {data_points} ポイント")
                    
                    # 視聴維持率データを正規化
                    for timestamp, retention in zip(timestamps, retention_rates):
                        retention_scores[timestamp] = retention
                else:
                    print(f"✓ 視聴維持率データを取得: 0 ポイント")
                    self.logger.info("✓ 視聴維持率データを取得: 0 ポイント")
            except Exception as e:
                self.logger.warning(f"視聴維持率データ取得エラー: {e}")
                print(f"✓ 視聴維持率データを取得: 0 ポイント")
            
            # 統計情報から同接数を推定
            view_count = int(video_details['statistics'].get('viewCount', 0))
            like_count = int(video_details['statistics'].get('likeCount', 0))
            comment_count = int(video_details['statistics'].get('commentCount', 0))
            
            viewer_scores = self.analytics_processor.estimate_concurrent_viewers(
                view_count, like_count, comment_count, video_duration
            )
            
            # 各種スコアを統合
            highlight_scores = self.analytics_processor.calculate_highlight_scores(
                comment_scores=comment_scores,
                viewer_scores=viewer_scores,
                retention_scores=retention_scores
            )
            
            # 見どころを検出
            # Gemini APIが利用可能な場合はAIで分析、そうでなければ従来の方法
            if self.gemini_client:
                try:
                    self.logger.info("🤖 Gemini APIで見どころを分析中...")
                    print("🤖 Gemini APIで見どころを分析中...")
                    
                    gemini_highlights = self.gemini_client.analyze_highlights(
                        video_title=video_title,
                        video_duration=video_duration,
                        comments=comments,
                        retention_data=retention_data if retention_data else None,
                        analytics_scores=highlight_scores
                    )
                    
                    if gemini_highlights:
                        self.logger.info(f"✓ Gemini APIで見どころを検出: {len(gemini_highlights)}個")
                        print(f"✓ Gemini APIで見どころを検出: {len(gemini_highlights)}個")
                        
                        # 開始2分間を除外（Geminiプロンプトにも指示済みだが、念のため再フィルタ）
                        skip_start_seconds = int(os.getenv('SKIP_START_SECONDS', '120'))
                        
                        # Geminiのフォーマットを統一
                        highlights = [
                            (h['start'], h['end'], h['score'])
                            for h in gemini_highlights
                            if h['start'] >= skip_start_seconds  # 開始時刻が120秒以降のみ
                        ]
                        
                        filtered_count = len(gemini_highlights) - len(highlights)
                        if filtered_count > 0:
                            print(f"⏭️ 開始 {skip_start_seconds}秒以内の見どころを {filtered_count}個 除外")
                    else:
                        raise ValueError("Gemini APIが空の結果を返しました")
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ Gemini API使用エラー: {e}")
                    print(f"⚠️ Gemini API使用エラー、従来の方法にフォールバック...")
                    self.gemini_client = None  # 次回から使わない
            
            # Gemini APIが使えない場合は従来の方法
            if not self.gemini_client:
                # 動画の長さに関わらず、常に設定値（デフォルト10分）を使用
                target_duration = self.config['clip_duration_target']  # 環境変数の値を使用
                max_segments = min(10, max(5, target_duration // 60))  # 目標時間に応じた見どころ数
                skip_start_seconds = int(os.getenv('SKIP_START_SECONDS', '120'))  # デフォルト2分
                
                highlights = self.analytics_processor.detect_highlights(
                    highlight_scores=highlight_scores,
                    target_duration=target_duration,
                    min_segment_duration=30,
                    max_segment_duration=90,  # 120 → 90秒に短縮
                    skip_start_seconds=skip_start_seconds
                )
            
            self.logger.info(f"検出された見どころ: {len(highlights)}個")
            
            if not highlights:
                return {
                    'success': False,
                    'error': '見どころが検出されませんでした',
                    'video_id': video_id,
                    'video_title': video_title
                }
            
            return {
                'success': True,
                'video_id': video_id,
                'video_title': video_title,
                'channel_id': channel_id,
                'video_duration': video_duration,
                'highlights': [
                    {
                        'start': h[0],
                        'end': h[1],
                        'score': h[2]
                    }
                    for h in highlights
                ],
                'stats': {
                    'comments': len(comments),
                    'views': view_count,
                    'likes': like_count,
                    'retention_data_points': len(retention_scores)
                }
            }
            
        except Exception as e:
            self.logger.error(f"見どころ検出エラー: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'video_id': video_id
            }
    
    def _parse_duration(self, duration_str: str) -> int:
        """
        ISO 8601形式の動画長さを秒に変換
        
        Args:
            duration_str: ISO 8601形式（例: PT1H23M45S）
            
        Returns:
            秒数
        """
        import re
        
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return 0
    
    def process_channel(self, channel_id: str, max_videos: int = 5) -> list:
        """
        チャンネルの最近の配信を処理
        
        Args:
            channel_id: YouTubeチャンネルID
            max_videos: 処理する最大動画数
            
        Returns:
            処理結果のリスト
        """
        self.logger.info(f"=== チャンネル処理開始: {channel_id} ===")
        
        # 最近の配信を取得
        livestreams = self.youtube_api.get_recent_livestreams(
            channel_id,
            max_results=max_videos,
            days_back=30
        )
        
        self.logger.info(f"取得した配信: {len(livestreams)}本")
        
        results = []
        for video in livestreams:
            video_id = video['id']
            result = self.process_video(video_id)
            results.append(result)
        
        return results
    
    def run_all_channels(self) -> dict:
        """
        設定された全チャンネルを処理
        
        Returns:
            処理結果のサマリー
        """
        self.logger.info("=== 全チャンネル処理開始 ===")
        
        all_results = {}
        for channel_id in self.config['target_channel_ids']:
            if channel_id.strip():
                results = self.process_channel(channel_id.strip(), max_videos=5)
                all_results[channel_id] = results
        
        # サマリー出力
        total_success = sum(
            sum(1 for r in results if r.get('success'))
            for results in all_results.values()
        )
        total_failed = sum(
            sum(1 for r in results if not r.get('success'))
            for results in all_results.values()
        )
        
        self.logger.info(f"=== 処理完了: 成功 {total_success}本, 失敗 {total_failed}本 ===")
        
        return {
            'total_success': total_success,
            'total_failed': total_failed,
            'results': all_results
        }


def main():
    """メイン関数"""
    pipeline = YouTubeClipperPipeline()
    
    # 全チャンネルを処理
    summary = pipeline.run_all_channels()
    
    print("\n=== 処理サマリー ===")
    print(f"成功: {summary['total_success']}本")
    print(f"失敗: {summary['total_failed']}本")
    
    # 詳細結果
    for channel_id, results in summary['results'].items():
        print(f"\nチャンネル: {channel_id}")
        for result in results:
            if result.get('success'):
                print(f"  ✓ {result.get('video_title')} -> {result.get('output_file')}")
            else:
                print(f"  ✗ エラー: {result.get('error')}")


if __name__ == '__main__':
    main()
