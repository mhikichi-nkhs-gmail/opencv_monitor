@echo off
echo ========================================
echo APIスタブサーバー起動
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
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Flaskをインストール中...
    pip install flask
)

echo.
echo APIスタブサーバーを起動します...
echo サーバーURL: http://localhost:3000
echo 停止するには Ctrl+C を押してください
echo.

python api_stub_server.py

pause
