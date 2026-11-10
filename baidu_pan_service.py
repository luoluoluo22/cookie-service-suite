"""
百度网盘 Web API 服务实现
基于浏览器实时 Cookie 调用百度网盘用户中心、容量配额及文件列表
具备持久化缓存、多域 Cookie 自动合并、代理直连避险及过期自动重试自愈能力
"""

import os
import sys
import requests
from typing import Dict, Any, Optional
from cookie_bridge import CookieBridge

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

COOKIE_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".baidu_cookie")


class BaiduPanService:
    def __init__(self, bridge: Optional[CookieBridge] = None):
        self.bridge = bridge or CookieBridge()
        self.cookie_header = ""
        
        # 1. 尝试从本地缓存载入
        cached = self.load_cookie_cache()
        if cached:
            self.cookie_header = cached

        # 2. 本地回环直接通信，规避外部代理
        self.session = requests.Session()
        # pan.baidu.com 国内请求必须直连，禁止走可能导致风控被拒的海外外部代理
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://pan.baidu.com/disk/main",
            "Cookie": self.cookie_header
        })

        # 首次初始化时若无缓存则尝试提取一次
        if not self.cookie_header:
            try:
                self.fetch_cookies_from_bridge(force=False)
            except Exception:
                pass

    @staticmethod
    def load_cookie_cache() -> Optional[str]:
        """从本地持久化缓存文件载入已保存的百度网盘 Cookie"""
        if os.path.isfile(COOKIE_CACHE_FILE):
            try:
                with open(COOKIE_CACHE_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content and ("BDUSS" in content or "BAIDUID" in content or "STOKEN" in content):
                        return content
            except Exception:
                pass
        return None

    @staticmethod
    def save_cookie_cache(cookie_str: str) -> bool:
        """保存 Cookie 至本地缓存文件，供无前台浏览器时直接复用"""
        if not cookie_str or not cookie_str.strip():
            return False
        try:
            with open(COOKIE_CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(cookie_str.strip())
            return True
        except Exception:
            return False

    def fetch_cookies_from_bridge(self, force: bool = False) -> str:
        """
        从 Cookie Hub (18888) 提取浏览器当前百度网盘 Cookie
        采用多域深度合并策略：同时抓取 baidu.com 根域凭证 (BDUSS, STOKEN) 与 pan.baidu.com 子域 Cookie
        """
        if self.cookie_header and not force:
            return self.cookie_header

        extracted_headers = []

        # 1. 获取 pan.baidu.com /disk/main 精确 Cookie
        try:
            resp = self.bridge.session.get(
                f"{self.bridge.bridge_url}/cookies",
                params={"url": "https://pan.baidu.com/disk/main", "format": "header"},
                timeout=8
            )
            if resp.ok and resp.text.strip():
                extracted_headers.append(resp.text.strip())
        except Exception:
            pass

        # 2. 获取 baidu.com 根域名通用鉴权凭证 (BDUSS / STOKEN 等关键票据)
        try:
            resp2 = self.bridge.session.get(
                f"{self.bridge.bridge_url}/cookies",
                params={"domain": "baidu.com", "format": "header"},
                timeout=8
            )
            if resp2.ok and resp2.text.strip():
                extracted_headers.append(resp2.text.strip())
        except Exception:
            pass

        # 合并去重
        cookie_dict = {}
        for h in extracted_headers:
            for item in h.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookie_dict[k.strip()] = v.strip()

        if not cookie_dict:
            # 若桥接未获取到，尝试退回本地缓存
            cached = self.load_cookie_cache()
            if cached:
                self.cookie_header = cached
                self.session.headers["Cookie"] = self.cookie_header
                return self.cookie_header
            raise RuntimeError("未能从 Cookie Hub 提取到有效的百度网盘 Cookie，请确保浏览器已登录 pan.baidu.com 并加载 Cookie Hub 扩展！")

        merged_header = "; ".join(f"{k}={v}" for k, v in cookie_dict.items())
        self.cookie_header = merged_header
        self.session.headers["Cookie"] = self.cookie_header
        self.save_cookie_cache(merged_header)
        return merged_header

    def _ensure_cookies(self):
        """确保会话中含有有效的 Cookie"""
        if not self.cookie_header:
            self.fetch_cookies_from_bridge(force=True)

    def refresh_auth(self) -> Dict[str, Any]:
        """强制从前台浏览器提取最新百度网盘 Cookie 并刷新会话"""
        hdr = self.fetch_cookies_from_bridge(force=True)
        uinfo = self.get_user_info()
        return {
            "success": True,
            "cookie_length": len(hdr),
            "user": uinfo.get("baidu_name", ""),
            "uk": uinfo.get("uk", 0),
        }

    def get_user_info(self) -> Dict[str, Any]:
        """获取百度网盘当前登录用户信息 (用户名、网盘昵称、UK) - 支持自动刷新自愈"""
        self._ensure_cookies()
        url = "https://pan.baidu.com/rest/2.0/xpan/nas?method=uinfo"

        for retry in range(2):
            resp = self.session.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errno") == 0:
                return data

            # 若遇到 errno != 0 (未登录或 Cookie 过期)，且为首次尝试，则自动强制向 Cookie Hub 刷新凭证重试
            if retry == 0:
                try:
                    self.fetch_cookies_from_bridge(force=True)
                    continue
                except Exception:
                    pass

            raise RuntimeError(f"获取用户信息失败 (errno={data.get('errno')}): {data.get('errmsg', '未登录或 Cookie 失效')}")

    def get_quota(self) -> Dict[str, Any]:
        """获取网盘总容量、已用空间及剩余空间 (单位: GB) - 支持自动刷新自愈"""
        self._ensure_cookies()
        url = "https://pan.baidu.com/api/quota?checkexpire=1&checkfree=1"

        for retry in range(2):
            resp = self.session.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errno") == 0:
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

            if retry == 0:
                try:
                    self.fetch_cookies_from_bridge(force=True)
                    continue
                except Exception:
                    pass

            raise RuntimeError(f"获取网盘容量失败 (errno={data.get('errno')})")

    def list_files(self, dir_path: str = "/", limit: int = 50) -> Dict[str, Any]:
        """获取网盘指定目录下的文件与文件夹列表 - 支持自动刷新自愈"""
        self._ensure_cookies()
        url = "https://pan.baidu.com/api/list"
        params = {
            "dir": dir_path,
            "num": limit,
            "order": "time",
            "desc": 1
        }

        for retry in range(2):
            resp = self.session.get(url, params=params, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errno") == 0:
                return data

            if retry == 0:
                try:
                    self.fetch_cookies_from_bridge(force=True)
                    continue
                except Exception:
                    pass

            raise RuntimeError(f"获取文件列表失败 (errno={data.get('errno')})")
