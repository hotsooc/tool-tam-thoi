@echo off
title Treasure Hunter Bot
color 0A
chcp 65001 >nul

echo ========================================================
echo        KHOI DONG TREASURE HUNTER BOT AUTO-PLAY
echo ========================================================
echo.

cd /d "%~dp0"

:: Kiem tra Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [LOI] Khong tim thay Python! Vui long cai dat Python.
    pause
    exit /b
)

:: Tao thu muc logs neu chua co
if not exist logs mkdir logs

echo ========================================================
echo  CAU HINH ADB
echo ========================================================
echo.
echo LDPlayer thuong o 1 trong cac duong dan sau:
echo   C:\LDPlayer\LDPlayer9\adb.exe
echo   F:\LDPlayer\LDPlayer9\adb.exe
echo   C:\Program Files\LDPlayer\LDPlayer9\adb.exe
echo.

:: Hoi duong dan ADB
set /p ADB_PATH="Nhap duong dan den adb.exe (Enter de dung mac dinh F:\LDPlayer\LDPlayer9\adb.exe): "
if "%ADB_PATH%"=="" set ADB_PATH=F:\LDPlayer\LDPlayer9\adb.exe

:: Kiem tra file adb.exe co ton tai khong
if not exist "%ADB_PATH%" (
    echo.
    echo [LOI] Khong tim thay adb.exe tai: %ADB_PATH%
    echo       Vui long kiem tra lai duong dan.
    pause
    exit /b
)

echo [OK] Tim thay adb.exe tai: %ADB_PATH%
echo.

:: Hoi Device ID
echo ========================================================
echo  DEVICE ID
echo ========================================================
echo.
echo Chay lenh sau de xem Device ID:
echo   "%ADB_PATH%" devices
echo.
echo Device ID thuong la:
echo   127.0.0.1:5555  (LDPlayer mac dinh)
echo   127.0.0.1:5554
echo   emulator-5554
echo.
set /p DEVICE_ID="Nhap Device ID (Enter de dung mac dinh 127.0.0.1:5555): "
if "%DEVICE_ID%"=="" set DEVICE_ID=127.0.0.1:5555

:: Thu ket noi ADB
echo.
echo [INFO] Dang ket noi ADB toi %DEVICE_ID%...
"%ADB_PATH%" connect %DEVICE_ID% >nul 2>&1
"%ADB_PATH%" -s %DEVICE_ID% shell echo "connected" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Khong the ket noi toi %DEVICE_ID%
    echo       - Hay chac chan LDPlayer dang chay
    echo       - Hay bat ADB trong Settings cua LDPlayer
    echo       - Hay thu chay: "%ADB_PATH%" connect %DEVICE_ID%
    pause
    exit /b
)
echo [OK] Ket noi ADB thanh cong!
echo.

:: Ghi cau hinh vao file tam de Python doc
echo ADB_PATH=%ADB_PATH%> config.tmp
echo DEVICE_ID=%DEVICE_ID%>> config.tmp

echo ========================================================
echo [INFO] Dang khoi dong bot...
echo [INFO] Log duoc luu tai: logs\bot_log.txt
echo [INFO] Nhan Ctrl+C de dung bot
echo ========================================================
echo.

:: Chay bot va luu log
python src\main.py 2>&1 | powershell -Command "$input | Tee-Object -FilePath 'logs\bot_log.txt'"

:: Xoa file config tam
if exist config.tmp del config.tmp

echo.
echo ========================================================
echo Bot da dung. Xem log day du tai: logs\bot_log.txt
pause