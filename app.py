"""
Flask Webアプリケーション
処理状況の確認と手動実行用のダッシュボード
"""

import os
import sys
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request, send_file
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import threading
import queue
import tempfile
import uuid

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from run_processor import YouTubeClipperPipeline
from auto_scheduler import AutoScheduler
from task_manager import task_queue
from src.editor.video_editor import VideoEditor
from src.subtitle.subtitle_generator import SubtitleGenerator

# 環境変数をロード
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB
app.config['UPLOAD_FOLDER'] = Path(tempfile.gettempdir()) / 'youtube_clipper_uploads'
app.config['OUTPUT_FOLDER'] = Path(tempfile.gettempdir()) / 'youtube_clipper_outputs'
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
app.config['OUTPUT_FOLDER'].mkdir(parents=True, exist_ok=True)

# 処理キュー（非同期処理用）
job_queue = queue.Queue()
job_results = {}

# ハイライトキャッシュ
if not hasattr(app, 'highlight_cache'):
    app.highlight_cache = {}

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
    """
    単一動画のテスト処理（見どころ検出のみ）
    結果を返し、ユーザーが動画をアップロードできるようにする
    """
    try:
        data = request.get_json()
        video_id = data.get('video_id', '').strip()
        
        if not video_id:
            return jsonify({'success': False, 'error': '動画IDが指定されていません'}), 400
        
        # パイプラインを初期化
        pipeline = init_pipeline()
        
        # 見どころ検出のみ実行（ダウンロード・編集はしない）
        result = pipeline.detect_highlights_only(video_id)
        
        if result and result.get('success'):
            # セッションに結果を保存（動画アップロード時に使用）
            session_key = f"highlights_{video_id}"
            # メモリに保存（簡易実装）
            if not hasattr(app, 'highlight_cache'):
                app.highlight_cache = {}
            app.highlight_cache[session_key] = result
            
            return jsonify({
                'success': True,
                'message': '見どころを検出しました。動画をアップロードしてください。',
                'video_id': video_id,
                'video_title': result.get('video_title', ''),
                'video_duration': result.get('video_duration', 0),
                'highlights': result.get('highlights', []),
                'highlights_count': len(result.get('highlights', [])),
                'stats': result.get('stats', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '見どころ検出に失敗しました')
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
    stats = task_queue.get_stats()
    return jsonify({
        'success': True,
        'total_processed': stats['completed'],
        'queue_size': stats['pending'],
        'task_stats': stats
    })


# ============================================================
# 動画アップロード & 切り抜き生成 API
# ============================================================

@app.route('/api/upload-video', methods=['POST'])
def api_upload_video():
    """
    動画をアップロードして切り抜き動画を生成
    """
    try:
        # ファイルの確認
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': '動画ファイルがアップロードされていません'}), 400
        
        video_file = request.files['video']
        video_id = request.form.get('video_id', '').strip()
        
        if not video_id:
            return jsonify({'success': False, 'error': '動画IDが指定されていません'}), 400
        
        if video_file.filename == '':
            return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400
        
        # ハイライト情報を取得
        session_key = f"highlights_{video_id}"
        if session_key not in app.highlight_cache:
            return jsonify({'success': False, 'error': '先に見どころ検出を実行してください'}), 400
        
        highlight_data = app.highlight_cache[session_key]
        highlights = highlight_data.get('highlights', [])
        
        if not highlights:
            return jsonify({'success': False, 'error': '見どころが検出されていません'}), 400
        
        # ファイルを保存
        filename = secure_filename(f"{video_id}_{uuid.uuid4().hex[:8]}.mp4")
        upload_path = app.config['UPLOAD_FOLDER'] / filename
        video_file.save(str(upload_path))
        
        # 非同期処理用のジョブIDを生成
        job_id = str(uuid.uuid4())
        
        # バックグラウンドで切り抜き動画を生成
        def process_video_job():
            try:
                job_results[job_id] = {
                    'status': 'processing',
                    'progress': 0,
                    'message': '処理を開始しています...'
                }
                
                # 動画編集の準備
                video_editor = VideoEditor(
                    output_dir=str(app.config['OUTPUT_FOLDER']),
                    temp_dir=str(app.config['UPLOAD_FOLDER'] / 'temp')
                )
                
                # クリップを生成
                job_results[job_id]['message'] = 'クリップを生成中...'
                job_results[job_id]['progress'] = 20
                
                clips = []
                temp_dir = app.config['UPLOAD_FOLDER'] / 'temp'
                temp_dir.mkdir(exist_ok=True)
                
                for i, highlight in enumerate(highlights, 1):
                    start = highlight['start']
                    end = highlight['end']
                    clip_path = temp_dir / f"{video_id}_clip_{i:02d}.mp4"
                    
                    result = video_editor.extract_clip(str(upload_path), str(clip_path), start, end)
                    
                    if result:
                        clips.append(str(clip_path))
                    
                    job_results[job_id]['progress'] = 20 + (40 * i // len(highlights))
                
                if not clips:
                    raise Exception("クリップ生成に失敗しました")
                
                # クリップを結合
                job_results[job_id]['message'] = 'クリップを結合中...'
                job_results[job_id]['progress'] = 60
                
                combined_path = app.config['OUTPUT_FOLDER'] / f"{video_id}_highlight.mp4"
                result = video_editor.concatenate_videos(clips, str(combined_path))
                
                if not result:
                    raise Exception("クリップ結合に失敗しました")
                
                # 字幕生成
                job_results[job_id]['message'] = '字幕を生成中...'
                job_results[job_id]['progress'] = 80
                
                subtitle_gen = SubtitleGenerator()
                subtitle_path = app.config['OUTPUT_FOLDER'] / f"{video_id}_highlight.srt"
                subtitle_gen.generate_subtitle(str(combined_path), str(subtitle_path))
                
                # 完了
                job_results[job_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': '切り抜き動画が完成しました！',
                    'output_file': str(combined_path),
                    'subtitle_file': str(subtitle_path),
                    'video_id': video_id,
                    'download_url': f'/api/download/{video_id}'
                }
                
                # アップロードファイルを削除
                upload_path.unlink(missing_ok=True)
                
                # 一時ファイルを削除
                for clip in clips:
                    Path(clip).unlink(missing_ok=True)
                
            except Exception as e:
                job_results[job_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'message': f'エラー: {str(e)}'
                }
        
        # バックグラウンドスレッドで処理を開始
        thread = threading.Thread(target=process_video_job)
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': '処理を開始しました'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/job-status/<job_id>', methods=['GET'])
def api_job_status(job_id):
    """ジョブの処理状況を取得"""
    if job_id not in job_results:
        return jsonify({'success': False, 'error': 'ジョブが見つかりません'}), 404
    
    return jsonify({
        'success': True,
        **job_results[job_id]
    })


@app.route('/api/download/<video_id>', methods=['GET'])
def api_download(video_id):
    """完成した動画をダウンロード"""
    try:
        video_path = app.config['OUTPUT_FOLDER'] / f"{video_id}_highlight.mp4"
        
        if not video_path.exists():
            return jsonify({'success': False, 'error': 'ファイルが見つかりません'}), 404
        
        return send_file(
            str(video_path),
            as_attachment=True,
            download_name=f"{video_id}_highlight.mp4",
            mimetype='video/mp4'
        )
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# タスク管理 API（ローカルワーカー用）
# ============================================================

@app.route('/api/tasks/create', methods=['POST'])
def api_create_task():
    """
    タスクを作成（見どころ検出後に呼び出し）
    
    Request Body:
    {
        "video_id": "dQw4w9WgXcQ",
        "video_title": "Rick Astley - Never Gonna Give You Up",
        "highlights": [
            {"start": 30, "end": 60, "score": 0.85},
            {"start": 120, "end": 150, "score": 0.78}
        ],
        "channel_id": "UCrzO_hsFW8vLLy8xFBADfqQ"
    }
    """
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        video_title = data.get('video_title', '')
        highlights = data.get('highlights', [])
        channel_id = data.get('channel_id')
        
        if not video_id or not highlights:
            return jsonify({'success': False, 'error': '必須パラメータが不足しています'}), 400
        
        # タスクを作成
        task = task_queue.add_task(video_id, video_title, highlights, channel_id)
        
        return jsonify({
            'success': True,
            'task': task.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/pending', methods=['GET'])
def api_get_pending_task():
    """
    処理待ちタスクを1つ取得（ローカルワーカーがポーリング）
    
    Response:
    {
        "success": true,
        "task": {
            "task_id": "uuid",
            "video_id": "dQw4w9WgXcQ",
            "video_title": "...",
            "highlights": [...],
            "status": "pending"
        }
    }
    """
    try:
        task = task_queue.get_pending_task()
        
        if task:
            # タスクを processing 状態に変更
            worker_id = request.args.get('worker_id', 'unknown-worker')
            task.start_processing(worker_id)
            
            return jsonify({
                'success': True,
                'task': task.to_dict()
            })
        else:
            return jsonify({
                'success': True,
                'task': None,
                'message': '処理待ちタスクはありません'
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/complete', methods=['POST'])
def api_complete_task():
    """
    タスク完了を通知（ローカルワーカーから）
    
    Request Body:
    {
        "task_id": "uuid",
        "output_file": "/path/to/output.mp4",
        "worker_id": "local-worker-1"
    }
    """
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        output_file = data.get('output_file')
        worker_id = data.get('worker_id', 'unknown')
        
        if not task_id or not output_file:
            return jsonify({'success': False, 'error': '必須パラメータが不足しています'}), 400
        
        task = task_queue.get_task(task_id)
        
        if not task:
            return jsonify({'success': False, 'error': 'タスクが見つかりません'}), 404
        
        task.complete(output_file)
        
        return jsonify({
            'success': True,
            'message': 'タスクを完了としてマークしました',
            'task': task.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/error', methods=['POST'])
def api_error_task():
    """
    タスクエラーを通知（ローカルワーカーから）
    
    Request Body:
    {
        "task_id": "uuid",
        "error": "エラーメッセージ",
        "worker_id": "local-worker-1"
    }
    """
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        error_message = data.get('error', '不明なエラー')
        worker_id = data.get('worker_id', 'unknown')
        
        if not task_id:
            return jsonify({'success': False, 'error': 'タスクIDが必要です'}), 400
        
        task = task_queue.get_task(task_id)
        
        if not task:
            return jsonify({'success': False, 'error': 'タスクが見つかりません'}), 404
        
        task.fail(error_message)
        
        return jsonify({
            'success': True,
            'message': 'タスクをエラーとしてマークしました',
            'task': task.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/list', methods=['GET'])
def api_list_tasks():
    """
    タスク一覧を取得
    
    Query Parameters:
    - status: pending, processing, completed, failed (オプション)
    - limit: 取得件数（デフォルト: 50）
    """
    try:
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        if status:
            tasks = task_queue.get_tasks_by_status(status)
        else:
            tasks = task_queue.get_all_tasks()
        
        # 最新順にソート
        tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)
        
        # 制限
        tasks = tasks[:limit]
        
        return jsonify({
            'success': True,
            'tasks': [task.to_dict() for task in tasks],
            'stats': task_queue.get_stats()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tasks/<task_id>', methods=['GET'])
def api_get_task(task_id):
    """特定のタスクを取得"""
    try:
        task = task_queue.get_task(task_id)
        
        if not task:
            return jsonify({'success': False, 'error': 'タスクが見つかりません'}), 404
        
        return jsonify({
            'success': True,
            'task': task.to_dict()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting Flask dashboard on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
