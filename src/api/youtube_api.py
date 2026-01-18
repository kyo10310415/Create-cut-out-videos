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
        
        # Analytics API (OAuth認証が必要)
        if self.credentials_file and os.path.exists(self.credentials_file):
            creds = self._get_authenticated_credentials()
            if creds:
                self.youtube_analytics = build('youtubeAnalytics', 'v2', credentials=creds)
    
    def _get_authenticated_credentials(self) -> Optional[Credentials]:
        """OAuth認証を行い、認証情報を取得"""
        creds = None
        token_file = 'token.pickle'
        
        # トークンファイルが存在すれば読み込む
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # 認証情報が無効な場合は再認証
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # トークンを保存
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
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
