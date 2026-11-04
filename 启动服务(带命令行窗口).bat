@echo off
chcp 65001 >nul
title Cookie Service Suite [Console Mode]
cd /d "%~dp0"

echo ================================================================
echo   Cookie Service Suite - 调试控制台模式
echo ================================================================
echo.
"C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe" run_service.py
pause
