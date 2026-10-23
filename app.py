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
import json
from datetime import datetime

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from run_processor import YouTubeClipperPipeline
from auto_scheduler import AutoScheduler
from task_manager import task_queue
from task_access import install_task_access
from task_api import create_task_api
from src.editor.video_editor import VideoEditor
from src.subtitle.subtitle_generator import SubtitleGenerator

# 環境変数をロード
load_dotenv()

app = Flask(__name__)
install_task_access(app, os.environ)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB
app.config['UPLOAD_FOLDER'] = Path(tempfile.gettempdir()) / 'youtube_clipper_uploads'
app.config['OUTPUT_FOLDER'] = Path(tempfile.gettempdir()) / 'youtube_clipper_outputs'
app.config['JOB_HISTORY_FILE'] = Path(tempfile.gettempdir()) / 'youtube_clipper_job_history.json'
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
app.config['OUTPUT_FOLDER'].mkdir(parents=True, exist_ok=True)

# 処理キュー（非同期処理用）
job_queue = queue.Queue()
job_results = {}

# ジョブ履歴をロード
def load_job_history():
    """ジョブ履歴をJSONファイルから読み込む"""
    try:
        if app.config['JOB_HISTORY_FILE'].exists():
            with open(app.config['JOB_HISTORY_FILE'], 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"ジョブ履歴の読み込みに失敗: {e}")
    return {}

def save_job_history():
    """ジョブ履歴をJSONファイルに保存"""
    try:
        with open(app.config['JOB_HISTORY_FILE'], 'w', encoding='utf-8') as f:
            json.dump(job_results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"ジョブ履歴の保存に失敗: {e}")

# 起動時にジョブ履歴をロード
job_results = load_job_history()

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
        
        <!-- ジョブ履歴 -->
        <div class="card" id="job-history-card">
            <h2>📋 ジョブ履歴</h2>
            <p style="margin-bottom: 20px; color: #666;">
                過去に処理した動画の履歴とダウンロード
            </p>
            
            <div id="job-history-list" style="margin-top: 20px;">
                <div style="text-align: center; color: #999;">
                    読み込み中...
                </div>
            </div>
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
        
        // ジョブ履歴の取得と表示
        async function loadJobHistory() {
            try {
                const response = await fetch('/api/jobs');
                const data = await response.json();
                
                if (data.success && data.jobs) {
                    displayJobHistory(data.jobs);
                } else {
                    document.getElementById('job-history-list').innerHTML = 
                        '<div style="text-align: center; color: #999;">履歴がありません</div>';
                }
            } catch (error) {
                console.error('ジョブ履歴の取得エラー:', error);
                document.getElementById('job-history-list').innerHTML = 
                    '<div style="text-align: center; color: #e74c3c;">エラーが発生しました</div>';
            }
        }
        
        function displayJobHistory(jobs) {
            const container = document.getElementById('job-history-list');
            
            if (jobs.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #999;">履歴がありません</div>';
                return;
            }
            
            let html = '';
            
            // 完了したジョブのみ表示
            const completedJobs = jobs.filter(job => job.status === 'completed');
            
            if (completedJobs.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #999;">完了したジョブがありません</div>';
                return;
            }
            
            completedJobs.forEach((job, index) => {
                const date = job.completed_at ? new Date(job.completed_at).toLocaleString('ja-JP') : '不明';
                const videoId = job.video_id || '不明';
                
                html += `
                    <div style="border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="flex: 1;">
                                <strong>動画ID:</strong> ${videoId}<br>
                                <small style="color: #666;">完了: ${date}</small>
                            </div>
                            <button 
                                class="btn download-btn" 
                                onclick="downloadJobVideo('${videoId}')"
                                style="margin-left: 10px; padding: 8px 16px; font-size: 0.9em;"
                            >
                                💾 ダウンロード
                            </button>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        function downloadJobVideo(videoId) {
            window.location.href = `/api/download/${videoId}`;
        }
        
        // ページ読み込み時にジョブ履歴を取得
        window.addEventListener('DOMContentLoaded', function() {
            loadJobHistory();
            
            // 10秒ごとにジョブ履歴を更新
            setInterval(loadJobHistory, 10000);
        });
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
                    'message': '処理を開始しています...',
                    'video_id': video_id,
                    'created_at': datetime.now().isoformat()
                }
                save_job_history()  # 初期状態を保存
                
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
                
                # オープニングタイトルを生成
                job_results[job_id]['message'] = 'オープニングタイトルを生成中...'
                job_results[job_id]['progress'] = 55
                
                try:
                    title_path = temp_dir / f"{video_id}_title.mp4"
                    video_title = highlight_data.get('video_title', 'YouTube切り抜き動画')
                    
                    # 背景画像パス（プロジェクト内のアセット）
                    background_image_path = '/app/assets/opening_background.jpg'
                    if not os.path.exists(background_image_path):
                        # ローカル開発環境用のパス
                        background_image_path = '/home/user/webapp/assets/opening_background.jpg'
                    
                    print(f"🎬 オープニングタイトルを生成: {video_title}")
                    print(f"📷 背景画像: {background_image_path} (存在: {os.path.exists(background_image_path)})")
                    title_result = video_editor.create_opening_title(
                        title=video_title,
                        output_file=str(title_path),
                        duration=5,  # 5秒間表示
                        background_image=background_image_path if os.path.exists(background_image_path) else None
                    )
                    
                    if title_result and title_path.exists():
                        # タイトルをクリップの先頭に追加
                        clips.insert(0, str(title_path))
                        print(f"✅ オープニングタイトルを追加: {title_path}")
                    else:
                        print(f"⚠️ オープニングタイトルの生成に失敗（ファイルが作成されませんでした）")
                except Exception as e:
                    print(f"⚠️ オープニングタイトルの生成エラー: {e}")
                    print(f"⚠️ オープニングタイトルをスキップして続行します")
                
                # クリップを結合
                job_results[job_id]['message'] = 'クリップを結合中...'
                job_results[job_id]['progress'] = 60
                
                combined_path = app.config['OUTPUT_FOLDER'] / f"{video_id}_highlight.mp4"
                print(f"🎬 動画結合を開始: {len(clips)}個のクリップ → {combined_path}")
                result = video_editor.concatenate_videos(clips, str(combined_path))
                
                if not result:
                    raise Exception("クリップ結合に失敗しました")
                
                # 結合された動画のサイズと存在を確認
                if not combined_path.exists():
                    raise Exception(f"結合動画が見つかりません: {combined_path}")
                
                file_size_mb = combined_path.stat().st_size / (1024 * 1024)
                print(f"✅ 動画結合完了: {combined_path}")
                print(f"   ファイルサイズ: {file_size_mb:.2f} MB")
                
                # 字幕生成（オプション：環境変数で制御）
                enable_subtitles = os.getenv('ENABLE_SUBTITLES', 'false').lower() == 'true'
                
                if enable_subtitles:
                    job_results[job_id]['message'] = '字幕を生成中...'
                    job_results[job_id]['progress'] = 70
                    
                    subtitle_gen = SubtitleGenerator()
                    subtitle_path = app.config['OUTPUT_FOLDER'] / f"{video_id}_highlight.srt"
                    
                    # 音声認識で字幕を生成（結合動画のみ）
                    print(f"🎤 音声認識を開始: {combined_path}")
                    segments = subtitle_gen.transcribe_audio(str(combined_path), model='small', language='ja')
                    if segments:
                        subtitle_gen.generate_srt(segments, str(subtitle_path))
                        print(f"✅ 字幕生成完了: {subtitle_path}")
                        
                        # 字幕を動画に焼き込む
                        job_results[job_id]['message'] = '字幕を動画に焼き込み中...'
                        job_results[job_id]['progress'] = 85
                        
                        burned_path = app.config['OUTPUT_FOLDER'] / f"{video_id}_highlight_burned.mp4"
                        print(f"🔥 字幕焼き込みを開始: {combined_path} -> {burned_path}")
                        
                        result = subtitle_gen.burn_subtitles(
                            str(combined_path),
                            str(subtitle_path),
                            str(burned_path)
                        )
                        
                        if result:
                            print(f"✅ 字幕焼き込み完了: {burned_path}")
                            # 焼き込み動画を最終出力として使用
                            combined_path = burned_path
                        else:
                            print("⚠️ 字幕焼き込み失敗（字幕ファイルのみ提供）")
                    else:
                        print("⚠️ 字幕生成をスキップ（音声認識失敗）")
                        subtitle_path = None
                else:
                    print("⏭️ 字幕生成をスキップ（環境変数 ENABLE_SUBTITLES=false）")
                    subtitle_path = None
                    job_results[job_id]['progress'] = 85
                
                # 完了
                print(f"✅ 切り抜き動画が完成しました！")
                print(f"   動画: {combined_path}")
                print(f"   字幕: {subtitle_path}")
                print(f"   ダウンロードURL: /api/download/{video_id}")
                
                # ファイル詳細を確認
                if combined_path.exists():
                    import subprocess
                    file_size_mb = combined_path.stat().st_size / (1024 * 1024)
                    print(f"📊 結合動画の詳細:")
                    print(f"   ファイルサイズ: {file_size_mb:.2f} MB")
                    
                    # ffprobe で動画の長さを確認
                    try:
                        result = subprocess.run(
                            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                             '-of', 'default=noprint_wrappers=1:nokey=1', str(combined_path)],
                            capture_output=True, text=True, timeout=10
                        )
                        duration_sec = float(result.stdout.strip())
                        duration_min = int(duration_sec // 60)
                        duration_sec_remainder = int(duration_sec % 60)
                        print(f"   動画の長さ: {duration_min}分{duration_sec_remainder}秒（{duration_sec:.1f}秒）")
                    except Exception as e:
                        print(f"   動画の長さ: 確認できませんでした（{e}）")
                else:
                    print(f"⚠️ 警告: 結合動画が見つかりません: {combined_path}")
                
                job_results[job_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': '切り抜き動画が完成しました！',
                    'output_file': str(combined_path),
                    'subtitle_file': str(subtitle_path) if subtitle_path else None,
                    'video_id': video_id,
                    'download_url': f'/api/download/{video_id}',
                    'completed_at': datetime.now().isoformat()
                }
                
                # ジョブ履歴を保存
                save_job_history()
                
                # アップロードファイルを削除
                upload_path.unlink(missing_ok=True)
                
                # 一時ファイルを削除
                for clip in clips:
                    Path(clip).unlink(missing_ok=True)
                
            except Exception as e:
                job_results[job_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'message': f'エラー: {str(e)}',
                    'failed_at': datetime.now().isoformat()
                }
                # ジョブ履歴を保存
                save_job_history()
        
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


@app.route('/api/jobs', methods=['GET'])
def api_jobs():
    """全ジョブの履歴を取得"""
    try:
        # ジョブをリスト形式で返す（新しい順）
        jobs_list = []
        for job_id, job_data in sorted(job_results.items(), 
                                       key=lambda x: x[1].get('completed_at', x[1].get('failed_at', '')), 
                                       reverse=True):
            jobs_list.append({
                'job_id': job_id,
                **job_data
            })
        
        return jsonify({
            'success': True,
            'jobs': jobs_list,
            'total': len(jobs_list)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
    """完成した動画をダウンロード（字幕焼き込み版を優先）"""
    try:
        # 字幕焼き込み版を優先
        burned_path = app.config['OUTPUT_FOLDER'] / f"{video_id}_highlight_burned.mp4"
        video_path = app.config['OUTPUT_FOLDER'] / f"{video_id}_highlight.mp4"
        
        # 字幕焼き込み版が存在すればそれを返す
        if burned_path.exists():
            video_path = burned_path
            filename = f"{video_id}_highlight_burned.mp4"
            print(f"📥 ダウンロード要求: {filename}（字幕焼き込み版）")
        elif video_path.exists():
            filename = f"{video_id}_highlight.mp4"
            print(f"📥 ダウンロード要求: {filename}（標準版）")
        else:
            return jsonify({'success': False, 'error': 'ファイルが見つかりません'}), 404
        
        # デバッグ情報
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        print(f"   ファイルパス: {video_path}")
        print(f"   ファイルサイズ: {file_size_mb:.2f} MB")
        
        return send_file(
            str(video_path),
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
    
    except Exception as e:
        print(f"❌ ダウンロードエラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# タスク管理 API（ローカルワーカー用）
# ============================================================

app.register_blueprint(create_task_api(task_queue))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting Flask dashboard on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
