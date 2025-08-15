@echo off
chcp 932 >nul
echo ET ROBOT CONTEST API スタブサーバーを起動します...
echo.


echo.
echo ET ROBOT CONTEST API スタブサーバーを開始中...
echo ホスト: localhost:5000
echo API エンドポイント: http://localhost:5000/snap
echo.

python et_robocon_api_stub.py --host localhost --port 5000

pause
