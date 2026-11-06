@echo off
chcp 65001 >nul
title Cookie Service Suite 启动器
cd /d "%~dp0"

echo ================================================================
echo   Cookie Service Suite - 本地统一服务与系统托盘常驻启动器
echo ================================================================
echo.
echo [*] 正在后台启动 API 服务 (http://127.0.0.1:18800) 与系统托盘...

set "PYW_EXE=pythonw"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" (
    set "PYW_EXE=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
) else (
    where pythonw >nul 2>nul && set "PYW_EXE=pythonw"
)

start "" "%PYW_EXE%" "%~dp0run_service.py"

echo.
echo [√] 启动指令已成功派发！
echo [!] 图标已驻留 Windows 任务栏右下角通知区域 (金色 Cookie 芯片图标)。
echo [!] 若任务栏未直接看到，请点击任务栏右下角的向上折叠箭头 [^] 查看。
echo [!] 左键双击托盘图标即可随时打开 Web 管理控制台与 API 调试工作台。
echo [!] 右键托盘图标可实时查看服务运行情况、端口号与开机自启设置。
echo.
echo 3 秒后本窗口自动退出...
timeout /t 3 >nul
exit
