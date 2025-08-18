@echo off
chcp 932 >nul
echo ========================================
echo 画像提出サーバーシステム 起動
echo ========================================
echo.

REM Python環境の確認
python --version
if errorlevel 1 (
    echo エラー: Pythonが見つかりません
    pause
    exit /b 1
)

REM 必要なライブラリの確認・インストール
echo 必要なライブラリを確認中...
python -c "import cv2, numpy, requests, flask" 2>nul
if errorlevel 1 (
    echo 必要なライブラリをインストール中...
    pip install -r requirements.txt
)

echo.
echo システムを起動します...
echo.
echo 1. APIスタブサーバー: http://localhost:3000
echo 2. 画像提出サーバー: 0.0.0.0:8080
echo.
echo 停止するには Ctrl+C を押してください
echo.

REM 新しいウィンドウでAPIスタブサーバーを起動
start "APIスタブサーバー" cmd /k "python api_stub_server.py"

REM 少し待機
timeout /t 3 /nobreak >nul

REM 画像中継サーバーを起動
python image_relay_server.py

pause
