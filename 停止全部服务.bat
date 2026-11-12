@echo off
chcp 65001 >nul
title Cookie Service Suite - 停止服务
cd /d "%~dp0"

echo ================================================================
echo   Cookie Service Suite - 停止所有后台服务
echo ================================================================
echo.

set "PY_EXE=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else (
    where python >nul 2>nul && set "PY_EXE=python"
)

"%PY_EXE%" -c "
import urllib.request, subprocess, sys

print('正在检测并关闭服务...')
# 尝试通知托盘或检查端口
for port in [18800, 18888, 18083, 18084, 2048]:
    try:
        cmd = f'Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique'
        res = subprocess.run(['powershell', '-Command', cmd], capture_output=True, text=True)
        pids = [p.strip() for p in res.stdout.strip().splitlines() if p.strip().isdigit()]
        for pid in pids:
            print(f'正在终止占用端口 {port} 的进程 PID: {pid}')
            subprocess.run(['taskkill', '/F', '/PID', pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        pass
print('已完成清理！')
"

echo.
echo ================================================================
echo [√] 所有相关后台进程已停止。
echo ================================================================
timeout /t 3 >nul
