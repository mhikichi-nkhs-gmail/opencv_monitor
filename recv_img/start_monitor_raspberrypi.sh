#!/bin/bash
# Raspberry Pi用フォルダ監視クライアント起動スクリプト

echo "Raspberry Pi フォルダ監視クライアントを起動します..."
echo "================================================"

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# Python環境の確認
if ! command -v python3 &> /dev/null; then
    echo "エラー: Python3がインストールされていません"
    echo "sudo apt update && sudo apt install python3 python3-pip を実行してください"
    exit 1
fi

# 依存関係のインストール
echo "依存関係をチェック中..."
pip3 install -r requirements.txt

# 監視ディレクトリの作成
MONITOR_DIR="./monitor_images"
if [ ! -d "$MONITOR_DIR" ]; then
    mkdir -p "$MONITOR_DIR"
    echo "監視ディレクトリを作成: $MONITOR_DIR"
fi

# ログディレクトリの作成
LOG_DIR="./logs"
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo "ログディレクトリを作成: $LOG_DIR"
fi

echo "フォルダ監視を開始中..."
echo "監視ディレクトリ: $MONITOR_DIR"
echo "ログファイル: $LOG_DIR/folder_monitor.log"
echo ""
echo "Ctrl+Cで停止できます"
echo "================================================"

# フォルダ監視クライアントを起動
python3 folder_monitor_client.py
