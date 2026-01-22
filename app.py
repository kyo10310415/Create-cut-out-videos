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
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Clipper - 切り抜き動画生成</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
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
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .card h2 {
            margin-bottom: 20px;
            color: #333;
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        .input-group label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        
        input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            width: 100%;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .highlights-list {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }
        
        .highlight-item {
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 4px solid #667eea;
        }
        
        .highlight-time {
            font-weight: bold;
            color: #667eea;
        }
        
        .highlight-score {
            color: #764ba2;
            font-size: 0.9em;
        }
        
        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 8px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s;
            cursor: pointer;
            margin-top: 20px;
        }
        
        .upload-area:hover {
            border-color: #667eea;
            background: #f8f9fa;
        }
        
        .upload-area.dragover {
            border-color: #667eea;
            background: #e7eaff;
        }
        
        .upload-icon {
            font-size: 3em;
            margin-bottom: 10px;
        }
        
        .progress-container {
            width: 100%;
            background: #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
            margin: 20px 0;
        }
        
        .progress-bar {
            height: 30px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        
        .status-message {
            text-align: center;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
        
        .status-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .status-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .hidden {
            display: none;
        }
        
        .download-btn {
            background: #28a745;
            margin-top: 15px;
        }
        
        .download-btn:hover {
            box-shadow: 0 5px 15px rgba(40, 167, 69, 0.4);
        }
        
        .video-info {
            background: #e7eaff;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
        
        .video-info h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #ddd;
        }
        
        .info-row:last-child {
            border-bottom: none;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
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
            <h1>🎬 YouTube Clipper</h1>
            <p>切り抜き動画自動生成システム</p>
        </div>
        
        <!-- ステップ1: 見どころ検出 -->
        <div class="card" id="step1-card">
            <h2>📊 ステップ1: 見どころ検出</h2>
            <p style="margin-bottom: 20px; color: #666;">
                YouTube動画のURLまたはIDを入力して、見どころを自動検出します
            </p>
            
            <div class="input-group">
                <label for="video-id">動画URL または 動画ID</label>
                <input 
                    type="text" 
                    id="video-id" 
                    placeholder="例: dQw4w9WgXcQ または https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                />
            </div>
            
            <button class="btn" onclick="detectHighlights()" id="detect-btn">
                🔍 見どころを検出
            </button>
            
            <div id="detection-status" class="hidden"></div>
        </div>
        
        <!-- ステップ2: 検出結果 -->
        <div class="card hidden" id="step2-card">
            <h2>✅ ステップ2: 検出結果</h2>
            
            <div class="video-info" id="video-info"></div>
            
            <div class="highlights-list" id="highlights-list"></div>
            
            <div style="margin-top: 20px; padding: 15px; background: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107;">
                <strong>📥 次のステップ:</strong>
                <p style="margin-top: 10px;">
                    この動画をダウンロードして、下のフォームからアップロードしてください。<br>
                    <small style="color: #666;">
                        YouTube Studioから直接ダウンロード、またはyt-dlpなどのツールを使用してください。
                    </small>
                </p>
            </div>
        </div>
        
        <!-- ステップ3: 動画アップロード -->
        <div class="card hidden" id="step3-card">
            <h2>📤 ステップ3: 動画アップロード</h2>
            
            <div class="upload-area" id="upload-area" onclick="document.getElementById('file-input').click()">
                <div class="upload-icon">📁</div>
                <p><strong>ファイルをドラッグ&ドロップ</strong></p>
                <p style="color: #999; margin-top: 10px;">または クリックしてファイルを選択</p>
                <input 
                    type="file" 
                    id="file-input" 
                    accept="video/*" 
                    style="display: none;"
                    onchange="handleFileSelect(event)"
                />
            </div>
            
            <div id="file-info" class="hidden" style="margin-top: 20px; padding: 15px; background: #e7eaff; border-radius: 8px;">
                <strong>選択されたファイル:</strong>
                <p id="file-name" style="margin-top: 5px;"></p>
                <p id="file-size" style="margin-top: 5px; color: #666;"></p>
            </div>
            
            <button class="btn hidden" onclick="uploadVideo()" id="upload-btn" style="margin-top: 20px;">
                🚀 アップロードして処理開始
            </button>
        </div>
        
        <!-- ステップ4: 処理中 -->
        <div class="card hidden" id="step4-card">
            <h2>⚙️ ステップ4: 切り抜き動画を生成中...</h2>
            
            <div class="spinner"></div>
            
            <div id="processing-message" style="text-align: center; margin: 20px 0; color: #666;">
                処理を開始しています...
            </div>
            
            <div class="progress-container">
                <div class="progress-bar" id="progress-bar">0%</div>
            </div>
        </div>
        
        <!-- ステップ5: 完成 -->
        <div class="card hidden" id="step5-card">
            <h2>🎉 完成！切り抜き動画が生成されました</h2>
            
            <div class="status-success" style="margin: 20px 0;">
                <strong>✅ 処理が完了しました！</strong>
                <p style="margin-top: 10px;">
                    切り抜き動画と字幕ファイルをダウンロードできます。
                </p>
            </div>
            
            <button class="btn download-btn" onclick="downloadVideo()" id="download-video-btn">
                💾 切り抜き動画をダウンロード (MP4)
            </button>
            
            <button class="btn" onclick="resetForm()" style="margin-top: 10px; background: #6c757d;">
                🔄 新しい動画を処理
            </button>
        </div>
    </div>
    
    <script>
        // Version: 2026-01-21-v2 - バグ修正版
        console.log('YouTube Clipper v2 - 前回の結果をクリアする修正版');
        
        let currentVideoId = '';
        let currentHighlights = [];
        let selectedFile = null;
        let currentJobId = '';
        
        // 動画IDをURLから抽出
        function extractVideoId(input) {
            input = input.trim();
            
            // 既に動画IDの場合
            if (/^[a-zA-Z0-9_-]{11}$/.test(input)) {
                return input;
            }
            
            // URLの場合
            const patterns = [
                /[?&]v=([a-zA-Z0-9_-]{11})/,
                /youtu\.be\/([a-zA-Z0-9_-]{11})/,
                /embed\/([a-zA-Z0-9_-]{11})/
            ];
            
            for (const pattern of patterns) {
                const match = input.match(pattern);
                if (match) return match[1];
            }
            
            return null;
        }
        
        // 見どころ検出
        async function detectHighlights() {
            const input = document.getElementById('video-id').value;
            const videoId = extractVideoId(input);
            
            if (!videoId) {
                showStatus('detection-status', 'error', '❌ 有効な動画URLまたはIDを入力してください');
                return;
            }
            
            // 前回の結果をクリア
            document.getElementById('step2-card').classList.add('hidden');
            document.getElementById('step3-card').classList.add('hidden');
            document.getElementById('file-info').classList.add('hidden');
            document.getElementById('upload-btn').classList.add('hidden');
            document.getElementById('file-input').value = '';
            selectedFile = null;
            
            document.getElementById('detect-btn').disabled = true;
            showStatus('detection-status', 'info', '🔍 見どころを検出しています...');
            
            try {
                const response = await fetch('/api/test-video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({video_id: videoId})
                });
                
                const data = await response.json();
                
                // デバッグ: APIレスポンスをコンソールに表示
                console.log('=== API Response ===');
                console.log('Video ID:', data.video_id);
                console.log('Video Title:', data.video_title);
                console.log('Highlights:', data.highlights);
                console.log('==================');
                
                if (data.success) {
                    currentVideoId = videoId;
                    currentHighlights = data.highlights;
                    
                    // 動画情報を表示
                    document.getElementById('video-info').innerHTML = `
                        <h3>${data.video_title}</h3>
                        <div class="info-row">
                            <span>動画ID:</span>
                            <span><code>${data.video_id}</code></span>
                        </div>
                        <div class="info-row">
                            <span>長さ:</span>
                            <span>${formatDuration(data.video_duration)}</span>
                        </div>
                        <div class="info-row">
                            <span>検出された見どころ:</span>
                            <span><strong>${data.highlights_count}個</strong></span>
                        </div>
                    `;
                    
                    // 見どころリストを表示
                    const highlightsList = document.getElementById('highlights-list');
                    highlightsList.innerHTML = '<h3 style="margin-bottom: 15px;">📍 見どころ一覧</h3>';
                    
                    data.highlights.forEach((h, i) => {
                        highlightsList.innerHTML += `
                            <div class="highlight-item">
                                <span>
                                    <strong>${i + 1}.</strong> 
                                    <span class="highlight-time">${formatTime(h.start)} - ${formatTime(h.end)}</span>
                                </span>
                                <span class="highlight-score">スコア: ${(h.score * 100).toFixed(0)}%</span>
                            </div>
                        `;
                    });
                    
                    showStatus('detection-status', 'success', '✅ 見どころの検出が完了しました！');
                    document.getElementById('step2-card').classList.remove('hidden');
                    document.getElementById('step3-card').classList.remove('hidden');
                } else {
                    showStatus('detection-status', 'error', '❌ ' + data.error);
                    document.getElementById('detect-btn').disabled = false;
                }
            } catch (error) {
                showStatus('detection-status', 'error', '❌ エラーが発生しました: ' + error.message);
                document.getElementById('detect-btn').disabled = false;
            }
        }
        
        // ファイル選択処理
        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                selectedFile = file;
                document.getElementById('file-name').textContent = file.name;
                document.getElementById('file-size').textContent = `サイズ: ${(file.size / (1024 * 1024)).toFixed(2)} MB`;
                document.getElementById('file-info').classList.remove('hidden');
                document.getElementById('upload-btn').classList.remove('hidden');
            }
        }
        
        // Drag & Drop対応
        const uploadArea = document.getElementById('upload-area');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('video/')) {
                selectedFile = file;
                document.getElementById('file-name').textContent = file.name;
                document.getElementById('file-size').textContent = `サイズ: ${(file.size / (1024 * 1024)).toFixed(2)} MB`;
                document.getElementById('file-info').classList.remove('hidden');
                document.getElementById('upload-btn').classList.remove('hidden');
            } else {
                alert('動画ファイルを選択してください');
            }
        });
        
        // 動画アップロード
        async function uploadVideo() {
            if (!selectedFile || !currentVideoId) {
                alert('ファイルが選択されていないか、動画IDが設定されていません');
                return;
            }
            
            const formData = new FormData();
            formData.append('video', selectedFile);
            formData.append('video_id', currentVideoId);
            
            document.getElementById('upload-btn').disabled = true;
            document.getElementById('step4-card').classList.remove('hidden');
            
            try {
                const response = await fetch('/api/upload-video', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    currentJobId = data.job_id;
                    // 処理状況をポーリング
                    pollJobStatus();
                } else {
                    alert('アップロード失敗: ' + data.error);
                    document.getElementById('upload-btn').disabled = false;
                    document.getElementById('step4-card').classList.add('hidden');
                }
            } catch (error) {
                alert('エラー: ' + error.message);
                document.getElementById('upload-btn').disabled = false;
                document.getElementById('step4-card').classList.add('hidden');
            }
        }
        
        // ジョブステータスのポーリング
        async function pollJobStatus() {
            try {
                const response = await fetch(`/api/job-status/${currentJobId}`);
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('processing-message').textContent = data.message;
                    document.getElementById('progress-bar').style.width = data.progress + '%';
                    document.getElementById('progress-bar').textContent = data.progress + '%';
                    
                    if (data.status === 'completed') {
                        document.getElementById('step4-card').classList.add('hidden');
                        document.getElementById('step5-card').classList.remove('hidden');
                    } else if (data.status === 'failed') {
                        alert('処理失敗: ' + data.message);
                        resetForm();
                    } else {
                        // 処理中の場合は2秒後に再チェック
                        setTimeout(pollJobStatus, 2000);
                    }
                }
            } catch (error) {
                console.error('ステータス取得エラー:', error);
                setTimeout(pollJobStatus, 2000);
            }
        }
        
        // 動画ダウンロード
        function downloadVideo() {
            window.location.href = `/api/download/${currentVideoId}`;
        }
        
        // フォームリセット
        function resetForm() {
            currentVideoId = '';
            currentHighlights = [];
            selectedFile = null;
            currentJobId = '';
            
            document.getElementById('video-id').value = '';
            document.getElementById('detect-btn').disabled = false;
            document.getElementById('detection-status').innerHTML = '';
            document.getElementById('detection-status').classList.add('hidden');
            document.getElementById('step2-card').classList.add('hidden');
            document.getElementById('step3-card').classList.add('hidden');
            document.getElementById('step4-card').classList.add('hidden');
            document.getElementById('step5-card').classList.add('hidden');
            document.getElementById('file-info').classList.add('hidden');
            document.getElementById('upload-btn').classList.add('hidden');
            document.getElementById('file-input').value = '';
        }
        
        // ユーティリティ関数
        function showStatus(elementId, type, message) {
            const element = document.getElementById(elementId);
            element.className = `status-message status-${type}`;
            element.textContent = message;
            element.classList.remove('hidden');
        }
        
        function formatDuration(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            
            if (h > 0) {
                return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
            }
            return `${m}:${String(s).padStart(2, '0')}`;
        }
        
        function formatTime(seconds) {
            const m = Math.floor(seconds / 60);
            const s = seconds % 60;
            return `${m}:${String(s).padStart(2, '0')}`;
        }
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
        # 注意: キャッシュを使用せず、毎回新しく検出する
        result = pipeline.detect_highlights_only(video_id)
        
        if result and result.get('success'):
            # セッションに結果を保存（動画アップロード時に使用）
            session_key = f"highlights_{video_id}"
            # メモリに保存（簡易実装）
            if not hasattr(app, 'highlight_cache'):
                app.highlight_cache = {}
            # 常に最新の結果で上書き（キャッシュ問題を回避）
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
                    # キャンセルチェック
                    if job_results[job_id]['status'] == 'failed':
                        print(f"ジョブ {job_id} がキャンセルされました")
                        return
                    
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
                
                # 音声認識で字幕を生成
                segments = subtitle_gen.transcribe_audio(str(combined_path), model='base', language='ja')
                if segments:
                    subtitle_gen.generate_srt(segments, str(subtitle_path))
                    print(f"字幕生成完了: {subtitle_path}")
                else:
                    print("字幕生成をスキップ（音声認識失敗）")
                    subtitle_path = None
                
                # 完了
                job_results[job_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': '切り抜き動画が完成しました！',
                    'output_file': str(combined_path),
                    'subtitle_file': str(subtitle_path) if subtitle_path else None,
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


@app.route('/api/job-cancel/<job_id>', methods=['POST'])
def api_job_cancel(job_id):
    """ジョブをキャンセル"""
    if job_id not in job_results:
        return jsonify({'success': False, 'error': 'ジョブが見つかりません'}), 404
    
    # ジョブを失敗状態にする（進行中のスレッドは次のチェックで停止）
    job_results[job_id] = {
        'status': 'failed',
        'progress': 0,
        'message': 'ユーザーによりキャンセルされました'
    }
    
    return jsonify({
        'success': True,
        'message': 'ジョブをキャンセルしました'
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
