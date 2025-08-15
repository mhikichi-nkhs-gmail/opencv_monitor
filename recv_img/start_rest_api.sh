#!/bin/bash
# REST API スタブサーバー起動スクリプト

echo "REST API スタブサーバーを起動します..."
echo "=========================================="

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# Python環境の確認
if ! command -v python3 &> /dev/null; then
    echo "エラー: Python3がインストールされていません"
    exit 1
fi

# 依存関係のインストール
echo "依存関係をチェック中..."
pip3 install -r requirements.txt

# ディレクトリの作成
mkdir -p received_images
mkdir -p backups
mkdir -p logs

echo "REST API スタブサーバーを開始中..."
echo "ホスト: 0.0.0.0:5000"
echo "API エンドポイント: http://localhost:5000/api/v1/"
echo "Ctrl+Cで停止"
echo "=========================================="

# REST API スタブサーバーを起動
python3 rest_api_stub.py --host 0.0.0.0 --port 5000
