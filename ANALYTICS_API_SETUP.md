# YouTube Analytics API v2 導入ガイド

## 📋 前提条件

### 現在の状況
- **YouTube運営アカウント**: アカウントA（チャンネルオーナー）
- **API設定アカウント**: アカウントB（現在のYouTube Data API v3を設定）

### 目標
- YouTube Analytics API v2を導入
- API使用量とコスト清算をアカウントBに統一

## 🔧 導入手順

### パターン1: 推奨構成（チャンネル運営アカウントでAPI設定）

#### メリット
- ✅ 設定が最もシンプル
- ✅ Analytics API v2に完全アクセス可能
- ✅ 権限管理が不要

#### 手順
1. **Google Cloud Console にアクセス**
   - アカウントA（チャンネル運営アカウント）でログイン
   - https://console.cloud.google.com

2. **新規プロジェクトを作成**
   ```
   プロジェクト名: youtube-clipper-analytics
   ```

3. **YouTube Data API v3を有効化**
   ```
   APIとサービス → ライブラリ → YouTube Data API v3 → 有効化
   ```

4. **YouTube Analytics API v2を有効化**
   ```
   APIとサービス → ライブラリ → YouTube Analytics API → 有効化
   ```

5. **APIキーを作成**
   ```
   認証情報 → 認証情報を作成 → APIキー
   → 生成されたキーをコピー
   ```

6. **OAuth 2.0クライアントIDを作成**
   ```
   認証情報 → 認証情報を作成 → OAuth 2.0クライアントID
   アプリケーションの種類: デスクトップアプリ
   名前: YouTube Clipper OAuth
   → 作成
   → JSONをダウンロード（credentials.json）
   ```

7. **Renderに設定**
   ```bash
   # Renderの環境変数
   YOUTUBE_API_KEY=<新しいAPIキー>
   
   # credentials.jsonの内容をBase64エンコード
   cat credentials.json | base64
   
   # Renderの環境変数に追加
   YOUTUBE_OAUTH_CREDENTIALS=<Base64エンコードした内容>
   ```

#### デメリット
- ⚠️ 既存のAPI設定をアカウントAに移行する必要がある
- ⚠️ コスト清算がアカウントAになる

---

### パターン2: 別アカウント構成（現在のAPI設定を維持）

#### メリット
- ✅ 現在のAPI設定（アカウントB）をそのまま使用
- ✅ コスト清算がアカウントBのまま

#### 制約
- ⚠️ YouTube Studio で権限付与が必要
- ⚠️ Analytics API v2は一部データにアクセス制限

#### 手順

**1. YouTube Studioで権限付与（アカウントAで実行）**
```
1. YouTube Studio にログイン（アカウントA）
   https://studio.youtube.com

2. 設定 → 権限 → 権限を管理

3. 招待 をクリック

4. アカウントBのメールアドレスを入力

5. 役割を選択: 「管理者（完全）」
   ⚠️ 重要: Analytics APIには「管理者」権限が必要

6. 招待を送信

7. アカウントBで招待メールを確認して承認
```

**2. Google Cloud Console設定（アカウントBで実行）**
```
1. 既存のプロジェクトを開く
   https://console.cloud.google.com

2. YouTube Analytics API v2を有効化
   APIとサービス → ライブラリ → YouTube Analytics API → 有効化

3. OAuth 2.0クライアントIDを作成
   認証情報 → 認証情報を作成 → OAuth 2.0クライアントID
   アプリケーションの種類: デスクトップアプリ
   名前: YouTube Clipper OAuth
   → JSONをダウンロード（credentials.json）
```

**3. OAuth認証フローを実装**

プロジェクトに以下のファイルを追加：

```bash
# credentials.jsonをプロジェクトに配置
# ⚠️ 本番環境では環境変数で管理
```

**4. コードを修正**

`src/api/youtube_api.py` に Analytics API v2のメソッドを追加：

```python
def get_analytics_data(
    self,
    video_id: str,
    start_date: str,
    end_date: str,
    metrics: str = 'views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration'
) -> Optional[Dict]:
    """
    YouTube Analytics API v2でアナリティクスデータを取得
    
    Args:
        video_id: YouTube動画ID
        start_date: 開始日（YYYY-MM-DD）
        end_date: 終了日（YYYY-MM-DD）
        metrics: 取得するメトリクス（カンマ区切り）
        
    Returns:
        アナリティクスデータの辞書
    """
    if not self.youtube_analytics:
        print("⚠️ YouTube Analytics API が初期化されていません")
        return None
    
    try:
        request = self.youtube_analytics.reports().query(
            ids=f'channel==MINE',  # 自分のチャンネル
            startDate=start_date,
            endDate=end_date,
            metrics=metrics,
            dimensions='video',
            filters=f'video=={video_id}'
        )
        response = request.execute()
        return response
    except HttpError as e:
        print(f"Analytics API エラー: {e}")
        return None

def get_audience_retention(
    self,
    video_id: str
) -> Optional[Dict]:
    """
    視聴維持率データを取得
    
    Args:
        video_id: YouTube動画ID
        
    Returns:
        視聴維持率データ
    """
    if not self.youtube_analytics:
        return None
    
    try:
        # 視聴維持率は特別なメトリクス
        request = self.youtube_analytics.reports().query(
            ids=f'channel==MINE',
            startDate='2020-01-01',  # 動画公開日以降
            endDate=datetime.now().strftime('%Y-%m-%d'),
            metrics='audienceWatchRatio,relativeRetentionPerformance',
            dimensions='elapsedVideoTimeRatio',
            filters=f'video=={video_id}'
        )
        response = request.execute()
        return response
    except HttpError as e:
        print(f"視聴維持率取得エラー: {e}")
        return None
```

**5. Renderに設定**
```bash
# Renderの環境変数に追加

# credentials.jsonの内容をBase64エンコード
cat credentials.json | base64

# Renderの環境変数
YOUTUBE_OAUTH_CREDENTIALS=<Base64エンコードした内容>
```

**6. 初回認証フロー**

ローカルで一度実行して認証：

```bash
# ローカル環境で実行
cd /home/user/webapp
python3 << 'PYTHON'
from src.api.youtube_api import YouTubeAPI

# credentials.jsonを配置
api = YouTubeAPI(
    api_key='YOUR_API_KEY',
    credentials_file='./credentials.json'
)

# 初回実行時、ブラウザが開いて認証画面が表示される
# アカウントBでログインして承認

# 認証後、token.pickleが生成される
# このファイルをRenderにアップロード
PYTHON
```

**7. token.pickleをRenderにアップロード**

Render環境で認証トークンを使用：

```bash
# token.pickleをBase64エンコード
cat token.pickle | base64

# Renderの環境変数に追加
YOUTUBE_OAUTH_TOKEN=<Base64エンコードした内容>
```

**8. 起動時にトークンをデコード**

`app.py` または `run_processor.py` に追加：

```python
import os
import base64

# 起動時にトークンをデコード
if os.getenv('YOUTUBE_OAUTH_TOKEN'):
    token_data = base64.b64decode(os.getenv('YOUTUBE_OAUTH_TOKEN'))
    with open('token.pickle', 'wb') as f:
        f.write(token_data)

if os.getenv('YOUTUBE_OAUTH_CREDENTIALS'):
    creds_data = base64.b64decode(os.getenv('YOUTUBE_OAUTH_CREDENTIALS'))
    with open('credentials.json', 'wb') as f:
        f.write(creds_data)
```

---

## 💰 コスト清算について

### API使用量の課金先
- **課金先**: Google Cloud Projectの所有者（アカウントB）
- **設定場所**: Google Cloud Console → お支払い

### YouTube Data API v3のコスト
- **無料枠**: 1日あたり10,000クォータユニット
- **超過料金**: 無料枠超過後、$0.002/クォータユニット

### YouTube Analytics API v2のコスト
- **完全無料**: Analytics APIには課金なし
- **クォータ**: 1日あたり50,000リクエスト

### 使用量の確認
```
Google Cloud Console → APIとサービス → ダッシュボード
→ 使用状況を確認
```

---

## 📊 取得できるデータ

### YouTube Analytics API v2で取得可能
- ✅ **視聴維持率（Audience Retention）**
- ✅ **リアルタイム統計**（配信中のみ）
- ✅ **詳細なエンゲージメント**（いいね、コメント、シェア）
- ✅ **視聴時間分布**
- ✅ **トラフィックソース**

### 制約
- ⚠️ 自分のチャンネルのみアクセス可能
- ⚠️ 別アカウントの場合、招待されたチャンネルのみ
- ⚠️ 管理者権限が必要

---

## 🎯 推奨構成

### 推奨: パターン1（チャンネル運営アカウントでAPI設定）
```
理由:
1. 設定が最もシンプル
2. Analytics API v2に完全アクセス
3. 権限管理が不要
4. 将来的な拡張性が高い

デメリット:
- コスト清算がアカウントAになる
  → 対策: Google Cloud の支払いアカウントをアカウントBに設定可能
```

### 代替: パターン2（現在のAPI設定を維持）
```
理由:
1. 既存の設定を変更しなくて良い
2. コスト清算がアカウントBのまま

デメリット:
- YouTube Studioで権限付与が必要
- OAuth認証フローの実装が必要
```

---

## 🚀 次のステップ

どちらのパターンを選択しますか？

### パターン1を選択する場合
1. アカウントAで新規Google Cloud Projectを作成
2. APIキーとOAuth認証を設定
3. Renderの環境変数を更新

### パターン2を選択する場合
1. YouTube Studioで権限付与
2. OAuth認証フローを実装
3. Renderにトークンをアップロード

どちらのパターンで進めますか？それとも質問がありますか？
