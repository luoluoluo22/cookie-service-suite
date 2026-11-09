"""
Cookie Hub 本地通信服务 Python SDK
用于向本地运行的 127.0.0.1:18888 请求前台浏览器的实时 Cookie
"""

import os
import requests
from typing import Dict, Any, Optional

DEFAULT_BRIDGE_URL = "http://127.0.0.1:18888"


class CookieBridge:
    def __init__(self, bridge_url: str = DEFAULT_BRIDGE_URL):
        self.bridge_url = bridge_url.rstrip("/")
        # 强制本地回环通信直连，不读取环境变量中的外部代理设置
        self.session = requests.Session()
        self.session.trust_env = False

    def check_status(self) -> Dict[str, Any]:
        """检查本地通信服务与扩展连接状态"""
        try:
            resp = self.session.get(f"{self.bridge_url}/status", timeout=1.5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise ConnectionError(f"无法连接到本地 Cookie Hub 服务 ({self.bridge_url}): {e}")

    def get_cookies_header(self, domain: str) -> str:
        """获取指定域名的 Header 格式 Cookie 字符串 (用于 requests headers)"""
        resp = self.session.get(
            f"{self.bridge_url}/cookies",
            params={"domain": domain, "format": "header"},
            timeout=15
        )
        resp.raise_for_status()
        return resp.text.strip()

    def get_cookies_dict(self, domain: str) -> Dict[str, str]:
        """获取指定域名的键值对字典 (用于 requests cookies 参数)"""
        resp = self.session.get(
            f"{self.bridge_url}/cookies",
            params={"domain": domain, "format": "json"},
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()

    def get_active_tab_cookies(self) -> Dict[str, Any]:
        """获取浏览器当前前台活动标签页的完整 Cookie"""
        resp = self.session.get(f"{self.bridge_url}/active", timeout=15)
        resp.raise_for_status()
        return resp.json()

    def auto_fetch_suno_cookies(self, force_visit: bool = False, timeout: int = 25) -> Dict[str, Any]:
        """通知浏览器扩展自动访问 Suno 并提取登录态 Cookie (免手动 F12 抓包)"""
        resp = self.session.get(
            f"{self.bridge_url}/suno/auto_fetch",
            params={
                "force": "true" if force_visit else "false",
                "timeout": int(timeout * 1000)
            },
            timeout=timeout + 2
        )
        resp.raise_for_status()
        return resp.json()

    def export_netscape_file(self, domain: str, output_path: str) -> str:
        """导出标准 Netscape 格式 cookies.txt (供 yt-dlp / curl -b / wget 使用)"""
        resp = self.session.get(
            f"{self.bridge_url}/cookies",
            params={"domain": domain, "format": "netscape"},
            timeout=5
        )
        resp.raise_for_status()
        content = resp.text

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        # 严格无 BOM UTF-8 保存
        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return output_path


# 默认单例
bridge = CookieBridge()
