@echo off
chcp 65001 >nul
title Cookie Service Suite - 开启开机自启
cd /d "%~dp0"

echo ================================================================
echo   Cookie Service Suite - 设置 Windows 开机自启动
echo ================================================================
echo.

set "PY_EXE=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else (
    where python >nul 2>nul && set "PY_EXE=python"
)

"%PY_EXE%" "%~dp0autostart.py" --enable

echo.
echo ================================================================
pause
