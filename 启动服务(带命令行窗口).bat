@echo off
chcp 65001 >nul
title Cookie Service Suite [Console Mode]
cd /d "%~dp0"

echo ================================================================
echo   Cookie Service Suite - 调试控制台模式
echo ================================================================
echo.

set "PY_EXE=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else (
    where python >nul 2>nul && set "PY_EXE=python"
)

"%PY_EXE%" "%~dp0run_service.py"
pause
