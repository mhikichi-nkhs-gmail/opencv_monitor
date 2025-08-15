#!/bin/bash
# Raspberry Pi初期セットアップスクリプト

echo "Raspberry Pi 画像中継クライアント セットアップ"
echo "=============================================="

# 管理者権限チェック
if [ "$EUID" -ne 0 ]; then
    echo "このスクリプトは管理者権限で実行する必要があります"
    echo "sudo ./raspberrypi_setup.sh を実行してください"
    exit 1
fi

# システムアップデート
echo "システムをアップデート中..."
apt update && apt upgrade -y

# 必要なパッケージのインストール
echo "必要なパッケージをインストール中..."
apt install -y python3 python3-pip python3-venv git

# カメラモジュールの有効化（オプション）
read -p "Raspberry Piカメラモジュールを有効にしますか？ (y/n): " enable_camera
if [[ $enable_camera =~ ^[Yy]$ ]]; then
    echo "カメラモジュールを有効化中..."
    raspi-config nonint do_camera 0
    echo "カメラモジュールが有効化されました"
fi

# ユーザーpiのホームディレクトリに移動
cd /home/pi

# プロジェクトディレクトリの作成
echo "プロジェクトディレクトリを作成中..."
mkdir -p /home/pi/image_relay_client
cd /home/pi/image_relay_client

# 監視ディレクトリの作成
mkdir -p monitor_images
mkdir -p logs
mkdir -p evidence_images

# 権限の設定
chown -R pi:pi /home/pi/image_relay_client
chmod -R 755 /home/pi/image_relay_client

echo "セットアップが完了しました"
echo "=============================================="
echo "次のステップ:"
echo "1. プロジェクトファイルを /home/pi/image_relay_client/ にコピー"
echo "2. raspberrypi_config.ini でサーバー設定を編集"
echo "3. ./start_monitor_raspberrypi.sh でクライアントを起動"


