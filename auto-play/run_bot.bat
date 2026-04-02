@echo off
title Treasure Hunter Bot
color 0A

echo ========================================================
echo        KHOI DONG TREASURE HUNTER BOT AUTO-PLAY
echo ========================================================
echo.

cd /d "%~dp0"

if not exist logs mkdir logs

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [LOI] Khong tim thay Python!
    pause
    exit /b
)

echo [INFO] Dang nap mo hinh AI va ket noi gia lap...
echo [INFO] Log duoc luu tai: logs\bot_log.txt
echo.

python src\main.py 2>&1 | powershell -Command "$input | Tee-Object -FilePath 'logs\bot_log.txt'"

echo.
echo ========================================================
echo Bot da dung. Xem log tai: logs\bot_log.txt
pause