"""
百度网盘 Web API 服务实现
基于浏览器实时 Cookie 调用百度网盘用户中心、容量配额及文件列表
"""

import sys
import requests
from typing import Dict, Any, Optional
from cookie_bridge import CookieBridge

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class BaiduPanService:
    def __init__(self, bridge: Optional[CookieBridge] = None):
        self.bridge = bridge or CookieBridge()
        
        # 使用 pan.baidu.com/disk/main 完整 URL 获取 Cookie，
        # 确保自动包含父域 .baidu.com 的核心鉴权票据 BDUSS 以及 pan.baidu.com 的 STOKEN
        resp = requests.get(
            f"{self.bridge.bridge_url}/cookies",
            params={"url": "https://pan.baidu.com/disk/main", "format": "header"},
            timeout=5
        )
        resp.raise_for_status()
        self.cookie_header = resp.text.strip()

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://pan.baidu.com/disk/main",
            "Cookie": self.cookie_header
        })

    def get_user_info(self) -> Dict[str, Any]:
        """获取百度网盘当前登录用户信息 (用户名、网盘昵称、UK)"""
        url = "https://pan.baidu.com/rest/2.0/xpan/nas?method=uinfo"
        resp = self.session.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errno") != 0:
            raise RuntimeError(f"获取用户信息失败: {data.get('errmsg', '未登录或 Cookie 失效')}")
        return data

    def get_quota(self) -> Dict[str, Any]:
        """获取网盘总容量、已用空间及剩余空间 (单位: GB)"""
        url = "https://pan.baidu.com/api/quota?checkexpire=1&checkfree=1"
        resp = self.session.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errno") != 0:
            raise RuntimeError(f"获取网盘容量失败 (errno={data.get('errno')})")

        total_bytes = data.get("total", 0)
        used_bytes = data.get("used", 0)
        free_bytes = max(0, total_bytes - used_bytes)

        total_gb = round(total_bytes / (1024 ** 3), 2)
        used_gb = round(used_bytes / (1024 ** 3), 2)
        free_gb = round(free_bytes / (1024 ** 3), 2)

        return {
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "raw": data
        }

    def list_files(self, dir_path: str = "/", limit: int = 50) -> Dict[str, Any]:
        """获取网盘指定目录下的文件与文件夹列表"""
        url = "https://pan.baidu.com/api/list"
        params = {
            "dir": dir_path,
            "num": limit,
            "order": "time",
            "desc": 1
        }
        resp = self.session.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errno") != 0:
            raise RuntimeError(f"获取文件列表失败 (errno={data.get('errno')})")
        return data
