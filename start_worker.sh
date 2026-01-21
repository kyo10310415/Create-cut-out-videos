#!/bin/bash
# YouTube Clipper ローカルワーカー起動スクリプト (Mac/Linux)

echo "========================================"
echo "YouTube Clipper - ローカルワーカー"
echo "========================================"
echo ""

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# 仮想環境をアクティベート
if [ -f "venv/bin/activate" ]; then
    echo "仮想環境をアクティベート中..."
    source venv/bin/activate
else
    echo "エラー: 仮想環境が見つかりません"
    echo "先に以下を実行してください:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements_worker.txt"
    exit 1
fi

# .env.worker ファイルの確認
if [ ! -f ".env.worker" ]; then
    echo "エラー: .env.worker ファイルが見つかりません"
    echo ".env.worker.example をコピーして .env.worker を作成してください"
    exit 1
fi

echo ""
echo "ワーカーを起動しています..."
echo ""

# ワーカーを起動
python3 local_worker.py

echo ""
echo "ワーカーが停止しました"
