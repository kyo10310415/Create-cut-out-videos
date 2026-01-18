"""
音声解析モジュール
音声の音量やピッチから盛り上がりを検出
"""

import subprocess
import json
from typing import Dict, List, Tuple
import os


class AudioAnalyzer:
    """音声ファイルを解析して盛り上がりを検出するクラス"""
    
    def __init__(self):
        """初期化"""
        pass
    
    def analyze_audio_volume(self, audio_file: str, interval_seconds: int = 30) -> Dict[int, float]:
        """
        音声の音量を分析して盛り上がりを検出
        
        Args:
            audio_file: 音声ファイルのパス
            interval_seconds: 分析する時間間隔（秒）
            
        Returns:
            {秒数: 音量スコア} の辞書
        """
        if not os.path.exists(audio_file):
            print(f"⚠️ 音声ファイルが見つかりません: {audio_file}")
            return {}
        
        try:
            # FFmpegで音量を測定
            volume_scores = {}
            
            # 動画の長さを取得
            duration_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_file
            ]
            
            result = subprocess.run(duration_cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip())
            
            print(f"📊 音声解析開始: {audio_file} (長さ: {duration:.1f}秒)")
            
            # 区間ごとに音量を測定
            num_intervals = int(duration / interval_seconds) + 1
            
            for i in range(num_intervals):
                start_time = i * interval_seconds
                if start_time >= duration:
                    break
                
                # 区間の音量を測定（volumedetectフィルター）
                volume_cmd = [
                    'ffmpeg',
                    '-ss', str(start_time),
                    '-t', str(interval_seconds),
                    '-i', audio_file,
                    '-af', 'volumedetect',
                    '-f', 'null',
                    '-'
                ]
                
                result = subprocess.run(volume_cmd, capture_output=True, text=True, stderr=subprocess.STDOUT)
                output = result.stdout
                
                # mean_volumeを抽出
                mean_volume = None
                for line in output.split('\n'):
                    if 'mean_volume:' in line:
                        try:
                            mean_volume = float(line.split('mean_volume:')[1].strip().split()[0])
                            break
                        except:
                            pass
                
                if mean_volume is not None:
                    # 音量を0-1のスコアに正規化（-60dB～0dBを想定）
                    score = max(0, min(1, (mean_volume + 60) / 60))
                    volume_scores[start_time] = score
            
            # スコアを正規化
            if volume_scores:
                max_score = max(volume_scores.values())
                if max_score > 0:
                    volume_scores = {k: v / max_score for k, v in volume_scores.items()}
            
            print(f"✓ 音声解析完了: {len(volume_scores)} 個の区間を分析")
            return volume_scores
            
        except Exception as e:
            print(f"❌ 音声解析エラー: {e}")
            return {}
    
    def detect_speech_activity(self, audio_file: str, interval_seconds: int = 30) -> Dict[int, float]:
        """
        音声活動（会話の活発さ）を検出
        
        Args:
            audio_file: 音声ファイルのパス
            interval_seconds: 分析する時間間隔（秒）
            
        Returns:
            {秒数: 活動スコア} の辞書
        """
        if not os.path.exists(audio_file):
            return {}
        
        try:
            # FFmpegで無音区間を検出（silencedetect）
            silence_cmd = [
                'ffmpeg',
                '-i', audio_file,
                '-af', 'silencedetect=noise=-30dB:duration=0.5',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(silence_cmd, capture_output=True, text=True, stderr=subprocess.STDOUT)
            output = result.stdout
            
            # 無音区間を解析
            silence_periods = []
            for line in output.split('\n'):
                if 'silence_start:' in line:
                    try:
                        start = float(line.split('silence_start:')[1].strip().split()[0])
                        silence_periods.append({'start': start})
                    except:
                        pass
                elif 'silence_end:' in line and silence_periods:
                    try:
                        end = float(line.split('silence_end:')[1].strip().split()[0])
                        silence_periods[-1]['end'] = end
                    except:
                        pass
            
            # 動画の長さを取得
            duration_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_file
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip())
            
            # 区間ごとの活動スコアを計算
            activity_scores = {}
            num_intervals = int(duration / interval_seconds) + 1
            
            for i in range(num_intervals):
                start_time = i * interval_seconds
                end_time = min(start_time + interval_seconds, duration)
                
                # この区間内の無音時間を計算
                silence_duration = 0
                for period in silence_periods:
                    if 'end' not in period:
                        continue
                    
                    s_start = max(period['start'], start_time)
                    s_end = min(period['end'], end_time)
                    
                    if s_start < s_end:
                        silence_duration += s_end - s_start
                
                # 活動スコア = (区間長 - 無音時間) / 区間長
                interval_length = end_time - start_time
                activity_score = (interval_length - silence_duration) / interval_length
                activity_scores[start_time] = activity_score
            
            print(f"✓ 音声活動検出完了: {len(activity_scores)} 個の区間を分析")
            return activity_scores
            
        except Exception as e:
            print(f"❌ 音声活動検出エラー: {e}")
            return {}
    
    def analyze_audio_features(self, audio_file: str) -> Dict[str, Dict[int, float]]:
        """
        音声の複数の特徴を統合的に分析
        
        Args:
            audio_file: 音声ファイルのパス
            
        Returns:
            特徴名をキーとする辞書
            {
                'volume': {秒数: スコア},
                'activity': {秒数: スコア}
            }
        """
        print(f"🎵 音声特徴を分析中: {audio_file}")
        
        features = {
            'volume': self.analyze_audio_volume(audio_file),
            'activity': self.detect_speech_activity(audio_file)
        }
        
        return features
