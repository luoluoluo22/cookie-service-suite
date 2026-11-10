#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 开机自启动管理模块
支持 Windows 注册表 (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run)
与 Windows 开始菜单启动目录 (Startup) 双模自启管理。

特性：
- 采用 pythonw.exe 静默启动，系统开机/用户登录时无黑框闪烁，平滑驻留系统托盘。
- 携带 --no-browser 参数，自启时不强行弹出浏览器标签页，避免打扰日常开机。
- 双重保障机制：同时写入注册表 Run 键与开始菜单 Startup 启动项，重启免丢。
- 兼容命令行调用 (--enable / --disable / --status / --toggle) 与 Python SDK 导入。
"""

import os
import sys

if sys.platform == "win32":
    try:
        if sys.stdout:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import winreg
from typing import Tuple, Optional

APP_NAME = "CookieServiceSuite"
REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_pythonw_path() -> str:
    """获取无控制台窗口的 pythonw.exe 可执行路径"""
    curr_dir = os.path.dirname(sys.executable)
    cand_pythonw = os.path.join(curr_dir, "pythonw.exe")
    if os.path.isfile(cand_pythonw):
        return cand_pythonw

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


def get_startup_vbs_path() -> str:
    """获取 Windows 开始菜单启动目录下的启动脚本路径"""
    startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    return os.path.join(startup_dir, f"{APP_NAME}.vbs")


def is_autostart_enabled() -> bool:
    """检查是否已设置开机自启 (注册表或开始菜单 Startup 项任意一项存在即为已开启)"""
    reg_ok = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            reg_ok = bool(val and os.path.exists(get_run_service_path()))
    except (FileNotFoundError, OSError):
        reg_ok = False

    vbs_ok = os.path.isfile(get_startup_vbs_path())
    return reg_ok or vbs_ok


def get_autostart_entry() -> Optional[str]:
    """获取当前配置的自启指令与位置说明"""
    res = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            if val:
                res.append(f"[注册表 Run] {val}")
    except (FileNotFoundError, OSError):
        pass

    vbs_path = get_startup_vbs_path()
    if os.path.isfile(vbs_path):
        res.append(f"[开始菜单 Startup] {vbs_path}")

    return " | ".join(res) if res else None


def enable_autostart() -> Tuple[bool, str]:
    """
    开启开机自启 (双重保障：写入 HKCU Run 注册表 + 写入开始菜单 Startup 启动脚本)
    """
    cmd = get_autostart_command()
    python_exe = get_pythonw_path()
    service_py = get_run_service_path()
    errors = []

    # 1. 写入注册表 HKCU Run
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
    except Exception as e:
        errors.append(f"注册表写入失败: {e}")

    # 2. 写入开始菜单 Startup 目录 VBS 静默拉起脚本
    try:
        vbs_path = get_startup_vbs_path()
        os.makedirs(os.path.dirname(vbs_path), exist_ok=True)
        vbs_content = (
            'Set WshShell = CreateObject("WScript.Shell")\r\n'
            f'WshShell.Run """{python_exe}"" ""{service_py}"" --no-browser", 0, False\r\n'
        )
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
    except Exception as e:
        errors.append(f"开始菜单启动项写入失败: {e}")

    if is_autostart_enabled():
        return True, (
            f"✅ 已成功开启开机自启！\n"
            f"  - 注册表位置: HKCU\\{REG_RUN_KEY}\\{APP_NAME}\n"
            f"  - 开始菜单位置: {get_startup_vbs_path()}\n"
            f"  - 启动指令: {cmd}"
        )
    else:
        err_str = "; ".join(errors) if errors else "校验失败"
        return False, f"❌ 注册开机自启失败: {err_str}"


def disable_autostart() -> Tuple[bool, str]:
    """关闭开机自启 (同时移除注册表项与开始菜单启动脚本)"""
    # 1. 移除注册表
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    except Exception:
        pass

    # 2. 移除开始菜单 Startup 脚本
    vbs_path = get_startup_vbs_path()
    if os.path.isfile(vbs_path):
        try:
            os.remove(vbs_path)
        except Exception:
            pass

    return True, "✅ 已成功关闭开机自启！"


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
            print(f"当前生效位置:     {entry}")
        print(f"建议启动指令:     {get_autostart_command()}")
        print("--------------------------------------------------")
        print("可用命令:")
        print("  python autostart.py --enable   # 开启开机自启")
        print("  python autostart.py --disable  # 关闭开机自启")
        print("  python autostart.py --toggle   # 切换开机自启")
        print("==================================================")
