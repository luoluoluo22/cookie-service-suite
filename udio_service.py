#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Udio AI 音乐生成服务客户端 (UdioService)
=====================================
基于浏览器实时 Cookie 动态提取与 Supabase 会话令牌无感解析。
采用 curl_cffi 原生指纹伪装技术，突破 Cloudflare 盾与风控。

核心功能：
- 自动从本地 Cookie Hub / 浏览器扩展提取 udio.com 的登录态 Cookie (sb-api-auth-token)
- 解析与自动注入 Bearer JWT Token
- 查询账户积分额度 (Credits / Quota)
- 支持纯器乐配乐模式 (Instrumental) 与自定义歌词模式 (Custom Lyrics)
- 异步与同步轮询任务状态，等待音频渲染完成
- 自动流式下载生成的超高清 MP3 到本地 downloads/udio 目录
"""

import os
import sys
import time
import json
import re
import urllib.parse
from typing import Optional, Dict, Any, List, Union, Callable

# 本地环回通信不走系统外部代理
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

from curl_cffi import requests
from cookie_bridge import CookieBridge

DEFAULT_BRIDGE_URL = "http://127.0.0.1:18888"
UDIO_BASE_URL = "https://www.udio.com"
UDIO_API_URL = "https://www.udio.com/api"

COOKIE_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".udio_cookie")
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "udio")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_default_proxy() -> str:
    """获取可用本地代理"""
    for env_var in ["HTTPS_PROXY", "HTTP_PROXY", "all_proxy", "ALL_PROXY"]:
        val = os.environ.get(env_var)
        if val:
            return val
    return "http://127.0.0.1:7897"


DEFAULT_PROXY = get_default_proxy()
DEFAULT_IMPERSONATE = "chrome120"

COMMON_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://www.udio.com",
    "Referer": "https://www.udio.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
}


class UdioService:
    def __init__(
        self,
        cookie_string: Optional[str] = None,
        bridge_url: str = DEFAULT_BRIDGE_URL,
        proxy: str = DEFAULT_PROXY,
        impersonate: str = DEFAULT_IMPERSONATE,
    ):
        self.bridge = CookieBridge(bridge_url)
        self.proxy = proxy
        self.impersonate = impersonate
        self.cookie_string: Optional[str] = cookie_string
        self.auth_token: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None

        if not self.cookie_string:
            self._load_cookie_cache()

        if not self.cookie_string:
            self.refresh_cookie_from_browser()

        self._extract_auth_token()

    def _load_cookie_cache(self) -> bool:
        """从本地磁盘缓存读取 Cookie"""
        if os.path.isfile(COOKIE_CACHE_FILE):
            try:
                with open(COOKIE_CACHE_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self.cookie_string = content
                        return True
            except Exception:
                pass
        return False

    def _save_cookie_cache(self):
        """持久化 Cookie 到本地磁盘"""
        if not self.cookie_string:
            return
        try:
            with open(COOKIE_CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(self.cookie_string)
        except Exception:
            pass

    def refresh_cookie_from_browser(self, timeout: int = 15) -> bool:
        """尝试通过本地 CookieBridge 从 Chrome / Edge 提取 udio.com 的 Cookie"""
        try:
            header_cookie = self.bridge.get_cookies_header("udio.com")
            if header_cookie and "sb-" in header_cookie:
                self.cookie_string = header_cookie
                self._save_cookie_cache()
                self._extract_auth_token()
                return True
        except Exception:
            pass
        return False

    def _extract_auth_token(self):
        """从 Cookie 中提取 Supabase 的 Bearer JWT Token"""
        if not self.cookie_string:
            return

        # 匹配 sb-api-auth-token 或 sb-auth-auth-token
        match = re.search(r'sb-[^=]+-auth-token=([^;]+)', self.cookie_string)
        if match:
            raw_val = match.group(1).strip()
            # 解码 URL 编码
            decoded = urllib.parse.unquote(raw_val)
            try:
                # 可能是 JSON array: ["jwt_token", "refresh_token", ...]
                data = json.loads(decoded)
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], str):
                    self.auth_token = data[0]
                    return
                elif isinstance(data, dict) and "access_token" in data:
                    self.auth_token = data["access_token"]
                    return
            except Exception:
                pass

            # 如果本身就是 JWT
            if decoded.startswith("eyJ"):
                self.auth_token = decoded
                return

        # 备选匹配直接以 eyJ 开头的字段
        jwt_match = re.search(r'(eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)', self.cookie_string)
        if jwt_match:
            self.auth_token = jwt_match.group(1)

    def _get_request_headers(self) -> Dict[str, str]:
        """构造带有鉴权信息的 Headers"""
        headers = dict(COMMON_HEADERS)
        if self.cookie_string:
            headers["Cookie"] = self.cookie_string
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def check_auth(self) -> Dict[str, Any]:
        """检查登录态与获取用户额度"""
        if not self.cookie_string:
            return {"authenticated": False, "error": "尚未获取到 udio.com 的登录 Cookie"}

        headers = self._get_request_headers()
        url = f"{UDIO_API_URL}/users/me"

        try:
            resp = requests.get(
                url,
                headers=headers,
                impersonate=self.impersonate,
                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.user_info = data
                return {
                    "authenticated": True,
                    "user": data,
                }
            else:
                return {
                    "authenticated": False,
                    "status_code": resp.status_code,
                    "error": resp.text[:200],
                }
        except Exception as e:
            return {"authenticated": False, "error": str(e)}

    def create_music(
        self,
        prompt: str,
        is_instrumental: bool = True,
        lyrics: str = "",
        model_version: str = "udio-32",
        bypass_prompt_optimization: bool = False,
    ) -> Dict[str, Any]:
        """
        向 Udio 发起生成请求
        :param prompt: 风格/场景描述词 (如: 'cinematic trailer background music, epic drums')
        :param is_instrumental: 是否纯伴奏模式 (视频配乐强烈推荐 True)
        :param lyrics: 自定义歌词 (纯伴奏时留空)
        :param model_version: 模型版本
        :param bypass_prompt_optimization: 是否跳过官方 prompt 润色
        """
        if not self.cookie_string:
            raise ValueError("缺少 Udio 登录态，请先在浏览器登录 https://www.udio.com")

        url = f"{UDIO_API_URL}/songs/create"
        headers = self._get_request_headers()
        headers["Content-Type"] = "application/json"

        payload = {
            "prompt": prompt,
            "samplerOptions": {
                "seed": -1,
                "bypass_prompt_optimization": bypass_prompt_optimization,
            },
            "customLyrics": lyrics if not is_instrumental else "",
            "isInstrumental": is_instrumental,
            "model": model_version,
        }

        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            impersonate=self.impersonate,
            proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
            timeout=30,
        )

        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Udio 生成失败 (HTTP {resp.status_code}): {resp.text}")

        return resp.json()

    def get_recent_tracks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最新生成的音乐列表"""
        url = f"{UDIO_API_URL}/songs"
        headers = self._get_request_headers()
        params = {"page": 1, "perPage": limit}

        resp = requests.get(
            url,
            headers=headers,
            params=params,
            impersonate=self.impersonate,
            proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
            timeout=15,
        )

        if resp.status_code != 200:
            raise RuntimeError(f"获取曲目列表失败 (HTTP {resp.status_code}): {resp.text}")

        data = resp.json()
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "songs" in data:
            return data["songs"]
        return []

    def wait_for_tracks(
        self,
        expected_ids: Optional[List[str]] = None,
        timeout: int = 240,
        poll_interval: int = 6,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """轮询曲目生成状态，直到完成或超时"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                tracks = self.get_recent_tracks(limit=10)
                if expected_ids:
                    target_tracks = [t for t in tracks if t.get("id") in expected_ids]
                else:
                    target_tracks = tracks[:2]

                finished_tracks = []
                for t in target_tracks:
                    song_path = t.get("song_path") or t.get("audio_url")
                    status = t.get("status") or t.get("state")
                    if song_path or status in ("FINISHED", "COMPLETED", "ready"):
                        finished_tracks.append(t)

                if finished_tracks and len(finished_tracks) >= (len(expected_ids) if expected_ids else 1):
                    if progress_cb:
                        progress_cb(f"✅ 生成完成！获得 {len(finished_tracks)} 首音乐。")
                    return finished_tracks

                if progress_cb:
                    elapsed = int(time.time() - start_time)
                    progress_cb(f"⏳ 正在渲染中... 已等待 {elapsed}s")

            except Exception as e:
                if progress_cb:
                    progress_cb(f"⚠️ 状态轮询告警: {e}")

            time.sleep(poll_interval)

        raise TimeoutError(f"等待 Udio 渲染超时 ({timeout}s)")

    def download_track(self, track: Dict[str, Any], output_dir: str = DOWNLOAD_DIR) -> str:
        """下载指定曲目 MP3 到本地"""
        audio_url = track.get("song_path") or track.get("audio_url")
        if not audio_url:
            raise ValueError("曲目尚未包含可下载的音频直链")

        title = track.get("title") or "udio_track"
        # 移除非法文件名字符
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title).strip()
        track_id = track.get("id", str(int(time.time())))[:8]
        filename = f"{safe_title}_{track_id}.mp3"
        filepath = os.path.join(output_dir, filename)

        resp = requests.get(
            audio_url,
            impersonate=self.impersonate,
            proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
            timeout=60,
        )
        if resp.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return filepath
        raise RuntimeError(f"下载曲目失败 (HTTP {resp.status_code})")
