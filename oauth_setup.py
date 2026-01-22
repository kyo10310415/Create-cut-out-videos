"""
Webベースの OAuth 2.0 認証フロー
ユーザーAがブラウザで簡単に認証できるようにする
"""

import os
import json
import base64
from pathlib import Path
from flask import Flask, redirect, request, session, jsonify, render_template_string
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = os.urandom(24)

# OAuth設定
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/yt-analytics.readonly'
]

# credentials.jsonのパス
CREDENTIALS_FILE = 'credentials.json'

# 環境変数からcredentials.jsonを復元
if os.getenv('GOOGLE_OAUTH_CREDENTIALS') and not os.path.exists(CREDENTIALS_FILE):
    try:
        credentials_base64 = os.getenv('GOOGLE_OAUTH_CREDENTIALS')
        # 改行を削除
        credentials_base64 = credentials_base64.strip().replace('\n', '').replace('\r', '')
        credentials_bytes = base64.b64decode(credentials_base64)
        with open(CREDENTIALS_FILE, 'wb') as f:
            f.write(credentials_bytes)
        print(f"✓ {CREDENTIALS_FILE} を環境変数から復元しました")
    except Exception as e:
        print(f"⚠️ {CREDENTIALS_FILE} 復元エラー: {e}")

# リダイレクトURI（自動取得または環境変数）
def get_redirect_uri():
    """リダイレクトURIを取得"""
    # 環境変数から取得
    if os.getenv('OAUTH_REDIRECT_URI'):
        return os.getenv('OAUTH_REDIRECT_URI')
    
    # Renderのドメインを自動取得
    render_external_url = os.getenv('RENDER_EXTERNAL_URL')
    if render_external_url:
        return f"{render_external_url}/oauth2callback"
    
    # ローカル開発時
    return 'http://localhost:10000/oauth2callback'

REDIRECT_URI = get_redirect_uri()
print(f"📍 リダイレクトURI: {REDIRECT_URI}")


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Clipper - OAuth認証</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .info-box {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 8px;
        }
        .info-box h2 {
            color: #667eea;
            font-size: 18px;
            margin-bottom: 15px;
        }
        .info-box ul {
            padding-left: 20px;
        }
        .info-box li {
            margin-bottom: 8px;
            color: #555;
        }
        .btn {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            font-size: 16px;
            border: none;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        .success-box {
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .success-box h2 {
            color: #28a745;
            margin-bottom: 15px;
        }
        .code-box {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            word-break: break-all;
            max-height: 150px;
            overflow-y: auto;
        }
        .label {
            font-weight: 600;
            color: #333;
            margin-top: 15px;
            margin-bottom: 5px;
        }
        .copy-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
        }
        .copy-btn:hover {
            background: #218838;
        }
    </style>
</head>
<body>
    <div class="container">
        {% if status == 'start' %}
            <h1>🔐 YouTube Clipper</h1>
            <p class="subtitle">OAuth 2.0 認証</p>
            
            <div class="info-box">
                <h2>📋 認証の流れ</h2>
                <ul>
                    <li>Googleアカウントでログイン</li>
                    <li>YouTube アカウントの表示を許可</li>
                    <li>YouTube Analytics レポートの閲覧を許可</li>
                    <li>認証情報が自動的にBase64エンコードされます</li>
                </ul>
            </div>
            
            <div class="info-box">
                <h2>⚠️ 重要事項</h2>
                <ul>
                    <li><strong>チャンネル所有者（ユーザーA）</strong>のGoogleアカウントでログインしてください</li>
                    <li>「認証されていません」と表示された場合は「詳細」→「（unsafe）に移動」をクリック</li>
                    <li>すべての権限を許可してください</li>
                </ul>
            </div>
            
            <center>
                <a href="/oauth2/authorize" class="btn">🚀 認証を開始</a>
            </center>
            
        {% elif status == 'success' %}
            <h1>✅ 認証成功！</h1>
            <p class="subtitle">以下の認証情報をRenderに設定してください</p>
            
            <div class="success-box">
                <h2>📊 チャンネル情報</h2>
                <p><strong>チャンネル名:</strong> {{ channel_title }}</p>
                <p><strong>チャンネルID:</strong> {{ channel_id }}</p>
                <p><strong>登録者数:</strong> {{ subscriber_count }} 人</p>
            </div>
            
            <div class="label">1. YOUTUBE_OAUTH_CREDENTIALS（Base64）:</div>
            <div class="code-box" id="credentials">{{ credentials_base64 }}</div>
            <button class="copy-btn" onclick="copyToClipboard('credentials')">📋 コピー</button>
            
            <div class="label">2. YOUTUBE_OAUTH_TOKEN（Base64）:</div>
            <div class="code-box" id="token">{{ token_base64 }}</div>
            <button class="copy-btn" onclick="copyToClipboard('token')">📋 コピー</button>
            
            <div class="info-box" style="margin-top: 30px;">
                <h2>📝 次のステップ</h2>
                <ul>
                    <li>Renderダッシュボードを開く: <a href="https://dashboard.render.com" target="_blank">https://dashboard.render.com</a></li>
                    <li>youtube-clipper サービス → Environment タブ</li>
                    <li>上記の2つの環境変数を追加</li>
                    <li>Save Changes → Restart Service</li>
                </ul>
            </div>
            
        {% elif status == 'error' %}
            <h1>❌ 認証エラー</h1>
            <p class="subtitle">{{ error_message }}</p>
            
            <div class="info-box">
                <h2>🔧 トラブルシューティング</h2>
                <ul>
                    <li>credentials.json が正しく配置されているか確認</li>
                    <li>OAuth 2.0 クライアントIDが正しく設定されているか確認</li>
                    <li>リダイレクトURIが正しく設定されているか確認</li>
                </ul>
            </div>
            
            <center>
                <a href="/" class="btn">🔄 最初からやり直す</a>
            </center>
        {% endif %}
    </div>
    
    <script>
        function copyToClipboard(elementId) {
            const text = document.getElementById(elementId).textContent;
            navigator.clipboard.writeText(text).then(() => {
                alert('コピーしました！');
            });
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """認証開始ページ"""
    return render_template_string(HTML_TEMPLATE, status='start')


@app.route('/oauth2/authorize')
def authorize():
    """OAuth認証を開始"""
    
    if not os.path.exists(CREDENTIALS_FILE):
        return render_template_string(
            HTML_TEMPLATE,
            status='error',
            error_message='credentials.json が見つかりません'
        )
    
    try:
        # OAuth フローを作成
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # 認証URLを生成
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # 常に同意画面を表示
        )
        
        # セッションにstateを保存
        session['state'] = state
        
        return redirect(authorization_url)
        
    except Exception as e:
        return render_template_string(
            HTML_TEMPLATE,
            status='error',
            error_message=f'OAuth フロー作成エラー: {str(e)}'
        )


@app.route('/oauth2callback')
def oauth2callback():
    """OAuth コールバック"""
    
    try:
        # stateを検証
        state = session.get('state')
        if not state:
            raise ValueError('セッションのstateが見つかりません')
        
        # OAuth フローを復元
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
            state=state
        )
        
        # 認証コードを使ってトークンを取得
        flow.fetch_token(authorization_response=request.url)
        
        credentials = flow.credentials
        
        # チャンネル情報を取得
        youtube = build('youtube', 'v3', credentials=credentials)
        channel_response = youtube.channels().list(
            part='snippet,statistics',
            mine=True
        ).execute()
        
        if not channel_response.get('items'):
            raise ValueError('チャンネル情報を取得できませんでした')
        
        channel = channel_response['items'][0]
        channel_title = channel['snippet']['title']
        channel_id = channel['id']
        subscriber_count = channel['statistics'].get('subscriberCount', '非公開')
        
        # credentials.json をBase64エンコード
        with open(CREDENTIALS_FILE, 'rb') as f:
            credentials_bytes = f.read()
            credentials_base64 = base64.b64encode(credentials_bytes).decode('utf-8')
        
        # token情報をBase64エンコード
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        token_json = json.dumps(token_data)
        token_base64 = base64.b64encode(token_json.encode('utf-8')).decode('utf-8')
        
        return render_template_string(
            HTML_TEMPLATE,
            status='success',
            channel_title=channel_title,
            channel_id=channel_id,
            subscriber_count=subscriber_count,
            credentials_base64=credentials_base64,
            token_base64=token_base64
        )
        
    except Exception as e:
        return render_template_string(
            HTML_TEMPLATE,
            status='error',
            error_message=f'認証エラー: {str(e)}'
        )


if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
