@echo off
title Treasure Hunter Bot
color 0A

echo ========================================================
echo        KHOI DONG TREASURE HUNTER BOT AUTO-PLAY
echo ========================================================
echo.

:: Di chuyen den thu muc hien tai cua file bat
cd /d "%~dp0"

:: Kiem tra xem da cai python chua
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [LOI] Khong tim thay Python! Vui long cai dat Python va them vao bien moi truong (PATH).
    pause
    exit /b
)

:: Chay bot
echo [INFO] Dang nap mo hinh AI va ket noi gia lap...
python src\main.py

echo.
echo ========================================================
echo Bot da dung.
pause
