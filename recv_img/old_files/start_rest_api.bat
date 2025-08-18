@echo off
chcp 932 >nul
echo REST API スタブサーバーを起動します...
echo.

REM 依存関係をインストール
echo 依存関係をチェック中...
pip install -r requirements.txt

echo.
echo REST API スタブサーバーを開始中...
python rest_api_stub.py --host 0.0.0.0 --port 5000

pause
