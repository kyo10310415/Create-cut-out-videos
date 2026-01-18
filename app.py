"""
Flask Webアプリケーション
処理状況の確認と手動実行用のダッシュボード
"""

import os
import sys
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request
from dotenv import load_dotenv
import threading
import queue

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from run_processor import YouTubeClipperPipeline
from auto_scheduler import AutoScheduler

# 環境変数をロード
load_dotenv()

app = Flask(__name__)

# 処理キュー（非同期処理用）
job_queue = queue.Queue()
job_results = {}

# パイプライン（遅延初期化）
pipeline = None
scheduler = None


def init_pipeline():
    """パイプラインを初期化"""
    global pipeline
    if pipeline is None:
        pipeline = YouTubeClipperPipeline()
    return pipeline


def init_scheduler():
    """スケジューラーを初期化"""
    global scheduler
    if scheduler is None:
        scheduler = AutoScheduler()
    return scheduler


# HTMLテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Clipper Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .log-output {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1em;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 YouTube Clipper Dashboard</h1>
            <p>YouTube配信の切り抜き動画自動生成システム</p>
        </div>
        
        <div class="card">
            <h2>🧪 テストモード</h2>
            <p style="margin-bottom: 15px;">1本の動画だけを処理してシステムをテストできます。</p>
            
            <input 
                type="text" 
                id="test-video-id" 
                placeholder="例: dQw4w9WgXcQ"
            />
            
            <button class="btn" onclick="testSingleVideo()" style="width: 100%; margin-bottom: 10px;">
                🎬 この動画を処理
            </button>
        </div>
        
        <div class="card">
            <h2>⏰ 自動実行設定</h2>
            <p style="margin-bottom: 15px;">毎日前日の配信を自動的に切り抜き動画に変換します。</p>
            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                <button class="btn" onclick="enableAutoRun()" style="flex: 1;">
                    ✓ 有効にする
                </button>
                <button class="btn" onclick="disableAutoRun()" style="flex: 1;">
                    ✗ 無効にする
                </button>
            </div>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                <strong>現在のステータス:</strong> <span id="auto-run-status">読み込み中...</span>
            </div>
        </div>
        
        <div class="card">
            <h2>📝 処理ログ</h2>
            <div class="log-output" id="log-output">
                待機中...
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>処理中...</p>
        </div>
    </div>
    
    <script>
        function showLoading() {
            document.getElementById('loading').classList.add('active');
        }
        
        function hideLoading() {
            document.getElementById('loading').classList.remove('active');
        }
        
        function updateLog(message) {
            const logOutput = document.getElementById('log-output');
            logOutput.textContent = message;
            logOutput.scrollTop = logOutput.scrollHeight;
        }
        
        function testSingleVideo() {
            console.log('testSingleVideo called');
            const videoId = document.getElementById('test-video-id').value.trim();
            console.log('Video ID:', videoId);
            
            if (!videoId) {
                alert('動画IDを入力してください');
                return;
            }
            
            if (confirm('動画ID: ' + videoId + '\\nこの動画を処理しますか？テストのため時間がかかります。')) {
                console.log('Processing video:', videoId);
                showLoading();
                updateLog('処理を開始しています...');
                
                fetch('/api/test-video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({video_id: videoId})
                })
                .then(function(res) {
                    console.log('Response status:', res.status);
                    return res.json();
                })
                .then(function(data) {
                    console.log('Response data:', data);
                    hideLoading();
                    if (data.success) {
                        alert('✅ テスト処理成功!\\n出力: ' + data.result.output_file);
                        updateLog(JSON.stringify(data.result, null, 2));
                    } else {
                        alert('❌ テスト処理失敗\\nエラー: ' + data.error);
                        updateLog('エラー: ' + data.error);
                    }
                })
                .catch(function(err) {
                    console.error('Fetch error:', err);
                    hideLoading();
                    alert('エラー: ' + err);
                    updateLog('エラー: ' + err);
                });
            }
        }
        
        function enableAutoRun() {
            if (confirm('自動実行を有効にしますか？毎日前日の配信が自動処理されます。')) {
                fetch('/api/auto-run/enable', { method: 'POST' })
                    .then(function(res) { return res.json(); })
                    .then(function(data) {
                        alert(data.message);
                        updateAutoRunStatus();
                    })
                    .catch(function(err) { alert('エラー: ' + err); });
            }
        }
        
        function disableAutoRun() {
            if (confirm('自動実行を無効にしますか？')) {
                fetch('/api/auto-run/disable', { method: 'POST' })
                    .then(function(res) { return res.json(); })
                    .then(function(data) {
                        alert(data.message);
                        updateAutoRunStatus();
                    })
                    .catch(function(err) { alert('エラー: ' + err); });
            }
        }
        
        function updateAutoRunStatus() {
            fetch('/api/auto-run/status')
                .then(function(res) { return res.json(); })
                .then(function(data) {
                    const statusEl = document.getElementById('auto-run-status');
                    if (data.enabled) {
                        statusEl.innerHTML = '<span style="color: #43e97b; font-weight: bold;">✓ 有効</span>';
                    } else {
                        statusEl.innerHTML = '<span style="color: #fa709a; font-weight: bold;">✗ 無効</span>';
                    }
                });
        }
        
        // 初回ロード時にステータスを更新
        updateAutoRunStatus();
        
        // 定期的にステータスを更新
        setInterval(updateAutoRunStatus, 10000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """ダッシュボードページ"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/test-video', methods=['POST'])
def api_test_video():
    """単一動画のテスト処理"""
    try:
        data = request.get_json()
        video_id = data.get('video_id', '').strip()
        
        if not video_id:
            return jsonify({'success': False, 'error': '動画IDが指定されていません'}), 400
        
        # パイプラインを初期化
        pipeline = init_pipeline()
        
        # 動画を処理
        result = pipeline.process_video(video_id)
        
        if result and result.get('success'):
            return jsonify({
                'success': True,
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '処理に失敗しました')
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auto-run/enable', methods=['POST'])
def api_enable_auto_run():
    """自動実行を有効化"""
    try:
        scheduler = init_scheduler()
        scheduler.enable()
        return jsonify({'success': True, 'message': '自動実行を有効にしました'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auto-run/disable', methods=['POST'])
def api_disable_auto_run():
    """自動実行を無効化"""
    try:
        scheduler = init_scheduler()
        scheduler.disable()
        return jsonify({'success': True, 'message': '自動実行を無効にしました'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auto-run/status', methods=['GET'])
def api_auto_run_status():
    """自動実行の状態を取得"""
    try:
        scheduler = init_scheduler()
        enabled = scheduler.is_enabled()
        return jsonify({
            'success': True,
            'enabled': enabled
        })
    except Exception as e:
        print(f"Error in auto-run status: {e}")
        import traceback
        traceback.print_exc()
        # エラーが起きてもデフォルト値を返す
        return jsonify({
            'success': True,
            'enabled': False
        })


@app.route('/api/status', methods=['GET'])
def api_status():
    """システムステータスを取得"""
    return jsonify({
        'success': True,
        'total_processed': 0,
        'queue_size': job_queue.qsize()
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting Flask dashboard on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
