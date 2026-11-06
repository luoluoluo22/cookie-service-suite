@echo off
chcp 65001 >nul
title Cookie Service Suite - 关闭开机自启
cd /d "%~dp0"

echo ================================================================
echo   Cookie Service Suite - 取消 Windows 开机自启动
echo ================================================================
echo.

set "PY_EXE=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else (
    where python >nul 2>nul && set "PY_EXE=python"
)

"%PY_EXE%" "%~dp0autostart.py" --disable

echo.
echo ================================================================
pause
