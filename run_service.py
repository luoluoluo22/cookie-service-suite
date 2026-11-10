#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 统一服务启动与调度入口
用法:
  python run_service.py                 # 启动完整套件 (FastAPI + Cookie Hub + Gemini 池 + 系统托盘 + 打开控制台)
  python run_service.py --no-browser    # 启动托盘与后台服务，但不自动弹出浏览器网页 (适合开机自启)
  python run_service.py --no-tray       # 纯命令行模式 (仅运行 API 服务与 Web 界面，不加载系统托盘)
  python run_service.py --enable-autostart  # 开启 Windows 开机自启
  python run_service.py --disable-autostart # 关闭 Windows 开机自启
  python run_service.py --status-autostart  # 查看开机自启状态
  python run_service.py --help          # 查看帮助
"""

import sys
import os

# 确保在 pythonw 静默无控制台环境下，sys.stdout / sys.stderr / sys.stdin 健全可用，
# 防止 uvicorn (DefaultFormatter 调用 isatty) 及 logging 抛出 AttributeError: 'NoneType' object has no attribute 'isatty'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
STDOUT_LOG = os.path.join(LOGS_DIR, "stdout.log")
STDERR_LOG = os.path.join(LOGS_DIR, "stderr.log")

if sys.stdout is None:
    try:
        sys.stdout = open(STDOUT_LOG, "a", encoding="utf-8", buffering=1)
    except Exception:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
elif sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr is None:
    try:
        sys.stderr = open(STDERR_LOG, "a", encoding="utf-8", buffering=1)
    except Exception:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
elif sys.platform == "win32":
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stdin is None:
    try:
        sys.stdin = open(os.devnull, "r", encoding="utf-8")
    except Exception:
        pass

os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

from autostart import (
    is_autostart_enabled,
    enable_autostart,
    disable_autostart,
    get_autostart_entry,
    get_autostart_command,
)

# 帮助与参数解析
if "--help" in sys.argv or "-h" in sys.argv:
    print("=================================================================")
    print("📌 Cookie Service Suite 本地服务启动命令与参数:")
    print("=================================================================")
    print("  python run_service.py                 # 启动本地服务并驻留系统托盘，自动打开 Web 控制台")
    print("  python run_service.py --no-browser    # 启动后台服务与托盘，静默不弹出浏览器 (开机自启推荐)")
    print("  python run_service.py --no-tray       # 纯命令行模式 (仅运行 API 服务与 Web 界面，不加载托盘)")
    print("  python run_service.py --enable-autostart   # 将套件注册至 Windows 开机自启")
    print("  python run_service.py --disable-autostart  # 取消 Windows 开机自启")
    print("  python run_service.py --status-autostart   # 查询开机自启配置状态")
    print("=================================================================")
    sys.exit(0)

# 开机自启快捷操作
if "--enable-autostart" in sys.argv or "--autostart-enable" in sys.argv:
    ok, msg = enable_autostart()
    print(msg)
    sys.exit(0 if ok else 1)

if "--disable-autostart" in sys.argv or "--autostart-disable" in sys.argv:
    ok, msg = disable_autostart()
    print(msg)
    sys.exit(0 if ok else 1)

if "--status-autostart" in sys.argv or "--autostart-status" in sys.argv:
    enabled = is_autostart_enabled()
    print("==================================================")
    print("  Cookie Service Suite - 开机自启状态检查")
    print("==================================================")
    print(f"当前开机自启状态: {'🟢 [已开启]' if enabled else '⚪ [未开启]'}")
    if enabled:
        print(f"注册表启动命令:   {get_autostart_entry()}")
    print("==================================================")
    sys.exit(0)

# 运行模式选择
if "--no-tray" in sys.argv:
    import uvicorn
    from app_service import app
    print("🚀 [命令行模式] 正在启动 Cookie Service Suite API 服务: http://127.0.0.1:18800")
    print("📚 Swagger 交互式文档: http://127.0.0.1:18800/docs")
    print("🌐 Web 管理控制台:     http://127.0.0.1:18800/")
    uvicorn.run(app, host="127.0.0.1", port=18800)
else:
    from tray_service import TrayAppServer
    auto_open = "--no-browser" not in sys.argv
    try:
        server = TrayAppServer()
        server.run(auto_open_browser=auto_open)
    except Exception as e:
        import traceback
        import datetime
        with open(os.path.join(LOGS_DIR, "crash.log"), "a", encoding="utf-8") as f:
            f.write(f"\n[CRASH] {datetime.datetime.now()}: {e}\n")
            traceback.print_exc(file=f)
        raise
