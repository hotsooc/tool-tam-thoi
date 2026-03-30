@echo off
title Cai dat Treasure Hunter Bot
color 0A

echo ========================================================
echo        CAI DAT THU VIEN CHO MAY TINH MOI
echo ========================================================
echo.

cd /d "%~dp0"

echo Kiem tra cau hinh Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [LOI] May cua ban chua cai hoac chua Add To Path Python. 
    echo Ban hay vao python.org de tai bang cai nhe! Nho tick o "Add to PATH"
    pause
    exit /b
)

echo.
echo Dang tu dong cai dat cac thu vien can thiet (YOLO, OpenCV, Pillow...)...
pip install -r requirements.txt

echo.
echo ========================================================
echo Hoan tat cai dat! Tu bay gio ban chi can Bam vao file run_bot.bat de choi game thoi!
pause
