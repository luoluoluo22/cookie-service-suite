#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 统一服务启动脚本
用法:
  python run_service.py           # 启动本地服务 + 系统托盘 + 自动打开管理控制台
  python run_service.py --no-tray # 仅启动 FastAPI 本地 Web 服务 (不加载系统托盘，适合命令行/服务器环境)
  python run_service.py --help    # 查看帮助
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

if "--help" in sys.argv or "-h" in sys.argv:
    print("📌 Cookie Service Suite 本地服务启动命令:")
    print("  python run_service.py           # 启动本地 API 服务并在系统托盘驻留，自动弹出 Web 管理界面")
    print("  python run_service.py --no-tray # 纯命令行模式 (仅运行 API 服务与 Web 界面，不加载托盘)")
    print("  python run_service.py --no-browser # 启动托盘与服务，但不自动弹出浏览器标签页")
    sys.exit(0)

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
    server = TrayAppServer()
    server.run(auto_open_browser=auto_open)
