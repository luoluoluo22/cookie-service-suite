"""
Bilibili 服务接口实现
基于浏览器实时 Cookie 调用哔哩哔哩 Web 端 API 及高清视频下载
"""

import os
import subprocess
import requests
from typing import Dict, Any, Optional
from cookie_bridge import CookieBridge


class BilibiliService:
    def __init__(self, bridge: Optional[CookieBridge] = None):
        self.bridge = bridge or CookieBridge()
        self.cookie_header = ""
        self.cookie_dict = {}
        try:
            self.cookie_header = self.bridge.get_cookies_header("bilibili.com")
            self.cookie_dict = self.bridge.get_cookies_dict("bilibili.com")
        except Exception:
            pass

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
            "Cookie": self.cookie_header
        })

    def _ensure_cookies(self):
        if not self.cookie_header:
            self.cookie_header = self.bridge.get_cookies_header("bilibili.com")
            self.cookie_dict = self.bridge.get_cookies_dict("bilibili.com")
            self.session.headers["Cookie"] = self.cookie_header

    def get_user_info(self) -> Dict[str, Any]:
        """获取当前登录账号的完整个人中心信息"""
        self._ensure_cookies()
        url = "https://api.bilibili.com/x/web-interface/nav"
        resp = self.session.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取 B 站用户信息失败: {data.get('message')}")
        return data.get("data", {})

    def get_video_info(self, bvid: str) -> Dict[str, Any]:
        """获取视频的基础信息与分P列表 (含 cid)"""
        url = "https://api.bilibili.com/x/web-interface/view"
        resp = self.session.get(url, params={"bvid": bvid}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取视频信息失败: {data.get('message')}")
        return data.get("data", {})

    def get_play_url(self, bvid: str, cid: Optional[int] = None, qn: int = 116) -> Dict[str, Any]:
        """
        获取视频播放直链流 (qn 80=1080P, 112=1080P+, 116=1080P60, 120=4K超清)
        拥有大会员 Cookie 凭证可直接获取高码率视频流
        """
        if cid is None:
            info = self.get_video_info(bvid)
            cid = info["cid"]

        url = "https://api.bilibili.com/x/player/playurl"
        params = {
            "bvid": bvid,
            "cid": cid,
            "qn": qn,
            "fnval": 16,  # 16 代表 dash 格式, 支持更高画质分离流
            "fnver": 0,
            "fourk": 1
        }
        resp = self.session.get(url, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def download_video_hd(self, video_url: str, output_dir: str = "./downloads") -> str:
        """
        使用 yt-dlp 结合实时 Cookie 自动下载最高画质视频 (1080P/4K)
        """
        os.makedirs(output_dir, exist_ok=True)
        cookie_file = os.path.join(output_dir, "bili_cookies.txt")
        self.bridge.export_netscape_file("bilibili.com", cookie_file)

        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "--cookies", cookie_file,
            "-o", output_template,
            "--no-playlist",
            video_url
        ]

        print(f"🎬 正在调用 yt-dlp 下载视频: {video_url}")
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res.returncode != 0:
            raise RuntimeError(f"yt-dlp 下载失败: {res.stderr}")
        return res.stdout
