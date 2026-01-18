"""
テスト実行スクリプト
1本の動画だけを処理してシステムをテスト
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from run_processor import YouTubeClipperPipeline
from src.utils.helpers import setup_logger


def test_single_video():
    """1本の動画でテスト実行"""
    load_dotenv()
    
    logger = setup_logger('test', log_file='./logs/test.log', level='INFO')
    
    print("=" * 60)
    print("YouTube切り抜き動画生成システム - テストモード")
    print("=" * 60)
    print()
    
    # パイプラインを初期化
    pipeline = YouTubeClipperPipeline()
    
    # 対象チャンネルを取得
    channel_ids = pipeline.config['target_channel_ids']
    
    print(f"対象チャンネル数: {len(channel_ids)}")
    print()
    
    # 動画IDの入力方法を選択
    print("テスト方法を選択してください:")
    print("1. 動画IDを直接入力")
    print("2. 最新の配信から1本選択")
    print()
    
    choice = input("選択 (1 または 2): ").strip()
    
    if choice == '1':
        # 直接入力
        video_id = input("\n動画ID（例: dQw4w9WgXcQ）を入力: ").strip()
        
        if not video_id:
            print("❌ 動画IDが入力されていません")
            return
        
        print(f"\n動画ID: {video_id} を処理します...")
        
    elif choice == '2':
        # 最新配信から選択
        print(f"\nチャンネルの最新配信を取得中...")
        
        all_videos = []
        for channel_id in channel_ids:
            if not channel_id.strip():
                continue
            
            print(f"\nチャンネル: {channel_id}")
            videos = pipeline.youtube_api.get_recent_livestreams(
                channel_id.strip(),
                max_results=5,
                days_back=7
            )
            
            for video in videos:
                all_videos.append({
                    'id': video['id'],
                    'title': video['snippet']['title'],
                    'channel_id': channel_id,
                    'published_at': video['snippet']['publishedAt']
                })
        
        if not all_videos:
            print("❌ 最近の配信が見つかりませんでした")
            return
        
        print(f"\n最近の配信 ({len(all_videos)}本):")
        print("-" * 60)
        
        for i, video in enumerate(all_videos, 1):
            print(f"{i}. {video['title']}")
            print(f"   ID: {video['id']} | 公開: {video['published_at'][:10]}")
            print()
        
        selection = input(f"処理する動画を選択 (1-{len(all_videos)}): ").strip()
        
        try:
            index = int(selection) - 1
            if 0 <= index < len(all_videos):
                video_id = all_videos[index]['id']
                print(f"\n選択: {all_videos[index]['title']}")
            else:
                print("❌ 無効な選択です")
                return
        except ValueError:
            print("❌ 数字を入力してください")
            return
    else:
        print("❌ 無効な選択です")
        return
    
    # 確認
    print("\n" + "=" * 60)
    print("処理を開始しますか？")
    print("=" * 60)
    confirm = input("続行 (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("キャンセルしました")
        return
    
    # 処理開始
    print("\n" + "=" * 60)
    print("処理開始")
    print("=" * 60)
    print()
    
    result = pipeline.process_video(video_id)
    
    # 結果表示
    print("\n" + "=" * 60)
    print("処理結果")
    print("=" * 60)
    
    if result.get('success'):
        print("✅ 処理成功！")
        print()
        print(f"動画タイトル: {result.get('video_title')}")
        print(f"出力ファイル: {result.get('output_file')}")
        print(f"動画の長さ: {result.get('duration')}")
        print(f"見どころ数: {len(result.get('highlights', []))}個")
        
        if result.get('note'):
            print(f"備考: {result.get('note')}")
        
        print()
        print("見どころタイムスタンプ:")
        for i, (start, end, score) in enumerate(result.get('highlights', []), 1):
            print(f"  {i}. {pipeline.analytics_processor.format_timestamp(start)} - "
                  f"{pipeline.analytics_processor.format_timestamp(end)} "
                  f"(スコア: {score:.2f})")
    else:
        print("❌ 処理失敗")
        print(f"エラー: {result.get('error')}")
    
    print()
    print("=" * 60)


def test_api_connection():
    """YouTube API接続テスト"""
    load_dotenv()
    
    print("=" * 60)
    print("YouTube API接続テスト")
    print("=" * 60)
    print()
    
    pipeline = YouTubeClipperPipeline()
    channel_ids = pipeline.config['target_channel_ids']
    
    for channel_id in channel_ids:
        if not channel_id.strip():
            continue
        
        print(f"チャンネル: {channel_id}")
        
        # チャンネル情報取得
        channel_info = pipeline.youtube_api.get_channel_info(channel_id.strip())
        
        if channel_info:
            print(f"  ✅ チャンネル名: {channel_info['snippet']['title']}")
            print(f"  ✅ 登録者数: {channel_info['statistics'].get('subscriberCount', 'N/A')}")
            
            # 最新配信取得
            videos = pipeline.youtube_api.get_recent_livestreams(
                channel_id.strip(),
                max_results=1,
                days_back=30
            )
            
            if videos:
                print(f"  ✅ 最新配信: {videos[0]['snippet']['title']}")
            else:
                print(f"  ⚠️  最近の配信なし（30日以内）")
        else:
            print(f"  ❌ チャンネル情報取得失敗")
        
        print()


def main():
    """メイン関数"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'api':
            # API接続テスト
            test_api_connection()
        elif command == 'video' and len(sys.argv) > 2:
            # 動画IDを引数で指定
            video_id = sys.argv[2]
            
            load_dotenv()
            pipeline = YouTubeClipperPipeline()
            
            print(f"動画ID: {video_id} を処理中...")
            result = pipeline.process_video(video_id)
            
            if result.get('success'):
                print(f"✅ 処理成功: {result.get('output_file')}")
            else:
                print(f"❌ 処理失敗: {result.get('error')}")
        else:
            print("使い方:")
            print("  python test_run.py          # 対話形式でテスト")
            print("  python test_run.py api      # API接続テスト")
            print("  python test_run.py video ID # 指定した動画IDを処理")
    else:
        # 対話形式
        test_single_video()


if __name__ == '__main__':
    main()
