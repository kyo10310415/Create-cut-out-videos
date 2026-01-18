"""
アナリティクス分析モジュール
コメント密度、視聴維持率、同接数から見どころを判定
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import re


class AnalyticsProcessor:
    """動画アナリティクスを分析し、見どころを判定するクラス"""
    
    def __init__(
        self,
        min_highlight_score: float = 0.7,
        comment_weight: float = 0.4,
        viewer_weight: float = 0.3,
        retention_weight: float = 0.3
    ):
        """
        初期化
        
        Args:
            min_highlight_score: 見どころと判定する最小スコア (0-1)
            comment_weight: コメント密度の重み
            viewer_weight: 同接数の重み
            retention_weight: 視聴維持率の重み
        """
        self.min_highlight_score = min_highlight_score
        self.comment_weight = comment_weight
        self.viewer_weight = viewer_weight
        self.retention_weight = retention_weight
    
    def analyze_comments(
        self,
        comments: List[Dict],
        video_duration_seconds: int
    ) -> Dict[int, float]:
        """
        コメントからタイムスタンプごとの密度を計算
        
        Args:
            comments: コメントリスト
            video_duration_seconds: 動画の長さ（秒）
            
        Returns:
            {秒数: コメント密度スコア} の辞書
        """
        # 時間区間を60秒（1分）ごとに区切る
        interval_seconds = 60
        num_intervals = (video_duration_seconds + interval_seconds - 1) // interval_seconds
        
        comment_counts = [0] * num_intervals
        
        for comment in comments:
            # コメントからタイムスタンプを抽出
            timestamp_seconds = self._extract_timestamp_from_comment(comment['text'])
            
            if timestamp_seconds is not None and 0 <= timestamp_seconds < video_duration_seconds:
                interval_index = timestamp_seconds // interval_seconds
                comment_counts[interval_index] += 1
        
        # スコアを正規化（0-1）
        max_count = max(comment_counts) if comment_counts else 1
        comment_scores = {}
        
        for i, count in enumerate(comment_counts):
            timestamp = i * interval_seconds
            comment_scores[timestamp] = count / max_count if max_count > 0 else 0
        
        return comment_scores
    
    def _extract_timestamp_from_comment(self, comment_text: str) -> int | None:
        """
        コメントテキストからタイムスタンプを抽出
        
        Args:
            comment_text: コメント本文
            
        Returns:
            タイムスタンプ（秒）またはNone
        """
        # パターン1: MM:SS または HH:MM:SS
        patterns = [
            r'(\d{1,2}):(\d{2}):(\d{2})',  # HH:MM:SS
            r'(\d{1,2}):(\d{2})',           # MM:SS
        ]
        
        for pattern in patterns:
            match = re.search(pattern, comment_text)
            if match:
                groups = match.groups()
                if len(groups) == 3:  # HH:MM:SS
                    hours, minutes, seconds = map(int, groups)
                    return hours * 3600 + minutes * 60 + seconds
                elif len(groups) == 2:  # MM:SS
                    minutes, seconds = map(int, groups)
                    return minutes * 60 + seconds
        
        return None
    
    def analyze_live_chat(
        self,
        chat_messages: List[Dict],
        video_duration_seconds: int
    ) -> Dict[int, float]:
        """
        ライブチャット（コメント）の密度を時系列で分析
        
        Args:
            chat_messages: チャットメッセージのリスト（タイムスタンプ付き）
            video_duration_seconds: 動画の長さ（秒）
            
        Returns:
            {秒数: チャット密度スコア} の辞書
        """
        interval_seconds = 10  # 10秒ごとに集計
        num_intervals = (video_duration_seconds + interval_seconds - 1) // interval_seconds
        
        chat_counts = [0] * num_intervals
        
        for message in chat_messages:
            timestamp_seconds = message.get('timestamp_seconds', 0)
            
            if 0 <= timestamp_seconds < video_duration_seconds:
                interval_index = int(timestamp_seconds // interval_seconds)
                chat_counts[interval_index] += 1
        
        # スコアを正規化
        max_count = max(chat_counts) if chat_counts else 1
        chat_scores = {}
        
        for i, count in enumerate(chat_counts):
            timestamp = i * interval_seconds
            chat_scores[timestamp] = count / max_count if max_count > 0 else 0
        
        return chat_scores
    
    def estimate_concurrent_viewers(
        self,
        view_count: int,
        like_count: int,
        comment_count: int,
        video_duration_seconds: int
    ) -> Dict[int, float]:
        """
        同接数を推定（実際のAPIデータが無い場合の簡易版）
        
        Args:
            view_count: 総視聴回数
            like_count: 高評価数
            comment_count: コメント数
            video_duration_seconds: 動画の長さ（秒）
            
        Returns:
            {秒数: 推定同接スコア} の辞書
            
        Note:
            配信中のリアルタイムデータが取得できない場合の推定値
            視聴回数とエンゲージメントから相対的な人気度を算出
        """
        # エンゲージメント率を計算
        engagement_rate = (like_count + comment_count) / view_count if view_count > 0 else 0
        
        # 簡易的な推定: 均等分布として扱う
        # 実際のデータがある場合はこれを置き換える
        viewer_scores = {}
        
        interval_seconds = 60
        num_intervals = (video_duration_seconds + interval_seconds - 1) // interval_seconds
        
        # 基本スコアを設定（冒頭と中盤で高く、終盤で低い傾向を模擬）
        for i in range(num_intervals):
            timestamp = i * interval_seconds
            progress = i / num_intervals
            
            # 冒頭（0-20%）: 高い
            # 中盤（20-80%）: 中程度
            # 終盤（80-100%）: 低下
            if progress < 0.2:
                score = 1.0
            elif progress < 0.8:
                score = 0.7
            else:
                score = 0.4
            
            viewer_scores[timestamp] = score * engagement_rate
        
        return viewer_scores
    
    def calculate_highlight_scores(
        self,
        comment_scores: Dict[int, float],
        viewer_scores: Dict[int, float],
        retention_scores: Dict[int, float] = None
    ) -> Dict[int, float]:
        """
        各種スコアを統合して見どころスコアを計算
        
        Args:
            comment_scores: コメント密度スコア
            viewer_scores: 同接数スコア
            retention_scores: 視聴維持率スコア（オプション）
            
        Returns:
            {秒数: 総合スコア} の辞書
        """
        all_timestamps = set(comment_scores.keys()) | set(viewer_scores.keys())
        if retention_scores:
            all_timestamps |= set(retention_scores.keys())
        
        highlight_scores = {}
        
        for timestamp in sorted(all_timestamps):
            # 各スコアを取得（存在しない場合は0）
            comment_score = comment_scores.get(timestamp, 0)
            viewer_score = viewer_scores.get(timestamp, 0)
            retention_score = retention_scores.get(timestamp, 0.5) if retention_scores else 0.5
            
            # 重み付き平均で総合スコアを計算
            total_score = (
                self.comment_weight * comment_score +
                self.viewer_weight * viewer_score +
                self.retention_weight * retention_score
            )
            
            highlight_scores[timestamp] = total_score
        
        return highlight_scores
    
    def detect_highlights(
        self,
        highlight_scores: Dict[int, float],
        target_duration: int = 600,  # 10分
        min_segment_duration: int = 30,  # 最小セグメント長（秒）
        max_segment_duration: int = 120  # 最大セグメント長（秒）
    ) -> List[Tuple[int, int, float]]:
        """
        見どころ区間を検出
        
        Args:
            highlight_scores: 総合スコアの辞書
            target_duration: 目標の総時間（秒）
            min_segment_duration: 最小セグメント長（秒）
            max_segment_duration: 最大セグメント長（秒）
            
        Returns:
            [(開始秒, 終了秒, スコア)] のリスト
        """
        # スコアが閾値以上の区間を抽出
        sorted_timestamps = sorted(highlight_scores.keys())
        candidate_segments = []
        
        current_start = None
        current_scores = []
        
        for i, timestamp in enumerate(sorted_timestamps):
            score = highlight_scores[timestamp]
            
            if score >= self.min_highlight_score:
                if current_start is None:
                    current_start = timestamp
                current_scores.append(score)
            else:
                if current_start is not None:
                    # セグメントを確定
                    duration = timestamp - current_start
                    avg_score = sum(current_scores) / len(current_scores)
                    
                    if min_segment_duration <= duration <= max_segment_duration:
                        candidate_segments.append((current_start, timestamp, avg_score))
                    
                    current_start = None
                    current_scores = []
        
        # 最後のセグメント処理
        if current_start is not None:
            timestamp = sorted_timestamps[-1]
            duration = timestamp - current_start
            avg_score = sum(current_scores) / len(current_scores)
            
            if min_segment_duration <= duration <= max_segment_duration:
                candidate_segments.append((current_start, timestamp, avg_score))
        
        # スコア順にソート
        candidate_segments.sort(key=lambda x: x[2], reverse=True)
        
        # 目標時間に達するまでセグメントを選択
        selected_segments = []
        total_duration = 0
        
        for segment in candidate_segments:
            start, end, score = segment
            duration = end - start
            
            if total_duration + duration <= target_duration:
                selected_segments.append(segment)
                total_duration += duration
            
            if total_duration >= target_duration:
                break
        
        # 時系列順にソート
        selected_segments.sort(key=lambda x: x[0])
        
        return selected_segments
    
    def format_timestamp(self, seconds: int) -> str:
        """
        秒数をHH:MM:SS形式に変換
        
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


if __name__ == '__main__':
    # テスト実行
    processor = AnalyticsProcessor()
    
    # サンプルデータ
    sample_comments = [
        {'text': '12:34 ここ面白い！', 'published_at': '2024-01-01T00:00:00Z', 'like_count': 10},
        {'text': '12:35 草', 'published_at': '2024-01-01T00:01:00Z', 'like_count': 5},
        {'text': '25:00 ここ最高', 'published_at': '2024-01-01T00:15:00Z', 'like_count': 20},
    ]
    
    video_duration = 3600  # 1時間
    
    # コメント分析
    comment_scores = processor.analyze_comments(sample_comments, video_duration)
    print(f"コメントスコア: {len(comment_scores)}区間")
    
    # 同接推定
    viewer_scores = processor.estimate_concurrent_viewers(
        view_count=10000,
        like_count=500,
        comment_count=200,
        video_duration_seconds=video_duration
    )
    print(f"視聴者スコア: {len(viewer_scores)}区間")
    
    # 総合スコア計算
    highlight_scores = processor.calculate_highlight_scores(
        comment_scores, viewer_scores
    )
    print(f"総合スコア: {len(highlight_scores)}区間")
    
    # 見どころ検出
    highlights = processor.detect_highlights(highlight_scores, target_duration=600)
    print(f"\n検出された見どころ: {len(highlights)}個")
    for start, end, score in highlights:
        print(f"  {processor.format_timestamp(start)} - {processor.format_timestamp(end)} (スコア: {score:.2f})")
