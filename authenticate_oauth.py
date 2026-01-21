#!/usr/bin/env python3
"""
YouTube Analytics API v2 初回認証スクリプト

このスクリプトをローカル環境で実行して、OAuth認証を完了します。
認証後、token.pickleファイルが生成されます。
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.api.youtube_api import YouTubeAPI

def main():
    print("=" * 60)
    print("YouTube Analytics API v2 初回認証")
    print("=" * 60)
    print()
    
    # 環境変数をロード
    load_dotenv()
    
    # credentials.jsonが存在するか確認
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json が見つかりません")
        print()
        print("以下の手順で配置してください:")
        print("1. Google Cloud Console からダウンロードした credentials.json を")
        print("   このプロジェクトのルートディレクトリに配置")
        print()
        return False
    
    print("✓ credentials.json が見つかりました")
    print()
    
    # APIキーを確認
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("⚠️ YOUTUBE_API_KEY が設定されていません")
        print("   .env ファイルに YOUTUBE_API_KEY を設定してください")
        print()
    else:
        print("✓ YOUTUBE_API_KEY が設定されています")
        print()
    
    # YouTubeAPIを初期化（OAuth認証が実行される）
    print("📝 OAuth認証を開始します...")
    print("   ブラウザが開きます。以下の手順で認証してください:")
    print()
    print("   1. API設定アカウント（現在のYouTube API KEYを設定したアカウント）でログイン")
    print("   2. 「このアプリは確認されていません」と表示された場合:")
    print("      → 「詳細」をクリック → 「（アプリ名）に移動（安全ではないページ）」をクリック")
    print("   3. 権限リクエストを確認して「許可」をクリック")
    print()
    input("準備ができたら Enter キーを押してください...")
    print()
    
    try:
        api = YouTubeAPI(
            api_key=api_key,
            credentials_file='credentials.json'
        )
        
        # Analytics APIが初期化されたか確認
        if api.youtube_analytics:
            print()
            print("=" * 60)
            print("✅ OAuth認証が完了しました！")
            print("=" * 60)
            print()
            print("token.pickle ファイルが生成されました。")
            print()
            print("次のステップ:")
            print("1. token.pickle をBase64エンコード:")
            print("   base64 token.pickle")
            print()
            print("2. 出力された文字列をコピー")
            print()
            print("3. Renderの環境変数に設定:")
            print("   YOUTUBE_OAUTH_TOKEN=<コピーした文字列>")
            print()
            
            # テスト: チャンネル情報を取得
            channel_ids = os.getenv('TARGET_CHANNEL_IDS', '').split(',')
            if channel_ids and channel_ids[0]:
                print("=" * 60)
                print("テスト: チャンネル情報を取得")
                print("=" * 60)
                print()
                
                test_channel_id = channel_ids[0].strip()
                channel_info = api.get_channel_info(test_channel_id)
                
                if channel_info:
                    print(f"✓ チャンネル名: {channel_info['snippet']['title']}")
                    print(f"✓ 登録者数: {channel_info['statistics']['subscriberCount']}")
                    print()
                    
                    # 最近の配信を取得
                    livestreams = api.get_recent_livestreams(test_channel_id, max_results=1)
                    if livestreams:
                        video = livestreams[0]
                        video_id = video['id']
                        video_title = video['snippet']['title']
                        
                        print(f"最近の配信: {video_title}")
                        print(f"動画ID: {video_id}")
                        print()
                        
                        # 視聴維持率を取得（テスト）
                        print("視聴維持率データを取得中...")
                        retention_data = api.get_audience_retention(video_id)
                        
                        if retention_data:
                            print(f"✅ 視聴維持率データを取得: {len(retention_data['timestamps'])} ポイント")
                            print(f"   動画の長さ: {retention_data['duration']}秒")
                            print()
                        else:
                            print("⚠️ 視聴維持率データが取得できませんでした")
                            print("   原因:")
                            print("   - 動画が公開直後でデータが蓄積されていない")
                            print("   - Analytics APIにアクセス権限がない")
                            print()
            
            return True
        else:
            print()
            print("❌ Analytics API の初期化に失敗しました")
            print()
            return False
            
    except Exception as e:
        print()
        print(f"❌ エラーが発生しました: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
