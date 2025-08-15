#!/bin/bash
# Raspberry Pi systemdサービス設定スクリプト

echo "Raspberry Pi systemdサービス設定"
echo "================================"

# 管理者権限チェック
if [ "$EUID" -ne 0 ]; then
    echo "このスクリプトは管理者権限で実行する必要があります"
    echo "sudo ./raspberrypi_service.sh を実行してください"
    exit 1
fi

# サービスファイルの作成
cat > /etc/systemd/system/image-relay-monitor.service << EOF
[Unit]
Description=Image Relay Folder Monitor Client
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/image_relay_client
ExecStart=/usr/bin/python3 /home/pi/image_relay_client/folder_monitor_client.py --config raspberrypi_config.ini
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# systemdの再読み込み
systemctl daemon-reload

# サービスの有効化
systemctl enable image-relay-monitor.service

echo "systemdサービスが設定されました"
echo "================================"
echo "サービスの管理コマンド:"
echo "  開始: sudo systemctl start image-relay-monitor"
echo "  停止: sudo systemctl stop image-relay-monitor"
echo "  状態確認: sudo systemctl status image-relay-monitor"
echo "  ログ確認: sudo journalctl -u image-relay-monitor -f"
echo "  自動起動: sudo systemctl enable image-relay-monitor"
echo "  自動起動無効: sudo systemctl disable image-relay-monitor"


