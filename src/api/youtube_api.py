"""
YouTube Data API連携モジュール
配信動画の情報取得、アナリティクスデータの取得を行う
"""

import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle


class YouTubeAPI:
    """YouTube Data API v3のラッパークラス"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.readonly',
        'https://www.googleapis.com/auth/youtube.force-ssl',
        'https://www.googleapis.com/auth/yt-analytics.readonly'
    ]
    
    def __init__(self, api_key: Optional[str] = None, credentials_file: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: YouTube Data API Key (読み取り専用操作用)
            credentials_file: OAuth認証用のcredentials.jsonファイルパス
        """
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.credentials_file = credentials_file
        self.youtube = None
        self.youtube_analytics = None
        self._initialize_services()
    
    def _initialize_services(self):
        """YouTube API サービスを初期化"""
        # Data API (読み取り専用)
        if self.api_key:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        
        # 環境変数からcredentials.jsonを復元（Render対応）
        credentials_env = os.getenv('YOUTUBE_OAUTH_CREDENTIALS')
        if credentials_env and not os.path.exists('credentials.json'):
            try:
                import base64
                creds_data = base64.b64decode(credentials_env)
                with open('credentials.json', 'wb') as f:
                    f.write(creds_data)
                self.credentials_file = 'credentials.json'
                print("✓ credentials.json を環境変数から復元しました")
            except Exception as e:
                print(f"⚠️ credentials.json 復元エラー: {e}")
        
        # Analytics API (OAuth認証が必要)
        if self.credentials_file and os.path.exists(self.credentials_file):
            creds = self._get_authenticated_credentials()
            if creds:
                self.youtube_analytics = build('youtubeAnalytics', 'v2', credentials=creds)
                print("✓ YouTube Analytics API v2 が初期化されました")
    
    def _get_authenticated_credentials(self) -> Optional[Credentials]:
        """OAuth認証を行い、認証情報を取得"""
        creds = None
        token_file = 'token.pickle'
        
        # 環境変数からトークンを読み込む（Render対応）
        token_env = os.getenv('YOUTUBE_OAUTH_TOKEN')
        if token_env:
            try:
                import base64
                token_data = base64.b64decode(token_env)
                with open(token_file, 'wb') as f:
                    f.write(token_data)
                print("✓ OAuth トークンを環境変数から復元しました")
            except Exception as e:
                print(f"⚠️ トークン復元エラー: {e}")
        
        # トークンファイルが存在すれば読み込む
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # 認証情報が無効な場合は再認証
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("✓ OAuth トークンをリフレッシュしました")
                    # リフレッシュ後のトークンを保存
                    with open(token_file, 'wb') as token:
                        pickle.dump(creds, token)
                except Exception as e:
                    print(f"⚠️ トークンリフレッシュエラー: {e}")
                    creds = None
            
            # 再認証が必要な場合（ローカル環境のみ）
            if not creds:
                if not self.credentials_file or not os.path.exists(self.credentials_file):
                    print("⚠️ credentials.json が見つかりません")
                    return None
                
                # ローカル環境でのみ実行（Renderでは実行しない）
                if os.getenv('RENDER'):
                    print("⚠️ Render環境では新規認証ができません。ローカルで認証してください。")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
                
                # トークンを保存
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
                
                print("✓ 新規OAuth認証が完了しました")
        
        return creds
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """
        チャンネル情報を取得
        
        Args:
            channel_id: YouTubeチャンネルID
            
        Returns:
            チャンネル情報の辞書
        """
        try:
            request = self.youtube.channels().list(
                part='snippet,contentDetails,statistics',
                id=channel_id
            )
            response = request.execute()
            
            if response['items']:
                return response['items'][0]
            return None
        except HttpError as e:
            print(f"チャンネル情報取得エラー: {e}")
            return None
    
    def get_recent_livestreams(
        self, 
        channel_id: str, 
        max_results: int = 10,
        days_back: int = 30
    ) -> List[Dict]:
        """
        最近の配信動画を取得
        
        Args:
            channel_id: YouTubeチャンネルID
            max_results: 取得する最大件数
            days_back: 何日前までの配信を取得するか
            
        Returns:
            配信動画のリスト
        """
        try:
            # 日付範囲を設定
            published_after = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'
            
            # 配信動画を検索
            request = self.youtube.search().list(
                part='snippet',
                channelId=channel_id,
                type='video',
                eventType='completed',  # 完了した配信のみ
                maxResults=max_results,
                publishedAfter=published_after,
                order='date'
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                video_details = self.get_video_details(video_id)
                if video_details:
                    videos.append(video_details)
            
            return videos
        except HttpError as e:
            print(f"配信動画取得エラー: {e}")
            return []
    
    def get_video_details(self, video_id: str) -> Optional[Dict]:
        """
        動画の詳細情報を取得
        
        Args:
            video_id: YouTube動画ID
            
        Returns:
            動画詳細情報の辞書
        """
        try:
            request = self.youtube.videos().list(
                part='snippet,contentDetails,statistics,liveStreamingDetails',
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                return response['items'][0]
            return None
        except HttpError as e:
            print(f"動画詳細取得エラー: {e}")
            return None
    
    def get_video_comments(
        self, 
        video_id: str, 
        max_results: int = 100
    ) -> List[Dict]:
        """
        動画のコメントを取得（タイムスタンプ付き）
        
        Args:
            video_id: YouTube動画ID
            max_results: 取得する最大件数
            
        Returns:
            コメントのリスト
        """
        try:
            comments = []
            request = self.youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=min(max_results, 100),
                order='time',
                textFormat='plainText'
            )
            
            while request and len(comments) < max_results:
                response = request.execute()
                
                for item in response['items']:
                    comment = item['snippet']['topLevelComment']['snippet']
                    comments.append({
                        'text': comment['textDisplay'],
                        'author': comment['authorDisplayName'],
                        'published_at': comment['publishedAt'],
                        'like_count': comment['likeCount']
                    })
                
                request = self.youtube.commentThreads().list_next(request, response)
            
            return comments[:max_results]
        except HttpError as e:
            print(f"コメント取得エラー: {e}")
            return []
    
    def get_video_statistics(self, video_id: str) -> Optional[Dict]:
        """
        動画の統計情報を取得
        
        Args:
            video_id: YouTube動画ID
            
        Returns:
            統計情報の辞書（視聴回数、高評価数など）
        """
        video = self.get_video_details(video_id)
        if video:
            return video.get('statistics', {})
        return None
    
    def get_analytics_report(
        self,
        video_id: str,
        start_date: str,
        end_date: str,
        metrics: str = 'views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration'
    ) -> Optional[Dict]:
        """
        YouTube Analytics APIで詳細なアナリティクスデータを取得
        
        Args:
            video_id: YouTube動画ID
            start_date: 開始日 (YYYY-MM-DD)
            end_date: 終了日 (YYYY-MM-DD)
            metrics: 取得するメトリクス (カンマ区切り)
            
        Returns:
            アナリティクスデータの辞書
            
        Note:
            この機能を使用するにはOAuth認証が必要です
        """
        if not self.youtube_analytics:
            print("Analytics API未初期化。OAuth認証が必要です。")
            return None
        
        try:
            request = self.youtube_analytics.reports().query(
                ids=f'channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics=metrics,
                dimensions='day',
                filters=f'video=={video_id}',
                sort='day'
            )
            response = request.execute()
            return response
        except HttpError as e:
            print(f"Analyticsデータ取得エラー: {e}")
            return None
    
    def search_videos(
        self,
        query: str,
        channel_id: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict]:
        """
        キーワードで動画を検索
        
        Args:
            query: 検索キーワード
            channel_id: チャンネルIDで絞り込み（オプション）
            max_results: 取得する最大件数
            
        Returns:
            検索結果の動画リスト
        """
        try:
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': max_results,
                'order': 'relevance'
            }
            
            if channel_id:
                params['channelId'] = channel_id
            
            request = self.youtube.search().list(**params)
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                video_details = self.get_video_details(video_id)
                if video_details:
                    videos.append(video_details)
            
            return videos
        except HttpError as e:
            print(f"動画検索エラー: {e}")
            return []
    
    def get_audience_retention(self, video_id: str) -> Optional[Dict]:
        """
        視聴維持率データを取得（Analytics API v2）
        
        Args:
            video_id: YouTube動画ID
            
        Returns:
            視聴維持率データ
            {
                'timestamps': [0, 30, 60, 90, ...],  # 秒数
                'retention_rates': [1.0, 0.9, 0.8, ...]  # 維持率（0-1）
            }
        """
        if not self.youtube_analytics:
            print("⚠️ Analytics API未初期化。OAuth認証が必要です。")
            return None
        
        try:
            # 動画の公開日を取得
            video_details = self.get_video_details(video_id)
            if not video_details:
                return None
            
            published_at = video_details['snippet']['publishedAt']
            start_date = published_at.split('T')[0]
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # 視聴維持率を取得
            request = self.youtube_analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='audienceWatchRatio,relativeRetentionPerformance',
                dimensions='elapsedVideoTimeRatio',
                filters=f'video=={video_id}',
                sort='elapsedVideoTimeRatio'
            )
            response = request.execute()
            
            # データを整形
            if 'rows' not in response:
                print(f"⚠️ 視聴維持率データが見つかりません: {video_id}")
                return None
            
            # 動画の長さを取得（秒）
            duration_str = video_details['contentDetails']['duration']
            duration_seconds = self._parse_duration_to_seconds(duration_str)
            
            timestamps = []
            retention_rates = []
            
            for row in response['rows']:
                elapsed_ratio = float(row[0])  # elapsedVideoTimeRatio (0-1)
                watch_ratio = float(row[1])    # audienceWatchRatio (0-1)
                
                timestamp = int(elapsed_ratio * duration_seconds)
                timestamps.append(timestamp)
                retention_rates.append(watch_ratio)
            
            print(f"✓ 視聴維持率データを取得: {len(timestamps)} ポイント")
            
            return {
                'timestamps': timestamps,
                'retention_rates': retention_rates,
                'video_id': video_id,
                'duration': duration_seconds
            }
            
        except HttpError as e:
            print(f"❌ 視聴維持率取得エラー: {e}")
            return None
    
    def _parse_duration_to_seconds(self, duration: str) -> int:
        """
        ISO 8601形式の期間を秒に変換
        
        Args:
            duration: ISO 8601形式の期間（例: PT1H30M45S）
            
        Returns:
            秒数
        """
        import re
        
        hours = re.search(r'(\d+)H', duration)
        minutes = re.search(r'(\d+)M', duration)
        seconds = re.search(r'(\d+)S', duration)
        
        total_seconds = 0
        if hours:
            total_seconds += int(hours.group(1)) * 3600
        if minutes:
            total_seconds += int(minutes.group(1)) * 60
        if seconds:
            total_seconds += int(seconds.group(1))
        
        return total_seconds


if __name__ == '__main__':
    # テスト実行
    from dotenv import load_dotenv
    load_dotenv()
    
    api = YouTubeAPI()
    
    # チャンネルIDのテスト
    channel_ids = os.getenv('TARGET_CHANNEL_IDS', '').split(',')
    
    for channel_id in channel_ids:
        print(f"\n=== チャンネル: {channel_id} ===")
        
        # チャンネル情報取得
        channel_info = api.get_channel_info(channel_id)
        if channel_info:
            print(f"チャンネル名: {channel_info['snippet']['title']}")
            print(f"登録者数: {channel_info['statistics']['subscriberCount']}")
        
        # 最近の配信取得
        livestreams = api.get_recent_livestreams(channel_id, max_results=5)
        print(f"\n最近の配信: {len(livestreams)}件")
        
        for i, video in enumerate(livestreams, 1):
            print(f"{i}. {video['snippet']['title']}")
            print(f"   ID: {video['id']}")
            print(f"   視聴回数: {video['statistics'].get('viewCount', 'N/A')}")
