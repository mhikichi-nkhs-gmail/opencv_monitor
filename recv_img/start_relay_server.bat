@echo off
echo ========================================
echo �摜��o�T�[�o�[�N��
echo ========================================
echo.

REM Python���̊m�F
python --version
if errorlevel 1 (
    echo �G���[: Python��������܂���
    pause
    exit /b 1
)

REM �K�v�ȃ��C�u�����̊m�F
echo �K�v�ȃ��C�u�������m�F��...
python -c "import cv2, numpy, requests" 2>nul
if errorlevel 1 (
    echo �K�v�ȃ��C�u�������C���X�g�[����...
    pip install opencv-python numpy requests
)

echo.
echo �摜��o�T�[�o�[���N�����܂�...
echo �\�P�b�g�T�[�o�[: 0.0.0.0:8080
echo ��~����ɂ� Ctrl+C �������Ă�������
echo.

python image_relay_server.py

pause




