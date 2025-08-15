@echo off
chcp 932 >nul
echo 画像中継サーバーを起動します...
echo.

echo.
echo 画像中継サーバーを開始中...
echo ソケット: 0.0.0.0:8080
echo API: http://localhost:5000/snap
echo.

python image_relay_server.py

pause




