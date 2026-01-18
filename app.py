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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            font-size: 1.1em;
        }
        .card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .status-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .status-box h3 {
            font-size: 2em;
            margin-bottom: 5px;
        }
        .status-box p {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 5px;
            font-size: 1em;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn:active {
            transform: translateY(0);
        }
        .channel-list {
            list-style: none;
        }
        .channel-item {
            background: #f5f5f5;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .channel-item code {
            background: #e0e0e0;
            padding: 5px 10px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        .log-output {
            background: #1e1e1e;
            color: #00ff00;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            max-height: 400px;
            overflow-y: auto;
        }
        .config-table {
            width: 100%;
            border-collapse: collapse;
        }
        .config-table th,
        .config-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .config-table th {
            background: #f5f5f5;
            font-weight: bold;
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
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 YouTube Clipper Dashboard</h1>
            <p class="subtitle">自動切り抜き動画生成システム</p>
        </div>
        
        <div class="card">
            <h2>📊 システムステータス</h2>
            <div class="status-grid">
                <div class="status-box">
                    <h3 id="total-processed">0</h3>
                    <p>処理済み動画</p>
                </div>
                <div class="status-box">
                    <h3 id="total-channels">{{ channel_count }}</h3>
                    <p>監視チャンネル</p>
                </div>
                <div class="status-box">
                    <h3 id="queue-size">0</h3>
                    <p>待機中</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>🎯 対象チャンネル</h2>
            <ul class="channel-list">
                {% for channel_id in channel_ids %}
                <li class="channel-item">
                    <div>
                        <strong>チャンネル {{ loop.index }}</strong><br>
                        <code>{{ channel_id }}</code>
                    </div>
                    <button class="btn" onclick="processChannel('{{ channel_id }}')">処理実行</button>
                </li>
                {% endfor %}
            </ul>
        </div>
        
        <div class="card">
            <h2>▶️ 処理実行</h2>
            <button class="btn" onclick="processAllChannels()" style="width: 100%;">全チャンネルを処理</button>
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>処理中...</p>
            </div>
        </div>
        
        <div class="card">
            <h2>⏰ 自動実行設定</h2>
            <p style="margin-bottom: 15px;">毎日前日の配信を自動的に切り抜き動画に変換します。</p>
            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                <button class="btn" onclick="enableAutoRun()" style="flex: 1; background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                    ✓ 自動実行を有効にする
                </button>
                <button class="btn" onclick="disableAutoRun()" style="flex: 1; background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                    ✗ 自動実行を無効にする
                </button>
            </div>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                <strong>現在のステータス:</strong> <span id="auto-run-status">読み込み中...</span>
            </div>
            <button class="btn" onclick="processYesterday()" style="width: 100%; margin-top: 15px;">
                📅 前日の配信を今すぐ処理
            </button>
        </div>
        
        <div class="card">
            <h2>⚙️ 設定</h2>
            <table class="config-table">
                <tr>
                    <th>項目</th>
                    <th>値</th>
                </tr>
                <tr>
                    <td>目標動画長</td>
                    <td>{{ config.clip_duration_target }}秒 ({{ config.clip_duration_target // 60 }}分)</td>
                </tr>
                <tr>
                    <td>見どころスコア閾値</td>
                    <td>{{ config.min_highlight_score }}</td>
                </tr>
                <tr>
                    <td>動画解像度</td>
                    <td>{{ config.video_resolution }}</td>
                </tr>
                <tr>
                    <td>ジャンプカット</td>
                    <td>{{ '有効' if config.jump_cut_enabled else '無効' }}</td>
                </tr>
                <tr>
                    <td>字幕フォントサイズ</td>
                    <td>{{ config.subtitle_font_size }}px</td>
                </tr>
            </table>
        </div>
        
        <div class="card">
            <h2>📝 処理ログ</h2>
            <div class="log-output" id="log-output">
                待機中...
            </div>
        </div>
    </div>
    
    <script>
        function processChannel(channelId) {
            if (confirm(`チャンネル ${channelId} の処理を開始しますか？`)) {
                showLoading();
                fetch('/api/process-channel', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({channel_id: channelId})
                })
                .then(res => res.json())
                .then(data => {
                    hideLoading();
                    alert(data.message);
                    updateLog(JSON.stringify(data, null, 2));
                })
                .catch(err => {
                    hideLoading();
                    alert('エラーが発生しました: ' + err);
                });
            }
        }
        
        function processAllChannels() {
            if (confirm('全チャンネルの処理を開始しますか？時間がかかる場合があります。')) {
                showLoading();
                fetch('/api/process-all', {
                    method: 'POST'
                })
                .then(res => res.json())
                .then(data => {
                    hideLoading();
                    alert(data.message);
                    updateLog(JSON.stringify(data, null, 2));
                })
                .catch(err => {
                    hideLoading();
                    alert('エラーが発生しました: ' + err);
                });
            }
        }
        
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
        
        function enableAutoRun() {
            if (confirm('自動実行を有効にしますか？毎日前日の配信が自動処理されます。')) {
                fetch('/api/auto-run/enable', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        alert(data.message);
                        updateAutoRunStatus();
                    })
                    .catch(err => alert('エラー: ' + err));
            }
        }
        
        function disableAutoRun() {
            if (confirm('自動実行を無効にしますか？')) {
                fetch('/api/auto-run/disable', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        alert(data.message);
                        updateAutoRunStatus();
                    })
                    .catch(err => alert('エラー: ' + err));
            }
        }
        
        function processYesterday() {
            if (confirm('前日の配信を処理しますか？時間がかかる場合があります。')) {
                showLoading();
                fetch('/api/process-yesterday', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        hideLoading();
                        alert(data.message);
                        updateLog(JSON.stringify(data, null, 2));
                    })
                    .catch(err => {
                        hideLoading();
                        alert('エラー: ' + err);
                    });
            }
        }
        
        function updateAutoRunStatus() {
            fetch('/api/auto-run/status')
                .then(res => res.json())
                .then(data => {
                    const statusEl = document.getElementById('auto-run-status');
                    if (data.enabled) {
                        statusEl.innerHTML = '<span style="color: #43e97b; font-weight: bold;">✓ 有効</span>';
                    } else {
                        statusEl.innerHTML = '<span style="color: #fa709a; font-weight: bold;">✗ 無効</span>';
                    }
                });
        }
        
        function updateLog(message) {
            const logOutput = document.getElementById('log-output');
            logOutput.textContent = message;
            logOutput.scrollTop = logOutput.scrollHeight;
        }
        
        // ステータスを定期的に更新
        setInterval(() => {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('total-processed').textContent = data.total_processed;
                    document.getElementById('queue-size').textContent = data.queue_size;
                });
            
            updateAutoRunStatus();
        }, 5000);
        
        // 初回ロード時にステータスを更新
        updateAutoRunStatus();
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """ダッシュボード表示"""
    p = init_pipeline()
    
    return render_template_string(
        HTML_TEMPLATE,
        channel_ids=p.config['target_channel_ids'],
        channel_count=len(p.config['target_channel_ids']),
        config=p.config
    )


@app.route('/api/status')
def get_status():
    """システムステータスを取得"""
    p = init_pipeline()
    
    # 出力ディレクトリの動画数を数える
    output_dir = p.config['output_dir']
    total_processed = 0
    if os.path.exists(output_dir):
        total_processed = len([f for f in os.listdir(output_dir) if f.endswith('.mp4')])
    
    return jsonify({
        'total_processed': total_processed,
        'queue_size': job_queue.qsize(),
        'status': 'running'
    })


@app.route('/api/process-channel', methods=['POST'])
def process_channel():
    """チャンネルを処理"""
    data = request.json
    channel_id = data.get('channel_id')
    
    if not channel_id:
        return jsonify({'error': 'channel_id が必要です'}), 400
    
    # 非同期処理（実際の実装では別スレッドで実行すべき）
    p = init_pipeline()
    results = p.process_channel(channel_id, max_videos=3)
    
    success_count = sum(1 for r in results if r.get('success'))
    
    return jsonify({
        'message': f'処理完了: {success_count}本成功',
        'results': results
    })


@app.route('/api/process-all', methods=['POST'])
def process_all():
    """全チャンネルを処理"""
    p = init_pipeline()
    summary = p.run_all_channels()
    
    return jsonify({
        'message': f'全チャンネル処理完了: 成功 {summary["total_success"]}本, 失敗 {summary["total_failed"]}本',
        'summary': summary
    })


@app.route('/api/videos')
def list_videos():
    """出力済み動画一覧を取得"""
    p = init_pipeline()
    output_dir = p.config['output_dir']
    
    videos = []
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith('.mp4'):
                file_path = os.path.join(output_dir, filename)
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                videos.append({
                    'filename': filename,
                    'size_mb': round(file_size, 2),
                    'path': file_path
                })
    
    return jsonify({'videos': videos})


@app.route('/api/auto-run/status')
def get_auto_run_status():
    """自動実行のステータスを取得"""
    s = init_scheduler()
    return jsonify({
        'enabled': s.is_enabled(),
        'status': '有効' if s.is_enabled() else '無効'
    })


@app.route('/api/auto-run/enable', methods=['POST'])
def enable_auto_run():
    """自動実行を有効にする"""
    s = init_scheduler()
    s.set_auto_run(True)
    return jsonify({
        'success': True,
        'message': '自動実行を有効にしました',
        'enabled': True
    })


@app.route('/api/auto-run/disable', methods=['POST'])
def disable_auto_run():
    """自動実行を無効にする"""
    s = init_scheduler()
    s.set_auto_run(False)
    return jsonify({
        'success': True,
        'message': '自動実行を無効にしました',
        'enabled': False
    })


@app.route('/api/process-yesterday', methods=['POST'])
def process_yesterday():
    """前日の配信を処理"""
    s = init_scheduler()
    summary = s.process_yesterday_streams()
    
    return jsonify({
        'message': f'前日配信処理完了: 成功 {summary["total_success"]}本, 失敗 {summary["total_failed"]}本',
        'summary': summary
    })


def main():
    """メイン関数"""
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)


if __name__ == '__main__':
    main()
