#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 开机自启动管理模块
支持 Windows 注册表 (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run)
与 Windows 开始菜单启动目录 (Startup) 双模自启管理。

特性：
- 采用 pythonw.exe 静默启动，系统开机/用户登录时无黑框闪烁，平滑驻留系统托盘。
- 携带 --no-browser 参数，自启时不强行弹出浏览器标签页，避免打扰日常开机。
- 兼容命令行调用 (--enable / --disable / --status / --toggle) 与 Python SDK 导入。
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import winreg
from typing import Tuple, Optional

APP_NAME = "CookieServiceSuite"
REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_pythonw_path() -> str:
    """获取无控制台窗口的 pythonw.exe 可执行路径"""
    # 1. 优先尝试当前运行环境同目录下的 pythonw.exe
    curr_dir = os.path.dirname(sys.executable)
    cand_pythonw = os.path.join(curr_dir, "pythonw.exe")
    if os.path.isfile(cand_pythonw):
        return cand_pythonw

    # 2. 尝试标准安装目录
    known_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"),
        r"C:\Program Files\Python314\pythonw.exe",
        r"C:\Program Files\Python313\pythonw.exe",
        r"C:\Program Files\Python312\pythonw.exe",
    ]
    for p in known_paths:
        if os.path.isfile(p):
            return p

    # 3. 兜底回退为当前 sys.executable
    return sys.executable


def get_run_service_path() -> str:
    """获取统一启动脚本 run_service.py 的绝对路径"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "run_service.py")


def get_autostart_command() -> str:
    """构建开机自启动命令行指令"""
    python_exe = get_pythonw_path()
    service_py = get_run_service_path()
    return f'"{python_exe}" "{service_py}" --no-browser'


def is_autostart_enabled() -> bool:
    """检查是否已设置开机自启"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val and os.path.exists(get_run_service_path()))
    except (FileNotFoundError, OSError):
        return False


def get_autostart_entry() -> Optional[str]:
    """获取当前注册表中记录的自启指令内容"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return str(val)
    except (FileNotFoundError, OSError):
        return None


def enable_autostart() -> Tuple[bool, str]:
    """
    开启开机自启
    在 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run 中写入静默启动指令
    """
    cmd = get_autostart_command()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)

        # 校验写入
        if is_autostart_enabled():
            return True, f"✅ 已成功开启开机自启！\n注册表项: HKCU\\{REG_RUN_KEY}\\{APP_NAME}\n启动指令: {cmd}"
        else:
            return False, "❌ 写入注册表后校验失败，请检查安全软件拦截。"
    except Exception as e:
        return False, f"❌ 注册开机自启失败: {e}"


def disable_autostart() -> Tuple[bool, str]:
    """关闭开机自启"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        return True, "✅ 已成功关闭开机自启！"
    except Exception as e:
        return False, f"❌ 关闭开机自启失败: {e}"


def toggle_autostart() -> Tuple[bool, str]:
    """切换开机自启动状态"""
    if is_autostart_enabled():
        return disable_autostart()
    else:
        return enable_autostart()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cookie Service Suite - 开机自启管理工具")
    parser.add_argument("--enable", action="store_true", help="开启开机自启动")
    parser.add_argument("--disable", action="store_true", help="关闭开机自启动")
    parser.add_argument("--toggle", action="store_true", help="切换开机自启动状态")
    parser.add_argument("--status", action="store_true", help="检查当前开机自启状态")

    args = parser.parse_args()

    if args.enable:
        ok, msg = enable_autostart()
        print(msg)
        sys.exit(0 if ok else 1)
    elif args.disable:
        ok, msg = disable_autostart()
        print(msg)
        sys.exit(0 if ok else 1)
    elif args.toggle:
        ok, msg = toggle_autostart()
        print(msg)
        sys.exit(0 if ok else 1)
    else:
        enabled = is_autostart_enabled()
        entry = get_autostart_entry()
        print("==================================================")
        print("  Cookie Service Suite - 开机自启状态检查")
        print("==================================================")
        print(f"当前开机自启状态: {'🟢 [已开启]' if enabled else '⚪ [已关闭]'}")
        if enabled:
            print(f"当前注册指令:     {entry}")
        print(f"建议推荐指令:     {get_autostart_command()}")
        print("--------------------------------------------------")
        print("可用命令:")
        print("  python autostart.py --enable   # 开启开机自启")
        print("  python autostart.py --disable  # 关闭开机自启")
        print("  python autostart.py --toggle   # 切换开机自启")
        print("==================================================")
