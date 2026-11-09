#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 系统托盘应用与常驻守护中心
使用成熟稳定的 pystray + Pillow 框架封装：
- 在 Windows 系统托盘常驻高科技动态图标与实时健康监控
- 后台协同调度：FastAPI (18800)、Cookie Hub Node 桥接 (18888)、Gemini 4账号池 (18083) 与 ChatGPT 逆向 (18084)
- 托盘右键菜单实时显示所有子服务的在线状态、端口号与插件互联情况
- 托盘鼠标悬停 (Tooltip) 动态更新综合健康状态
- 集成 Windows 开机自启一键开启/关闭与状态切换
- 提供系统诊断报告弹窗、一键自愈与浏览器 Cookie 动态提取
"""

import os
import sys
import time
import datetime
import threading
import webbrowser
import subprocess
import shutil
import urllib.request
import json
import ctypes
from typing import Optional, Dict, Any, List, Tuple

# 编码与网络环境配置
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"
_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

import pystray
from PIL import Image
import uvicorn

from generate_icon import ensure_app_icon, PNG_PATH, ICO_PATH
from app_service import app, gemini_pool, chatgpt_client
from autostart import (
    is_autostart_enabled,
    enable_autostart,
    disable_autostart,
    toggle_autostart,
    get_autostart_command,
)

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 18800
HUB_PORT = 18888
GEMINI_PORT = 18083
CHATGPT_PORT = 18084

DASHBOARD_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/"
DOCS_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/docs"
REDOC_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/redoc"
HUB_URL = f"http://{SERVER_HOST}:{HUB_PORT}/status"


def attach_to_default_desktop():
    """在 Windows 下将当前线程挂载至交互用户的主桌面 (default)，确保系统托盘图标立即可见"""
    if sys.platform == "win32":
        try:
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
        self.node_proc: Optional[subprocess.Popen] = None
        self.is_running = False
        self.start_time = time.time()
        self.monitor_thread: Optional[threading.Thread] = None

        # 实时服务状态缓存 (线程安全)
        self.status_cache: Dict[str, Any] = {
            "api_ok": False,
            "api_port": SERVER_PORT,
            "hub_ok": False,
            "hub_port": HUB_PORT,
            "ext_connected": False,
            "ext_clients": 0,
            "gemini_ok": False,
            "gemini_accounts": 0,
            "gemini_active": 0,
            "gemini_port": GEMINI_PORT,
            "chatgpt_ok": False,
            "chatgpt_port": CHATGPT_PORT,
            "uptime_str": "0秒",
            "last_checked": 0,
        }

    # ==========================================
    # 1. 后台子服务编排与生命周期管理
    # ==========================================

    def ensure_node_bridge(self) -> bool:
        """检查并在需要时启动本地 Cookie Hub Node 桥接守护服务 (extension/server.js:18888)"""
        # 1. 探活检测
        try:
            req = urllib.request.Request(HUB_URL)
            with _LOCAL_OPENER.open(req, timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass

        # 2. 定位 server.js 路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        server_js = os.path.join(base_dir, "extension", "server.js")
        if not os.path.isfile(server_js):
            print(f"⚠️ [Cookie Hub] 未找到桥接脚本: {server_js}", flush=True)
            return False

        # 3. 寻找 Node.js 运行时
        node_bin = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
        if not os.path.exists(node_bin) and not shutil.which("node"):
            print("⚠️ [Cookie Hub] 系统未检测到 node.exe，请确保已安装 Node.js", flush=True)
            return False

        # 4. 后台静默启动 Node 进程
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
            self.node_proc = subprocess.Popen(
                [node_bin, server_js],
                cwd=os.path.dirname(server_js),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            print("🚀 [Cookie Hub] Node 守护桥接服务已在后台静默启动 (端口: 18888)", flush=True)

            # 轮询等待就绪
            for _ in range(12):
                time.sleep(0.3)
                try:
                    req = urllib.request.Request(HUB_URL)
                    with _LOCAL_OPENER.open(req, timeout=0.5) as resp:
                        if resp.status == 200:
                            return True
                except Exception:
                    pass
            return False
        except Exception as e:
            print(f"❌ [Cookie Hub] 启动失败: {e}", flush=True)
            return False

    def start_api_server(self):
        """在后台守护线程中启动 FastAPI + Uvicorn 统一本地 API 服务 (18800)"""
        config = uvicorn.Config(
            app=app,
            host=SERVER_HOST,
            port=SERVER_PORT,
            log_level="warning",
            access_log=False,
        )
        self.uvicorn_server = uvicorn.Server(config)

        def _run():
            print(f"🚀 [API 服务] 正在监听: http://{SERVER_HOST}:{SERVER_PORT}", flush=True)
            self.uvicorn_server.run()

        self.server_thread = threading.Thread(target=_run, daemon=True)
        self.server_thread.start()

        # 等待服务就绪
        for _ in range(20):
            time.sleep(0.2)
            if self.uvicorn_server.started:
                self.status_cache["api_ok"] = True
                break

    def ensure_gemini_pool(self, icon=None, item=None):
        """启动或健康检查 Gemini 多账号统一代理服务 (18083)"""
        try:
            if not gemini_pool.is_running():
                gemini_pool.start()
            is_ok = gemini_pool.is_running()
            status = "🟢 运行正常" if is_ok else "🔴 启动异常"
            if self.tray_icon:
                self.tray_icon.notify(f"Gemini 多账号统一服务 (18083): {status}", "服务运行状态")
            print(f"🤖 [Gemini 池] 状态检查: {status}", flush=True)
            return is_ok
        except Exception as e:
            if self.tray_icon:
                self.tray_icon.notify(f"Gemini 启动失败: {e}", "错误通知")
            print(f"❌ [Gemini 池] 启动异常: {e}", flush=True)
            return False

    def toggle_chatgpt_engine(self, icon=None, item=None):
        """启动或关闭 ChatGPT 独立逆向后端 (18084)"""
        try:
            if chatgpt_client.reverse.is_running():
                chatgpt_client.reverse.stop()
                if self.tray_icon:
                    self.tray_icon.notify("ChatGPT 逆向引擎已停止。", "服务操作")
            else:
                chatgpt_client.reverse.start()
                if self.tray_icon:
                    self.tray_icon.notify("ChatGPT 逆向引擎已在后台启动 (端口 18084)！", "服务操作")
            self._update_service_status()
        except Exception as e:
            if self.tray_icon:
                self.tray_icon.notify(f"ChatGPT 服务操作失败: {e}", "错误")

    def stop_all_subservices(self):
        """完全停止所有后台衍生子服务"""
        # 1. 停止 FastAPI
        if self.uvicorn_server:
            self.uvicorn_server.should_exit = True
            print("🛑 [API 服务] 已发出停机信号。", flush=True)

        # 2. 停止 Node 桥接
        if self.node_proc:
            try:
                self.node_proc.terminate()
                self.node_proc.wait(timeout=2)
            except Exception:
                try:
                    self.node_proc.kill()
                except Exception:
                    pass
            self.node_proc = None
            print("🛑 [Cookie Hub] Node 守护进程已停止。", flush=True)

        # 3. 停止 Gemini 池
        try:
            if gemini_pool.is_running():
                gemini_pool.stop()
                print("🛑 [Gemini 池] 统一代理已安全停止。", flush=True)
        except Exception:
            pass

        # 4. 停止 ChatGPT 逆向后端
        try:
            if chatgpt_client.reverse.is_running():
                chatgpt_client.reverse.stop()
                print("🛑 [ChatGPT 逆向] 服务已停止。", flush=True)
        except Exception:
            pass

    # ==========================================
    # 2. 实时状态监控与动态更新
    # ==========================================

    def _format_uptime(self) -> str:
        """计算人类可读的系统运行时间"""
        uptime_sec = int(time.time() - self.start_time)
        hours = uptime_sec // 3600
        minutes = (uptime_sec % 3600) // 60
        seconds = uptime_sec % 60
        if hours > 0:
            return f"{hours}小时{minutes}分"
        elif minutes > 0:
            return f"{minutes}分{seconds}秒"
        else:
            return f"{seconds}秒"

    def _update_service_status(self):
        """探活所有核心子服务并更新实时缓存"""
        # 1. API 状态
        api_ok = False
        try:
            api_ok = bool(self.uvicorn_server and self.uvicorn_server.started)
        except Exception:
            pass

        # 2. Cookie Hub 状态与插件连接
        hub_ok = False
        ext_connected = False
        ext_clients = 0
        try:
            req = urllib.request.Request(HUB_URL)
            with _LOCAL_OPENER.open(req, timeout=0.6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    hub_ok = True
                    ext_connected = data.get("extensionConnected", False)
                    ext_clients = data.get("connectedClients", 0)
        except Exception:
            pass

        # 3. Gemini 池
        gemini_ok = False
        gemini_accounts = 0
        gemini_active = 0
        try:
            gemini_ok = gemini_pool.is_running()
            if gemini_ok:
                accts = gemini_pool.list_accounts()
                gemini_accounts = len(accts)
                gemini_active = sum(1 for a in accts if a.get("status") == "enabled")
        except Exception:
            pass

        # 4. ChatGPT 逆向
        chatgpt_ok = False
        try:
            chatgpt_ok = chatgpt_client.reverse.is_running()
        except Exception:
            pass

        self.status_cache.update({
            "api_ok": api_ok,
            "hub_ok": hub_ok,
            "ext_connected": ext_connected,
            "ext_clients": ext_clients,
            "gemini_ok": gemini_ok,
            "gemini_accounts": gemini_accounts,
            "gemini_active": gemini_active,
            "chatgpt_ok": chatgpt_ok,
            "uptime_str": self._format_uptime(),
            "last_checked": time.time(),
        })

        # 5. 更新托盘悬浮提示 Tooltip (Windows szTip 限制 127 字符)
        if self.tray_icon:
            try:
                hub_mark = "🟢" if hub_ok else "🔴"
                ext_mark = f"🟢已连({ext_clients})" if ext_connected else "⚪未连"
                gem_mark = f"🟢{gemini_accounts}号" if gemini_ok else "⚪停"
                title_lines = [
                    f"Cookie Service Suite (端口 {SERVER_PORT})",
                    f"Hub: {hub_mark} | 插件: {ext_mark} | Gemini: {gem_mark}",
                    f"运行状态: {'🟢正常运行' if (api_ok and hub_ok) else '🟡部分服务异常'}",
                ]
                self.tray_icon.title = "\n".join(title_lines)[:125]
            except Exception:
                pass

            # 触发菜单文字动态刷新
            try:
                self.tray_icon.update_menu()
            except Exception:
                pass

    def _status_monitor_loop(self):
        """后台常驻状态轮询线程 (每 3 秒检测一次)"""
        while self.is_running:
            try:
                self._update_service_status()
            except Exception:
                pass
            time.sleep(3.0)

    # ==========================================
    # 3. 托盘菜单动态文本回调函数
    # ==========================================

    def _menu_text_summary(self, item=None) -> str:
        c = self.status_cache
        if c["api_ok"] and c["hub_ok"] and c["gemini_ok"]:
            return f"📊 服务总览: 🟢 全部正常 (运行 {c['uptime_str']})"
        elif c["api_ok"] and c["hub_ok"]:
            return f"📊 服务总览: 🟢 运行中 (运行 {c['uptime_str']})"
        else:
            return f"📊 服务总览: 🟡 存在异常 (运行 {c['uptime_str']})"

    def _menu_text_api(self, item=None) -> str:
        ok = self.status_cache["api_ok"]
        mark = "🟢 在线" if ok else "🔴 异常"
        return f"  ├─ 🌐 Web 控制台: {mark} (端口 {SERVER_PORT})"

    def _menu_text_hub(self, item=None) -> str:
        ok = self.status_cache["hub_ok"]
        mark = "🟢 在线" if ok else "🔴 离线"
        return f"  ├─ 🔌 Cookie Hub: {mark} (端口 {HUB_PORT})"

    def _menu_text_extension(self, item=None) -> str:
        c = self.status_cache
        if c["ext_connected"]:
            return f"  ├─ 🧩 浏览器插件: 🟢 已连接 ({c['ext_clients']} 台设备)"
        else:
            return "  ├─ 🧩 浏览器插件: ⚪ 等待浏览器连接 (点击查看指引)"

    def _menu_text_gemini(self, item=None) -> str:
        c = self.status_cache
        if c["gemini_ok"]:
            return f"  ├─ 🤖 Gemini 统一池: 🟢 运行中 ({c['gemini_accounts']}账号/{c['gemini_active']}可用)"
        else:
            return "  ├─ 🤖 Gemini 统一池: ⚪ 未启动 (点击启动)"

    def _menu_text_chatgpt(self, item=None) -> str:
        ok = self.status_cache["chatgpt_ok"]
        mark = "🟢 运行中" if ok else "⚪ 未启动"
        return f"  └─ ⚡ ChatGPT 逆向: {mark} (端口 {CHATGPT_PORT})"

    def _menu_text_autostart(self, item=None) -> str:
        enabled = is_autostart_enabled()
        return f"🚀 开机自启动: {'[√] 已开启' if enabled else '[  ] 已关闭'} (点击切换)"

    # ==========================================
    # 4. 托盘交互操作响应
    # ==========================================

    def open_dashboard(self, icon=None, item=None):
        """打开 Web 管理控制台"""
        print(f"🌐 [系统托盘] 打开管理界面: {DASHBOARD_URL}", flush=True)
        webbrowser.open(DASHBOARD_URL)

    def open_docs(self, icon=None, item=None):
        """打开 Swagger API 交互文档"""
        print(f"📚 [系统托盘] 打开 Swagger API 文档: {DOCS_URL}", flush=True)
        webbrowser.open(DOCS_URL)

    def open_redoc(self, icon=None, item=None):
        """打开 ReDoc API 规范文档"""
        print(f"📖 [系统托盘] 打开 ReDoc 文档: {REDOC_URL}", flush=True)
        webbrowser.open(REDOC_URL)

    def open_hub_status(self, icon=None, item=None):
        """查看 Cookie Hub 状态页面"""
        webbrowser.open(HUB_URL)

    def show_extension_guide(self, icon=None, item=None):
        """弹出浏览器插件接入指引"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ext_dir = os.path.join(base_dir, "extension")
        guide_text = (
            "【Cookie Hub 浏览器扩展接入指南】\n\n"
            "1. 打开 Edge (edge://extensions/) 或 Chrome (chrome://extensions/)\n"
            "2. 开启右上角「开发者模式」\n"
            "3. 点击「加载已解压的扩展程序」，选择项目下的目录:\n"
            f"   {ext_dir}\n\n"
            "4. 加载后打开任意网页 (如 B站 / 百度网盘 / Google / Suno)，扩展将自动完成握手！"
        )

        def _box():
            if sys.platform == "win32":
                ctypes.windll.user32.MessageBoxW(0, guide_text, "浏览器扩展连接指引", 0x40)

        threading.Thread(target=_box, daemon=True).start()
        if self.tray_icon:
            self.tray_icon.notify("已弹出浏览器扩展加载指引弹窗！", "浏览器插件指引")

    def show_status_dialog(self, icon=None, item=None):
        """弹出当前服务整体运行状态详细诊断报告"""
        self._update_service_status()
        c = self.status_cache
        autostart_str = "🟢 已开启 (注册表 HKCU Run)" if is_autostart_enabled() else "⚪ 已关闭"

        report = (
            "======================================================\n"
            "🍪 Cookie Service Suite 服务实时运行诊断简报\n"
            "======================================================\n\n"
            f"⏱️ 系统运行时间: {c['uptime_str']}\n"
            f"🚀 开机自启动项: {autostart_str}\n\n"
            "【核心服务清单】:\n"
            f"1. 🌐 Web 控制台与 REST API\n"
            f"   - 端口地址: http://127.0.0.1:{SERVER_PORT}/\n"
            f"   - 运行状态: {'🟢 正常运行中' if c['api_ok'] else '🔴 未运行'}\n"
            f"   - API 交互文档: http://127.0.0.1:{SERVER_PORT}/docs\n\n"
            f"2. 🔌 Cookie Hub 通信守护服务\n"
            f"   - 端口地址: http://127.0.0.1:{HUB_PORT}/\n"
            f"   - 运行状态: {'🟢 在线 (Node.js)' if c['hub_ok'] else '🔴 离线'}\n"
            f"   - 浏览器插件: {'🟢 已连接 (' + str(c['ext_clients']) + '台设备)' if c['ext_connected'] else '⚪ 等待连接 (扩展未激活)'}\n\n"
            f"3. 🤖 Google Gemini 多账号统一代理池\n"
            f"   - 端口地址: http://127.0.0.1:{GEMINI_PORT}/\n"
            f"   - 运行状态: {'🟢 正常运行中' if c['gemini_ok'] else '⚪ 未启动'}\n"
            f"   - 账号状态: {c['gemini_accounts']} 个账号接入 / {c['gemini_active']} 个可用\n\n"
            f"4. ⚡ ChatGPT 独立网页逆向后端\n"
            f"   - 端口地址: http://127.0.0.1:{CHATGPT_PORT}/\n"
            f"   - 运行状态: {'🟢 正常运行中' if c['chatgpt_ok'] else '⚪ 未启动'}\n\n"
            "======================================================\n"
            "提示: 如需打开管理控制台，可在托盘菜单中选择对应入口。"
        )

        def _show_box():
            if sys.platform == "win32":
                ctypes.windll.user32.MessageBoxW(0, report, "Cookie Service Suite 运行诊断报告", 0x40)

        threading.Thread(target=_show_box, daemon=True).start()

    def restart_subservices(self, icon=None, item=None):
        """一键健康自愈：重启检测所有异常子服务"""
        try:
            print("🔄 [系统托盘] 正在执行全套子服务一键自愈...", flush=True)
            self.ensure_node_bridge()
            self.ensure_gemini_pool()
            self._update_service_status()
            if self.tray_icon:
                self.tray_icon.notify("已完成 Cookie Hub 与 Gemini 池后台自愈探活！", "服务自愈完成")
        except Exception as e:
            if self.tray_icon:
                self.tray_icon.notify(f"自愈过程提示: {e}", "操作反馈")

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

    def toggle_autostart_action(self, icon=None, item=None):
        """切换开机自启动开关"""
        ok, msg = toggle_autostart()
        enabled = is_autostart_enabled()
        title = "开机自启已开启" if enabled else "开机自启已关闭"
        body = "系统每次登录时将自动在后台静默拉起 Cookie Service Suite 系统托盘。" if enabled else "已从 Windows 开机自启列表中移除。"
        if self.tray_icon:
            self.tray_icon.notify(body, title)
        print(f"🚀 [系统托盘] 开机自启切换: {msg}", flush=True)
        self._update_service_status()

    def on_exit(self, icon=None, item=None):
        """安全停止并退出所有托盘应用与后台服务"""
        print("\n🛑 [系统托盘] 正在安全停止 Cookie Service Suite 全部子服务...", flush=True)
        self.is_running = False
        self.stop_all_subservices()
        if self.tray_icon:
            self.tray_icon.stop()
        print("👋 感谢使用 Cookie Service Suite，服务已平稳下线。", flush=True)
        sys.exit(0)

    # ==========================================
    # 5. 托盘应用启动入口
    # ==========================================

    def run(self, auto_open_browser: bool = True):
        """运行托盘常驻守护"""
        self.is_running = True

        # 0. 尝试挂载至 Windows 交互主桌面 (default)
        attach_to_default_desktop()

        # 1. 确保图标生成
        icon_image = ensure_app_icon()

        # 2. 启动 Cookie Hub Node 守护桥接服务 (18888)
        self.ensure_node_bridge()

        # 3. 启动 FastAPI API 主服务 (18800)
        self.start_api_server()

        # 4. 确保底层 Gemini 多账号代理就绪 (18083)
        try:
            self.ensure_gemini_pool()
        except Exception as e:
            print(f"⚠️ Gemini 后台池启动提示: {e}", flush=True)

        # 5. 立即探活一次
        self._update_service_status()

        # 6. 构建系统托盘右键菜单 (全面动态化)
        menu = pystray.Menu(
            # 顶部实时状态展示区
            pystray.MenuItem(self._menu_text_summary, self.show_status_dialog),
            pystray.MenuItem(self._menu_text_api, self.open_dashboard),
            pystray.MenuItem(self._menu_text_hub, self.open_hub_status),
            pystray.MenuItem(self._menu_text_extension, self.show_extension_guide),
            pystray.MenuItem(self._menu_text_gemini, self.ensure_gemini_pool),
            pystray.MenuItem(self._menu_text_chatgpt, self.toggle_chatgpt_engine),
            pystray.Menu.SEPARATOR,
            # 常用访问入口
            pystray.MenuItem("🌐 打开 Web 管理控制台", self.open_dashboard, default=True),
            pystray.MenuItem("⚡ 查看 API 交互文档 (Swagger)", self.open_docs),
            pystray.MenuItem("📖 查看 API 规范文档 (ReDoc)", self.open_redoc),
            pystray.Menu.SEPARATOR,
            # 诊断与运维操作
            pystray.MenuItem("📋 查看服务运行详细诊断报告", self.show_status_dialog),
            pystray.MenuItem("🔄 一键自愈 / 重启异常子服务", self.restart_subservices),
            pystray.MenuItem("🔄 刷新 Google 会话凭证", self.refresh_cookies),
            pystray.Menu.SEPARATOR,
            # 开机自启控制
            pystray.MenuItem(
                self._menu_text_autostart,
                self.toggle_autostart_action,
                checked=lambda item: is_autostart_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            # 退出程序
            pystray.MenuItem("🛑 退出服务 (Exit)", self.on_exit),
        )

        initial_title = (
            f"Cookie Service Suite (端口 {SERVER_PORT})\n"
            f"Hub: 🟢 18888 | 插件: 等待连接\n"
            f"点击打开 Web 管理控制台"
        )

        self.tray_icon = pystray.Icon(
            name="CookieServiceSuite",
            icon=icon_image,
            title=initial_title[:125],
            menu=menu,
        )

        # 7. 启动常驻状态轮询监控线程
        self.monitor_thread = threading.Thread(target=self._status_monitor_loop, daemon=True)
        self.monitor_thread.start()

        print("\n" + "=" * 62, flush=True)
        print("🎉 Cookie Service Suite 本地服务与托盘常驻中心已启动！", flush=True)
        print(f"📍 Web 管理控制台:  {DASHBOARD_URL}", flush=True)
        print(f"📚 Swagger API 文档: {DOCS_URL}", flush=True)
        print(f"📖 ReDoc API 规范:   {REDOC_URL}", flush=True)
        print(f"🔌 Cookie Hub 桥接:  http://127.0.0.1:{HUB_PORT}", flush=True)
        print(f"🖼️ 应用图标路径:     {PNG_PATH}", flush=True)
        print(f"🚀 开机自启状态:     {'🟢 [已开启]' if is_autostart_enabled() else '⚪ [未开启]'}", flush=True)
        print("📌 系统托盘: 图标已驻留 Windows 托盘栏，左键点击即开管理界面", flush=True)
        print("=" * 62 + "\n", flush=True)

        # 是否自动弹窗打开管理控制台
        if auto_open_browser:
            threading.Timer(1.0, lambda: webbrowser.open(DASHBOARD_URL)).start()

        def on_tray_setup(icon):
            attach_to_default_desktop()
            try:
                icon.notify(
                    "Cookie Service Suite 已在系统托盘常驻！\n"
                    "左键点击托盘图标即可打开管理控制台并在线测试 API 端点。\n"
                    "右键可查看服务健康状态与开机自启设置。",
                    f"本地统一服务就绪 (端口 {SERVER_PORT})",
                )
            except Exception:
                pass

        # 运行托盘消息循环（守护主线程，防止托盘意外关闭导致服务中止）
        while self.is_running:
            try:
                self.tray_icon.run(setup=on_tray_setup)
            except Exception as e:
                print(f"⚠️ [系统托盘] 托盘消息循环提示: {e}", flush=True)

            if not self.is_running:
                break

            time.sleep(1.5)
            try:
                self.tray_icon = pystray.Icon(
                    name="CookieServiceSuite",
                    icon=icon_image,
                    title=initial_title[:125],
                    menu=menu,
                )
            except Exception:
                # 托盘不可用时，维持主线程等待，确保 FastAPI/Node/Gemini 等后台服务不中断
                while self.is_running:
                    time.sleep(1.0)


if __name__ == "__main__":
    auto_open = "--no-browser" not in sys.argv
    app_server = TrayAppServer()
    app_server.run(auto_open_browser=auto_open)
