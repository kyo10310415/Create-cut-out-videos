"""
動画編集モジュール
FFmpegを使用した動画の切り抜き、結合、エンコード
Lesson 5のテンポ&リズム演出を実装
"""

import os
import subprocess
from typing import List, Tuple, Optional
import ffmpeg


class VideoEditor:
    """FFmpegを使用した動画編集クラス"""
    
    def __init__(
        self,
        output_dir: str = './output',
        temp_dir: str = './temp',
        video_resolution: str = '1920x1080',
        video_fps: int = 30,
        video_bitrate: str = '5000k',
        audio_bitrate: str = '192k'
    ):
        """
        初期化
        
        Args:
            output_dir: 出力ディレクトリ
            temp_dir: 一時ファイルディレクトリ
            video_resolution: 動画解像度
            video_fps: フレームレート
            video_bitrate: ビデオビットレート
            audio_bitrate: オーディオビットレート
        """
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        self.video_resolution = video_resolution
        self.video_fps = video_fps
        self.video_bitrate = video_bitrate
        self.audio_bitrate = audio_bitrate
        
        # ディレクトリ作成
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
    
    def extract_clip(
        self,
        input_video: str,
        output_file: str,
        start_time: int,
        end_time: int
    ) -> Optional[str]:
        """
        動画から1つのクリップを切り出す
        
        Args:
            input_video: 入力動画ファイルパス
            output_file: 出力ファイルパス
            start_time: 開始時刻（秒）
            end_time: 終了時刻（秒）
            
        Returns:
            出力ファイルパスまたはNone
        """
        duration = end_time - start_time
        
        try:
            # FFmpegでクリップ抽出（再エンコードで確実に処理）
            # ストリームコピーは高速だがエラーが発生しやすいため、再エンコードを使用
            (
                ffmpeg
                .input(input_video, ss=start_time, t=duration)
                .output(
                    output_file,
                    vcodec='libx264',
                    acodec='aac',
                    video_bitrate=self.video_bitrate,
                    audio_bitrate=self.audio_bitrate,
                    preset='fast'  # fast で高速化
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            
            print(f"✓ クリップ抽出完了: {output_file} ({start_time}-{end_time}秒)")
            return output_file
        except ffmpeg.Error as e:
            print(f"❌ クリップ抽出エラー ({start_time}-{end_time}): {e.stderr.decode()}")
            return None
    
    def extract_segments(
        self,
        input_video: str,
        segments: List[Tuple[int, int]],
        output_prefix: str = 'segment'
    ) -> List[str]:
        """
        動画から複数のセグメントを切り出す
        
        Args:
            input_video: 入力動画ファイルパス
            segments: [(開始秒, 終了秒), ...] のリスト
            output_prefix: 出力ファイル名のプレフィックス
            
        Returns:
            切り出したセグメントファイルパスのリスト
        """
        segment_files = []
        
        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            output_file = os.path.join(
                self.temp_dir, 
                f'{output_prefix}_{i:03d}_{start}_{end}.mp4'
            )
            
            try:
                # FFmpegでセグメント抽出（高速・高品質）
                (
                    ffmpeg
                    .input(input_video, ss=start, t=duration)
                    .output(
                        output_file,
                        vcodec='libx264',
                        acodec='aac',
                        video_bitrate=self.video_bitrate,
                        audio_bitrate=self.audio_bitrate,
                        preset='medium',
                        **{'c:v': 'libx264', 'c:a': 'aac'}
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
                
                segment_files.append(output_file)
                print(f"セグメント抽出完了: {output_file}")
            except ffmpeg.Error as e:
                print(f"セグメント抽出エラー ({start}-{end}): {e.stderr.decode()}")
        
        return segment_files
    
    def concatenate_videos(
        self,
        video_files: List[str],
        output_file: str,
        add_transitions: bool = False
    ) -> Optional[str]:
        """
        複数の動画を結合
        
        Args:
            video_files: 入力動画ファイルパスのリスト
            output_file: 出力ファイルパス
            add_transitions: トランジション効果を追加するか
            
        Returns:
            出力ファイルパスまたはNone
        """
        if not video_files:
            print("結合する動画がありません")
            return None
        
        print(f"📹 結合する動画: {len(video_files)}個")
        for i, vf in enumerate(video_files, 1):
            if os.path.exists(vf):
                size_mb = os.path.getsize(vf) / (1024 * 1024)
                print(f"   {i}. {os.path.basename(vf)} ({size_mb:.2f} MB)")
            else:
                print(f"   {i}. {os.path.basename(vf)} (❌ ファイルが見つかりません)")
        
        # concat demuxerを使用（高速）
        concat_file = os.path.join(self.temp_dir, 'concat_list.txt')
        
        with open(concat_file, 'w', encoding='utf-8') as f:
            for video_file in video_files:
                # ファイルパスをエスケープ
                escaped_path = video_file.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
        
        print(f"📝 concat_list.txt を作成: {concat_file}")
        
        try:
            if add_transitions:
                # トランジション付き結合（処理時間が長い）
                return self._concatenate_with_transitions(video_files, output_file)
            else:
                # 再エンコードで確実に結合（品質と安定性を優先）
                print(f"🎬 FFmpeg で結合を開始（再エンコードモード）...")
                (
                    ffmpeg
                    .input(concat_file, format='concat', safe=0)
                    .output(
                        output_file,
                        vcodec='libx264',
                        acodec='aac',
                        video_bitrate=self.video_bitrate,
                        audio_bitrate=self.audio_bitrate,
                        preset='fast'  # fast で高速化
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
            
            # 結合結果を確認
            if os.path.exists(output_file):
                size_mb = os.path.getsize(output_file) / (1024 * 1024)
                print(f"✅ 動画結合完了: {output_file} ({size_mb:.2f} MB)")
            else:
                print(f"❌ 結合動画が作成されませんでした: {output_file}")
                return None
            
            return output_file
        except ffmpeg.Error as e:
            print(f"❌ 動画結合エラー: {e.stderr.decode()}")
            return None
    
    def _concatenate_with_transitions(
        self,
        video_files: List[str],
        output_file: str,
        transition_duration: float = 0.5
    ) -> Optional[str]:
        """
        トランジション効果付きで動画を結合
        
        Args:
            video_files: 入力動画ファイルパスのリスト
            output_file: 出力ファイルパス
            transition_duration: トランジション時間（秒）
            
        Returns:
            出力ファイルパスまたはNone
        """
        # xfade フィルタを使用したトランジション
        # 実装は複雑なため、シンプルなフェード効果のみ
        
        if len(video_files) == 1:
            return video_files[0]
        
        try:
            # 各動画の入力を準備
            inputs = [ffmpeg.input(f) for f in video_files]
            
            # フィルタグラフを構築
            # 簡易実装: フェードイン/アウト
            streams = []
            for i, inp in enumerate(inputs):
                if i == 0:
                    # 最初の動画: フェードアウトのみ
                    stream = inp.video.filter('fade', type='out', start_time=0, duration=transition_duration)
                elif i == len(inputs) - 1:
                    # 最後の動画: フェードインのみ
                    stream = inp.video.filter('fade', type='in', start_time=0, duration=transition_duration)
                else:
                    # 中間の動画: フェードイン/アウト
                    stream = (
                        inp.video
                        .filter('fade', type='in', start_time=0, duration=transition_duration)
                        .filter('fade', type='out', start_time=0, duration=transition_duration)
                    )
                streams.append(stream)
            
            # 結合
            joined = ffmpeg.concat(*streams, v=1, a=0)
            audio = ffmpeg.concat(*[inp.audio for inp in inputs], v=0, a=1)
            
            (
                ffmpeg
                .output(
                    joined, audio, output_file,
                    vcodec='libx264',
                    acodec='aac',
                    video_bitrate=self.video_bitrate,
                    audio_bitrate=self.audio_bitrate
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            
            return output_file
        except Exception as e:
            print(f"トランジション付き結合エラー: {e}")
            # フォールバック: シンプルな結合
            return None
    
    def remove_silence(
        self,
        input_video: str,
        output_video: str,
        silence_threshold: str = '-40dB',
        min_silence_duration: float = 0.3
    ) -> Optional[str]:
        """
        無音部分を削除（Lesson 5: ジャンプカット）
        
        Args:
            input_video: 入力動画ファイルパス
            output_video: 出力動画ファイルパス
            silence_threshold: 無音判定の閾値
            min_silence_duration: 無音と判定する最小時間（秒）
            
        Returns:
            出力ファイルパスまたはNone
        """
        try:
            # silencedetect フィルタで無音区間を検出
            silence_detect_cmd = [
                'ffmpeg',
                '-i', input_video,
                '-af', f'silencedetect=noise={silence_threshold}:d={min_silence_duration}',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                silence_detect_cmd,
                capture_output=True,
                text=True
            )
            
            # 無音区間をパース
            silence_intervals = self._parse_silence_intervals(result.stderr)
            
            if not silence_intervals:
                print("無音区間が検出されませんでした")
                return input_video
            
            # 無音区間を除外したセグメントを抽出
            video_duration = self._get_video_duration(input_video)
            keep_segments = self._calculate_keep_segments(silence_intervals, video_duration)
            
            # セグメントを抽出して結合
            segment_files = self.extract_segments(input_video, keep_segments, output_prefix='nosilence')
            result_file = self.concatenate_videos(segment_files, output_video)
            
            # 一時ファイルを削除
            for segment_file in segment_files:
                if os.path.exists(segment_file):
                    os.remove(segment_file)
            
            return result_file
        except Exception as e:
            print(f"無音削除エラー: {e}")
            return None
    
    def _parse_silence_intervals(self, ffmpeg_output: str) -> List[Tuple[float, float]]:
        """FFmpegの出力から無音区間を抽出"""
        import re
        
        silence_intervals = []
        silence_start = None
        
        for line in ffmpeg_output.split('\n'):
            if 'silencedetect' in line:
                if 'silence_start' in line:
                    match = re.search(r'silence_start: ([\d.]+)', line)
                    if match:
                        silence_start = float(match.group(1))
                elif 'silence_end' in line and silence_start is not None:
                    match = re.search(r'silence_end: ([\d.]+)', line)
                    if match:
                        silence_end = float(match.group(1))
                        silence_intervals.append((silence_start, silence_end))
                        silence_start = None
        
        return silence_intervals
    
    def _calculate_keep_segments(
        self,
        silence_intervals: List[Tuple[float, float]],
        video_duration: float
    ) -> List[Tuple[int, int]]:
        """無音区間から保持すべきセグメントを計算"""
        keep_segments = []
        current_start = 0
        
        for silence_start, silence_end in silence_intervals:
            if silence_start > current_start:
                keep_segments.append((int(current_start), int(silence_start)))
            current_start = silence_end
        
        # 最後のセグメント
        if current_start < video_duration:
            keep_segments.append((int(current_start), int(video_duration)))
        
        return keep_segments
    
    def _get_video_duration(self, video_file: str) -> float:
        """動画の長さを取得（秒）"""
        try:
            probe = ffmpeg.probe(video_file)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            print(f"動画長さ取得エラー: {e}")
            return 0
    
    def add_background_music(
        self,
        input_video: str,
        music_file: str,
        output_video: str,
        music_volume: float = 0.3
    ) -> Optional[str]:
        """
        BGMを追加
        
        Args:
            input_video: 入力動画ファイルパス
            music_file: BGM音楽ファイルパス
            output_video: 出力動画ファイルパス
            music_volume: BGM音量（0.0-1.0）
            
        Returns:
            出力ファイルパスまたはNone
        """
        try:
            video = ffmpeg.input(input_video)
            audio = ffmpeg.input(music_file)
            
            # 動画の長さを取得
            video_duration = self._get_video_duration(input_video)
            
            # BGMをループして動画の長さに合わせる
            (
                ffmpeg
                .filter([video.audio, audio], 'amix', inputs=2, duration='first', weights=f'1 {music_volume}')
                .output(
                    video.video,
                    output_video,
                    vcodec='copy',
                    acodec='aac',
                    audio_bitrate=self.audio_bitrate
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            
            print(f"BGM追加完了: {output_video}")
            return output_video
        except ffmpeg.Error as e:
            print(f"BGM追加エラー: {e.stderr.decode()}")
            return None
    
    def apply_speed_changes(
        self,
        input_video: str,
        output_video: str,
        speed_segments: List[Tuple[int, int, float]]
    ) -> Optional[str]:
        """
        部分的に再生速度を変更（テンポ調整）
        
        Args:
            input_video: 入力動画ファイルパス
            output_video: 出力動画ファイルパス
            speed_segments: [(開始秒, 終了秒, 速度), ...] のリスト
                            速度は1.0が通常、2.0が2倍速、0.5が0.5倍速
            
        Returns:
            出力ファイルパスまたはNone
        """
        # 実装は複雑なため、基本的な速度変更のみ対応
        try:
            # 全体の速度変更（簡易版）
            if len(speed_segments) == 1:
                _, _, speed = speed_segments[0]
                (
                    ffmpeg
                    .input(input_video)
                    .filter('setpts', f'{1/speed}*PTS')
                    .output(
                        output_video,
                        vcodec='libx264',
                        acodec='aac',
                        video_bitrate=self.video_bitrate,
                        audio_bitrate=self.audio_bitrate
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
                return output_video
            else:
                print("複数セグメントの速度変更は未実装")
                return None
        except ffmpeg.Error as e:
            print(f"速度変更エラー: {e.stderr.decode()}")
            return None


if __name__ == '__main__':
    # テスト実行
    editor = VideoEditor()
    print("VideoEditorモジュール初期化完了")
    print(f"出力ディレクトリ: {editor.output_dir}")
    print(f"一時ディレクトリ: {editor.temp_dir}")
