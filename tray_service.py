#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 系统托盘应用与驻留守护进程
使用成熟稳定的 pystray + Pillow 框架封装：
- 在 Windows 系统托盘常驻高科技应用图标
- 后台自启动 FastAPI + Uvicorn 本地统一 API 服务 (端口: 18800)
- 点击托盘图标或菜单即可一键打开 Web 管理控制台与 Swagger API 交互文档
- 提供快速保活、Cookie 刷新与服务退出功能
"""

import os
import sys
import time
import threading
import webbrowser
from typing import Optional

# 编码与网络环境配置
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

import pystray
from PIL import Image
import uvicorn

from generate_icon import ensure_app_icon, PNG_PATH, ICO_PATH
from app_service import app, gemini_pool

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 18800
DASHBOARD_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/"
DOCS_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/docs"
REDOC_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/redoc"


def attach_to_default_desktop():
    """在 Windows 下将当前线程挂载至交互用户的主桌面 (default)，确保系统托盘图标立即可见"""
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_default = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if h_default:
                res = user32.SetThreadDesktop(h_default)
                if res:
                    print("🖥️ [系统托盘] 已成功切换并挂载至 Windows 交互桌面 (default)，通知栏可见", flush=True)
        except Exception as e:
            print(f"⚠️ [系统托盘] 挂载桌面提示: {e}", flush=True)


class TrayAppServer:
    def __init__(self):
        self.uvicorn_server: Optional[uvicorn.Server] = None
        self.server_thread: Optional[threading.Thread] = None
        self.tray_icon: Optional[pystray.Icon] = None
        self.is_running = False

    def start_api_server(self):
        """在后台线程中启动 Uvicorn FastAPI 服务"""
        config = uvicorn.Config(
            app=app,
            host=SERVER_HOST,
            port=SERVER_PORT,
            log_level="info",
            access_log=False,
        )
        self.uvicorn_server = uvicorn.Server(config)

        def _run():
            print(f"🚀 [API 服务] 正在监听: http://{SERVER_HOST}:{SERVER_PORT}", flush=True)
            self.uvicorn_server.run()

        self.server_thread = threading.Thread(target=_run, daemon=True)
        self.server_thread.start()

        # 等待服务就绪
        for _ in range(15):
            time.sleep(0.3)
            if self.uvicorn_server.started:
                break

    def stop_api_server(self):
        """停止 Uvicorn 服务"""
        if self.uvicorn_server:
            self.uvicorn_server.should_exit = True
            print("🛑 [API 服务] 已发出停机信号。", flush=True)

    def open_dashboard(self, icon=None, item=None):
        """打开 Web 管理控制台"""
        print(f"🌐 [系统托盘] 打开管理界面: {DASHBOARD_URL}", flush=True)
        webbrowser.open(DASHBOARD_URL)

    def open_docs(self, icon=None, item=None):
        """打开 Swagger 交互文档"""
        print(f"📚 [系统托盘] 打开 Swagger API 文档: {DOCS_URL}", flush=True)
        webbrowser.open(DOCS_URL)

    def open_redoc(self, icon=None, item=None):
        """打开 ReDoc API 规范文档"""
        print(f"📖 [系统托盘] 打开 ReDoc 文档: {REDOC_URL}", flush=True)
        webbrowser.open(REDOC_URL)

    def refresh_cookies(self, icon=None, item=None):
        """从前台 Cookie Hub 刷新凭证"""
        try:
            print("🔄 [系统托盘] 正在从 Cookie Hub 提取最新凭证...", flush=True)
            cookie_str = gemini_pool.refresh_pool_cookies()
            if self.tray_icon:
                self.tray_icon.notify("已成功从浏览器拉取最新 Google 会话凭证！", "凭证刷新成功")
            print("✅ [系统托盘] 凭证刷新成功，Cookie 长度:", len(cookie_str), flush=True)
        except Exception as e:
            if self.tray_icon:
                self.tray_icon.notify(f"刷新失败: {e}", "异常通知")
            print("❌ [系统托盘] 刷新异常:", e, flush=True)

    def ensure_gemini_pool(self, icon=None, item=None):
        """启动或校验 Gemini 多账号池服务"""
        try:
            started = gemini_pool.start()
            status = "运行正常" if started else "启动失败"
            if self.tray_icon:
                self.tray_icon.notify(f"Gemini 多账号统一服务 (18083): {status}", "服务状态")
            print(f"🤖 [系统托盘] Gemini 统一池检查: {status}", flush=True)
        except Exception as e:
            if self.tray_icon:
                self.tray_icon.notify(f"操作失败: {e}", "错误")

    def on_exit(self, icon=None, item=None):
        """退出托盘应用与后台服务"""
        print("🛑 [系统托盘] 正在安全退出 Cookie Service Suite...", flush=True)
        self.stop_api_server()
        if self.tray_icon:
            self.tray_icon.stop()
        sys.exit(0)

    def run(self, auto_open_browser: bool = True):
        """运行托盘常驻守护"""
        # 0. 尝试挂载至 Windows 交互主桌面 (default)
        attach_to_default_desktop()

        # 1. 确保图标生成
        icon_image = ensure_app_icon()

        # 2. 启动 API 服务
        self.start_api_server()

        # 3. 确保底层 Gemini 多账号代理就绪
        try:
            if not gemini_pool.is_running():
                gemini_pool.start()
        except Exception as e:
            print(f"⚠️ Gemini 后台池启动提示: {e}", flush=True)

        # 4. 构建系统托盘右键菜单
        menu = pystray.Menu(
            pystray.MenuItem("🌐 打开管理控制台", self.open_dashboard, default=True),
            pystray.MenuItem("⚡ 查看 API 交互文档 (Swagger)", self.open_docs),
            pystray.MenuItem("📖 查看 API 规范文档 (ReDoc)", self.open_redoc),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🔄 刷新 Google 会话凭证", self.refresh_cookies),
            pystray.MenuItem("🤖 校验/启动 Gemini 池服务", self.ensure_gemini_pool),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🛑 退出服务 (Exit)", self.on_exit),
        )

        self.tray_icon = pystray.Icon(
            name="CookieServiceSuite",
            icon=icon_image,
            title="Cookie Service Suite (端口: 18800)\n点击打开管理控制台",
            menu=menu,
        )

        print("\n=======================================================", flush=True)
        print("🎉 Cookie Service Suite 本地服务与托盘应用已启动！", flush=True)
        print(f"📍 Web 管理控制台:  {DASHBOARD_URL}", flush=True)
        print(f"📚 Swagger API 文档: {DOCS_URL}", flush=True)
        print(f"📖 ReDoc API 规范:   {REDOC_URL}", flush=True)
        print(f"🖼️ 应用图标路径:     {PNG_PATH}", flush=True)
        print("📌 系统托盘: 图标已驻留 Windows 托盘栏，左键点击即开管理界面", flush=True)
        print("=======================================================\n", flush=True)

        # 是否自动弹窗打开管理控制台
        if auto_open_browser:
            threading.Timer(1.0, lambda: webbrowser.open(DASHBOARD_URL)).start()

        def on_tray_setup(icon):
            attach_to_default_desktop()
            try:
                icon.notify(
                    "Cookie Service Suite 已在系统托盘常驻！点击托盘图标可随时进入管理控制台。",
                    "本地统一服务就绪 (端口 18800)",
                )
            except Exception:
                pass

        # 运行托盘消息循环（阻塞主线程直至用户点击退出）
        self.tray_icon.run(setup=on_tray_setup)


if __name__ == "__main__":
    auto_open = "--no-browser" not in sys.argv
    app_server = TrayAppServer()
    app_server.run(auto_open_browser=auto_open)
