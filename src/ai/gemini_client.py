"""
Gemini APIクライアント
見どころ分析と字幕最適化にGemini APIを使用
"""

import os
import json
import re
from typing import List, Dict, Optional
import requests


class GeminiClient:
    """Gemini APIクライアント"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: Gemini APIキー（省略時は環境変数から取得）
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY が設定されていません")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.5-flash"  # 高速・低コスト（2025年6月リリース）
    
    def analyze_highlights(
        self,
        video_title: str,
        video_duration: int,
        comments: List[Dict],
        retention_data: Optional[Dict] = None,
        analytics_scores: Optional[Dict[int, float]] = None
    ) -> List[Dict]:
        """
        Gemini APIを使用して見どころを分析
        
        Args:
            video_title: 動画タイトル
            video_duration: 動画の長さ（秒）
            comments: コメントリスト
            retention_data: 視聴維持率データ
            analytics_scores: アナリティクスから計算されたスコア
            
        Returns:
            見どころリスト [{"start": int, "end": int, "reason": str, "score": float}]
        """
        # プロンプトを構築
        prompt = self._build_highlight_prompt(
            video_title,
            video_duration,
            comments,
            retention_data,
            analytics_scores
        )
        
        # Gemini APIを呼び出し
        response = self._call_gemini_api(prompt)
        
        # レスポンスをパース
        highlights = self._parse_highlight_response(response)
        
        return highlights
    
    def optimize_subtitles(
        self,
        transcript: List[Dict],
        video_title: str
    ) -> List[Dict]:
        """
        Gemini APIを使用して字幕を最適化
        
        Args:
            transcript: 文字起こしデータ
            video_title: 動画タイトル
            
        Returns:
            最適化された字幕データ
        """
        # プロンプトを構築
        prompt = self._build_subtitle_prompt(transcript, video_title)
        
        # Gemini APIを呼び出し
        response = self._call_gemini_api(prompt)
        
        # レスポンスをパース
        optimized = self._parse_subtitle_response(response)
        
        return optimized
    
    def _build_highlight_prompt(
        self,
        video_title: str,
        video_duration: int,
        comments: List[Dict],
        retention_data: Optional[Dict],
        analytics_scores: Optional[Dict[int, float]]
    ) -> str:
        """見どころ分析用のプロンプトを構築"""
        
        # 動画情報
        duration_str = self._format_duration(video_duration)
        
        prompt = f"""あなたはYouTube動画の見どころを分析する専門家です。

【動画情報】
タイトル: {video_title}
長さ: {duration_str}

"""
        
        # コメント情報
        if comments:
            comment_texts = []
            for comment in comments[:20]:  # 最初の20件
                text = comment.get('text', '')
                comment_texts.append(f"- {text}")
            
            prompt += f"""【コメント】（全{len(comments)}件中、最初の20件）
{chr(10).join(comment_texts)}

"""
        
        # 視聴維持率データ
        if retention_data and retention_data.get('retention_rates'):
            retention_summary = self._summarize_retention(retention_data)
            prompt += f"""【視聴維持率】
{retention_summary}

"""
        
        # アナリティクススコア
        if analytics_scores:
            top_scores = sorted(
                analytics_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            score_lines = []
            for timestamp, score in top_scores:
                time_str = self._format_duration(timestamp)
                score_lines.append(f"- {time_str}: スコア {score:.2f}")
            
            prompt += f"""【アナリティクススコア（上位10件）】
{chr(10).join(score_lines)}

"""
        
        # 指示
        prompt += f"""【タスク】
上記のデータを分析し、この動画の見どころ（ハイライト）を8-10個抽出してください。

【出力形式】
JSON配列で以下の形式で出力してください：
```json
[
  {{
    "start": 開始秒数（整数）,
    "end": 終了秒数（整数）,
    "reason": "見どころの理由（日本語、50文字以内）",
    "score": スコア（0-1の小数）
  }},
  ...
]
```

【条件】
1. 各見どころは30秒〜120秒の長さ
2. 見どころ同士が重複しないこと
3. 動画全体から均等に選ぶこと
4. スコアが高い順にソートすること
5. コメントや視聴維持率の急上昇箇所を優先
6. 動画の冒頭（最初の30秒）は必ず含める

JSON配列のみを出力し、説明文は不要です。
"""
        
        return prompt
    
    def _build_subtitle_prompt(
        self,
        transcript: List[Dict],
        video_title: str
    ) -> str:
        """字幕最適化用のプロンプトを構築"""
        
        # トランスクリプトをテキストに変換
        transcript_text = []
        for segment in transcript[:50]:  # 最初の50セグメント
            text = segment.get('text', '')
            start = segment.get('start', 0)
            transcript_text.append(f"[{start:.1f}s] {text}")
        
        prompt = f"""あなたはYouTube動画の字幕を最適化する専門家です。

【動画情報】
タイトル: {video_title}

【文字起こし】（一部抜粋）
{chr(10).join(transcript_text)}

【タスク】
上記の文字起こしを、読みやすく、わかりやすい字幕に最適化してください。

【最適化の方針】
1. 句読点を適切に追加
2. フィラー（えー、あのー等）を削除
3. 長すぎる文は2つに分割
4. 話し言葉を自然な文章に整形
5. 重要なキーワードはそのまま残す

【出力形式】
JSON配列で以下の形式で出力してください：
```json
[
  {{
    "start": 開始時間（秒）,
    "end": 終了時間（秒）,
    "text": "最適化された字幕テキスト"
  }},
  ...
]
```

元のタイミング情報は保持し、テキストのみを最適化してください。
JSON配列のみを出力し、説明文は不要です。
"""
        
        return prompt
    
    def _call_gemini_api(self, prompt: str) -> str:
        """Gemini APIを呼び出し"""
        
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,  # 低めに設定（より一貫性のある出力）
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192,
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # レスポンスからテキストを抽出
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate:
                    parts = candidate['content'].get('parts', [])
                    if parts and 'text' in parts[0]:
                        return parts[0]['text']
            
            raise ValueError(f"Unexpected API response: {result}")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Gemini API呼び出しエラー: {e}")
    
    def _parse_highlight_response(self, response: str) -> List[Dict]:
        """見どころレスポンスをパース"""
        
        try:
            # JSONコードブロックを抽出
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # コードブロックがない場合は全体をJSONとみなす
                json_str = response.strip()
            
            highlights = json.loads(json_str)
            
            # バリデーション
            if not isinstance(highlights, list):
                raise ValueError("Highlights must be a list")
            
            for h in highlights:
                if not all(k in h for k in ['start', 'end', 'reason', 'score']):
                    raise ValueError(f"Invalid highlight format: {h}")
            
            return highlights
            
        except Exception as e:
            print(f"⚠️ Gemini APIレスポンスのパースエラー: {e}")
            print(f"レスポンス: {response}")
            return []
    
    def _parse_subtitle_response(self, response: str) -> List[Dict]:
        """字幕レスポンスをパース"""
        
        try:
            # JSONコードブロックを抽出
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()
            
            subtitles = json.loads(json_str)
            
            # バリデーション
            if not isinstance(subtitles, list):
                raise ValueError("Subtitles must be a list")
            
            for s in subtitles:
                if not all(k in s for k in ['start', 'end', 'text']):
                    raise ValueError(f"Invalid subtitle format: {s}")
            
            return subtitles
            
        except Exception as e:
            print(f"⚠️ Gemini APIレスポンスのパースエラー: {e}")
            print(f"レスポンス: {response}")
            return []
    
    def _summarize_retention(self, retention_data: Dict) -> str:
        """視聴維持率データを要約"""
        
        timestamps = retention_data.get('timestamps', [])
        retention_rates = retention_data.get('retention_rates', [])
        
        if not timestamps or not retention_rates:
            return "データなし"
        
        # 急上昇箇所を検出
        increases = []
        for i in range(1, len(retention_rates)):
            diff = retention_rates[i] - retention_rates[i-1]
            if diff > 0.1:  # 10%以上の上昇
                time_str = self._format_duration(timestamps[i])
                increases.append(f"- {time_str}: +{diff*100:.1f}%")
        
        summary = f"平均維持率: {sum(retention_rates)/len(retention_rates)*100:.1f}%\n"
        
        if increases:
            summary += f"\n【急上昇箇所】\n" + "\n".join(increases[:5])
        
        return summary
    
    def _format_duration(self, seconds: int) -> str:
        """秒数を HH:MM:SS 形式に変換"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
