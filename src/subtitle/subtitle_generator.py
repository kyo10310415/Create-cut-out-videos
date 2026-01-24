"""
テロップ生成モジュール
Lesson 4の可読性原則に基づく字幕生成
音声認識 + テキストオーバーレイ
"""

import os
from typing import List, Dict, Optional, Tuple
import subprocess
import json


class SubtitleGenerator:
    """音声認識とテロップ生成を行うクラス"""
    
    def __init__(
        self,
        font_file: Optional[str] = None,
        font_size: int = 48,
        font_color: str = 'white',
        outline_color: str = 'black',
        outline_width: int = 3,
        bg_opacity: float = 0.7,
        position: str = 'bottom'
    ):
        """
        初期化
        
        Args:
            font_file: フォントファイル名（Noneの場合は自動検出）
            font_size: フォントサイズ
            font_color: 文字色
            outline_color: 縁取り色
            outline_width: 縁取り幅
            bg_opacity: 背景の不透明度（0.0-1.0）
            position: 表示位置（'top', 'center', 'bottom'）
        """
        # フォントパスを自動検出
        if font_file is None:
            font_paths = [
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',  # Debian系 (fonts-noto-cjk)
                '/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf',  # 日本語専用
                '/app/assets/fonts/NotoSansJP-Bold.ttf',  # プロジェクト内 (Docker)
                '/home/user/webapp/assets/fonts/NotoSansJP-Bold.ttf',  # プロジェクト内 (開発環境)
                '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc',  # 代替パス
            ]
            font_file = None
            for path in font_paths:
                if os.path.exists(path):
                    font_file = path
                    print(f"✅ 字幕フォントを検出: {path}")
                    break
            if font_file is None:
                print(f"⚠️ 日本語フォントが見つかりません。デフォルトフォントを使用します。")
                font_file = 'NotoSansJP-Bold.ttf'  # フォールバック
        
        self.font_file = font_file
        self.font_size = font_size
        self.font_color = font_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.bg_opacity = bg_opacity
        self.position = position
    
    def transcribe_audio(
        self,
        video_file: str,
        model: str = 'base',
        language: str = 'ja'
    ) -> Optional[List[Dict]]:
        """
        動画から音声を抽出して文字起こし（Whisper使用）
        
        Args:
            video_file: 入力動画ファイルパス
            model: Whisperモデル ('tiny', 'base', 'small', 'medium', 'large')
            language: 言語コード ('ja', 'en', etc.)
            
        Returns:
            [{
                'start': 開始時間(秒),
                'end': 終了時間(秒),
                'text': テキスト
            }, ...] のリスト
        """
        try:
            import whisper
            
            print(f"音声認識を開始: {video_file}")
            print(f"モデル: {model}, 言語: {language}")
            
            # Whisperモデルをロード
            whisper_model = whisper.load_model(model)
            
            # 音声認識実行
            result = whisper_model.transcribe(
                video_file,
                language=language,
                verbose=False,
                word_timestamps=True  # 単語レベルのタイムスタンプ
            )
            
            # セグメント情報を整形
            segments = []
            for segment in result['segments']:
                segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip()
                })
            
            print(f"音声認識完了: {len(segments)}セグメント")
            return segments
        except Exception as e:
            print(f"音声認識エラー: {e}")
            return None
    
    def generate_srt(
        self,
        segments: List[Dict],
        output_file: str
    ) -> Optional[str]:
        """
        SRT字幕ファイルを生成
        
        Args:
            segments: 音声認識結果のセグメントリスト
            output_file: 出力SRTファイルパス
            
        Returns:
            出力ファイルパスまたはNone
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    start = self._format_srt_time(segment['start'])
                    end = self._format_srt_time(segment['end'])
                    text = segment['text']
                    
                    f.write(f"{i}\n")
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{text}\n")
                    f.write("\n")
            
            print(f"SRTファイル生成完了: {output_file}")
            return output_file
        except Exception as e:
            print(f"SRT生成エラー: {e}")
            return None
    
    def _format_srt_time(self, seconds: float) -> str:
        """秒数をSRT時間形式（HH:MM:SS,mmm）に変換"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def burn_subtitles(
        self,
        input_video: str,
        srt_file: str,
        output_video: str,
        custom_style: Optional[Dict] = None
    ) -> Optional[str]:
        """
        動画に字幕を焼き込む（Lesson 4準拠のデザイン）
        
        Args:
            input_video: 入力動画ファイルパス
            srt_file: SRT字幕ファイルパス
            output_video: 出力動画ファイルパス
            custom_style: カスタムスタイル設定
            
        Returns:
            出力ファイルパスまたはNone
        """
        try:
            # スタイル設定
            style = self._build_subtitle_style(custom_style)
            
            # FFmpegで字幕を焼き込む
            # Lesson 4の可読性原則を適用:
            # - 白文字 + 黒縁取り（明暗差）
            # - 半透明黒背景（ベース）
            # - 大きめのフォントサイズ
            
            # 字幕フィルタを構築
            srt_file_escaped = srt_file.replace('\\', '/').replace(':', '\\:')
            
            subtitle_filter = (
                f"subtitles={srt_file_escaped}:"
                f"force_style='"
                f"FontName={self.font_file},"
                f"FontSize={self.font_size},"
                f"PrimaryColour=&H{self._color_to_ass(self.font_color)},"
                f"OutlineColour=&H{self._color_to_ass(self.outline_color)},"
                f"BackColour=&H{self._opacity_to_ass(self.bg_opacity)}000000,"
                f"Outline={self.outline_width},"
                f"Shadow=0,"
                f"Bold=1,"
                f"Alignment={self._get_alignment()},"
                f"MarginV=50"
                f"'"
            )
            
            # FFmpegコマンド実行
            cmd = [
                'ffmpeg',
                '-i', input_video,
                '-vf', subtitle_filter,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-c:a', 'copy',
                '-y',
                output_video
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"字幕焼き込み完了: {output_video}")
                return output_video
            else:
                print(f"字幕焼き込みエラー: {result.stderr}")
                return None
        except Exception as e:
            print(f"字幕焼き込みエラー: {e}")
            return None
    
    def _build_subtitle_style(self, custom_style: Optional[Dict]) -> Dict:
        """字幕スタイルを構築"""
        style = {
            'font': self.font_file,
            'font_size': self.font_size,
            'color': self.font_color,
            'outline_color': self.outline_color,
            'outline_width': self.outline_width,
            'bg_opacity': self.bg_opacity,
            'position': self.position
        }
        
        if custom_style:
            style.update(custom_style)
        
        return style
    
    def _color_to_ass(self, color_name: str) -> str:
        """色名をASS形式に変換"""
        color_map = {
            'white': 'FFFFFF',
            'black': '000000',
            'red': '0000FF',
            'green': '00FF00',
            'blue': 'FF0000',
            'yellow': '00FFFF',
        }
        return color_map.get(color_name.lower(), 'FFFFFF')
    
    def _opacity_to_ass(self, opacity: float) -> str:
        """不透明度をASS形式に変換（16進数）"""
        # ASSでは00が完全不透明、FFが完全透明
        alpha = int((1.0 - opacity) * 255)
        return f"{alpha:02X}"
    
    def _get_alignment(self) -> int:
        """表示位置をASS alignment値に変換"""
        alignment_map = {
            'bottom': 2,  # 下部中央
            'center': 5,  # 中央
            'top': 8      # 上部中央
        }
        return alignment_map.get(self.position, 2)
    
    def create_highlight_subtitles(
        self,
        segments: List[Dict],
        keywords: List[str] = None
    ) -> List[Dict]:
        """
        見どころに対応する字幕を強調（Lesson 4: 字幕芸）
        
        Args:
            segments: 音声認識結果のセグメントリスト
            keywords: 強調するキーワードリスト
            
        Returns:
            強調情報付きセグメントリスト
        """
        if not keywords:
            keywords = ['すごい', '面白い', '最高', '草', 'やばい', 'えぐい']
        
        highlighted_segments = []
        
        for segment in segments:
            text = segment['text']
            is_highlight = any(keyword in text for keyword in keywords)
            
            highlighted_segments.append({
                'start': segment['start'],
                'end': segment['end'],
                'text': text,
                'highlight': is_highlight,
                'style': 'emphasis' if is_highlight else 'normal'
            })
        
        return highlighted_segments
    
    def apply_subtitle_effects(
        self,
        input_video: str,
        segments: List[Dict],
        output_video: str,
        effect_type: str = 'typewriter'
    ) -> Optional[str]:
        """
        字幕にアニメーション効果を適用
        
        Args:
            input_video: 入力動画ファイルパス
            segments: セグメントリスト
            output_video: 出力動画ファイルパス
            effect_type: 効果タイプ ('typewriter', 'fade', 'slide')
            
        Returns:
            出力ファイルパスまたはNone
            
        Note:
            FFmpegでの複雑なアニメーションは難しいため、基本的な効果のみ対応
        """
        # 簡易実装: SRTファイル経由での字幕焼き込み
        srt_file = output_video.replace('.mp4', '.srt')
        self.generate_srt(segments, srt_file)
        result = self.burn_subtitles(input_video, srt_file, output_video)
        
        # SRTファイルを削除
        if os.path.exists(srt_file):
            os.remove(srt_file)
        
        return result
    
    def add_text_overlay(
        self,
        input_video: str,
        output_video: str,
        text: str,
        start_time: float,
        duration: float,
        position: Tuple[int, int] = None
    ) -> Optional[str]:
        """
        動画に固定テキストオーバーレイを追加
        
        Args:
            input_video: 入力動画ファイルパス
            output_video: 出力動画ファイルパス
            text: 表示テキスト
            start_time: 開始時間（秒）
            duration: 表示時間（秒）
            position: 表示位置 (x, y) またはNone（中央下部）
            
        Returns:
            出力ファイルパスまたはNone
        """
        try:
            # 位置設定
            if position:
                x, y = position
            else:
                # デフォルト: 中央下部
                x = '(w-text_w)/2'
                y = 'h-th-50'
            
            # drawtext フィルタ
            text_escaped = text.replace("'", "\\'").replace(":", "\\:")
            
            drawtext_filter = (
                f"drawtext="
                f"text='{text_escaped}':"
                f"fontfile={self.font_file}:"
                f"fontsize={self.font_size}:"
                f"fontcolor={self.font_color}:"
                f"borderw={self.outline_width}:"
                f"bordercolor={self.outline_color}:"
                f"x={x}:y={y}:"
                f"enable='between(t,{start_time},{start_time + duration})'"
            )
            
            cmd = [
                'ffmpeg',
                '-i', input_video,
                '-vf', drawtext_filter,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-c:a', 'copy',
                '-y',
                output_video
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"テキストオーバーレイ完了: {output_video}")
                return output_video
            else:
                print(f"テキストオーバーレイエラー: {result.stderr}")
                return None
        except Exception as e:
            print(f"テキストオーバーレイエラー: {e}")
            return None


if __name__ == '__main__':
    # テスト実行
    generator = SubtitleGenerator()
    print("SubtitleGeneratorモジュール初期化完了")
    print(f"フォント: {generator.font_file}")
    print(f"フォントサイズ: {generator.font_size}")
    print(f"文字色: {generator.font_color}")
    print(f"縁取り色: {generator.outline_color}")
    print(f"表示位置: {generator.position}")
