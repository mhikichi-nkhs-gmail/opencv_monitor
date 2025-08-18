@echo off
echo ========================================
echo 画像中継サーバー起動
echo ========================================
echo.

REM Python環境の確認
python --version
if errorlevel 1 (
    echo エラー: Pythonが見つかりません
    pause
    exit /b 1
)

REM 必要なライブラリの確認
echo 必要なライブラリを確認中...
python -c "import cv2, numpy, requests" 2>nul
if errorlevel 1 (
    echo 必要なライブラリをインストール中...
    pip install opencv-python numpy requests
)

echo.
echo 画像中継サーバーを起動します...
echo ソケットサーバー: 0.0.0.0:8080
echo 停止するには Ctrl+C を押してください
echo.

python image_relay_server.py

pause




