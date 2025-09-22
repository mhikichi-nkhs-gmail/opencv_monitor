@echo off
chcp 932 >nul
echo ========================================
echo �摜��o�T�[�o�[�V�X�e�� �N��
echo ========================================
echo.

REM Python���̊m�F
python --version
if errorlevel 1 (
    echo �G���[: Python��������܂���
    pause
    exit /b 1
)

REM �K�v�ȃ��C�u�����̊m�F�E�C���X�g�[��
echo �K�v�ȃ��C�u�������m�F��...
python -c "import cv2, numpy, requests, flask" 2>nul
if errorlevel 1 (
    echo �K�v�ȃ��C�u�������C���X�g�[����...
    pip install -r requirements.txt
)

echo.
echo �V�X�e�����N�����܂�...
echo.
echo 1. API�X�^�u�T�[�o�[: http://localhost:3000
echo 2. �摜��o�T�[�o�[: 0.0.0.0:8080
echo.
echo ��~����ɂ� Ctrl+C �������Ă�������
echo.

REM �V�����E�B���h�E��API�X�^�u�T�[�o�[���N��
start "API�X�^�u�T�[�o�[" cmd /k "python api_stub_server.py"

REM �����ҋ@
timeout /t 3 /nobreak >nul

REM �摜���p�T�[�o�[���N��
python image_relay_server.py

pause
