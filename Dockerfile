FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージを更新してFFmpegをインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# requirements.txtをコピーして依存関係をインストール
COPY requirements.txt .

# torchを先にインストール（CPU版・軽量）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# アセット（フォント・画像）をコピー（必須）
COPY assets /app/assets

# ディレクトリを作成
RUN mkdir -p downloads temp output logs config

# ポートを公開
EXPOSE 10000

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

# アプリケーションを起動
CMD ["python", "app.py"]
