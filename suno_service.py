#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Suno AI 音乐生成服务客户端 (SunoService)
=====================================
基于浏览器实时 Cookie 动态提取与 Clerk 会话令牌无感换取。
采用成熟的 curl_cffi 原生指纹伪装技术，完美突破 Cloudflare TLS 与 Bot 风控。
功能覆盖：
- 自动从本地 Cookie Hub 提取前台已登录的 Suno / Clerk Cookie (免手动 F12)
- 自动兑换与毫秒级保活 Clerk JWT 令牌 (Bearer Token)
- 查询账户积分额度 (Credits / Quota)
- 灵感描述模式 (Description Mode) 与 自定义歌词模式 (Custom Mode) 音乐生成
- 纯伴奏模式 (Make Instrumental) 与多版本模型切换 (chirp-v3-5, chirp-v4)
- 异步/同步状态轮询，等待歌曲渲染完成
- 纯歌词 AI 创作与获取
- 生成完毕后自动流式下载高清 MP3 到本地目录
"""

import os
import sys
import time
import json
import re
import subprocess
from typing import Optional, Dict, Any, List, Union, Callable
from urllib.parse import urlparse

# 保证本地通信不走系统外部代理，但对外请求走指定代理
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

from curl_cffi import requests
from cookie_bridge import CookieBridge

DEFAULT_BRIDGE_URL = "http://127.0.0.1:18888"
STUDIO_API_URL = "https://studio-api.prod.suno.com"
CLERK_CLIENT_URL = "https://clerk.suno.com/v1/client?_clerk_js_version=5.15.0"
CLERK_TOKEN_URL_TMPL = "https://clerk.suno.com/v1/client/sessions/{sid}/tokens/api?_clerk_js_version=5.15.0"
CLERK_TOKEN_ALT_URL_TMPL = "https://clerk.suno.com/v1/client/sessions/{sid}/tokens?_clerk_js_version=5.15.0"

DEFAULT_PROXY = "http://127.0.0.1:7897"
DEFAULT_IMPERSONATE = "edge101"

COOKIE_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".suno_cookie")
ALT_COOKIE_CACHE_FILE = os.path.join(os.path.expanduser("~"), ".suno_cookie")

COMMON_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://suno.com",
    "Referer": "https://suno.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
}


def ensure_bridge_server_running(bridge_url: str = DEFAULT_BRIDGE_URL, timeout: int = 5) -> bool:
    """检测并在需要时自动在后台静默拉起本地 Node 守护桥接服务 (node extension/server.js)"""
    import urllib.request
    local_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        req = urllib.request.Request(f"{bridge_url.rstrip('/')}/status")
        with local_opener.open(req, timeout=0.8) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass

    server_js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extension", "server.js")
    if not os.path.isfile(server_js):
        return False

    try:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW | 0x00000008  # DETACHED_PROCESS

        subprocess.Popen(
            ["node", server_js],
            cwd=os.path.dirname(server_js),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.3)
            try:
                req = urllib.request.Request(f"{bridge_url.rstrip('/')}/status")
                with local_opener.open(req, timeout=0.8) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                pass
    except Exception:
        pass

    return False


class SunoService:
    """
    Suno 音乐生成服务统一客户端
    """

    def __init__(
        self,
        bridge: Optional[CookieBridge] = None,
        cookie: Optional[str] = None,
        proxy: Optional[str] = DEFAULT_PROXY,
        impersonate: str = DEFAULT_IMPERSONATE,
        auto_init: bool = False,
    ):
        """
        初始化客户端
        :param bridge: 本地 CookieBridge 单例
        :param cookie: 手动传入的 Cookie 字符串 (可选，默认通过 CookieBridge 自动拉取)
        :param proxy: 外部请求 HTTP 代理地址 (默认 http://127.0.0.1:7897)
        :param impersonate: 伪装浏览器指纹 (默认 edge101，可选 chrome120 等)
        """
        self.bridge = bridge or CookieBridge(bridge_url=DEFAULT_BRIDGE_URL)
        self.manual_cookie = cookie or os.getenv("SUNO_COOKIE")
        self.proxy = proxy
        self.impersonate = impersonate

        # 凭证与会话状态
        self.session = requests.Session(impersonate=self.impersonate)
        if self.proxy:
            self.session.proxies = {"http": self.proxy, "https": self.proxy}

        self.cookie_header: str = ""
        self.jwt_token: Optional[str] = None
        self.jwt_expires_at: float = 0
        self.last_sid: Optional[str] = None

        if auto_init:
            self.refresh_auth()

    @staticmethod
    def load_cookie_cache() -> Optional[str]:
        """从本地持久化缓存文件载入已保存的 Cookie (支持免启动服务离线使用)"""
        for p in [COOKIE_CACHE_FILE, ALT_COOKIE_CACHE_FILE]:
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            return content
                except Exception:
                    pass
        return None

    @staticmethod
    def save_cookie_cache(cookie_str: str) -> bool:
        """保存 Cookie 至本地缓存文件，供无服务离线环境下直接读取"""
        if not cookie_str or not cookie_str.strip():
            return False
        try:
            with open(COOKIE_CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(cookie_str.strip())
            return True
        except Exception:
            return False

    def get_raw_cookies(self, force_fetch: bool = False, auto_visit: bool = True) -> str:
        """
        获取 Suno 与 Clerk 完整 Cookie
        采用全自动无感穿透策略：
        1. 显式传入的 manual_cookie / 环境变量 SUNO_COOKIE
        2. 本地持久化缓存 (.suno_cookie)
        3. 自动静默拉起本地 Bridge 守护服务，并通过 Cookie Hub 扩展直接从浏览器提取
        4. 若浏览器中尚未打开过 Suno，扩展将自动在后台静默打开 https://suno.com/create 唤醒会话并提取
        """
        if self.cookie_header and not force_fetch:
            return self.cookie_header

        # 1. 显式传入或环境变量
        if self.manual_cookie and not force_fetch:
            self.cookie_header = self.manual_cookie.strip()
            self.save_cookie_cache(self.cookie_header)
            return self.cookie_header

        env_cookie = os.getenv("SUNO_COOKIE")
        if env_cookie and not force_fetch:
            self.cookie_header = env_cookie.strip()
            self.save_cookie_cache(self.cookie_header)
            return self.cookie_header

        # 2. 若未指定强制刷新，先检查本地持久缓存
        if not force_fetch:
            cached = self.load_cookie_cache()
            if cached and ("__client" in cached or "__session" in cached):
                self.cookie_header = cached
                return self.cookie_header

        # 3. 自动探测并拉起本地 Bridge 服务，通知浏览器扩展自动提取或自动访问
        bridge_alive = ensure_bridge_server_running(self.bridge.bridge_url, timeout=3)
        if bridge_alive:
            try:
                # 首次尝试直接获取（若扩展已有 Cookie 则秒级返回）
                auto_res = self.bridge.auto_fetch_suno_cookies(force_visit=False, timeout=6)
                if auto_res.get("success") and auto_res.get("header"):
                    hdr = auto_res["header"].strip()
                    if "__client" in hdr or "__session" in hdr:
                        self.cookie_header = hdr
                        self.save_cookie_cache(hdr)
                        return self.cookie_header
            except Exception:
                pass

            # 若未获取到且允许自动唤醒，通知扩展在后台静默打开 suno.com 唤醒会话
            if auto_visit:
                try:
                    print("🌐 正在通过 Cookie Hub 扩展在浏览器中自动访问 suno.com 唤醒会话凭据...")
                    auto_res = self.bridge.auto_fetch_suno_cookies(force_visit=True, timeout=12)
                    if auto_res.get("success") and auto_res.get("header"):
                        hdr = auto_res["header"].strip()
                        if "__client" in hdr or "__session" in hdr:
                            self.cookie_header = hdr
                            self.save_cookie_cache(hdr)
                            return self.cookie_header
                except Exception:
                    pass

            # 普通域名提取兜底
            extracted_cookies = []
            try:
                c1 = self.bridge.get_cookies_header("suno.com")
                if c1:
                    extracted_cookies.append(c1)
            except Exception:
                pass
            try:
                c2 = self.bridge.get_cookies_header("clerk.suno.com")
                if c2 and c2 != (extracted_cookies[0] if extracted_cookies else ""):
                    extracted_cookies.append(c2)
            except Exception:
                pass

            merged = "; ".join(filter(None, extracted_cookies)).strip()
            if merged and ("__client" in merged or "__session" in merged):
                self.cookie_header = merged
                self.save_cookie_cache(merged)
                return self.cookie_header

        # 4. 再次检查本地缓存
        cached = self.load_cookie_cache()
        if cached:
            self.cookie_header = cached
            return self.cookie_header

        if not self.cookie_header:
            raise RuntimeError(
                "未能自动获取到 Suno 登录凭证！\n"
                "提示：Cookie Hub 扩展已尝试在浏览器中自动访问 suno.com，若您尚未在浏览器登录 Suno，\n"
                "请先在 Edge / Chrome 浏览器中登录一次 https://suno.com 账号（例如通过 Google 快捷登录），\n"
                "完成后本工具即可永久全自动感知提取，无需手动 F12 抓包！"
            )

        return self.cookie_header

    def _exchange_jwt_from_clerk(self) -> str:
        """
        使用 Cookie 向 Clerk 换取用于调用 Suno Studio API 的短效 JWT 访问令牌
        """
        cookies = self.get_raw_cookies()
        headers = dict(COMMON_HEADERS)
        headers["Cookie"] = cookies

        # 1. 向 Clerk 请求当前活跃 Session
        resp = self.session.get(
            CLERK_CLIENT_URL,
            headers=headers,
            timeout=20,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Clerk 接口响应异常 (HTTP {resp.status_code}): {resp.text[:300]}"
            )

        try:
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"Clerk 返回内容非合法 JSON: {resp.text[:300]}") from e

        res_obj = data.get("response", {})
        sid = res_obj.get("last_active_session_id")

        if not sid:
            # 尝试从 sessions 数组中获取首个活跃会话
            sessions = res_obj.get("sessions", [])
            for s in sessions:
                if s.get("status") == "active":
                    sid = s.get("id")
                    break
            if not sid and sessions:
                sid = sessions[0].get("id")

        if not sid:
            raise RuntimeError(
                "未能从 Clerk 解析到活跃会话 (last_active_session_id)！\n"
                "请检查浏览器中的 Suno 账号是否处于有效登录状态，或尝试在 suno.com 刷新页面。"
            )

        self.last_sid = sid

        # 2. 向 Clerk 换取 JWT Token
        token_url = CLERK_TOKEN_URL_TMPL.format(sid=sid)
        token_resp = self.session.post(token_url, headers=headers, timeout=20)

        # 兼容性重试备用 Token 端点
        if token_resp.status_code != 200:
            alt_url = CLERK_TOKEN_ALT_URL_TMPL.format(sid=sid)
            token_resp = self.session.post(alt_url, headers=headers, timeout=20)

        if token_resp.status_code != 200:
            raise RuntimeError(
                f"Clerk JWT Token 兑换失败 (HTTP {token_resp.status_code}): {token_resp.text[:300]}"
            )

        token_data = token_resp.json()
        jwt = token_data.get("jwt")
        if not jwt:
            raise RuntimeError(f"Clerk 响应未包含 jwt 字段: {token_resp.text}")

        self.jwt_token = jwt
        # JWT 有效期通常为 60 秒，设定 45 秒本地缓存安全时间
        self.jwt_expires_at = time.time() + 45
        return jwt

    def ensure_jwt(self, force_refresh: bool = False) -> str:
        """
        保证返回有效未过期的 JWT Token
        """
        if (
            not force_refresh
            and self.jwt_token
            and time.time() < self.jwt_expires_at
        ):
            return self.jwt_token

        return self._exchange_jwt_from_clerk()

    def refresh_auth(self) -> Dict[str, Any]:
        """
        强制刷新 Cookie 与 JWT 凭证，并测试连通性
        """
        self.get_raw_cookies(force_fetch=True)
        jwt = self.ensure_jwt(force_refresh=True)
        quota = self.get_credits()
        return {
            "success": True,
            "session_id": self.last_sid,
            "jwt_preview": jwt[:15] + "..." + jwt[-10:],
            "quota": quota,
        }

    def _api_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> Any:
        """
        向 Suno Studio API 发起带鉴权的请求 (含自动重试与 Token 自动续期)
        """
        jwt = self.ensure_jwt()
        headers = dict(COMMON_HEADERS)
        headers["Authorization"] = f"Bearer {jwt}"
        headers["Content-Type"] = "application/json"

        url = f"{STUDIO_API_URL.rstrip('/')}/{endpoint.lstrip('/')}"

        for retry in range(2):
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                )
            except Exception as e:
                if retry == 1:
                    raise
                time.sleep(1)
                continue

            # 若遇到 401 Unauthorized，则强制刷新 JWT 令牌并重试一次
            if resp.status_code == 401 and retry == 0:
                jwt = self.ensure_jwt(force_refresh=True)
                headers["Authorization"] = f"Bearer {jwt}"
                continue

            if not resp.ok:
                raise RuntimeError(
                    f"Suno API 请求失败 ({resp.status_code} {url}): {resp.text}"
                )

            return resp.json()

    # ==========================================
    # 核心业务接口
    # ==========================================

    def get_credits(self) -> Dict[str, Any]:
        """
        获取当前 Suno 账号的积分额度与使用情况
        """
        data = self._api_request("GET", "/api/billing/info/")
        total_credits = data.get("total_credits_left", 0)
        return {
            "total_credits_left": total_credits,
            "songs_left": int(total_credits // 10),
            "period": data.get("period", "day"),
            "monthly_limit": data.get("monthly_limit", 0),
            "monthly_usage": data.get("monthly_usage", 0),
            "raw": data,
        }

    def get_feed(self, page: int = 1) -> List[Dict[str, Any]]:
        """
        获取当前账号的历史曲库作品列表 (分页)
        """
        return self._api_request("GET", "/api/feed/", params={"page": page})

    def generate_music(
        self,
        prompt: str,
        is_custom: bool = False,
        tags: Optional[str] = None,
        title: str = "",
        make_instrumental: bool = False,
        model: str = "chirp-goose",
    ) -> List[Dict[str, Any]]:
        """
        提交音乐生成任务
        :param prompt: 提示词。在描述模式下为灵感描述；在自定义模式下为歌词正文。
        :param is_custom: 是否为自定义歌词模式 (Custom Mode)
        :param tags: 音乐风格标签 (仅自定义模式有效，如 "acoustic pop, guitar, upbeat, male vocal")
        :param title: 歌曲标题 (仅自定义模式有效)
        :param make_instrumental: 是否生成纯器乐伴奏 (无主唱人声)
        :param model: 模型版本 ("chirp-goose" (v6-mini 免费推荐), "chirp-v3-5", "chirp-v4" (需Pro))
        :return: 包含 2 个任务 clip 对象的列表 (含 clip id)
        """
        payload: Dict[str, Any] = {
            "mv": model,
            "make_instrumental": bool(make_instrumental),
        }

        if is_custom:
            payload["prompt"] = prompt.strip()
            payload["gpt_description_prompt"] = ""
            payload["title"] = title.strip()
            payload["tags"] = (tags or "").strip()
        else:
            payload["gpt_description_prompt"] = prompt.strip()
            payload["prompt"] = ""

        try:
            result = self._api_request("POST", "/api/generate/v2/", json_data=payload)
        except Exception as e:
            err_str = str(e).lower()
            # 若指定的模型需要 Pro 会员权限 (permission_denied)，自动降级为免费推荐模型 chirp-goose 重试
            if ("permission_denied" in err_str or "403" in err_str) and model != "chirp-goose":
                print(f"⚠️ 指定模型 {model} 限制 Pro 用户，自动降级为免费推荐模型 chirp-goose 重试...")
                payload["mv"] = "chirp-goose"
                result = self._api_request("POST", "/api/generate/v2/", json_data=payload)
            else:
                raise

        clips = result.get("clips", [])
        if not clips:
            raise RuntimeError(f"Suno 响应成功但未返回有效 clips: {result}")

        return clips

    def fetch_clips_status(self, clip_ids: List[str]) -> List[Dict[str, Any]]:
        """
        查询指定任务 clip 的当前生成进度与元数据
        """
        if not clip_ids:
            return []
        ids_str = "%2C".join(clip_ids)
        # 注意: Suno 要求逗号以 %2C 传入
        endpoint = f"/api/feed/?ids={ids_str}"
        return self._api_request("GET", endpoint)

    def wait_for_completion(
        self,
        clip_ids: List[str],
        timeout: int = 600,
        poll_interval: int = 5,
        progress_callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        阻塞轮询直到指定任务 clip 全部生成完毕并产出音频直链
        :param clip_ids: 待等待的 clip ID 列表
        :param timeout: 超时时间 (默认 600 秒)
        :param poll_interval: 轮询间隔 (默认 5 秒)
        :param progress_callback: 每次轮询后的进度回调函数 (入参为当前 clips 列表)
        :return: 生成完成的完整 clips 元数据列表
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            clips = self.fetch_clips_status(clip_ids)
            if progress_callback:
                progress_callback(clips)

            all_done = True
            for c in clips:
                status = c.get("status")
                # 严格等待 Suno 渲染状态到达 complete，确保音轨与 Progressive CDN 完全就绪
                if status == "error":
                    raise RuntimeError(
                        f"歌曲生成失败: Clip {c.get('id')} 状态为 error! (元数据: {c.get('metadata')})"
                    )
                if status != "complete":
                    all_done = False
                    break

            if all_done and clips:
                return clips

            time.sleep(poll_interval)

        raise TimeoutError(f"等待 Suno 生成超时 ({timeout} 秒)！当前 IDs: {clip_ids}")

    def decrypt_and_download_clip(
        self,
        clip_id: str,
        output_file_path: Optional[str] = None,
        media_url: Optional[str] = None,
        transcode_to_mp3: bool = False,
    ) -> str:
        """
        全量获取 Suno 最新加密渐进式媒体流 (delivery: progressive, content_type: m4a-opus, encoding: 1.0.0)。
        自动向 /api/mango/rights 端点获取封装凭证，以用户会话 JWT 为主密钥进行 AES-256-GCM 解包，
        最后通过 AES-CTR 逐块解密还原出 100% 原汁原味的标准无损 M4A/Opus 音频文件。
        """
        import base64
        import hashlib
        from Crypto.Cipher import AES

        self.ensure_jwt()
        if not self.jwt_token:
            raise RuntimeError("缺失有效的 Clerk JWT 凭据，无法解包 Suno 音频播放密钥！")

        # 1. 构造主解包密钥: SHA-256(jwt_token)
        master_key = hashlib.sha256(self.jwt_token.encode("utf-8")).digest()

        # 2. 调用 /api/mango/rights 获取 clip 对应的 Wrapped Key 与 Wrapped IV
        rights = self._api_request(
            "POST",
            "/api/mango/rights",
            json_data={
                "content_params": {
                    "content_id": clip_id,
                    "content_type": "clip"
                }
            }
        )

        key_b64 = rights.get("key")
        iv_b64 = rights.get("iv")
        if not key_b64 or not iv_b64:
            raise RuntimeError(f"获取媒体权限响应异常: {rights}")

        raw_key_wrapped = base64.b64decode(key_b64)
        raw_iv_wrapped = base64.b64decode(iv_b64)

        # 3. AES-256-GCM 解包出 Content Key (16字节) 和 Stream IV (16字节)
        def _unwrap(wrapped_data: bytes, aad_str: str) -> bytes:
            iv = wrapped_data[:12]
            ciphertext = wrapped_data[12:-16]
            tag = wrapped_data[-16:]
            cipher = AES.new(master_key, AES.MODE_GCM, nonce=iv)
            cipher.update(aad_str.encode("utf-8"))
            return cipher.decrypt_and_verify(ciphertext, tag)

        content_key = _unwrap(raw_key_wrapped, clip_id)
        content_iv = _unwrap(raw_iv_wrapped, clip_id)

        # 4. 下载 CDN 渐进加密音频流
        if not media_url:
            media_url = f"https://d2lwuy8qc234o3.cloudfront.net/1/clip/{clip_id}.m4a"

        headers = dict(COMMON_HEADERS)
        resp = self.session.get(media_url, headers=headers, timeout=60)
        resp.raise_for_status()
        encrypted_bytes = resp.content

        # 5. AES-CTR 解密出原汁原味的 M4A 容器 (内含 Opus 音频)
        ctr_cipher = AES.new(content_key, AES.MODE_CTR, initial_value=content_iv, nonce=b"")
        decrypted_bytes = ctr_cipher.decrypt(encrypted_bytes)

        if len(decrypted_bytes) >= 8 and b"ftyp" not in decrypted_bytes[:16]:
            raise RuntimeError("解密后未检测到标准 MP4/M4A 头部标识 (ftyp)！")

        # 6. 保存到文件
        if not output_file_path:
            output_file_path = os.path.join(".", "downloads", "suno", f"{clip_id}.m4a")

        os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)

        wants_mp3 = output_file_path.lower().endswith(".mp3") or transcode_to_mp3
        m4a_path = output_file_path if not wants_mp3 else (output_file_path[:-4] + ".m4a" if output_file_path.lower().endswith(".mp3") else output_file_path + ".m4a")

        with open(m4a_path, "wb") as f:
            f.write(decrypted_bytes)

        # 可选自动转码为 MP3 (若用户指定了 .mp3 扩展名)
        if wants_mp3:
            mp3_path = output_file_path if output_file_path.lower().endswith(".mp3") else output_file_path + ".mp3"
            try:
                import imageio_ffmpeg
                import subprocess
                ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                subprocess.run(
                    [ffmpeg_bin, "-y", "-i", m4a_path, "-c:a", "libmp3lame", "-q:a", "1", mp3_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                return os.path.abspath(mp3_path)
            except Exception:
                return os.path.abspath(m4a_path)

        return os.path.abspath(m4a_path)

    def get_or_decrypt_clip(
        self,
        clip_id: str,
        cache_dir: Optional[str] = None,
    ) -> str:
        """
        获取解密后的本地音频文件路径。
        若本地已有有效缓存（>10KB）则直接秒级返回缓存路径；
        若不存在则自动从 Suno CDN 拉取加密流并解密后存盘返回。
        """
        base_dir = cache_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "suno")
        os.makedirs(base_dir, exist_ok=True)

        for ext in [".m4a", ".mp3"]:
            target_path = os.path.join(base_dir, f"{clip_id}{ext}")
            if os.path.isfile(target_path) and os.path.getsize(target_path) > 10240:
                return os.path.abspath(target_path)

        # 检查是否已有带有短 id 或歌名的本地文件 (如 午后咖啡杯_a8d052.m4a)
        short_id = clip_id[:6]
        try:
            for fname in os.listdir(base_dir):
                if (clip_id in fname or fname.endswith(f"_{short_id}.m4a") or fname.endswith(f"_{short_id}.mp3")):
                    fpath = os.path.join(base_dir, fname)
                    if os.path.isfile(fpath) and os.path.getsize(fpath) > 10240:
                        return os.path.abspath(fpath)
        except Exception:
            pass

        # 缓存未命中，执行解密下载
        save_path = os.path.join(base_dir, f"{clip_id}.m4a")
        return self.decrypt_and_download_clip(clip_id=clip_id, output_file_path=save_path)

    def download_song(
        self,
        audio_url_or_clip_id: str,
        output_file_path: str,
        chunk_size: int = 64 * 1024,
    ) -> str:
        """
        智能下载音频：
        - 若传入的是 Clip ID 或包含 UUID / forbidden 的链接，自动执行 AES 密钥解包与 CTR 解密还原 M4A；
        - 若传入的是普通 MP3 CDN 直链，则按传统流式拉取。
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)

        # 识别 UUID 智能转入解密流
        uuid_match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', audio_url_or_clip_id.lower())
        if uuid_match:
            clip_id = uuid_match.group(0)
            try:
                return self.decrypt_and_download_clip(clip_id=clip_id, output_file_path=output_file_path)
            except Exception as e:
                # 若常规直链可用且不含 forbidden，降级尝试传统拉取
                if "forbidden" in audio_url_or_clip_id or not audio_url_or_clip_id.startswith("http"):
                    raise
                pass

        headers = dict(COMMON_HEADERS)
        resp = self.session.get(audio_url_or_clip_id, headers=headers, stream=True, timeout=60)
        resp.raise_for_status()

        with open(output_file_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        return os.path.abspath(output_file_path)

    def generate_lyrics(self, prompt: str, timeout: int = 60) -> Dict[str, Any]:
        """
        使用 Suno AI 单独创作歌词
        """
        res = self._api_request("POST", "/api/generate/lyrics/", json_data={"prompt": prompt})
        lid = res.get("id")
        if not lid:
            raise RuntimeError(f"生成歌词接口未返回 id: {res}")

        start_time = time.time()
        while time.time() - start_time < timeout:
            status_data = self._api_request("GET", f"/api/generate/lyrics/{lid}")
            if status_data.get("status") == "complete":
                return {
                    "id": lid,
                    "title": status_data.get("title", ""),
                    "text": status_data.get("text", ""),
                }
            time.sleep(2)

        raise TimeoutError(f"生成歌词超时 ({timeout} 秒)")

    def generate_and_download(
        self,
        prompt: str,
        output_dir: str = "./downloads/suno",
        is_custom: bool = False,
        tags: Optional[str] = None,
        title: str = "",
        make_instrumental: bool = False,
        model: str = "chirp-v3-5",
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        一站式自动化工作流：提交生成 -> 状态轮询 -> 下载音频 -> 返回完整文件路径与歌曲信息
        """
        if progress_callback:
            progress_callback(f"🎵 正在向 Suno 提交生成任务 (模型: {model})...")

        submitted_clips = self.generate_music(
            prompt=prompt,
            is_custom=is_custom,
            tags=tags,
            title=title,
            make_instrumental=make_instrumental,
            model=model,
        )

        clip_ids = [c["id"] for c in submitted_clips]
        if progress_callback:
            progress_callback(f"⏳ 任务已提交，获得 {len(clip_ids)} 个生成变体: {', '.join(clip_ids)}")

        # 轮询状态
        def _on_poll(clips):
            if progress_callback:
                statuses = [f"{c.get('title') or c.get('id')[:8]}: {c.get('status')}" for c in clips]
                progress_callback(f"⏳ 渲染进度: {' | '.join(statuses)}")

        completed_clips = self.wait_for_completion(
            clip_ids=clip_ids,
            timeout=600,
            poll_interval=5,
            progress_callback=_on_poll,
        )

        # 下载结果
        results = []
        for idx, clip in enumerate(completed_clips, 1):
            song_title = clip.get("title") or f"suno_track_{clip['id'][:8]}"
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", song_title)
            filename = f"{safe_title}_{clip['id'][:6]}.m4a"
            save_path = os.path.join(output_dir, filename)

            clip_id = clip.get("id")
            audio_url = clip.get("audio_url")
            if progress_callback:
                progress_callback(f"📥 正在解密下载第 {idx}/{len(completed_clips)} 首歌曲: {filename}...")

            try:
                # 优先走最新 Progressive 加密流解密通道
                downloaded_file = self.decrypt_and_download_clip(clip_id, save_path)
                clip["local_file"] = downloaded_file
            except Exception as e:
                # 降级尝试旧版直链
                if audio_url and "forbidden" not in audio_url:
                    try:
                        downloaded_file = self.download_song(audio_url, save_path)
                        clip["local_file"] = downloaded_file
                    except Exception:
                        clip["local_file"] = None
                else:
                    clip["local_file"] = None

            results.append(clip)

        if progress_callback:
            progress_callback(f"✅ 全部生成并下载完毕！已保存至: {os.path.abspath(output_dir)}")

        return results


# 默认单例
suno_service = SunoService()
