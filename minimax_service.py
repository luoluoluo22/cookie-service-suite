#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MiniMax Audio / 海螺语音服务客户端 (MinimaxAudioService)
======================================================
将 MiniMax Web 音频合成平台 (https://www.minimax.io/audio) 封装为本地高可用 API 服务。
支持功能：
1. 自动从本地 Cookie Hub 提取浏览器已登录的 _token 与 设备指纹 (免手动 F12)
2. 双通道合成驱动机制：
   - 优先通过浏览器扩展在真实网页 Context 驱动原生 WebSocket (100% 突破 TLS / Cloudflare / 签名风控)
   - 支持纯 Python 本地逆向计算 yy MD5 签名并直连官方 WebSocket (wss://www.minimax.io/v1/api/audio/ws)
3. 完美兼容标准 OpenAI Speech API (/v1/audio/speech)
4. 支持预置优质音色库（普通话沉稳高管、甜美亲切、知性主播、磁性大叔、英文优雅女声等）与音色克隆调用
5. 查询账户剩余可用字符配额 (Quota / Credits)
6. 自动将生成的高保真 MP3 文件持久化暂存至本地
"""

import os
import sys
import time
import json
import base64
import hashlib
import asyncio
import urllib.parse
from typing import Optional, Dict, Any, List, Union

# 保证本地通信不走系统代理
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

import requests
from cookie_bridge import CookieBridge
from web_api_switches import is_service_enabled, require_service_enabled

COOKIE_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".minimax_cookie")
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "minimax")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 默认预置官方优质音色库
PRESET_VOICES = [
    {
        "id": "355622221676659",
        "name": "纪录片中国配音 (经典女声)",
        "language": "zh",
        "gender": "female",
        "openai_alias": "documentary",
        "description": "中文普通话，大气沉稳，央视纪录片经典播音质感，极具感染力"
    },
    {
        "id": "226869000163456",
        "name": "沉稳高管 (青年男声)",
        "language": "zh",
        "gender": "male",
        "openai_alias": "alloy",
        "description": "中文普通话，标准口音，稳重大气，适合企业解说、科技评测与商业旁白"
    },
    {
        "id": "226869000163457",
        "name": "甜美悦耳 (温柔女声)",
        "language": "zh",
        "gender": "female",
        "openai_alias": "nova",
        "description": "中文普通话，甜美亲切，元气活泼，适合社媒短视频、故事陪伴与客服"
    },
    {
        "id": "226869000163458",
        "name": "磁性大叔 (浑厚男声)",
        "language": "zh",
        "gender": "male",
        "openai_alias": "onyx",
        "description": "中文普通话，低沉醇厚，富有故事感染力，适合纪录片、小说连载"
    },
    {
        "id": "226869000163459",
        "name": "知性主播 (专业女声)",
        "language": "zh",
        "gender": "female",
        "openai_alias": "shimmer",
        "description": "中文普通话，吐字清晰专业，适合新闻资讯、播客与长篇深度解读"
    },
    {
        "id": "355256451461319",
        "name": "Calm Woman (Smooth & Warm)",
        "language": "en",
        "gender": "female",
        "openai_alias": "fable",
        "description": "EN-US, smooth, articulate, calm assurance, perfect for audiobooks and essays"
    },
    {
        "id": "209533299589184",
        "name": "Energetic Youth (US Male)",
        "language": "en",
        "gender": "male",
        "openai_alias": "echo",
        "description": "EN-US, dynamic, confident, engaging tone for tutorials and podcasts"
    }
]

OPENAI_VOICE_MAP = {
    "alloy": "226869000163456",
    "nova": "226869000163457",
    "onyx": "226869000163458",
    "shimmer": "226869000163459",
    "fable": "355256451461319",
    "echo": "209533299589184",
    "documentary": "355622221676659"
}


class MinimaxAudioService:
    def __init__(self, bridge_url: str = "http://127.0.0.1:18888"):
        self.bridge_url = bridge_url.rstrip("/")
        self.bridge = CookieBridge(bridge_url)
        self.token = ""
        self.uuid = ""
        self.device_id = ""
        self.migrate_token = ""
        self.cookies_header = ""
        self.cookies_kv = {}
        self.last_fetch_time = 0
        self.auth_source = ""
        self._load_cached_auth()

    def _load_cached_auth(self) -> bool:
        """从本地磁盘读取上次缓存的登录态"""
        if os.path.exists(COOKIE_CACHE_FILE):
            try:
                with open(COOKIE_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.token = data.get("token", "")
                    self.uuid = data.get("uuid", "")
                    self.device_id = data.get("device_id", "")
                    self.migrate_token = data.get("migrate_token", "")
                    self.cookies_header = data.get("header", "")
                    self.cookies_kv = data.get("kv", {})
                    self.last_fetch_time = data.get("last_fetch_time", 0)
                    if self.token:
                        self.auth_source = "token_cache"
                    return bool(self.token)
            except Exception as e:
                print(f"[MiniMax] 加载缓存凭证警告: {e}")
        return False

    def _save_cached_auth(self):
        """将获取到的登录凭证暂存至本地磁盘"""
        try:
            data = {
                "token": self.token,
                "uuid": self.uuid,
                "device_id": self.device_id,
                "migrate_token": self.migrate_token,
                "header": self.cookies_header,
                "kv": self.cookies_kv,
                "last_fetch_time": time.time()
            }
            with open(COOKIE_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[MiniMax] 缓存凭证失败: {e}")

    def auto_refresh_auth(self, force_visit: bool = False, timeout: int = 20) -> Dict[str, Any]:
        """通过本地 Cookie Hub 扩展从浏览器中自动拉取最新 Token 与环境指纹"""
        require_service_enabled("minimax")
        try:
            res = self.bridge.auto_fetch_minimax_cookies(force_visit=force_visit, timeout=timeout)
            if res.get("success"):
                if res.get("token"):
                    self.token = res["token"]
                elif res.get("kv", {}).get("_token"):
                    self.token = res["kv"]["_token"]
                
                self.uuid = res.get("uuid") or self.uuid or "web_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:16]
                self.device_id = res.get("deviceId") or self.device_id
                self.migrate_token = res.get("migrateToken") or self.migrate_token
                self.cookies_header = res.get("header") or self.cookies_header
                self.cookies_kv = res.get("kv") or self.cookies_kv
                self.last_fetch_time = time.time()
                self.auth_source = "cookie_hub"
                self._save_cached_auth()
                return {"success": True, "token_ready": bool(self.token), "has_auth": res.get("hasAuth", False)}
            return res
        except Exception as e:
            return {"success": False, "error": str(e), "token_ready": bool(self.token)}

    def ensure_auth(self) -> bool:
        """确保当前具备可用的 Token"""
        require_service_enabled("minimax")
        if self.token:
            return True
        res = self.auto_refresh_auth(force_visit=False, timeout=10)
        return bool(self.token)

    @staticmethod
    def calc_yy_signature(path_with_params: str, method: str = "GET", body: Optional[dict] = None, timestamp_ms: Optional[int] = None) -> str:
        """
        逆向自海螺语音前端 module 51063 的核心签名算法:
        yy = MD5(encodeURIComponent(path_with_params) + "_" + JSON.stringify(body) + MD5(timestamp) + "ooui")
        """
        if timestamp_ms is None:
            timestamp_ms = int(time.time() * 1000)

        u_str = "{}"
        if method.upper() == "POST" and body:
            u_str = json.dumps(body, separators=(',', ':'), ensure_ascii=False)

        time_md5 = hashlib.md5(str(timestamp_ms).encode('utf-8')).hexdigest()
        raw = urllib.parse.quote(path_with_params, safe='') + "_" + u_str + time_md5 + "ooui"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def build_ws_url(self) -> str:
        """构造 WebSocket 握手 URL 并携带完整合法签名与会话凭证"""
        ts = int(time.time() * 1000)
        params = [
            ("device_platform", "web"),
            ("app_id", "3001"),
            ("version_code", "22201"),
            ("biz_id", "1"),
            ("lang", "en"),
            ("uuid", self.uuid or "anonymous"),
            ("device_id", self.device_id or "web_dev"),
            ("os_name", "Windows"),
            ("browser_name", "Chrome"),
            ("device_memory", "8"),
            ("cpu_core_num", "8"),
            ("browser_language", "zh-CN"),
            ("browser_platform", "Win32"),
            ("screen_width", "1920"),
            ("screen_height", "1080"),
            ("unix", str(ts))
        ]
        query_str = urllib.parse.urlencode(params)
        path_with_params = f"/v1/api/audio/ws?{query_str}"
        yy_sign = self.calc_yy_signature(path_with_params, method="GET", body=None, timestamp_ms=ts)

        full_url = (
            f"wss://www.minimax.io{path_with_params}"
            f"&yy={urllib.parse.quote(yy_sign)}"
            f"&token={urllib.parse.quote(self.token)}"
            f"&op_ticket="
        )
        return full_url

    async def _direct_websocket_synthesize(
        self,
        text: str,
        voice_id: str = "355622221676659",
        speed: float = 1.0,
        vol: float = 1.0,
        pitch: float = 0.0,
        format: str = "mp3",
        timeout: int = 40
    ) -> bytes:
        """纯 Python 异步连接官方 WebSocket 直连合成 (零浏览器依赖，秒级响应)"""
        import websockets

        ws_url = self.build_ws_url()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://www.minimax.io",
            "Referer": "https://www.minimax.io/audio",
            "Cookie": self.cookies_header
        }

        audio_chunks = []
        msg_id = f"py_t2a_{int(time.time() * 1000)}"

        # 核心逆向成果: method 必须为 "T2a", pitch 必须为整数类型
        payload = {
            "method": "T2a",
            "msg_id": msg_id,
            "payload": {
                "model": "speech-2.8-hd",
                "text": text,
                "stream": True,
                "voice_setting": {
                    "voice_id": str(voice_id),
                    "speed": float(speed),
                    "vol": float(vol),
                    "pitch": int(pitch)
                },
                "audio_setting": {
                    "sample_rate": 32000,
                    "bitrate": 128000,
                    "format": format,
                    "channel": 1
                }
            }
        }

        async with websockets.connect(
            ws_url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=15,
            open_timeout=15,
            max_size=32 * 1024 * 1024
        ) as ws:
            await ws.send(json.dumps(payload))

            start_t = time.time()
            while time.time() - start_t < timeout:
                try:
                    res_raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    msg = json.loads(res_raw)

                    if msg.get("statusInfo", {}).get("code", 0) != 0 and msg.get("statusInfo", {}).get("code") is not None:
                        raise RuntimeError(f"MiniMax 报错: {msg.get('statusInfo', {}).get('message', '未知错误')}")

                    if msg.get("method") == "Heartbeat":
                        await ws.send(json.dumps({"method": "Heartbeat", "msg_id": msg.get("msg_id"), "timestamp": int(time.time() * 1000)}))
                        continue

                    data = msg.get("data", {})
                    if data.get("audio"):
                        audio_chunks.append(data["audio"])

                    # status 2 代表 COMPLETED
                    if data.get("status") == 2 or data.get("is_end"):
                        break
                except asyncio.TimeoutError:
                    break

        if not audio_chunks:
            raise RuntimeError("未收到任何音频数据包")

        full_raw_str = "".join(audio_chunks)
        try:
            return bytes.fromhex(full_raw_str)
        except Exception:
            return base64.b64decode(full_raw_str)

    def synthesize(
        self,
        text: str,
        voice: str = "355622221676659",
        speed: float = 1.0,
        vol: float = 1.0,
        pitch: float = 0.0,
        format: str = "mp3",
        timeout: int = 40
    ) -> bytes:
        """
        统一合成入口（高可用双引擎调度）：
        1. 优先采用 Python 原生 WebSocket 直连通道（秒级响应、无 UI 阻塞）
        2. 直连异常时平滑降级至本地浏览器扩展 Bridge 通道
        """
        require_service_enabled("minimax")
        resolved_voice_id = OPENAI_VOICE_MAP.get(voice.lower(), voice)

        # 尝试通道 1：Python 原生直连 WebSocket 引擎
        self.ensure_auth()
        if self.token:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_bytes = loop.run_until_complete(
                    self._direct_websocket_synthesize(
                        text=text,
                        voice_id=resolved_voice_id,
                        speed=speed,
                        vol=vol,
                        pitch=pitch,
                        format=format,
                        timeout=timeout
                    )
                )
                loop.close()
                self._save_audio_file(audio_bytes, format)
                return audio_bytes
            except Exception as e:
                print(f"[MiniMax] 直连 WebSocket 引擎提示 (平滑切至浏览器扩展桥接): {e}")

        # 尝试通道 2：浏览器扩展 原生 Hook 驱动
        try:
            status = self.bridge.check_status()
            if status.get("extensionConnected"):
                bridge_res = self.bridge.generate_minimax_speech_via_bridge(
                    text=text,
                    voice_id=resolved_voice_id,
                    speed=speed,
                    vol=vol,
                    pitch=pitch,
                    format=format,
                    timeout=timeout
                )
                if bridge_res.get("success") and bridge_res.get("audio_base64"):
                    audio_raw = bridge_res["audio_base64"]
                    try:
                        audio_bytes = bytes.fromhex(audio_raw)
                    except Exception:
                        audio_bytes = base64.b64decode(audio_raw)
                    self._save_audio_file(audio_bytes, format)
                    return audio_bytes
        except Exception as e:
            print(f"[MiniMax] 扩展桥接通道异常: {e}")

        raise RuntimeError("MiniMax 语音合成在直连模式与扩展桥接模式下均未能成功生成")

    def _save_audio_file(self, audio_bytes: bytes, format: str = "mp3") -> str:
        """保存音频到本地 downloads/minimax 目录"""
        try:
            filename = f"speech_{int(time.time())}_{hashlib.md5(audio_bytes[:100]).hexdigest()[:8]}.{format}"
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(audio_bytes)
            return filepath
        except Exception:
            return ""

    @staticmethod
    def _decode_jwt_claims(token: Optional[str]) -> Dict[str, Any]:
        """无签名校验解析 MiniMax _token JWT 载荷"""
        if not token or "." not in token:
            return {}
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return {}
            payload = parts[1]
            payload += "=" * (-len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload.encode("utf-8"))
            obj = json.loads(decoded.decode("utf-8"))
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def _api_get(self, path_base: str, extra_params: Optional[Dict[str, Any]] = None, timeout: int = 8) -> Dict[str, Any]:
        """向 MiniMax Web API 发起带 yy 签名的 GET 请求"""
        ts = int(time.time() * 1000)
        params = {
            "device_platform": "web",
            "app_id": "3001",
            "version_code": "22201",
            "biz_id": "1",
            "lang": "en",
            "uuid": self.uuid or "anonymous",
            "device_id": self.device_id or "web_dev",
            "unix": str(ts),
        }
        if extra_params:
            params.update(extra_params)
        query_str = urllib.parse.urlencode(params)
        path = f"{path_base}?{query_str}"
        yy = self.calc_yy_signature(path, method="GET", timestamp_ms=ts)

        headers = {
            "token": self.token,
            "yy": yy,
            "Cookie": self.cookies_header or "",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.minimax.io/audio",
            "Origin": "https://www.minimax.io",
        }
        r = requests.get(f"https://www.minimax.io{path}", headers=headers, timeout=timeout)
        r.raise_for_status()
        res = r.json()
        return res if isinstance(res, dict) else {}

    def get_user_info(self, timeout: int = 8) -> Dict[str, Any]:
        """查询 MiniMax 当前登录用户信息与 VIP 状态 (/v1/api/user/info)"""
        if not self.token:
            return {"error": "未登录或未获取到 Token"}
        try:
            return self._api_get("/v1/api/user/info", timeout=timeout)
        except Exception as e:
            return {"error": str(e)}

    def get_billing_credit(self, timeout: int = 8) -> Dict[str, Any]:
        """查询 MiniMax 账户积分与订阅包 (/v1/api/billing/credit)"""
        if not self.token:
            return {"error": "未登录或未获取到 Token"}
        try:
            return self._api_get("/v1/api/billing/credit", timeout=timeout)
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _parse_minimax_membership(
        user_info: Optional[Dict[str, Any]] = None,
        credit_data: Optional[Dict[str, Any]] = None,
        remains_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """综合 userInfo.vipInfo、billing/credit 与 remains_cnt 解析 MiniMax 会员与计费类型"""
        u = user_info or {}
        credit = credit_data or {}
        remains = remains_data or {}

        vip_info = u.get("vipInfo") if isinstance(u.get("vipInfo"), dict) else {}
        raw_vip_type = vip_info.get("type", 0)
        try:
            vip_type = int(raw_vip_type or 0)
        except Exception:
            vip_type = 0

        raw_expire = vip_info.get("expireTime", 0) or 0
        try:
            expire_at = int(float(raw_expire))
            if expire_at > 10**12:
                expire_at = expire_at // 1000
        except Exception:
            expire_at = 0

        now = int(time.time())
        is_expired = expire_at > 0 and expire_at < now

        vip_name = (
            str(
                vip_info.get("name")
                or vip_info.get("planName")
                or vip_info.get("title")
                or vip_info.get("levelName")
                or u.get("plan")
                or u.get("membership")
                or remains.get("plan")
                or ""
            ).strip()
        )

        sub_credits = credit.get("sub_credits") if isinstance(credit.get("sub_credits"), list) else []
        try:
            total_credit = float(credit.get("total_credit") or 0)
        except Exception:
            total_credit = 0.0
        try:
            debit_credit = float(credit.get("debit_credit") or 0)
        except Exception:
            debit_credit = 0.0

        if not is_expired and vip_name and vip_name.lower() not in ("free", "免费版", "none", "0", "normal"):
            low = vip_name.lower()
            tier = "PRO" if "pro" in low else ("PLUS" if "plus" in low else ("MAX" if "max" in low else vip_name.upper()))
            label = vip_name if "minimax" in low else f"MiniMax {vip_name}"
            return {
                "is_member": True,
                "plan_tier": tier,
                "membership_label": label,
                "vip_type": vip_type,
                "expire_at": expire_at,
            }

        if not is_expired and vip_type > 0:
            vip_map = {
                1: ("VIP", "MiniMax VIP"),
                2: ("PRO", "MiniMax Pro"),
                3: ("MAX", "MiniMax Max"),
            }
            tier, label = vip_map.get(vip_type, ("VIP", f"MiniMax VIP ({vip_type})"))
            return {
                "is_member": True,
                "plan_tier": tier,
                "membership_label": label,
                "vip_type": vip_type,
                "expire_at": expire_at,
            }

        if len(sub_credits) > 0:
            return {
                "is_member": True,
                "plan_tier": "SUB",
                "membership_label": "MiniMax 订阅会员",
                "vip_type": vip_type,
                "expire_at": expire_at,
            }

        if total_credit > 0 or debit_credit > 0:
            return {
                "is_member": False,
                "plan_tier": "PAYG",
                "membership_label": "按量计费",
                "vip_type": vip_type,
                "expire_at": expire_at,
            }

        return {
            "is_member": False,
            "plan_tier": "FREE",
            "membership_label": "免费版",
            "vip_type": vip_type,
            "expire_at": expire_at,
        }

    def get_quota(self) -> Dict[str, Any]:
        """查询剩余配额字符数与账户权益"""
        self.ensure_auth()
        if not self.token:
            return {"error": "未登录或未获取到 Token", "remains": 0, "credit": 0}

        ts = int(time.time() * 1000)
        params = {"device_platform": "web", "app_id": "3001", "version_code": "22201", "biz_id": "1", "unix": str(ts)}
        query_str = urllib.parse.urlencode(params)
        path = f"/v1/api/audio/billing/remains_cnt?{query_str}"
        yy = self.calc_yy_signature(path, method="GET", timestamp_ms=ts)

        headers = {
            "token": self.token,
            "yy": yy,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.minimax.io/audio"
        }
        try:
            r = requests.get(f"https://www.minimax.io{path}", headers=headers, timeout=8)
            res = r.json()
            data = res.get("data", res)
            if isinstance(data, dict) and not data:
                # 兜底补充 /v1/api/billing/credit 积分数据
                credit_res = self.get_billing_credit(timeout=8)
                credit_data = credit_res.get("data") if isinstance(credit_res.get("data"), dict) else {}
                if credit_data:
                    merged = dict(credit_data)
                    status_info = res.get("statusInfo") or {}
                    if status_info.get("code", 0) != 0:
                        merged["remains_message"] = status_info.get("message", "")
                    return merged
            return data
        except Exception as e:
            return {"error": str(e), "remains": "未知"}

    def get_dashboard_accounts(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """返回供统一账号看板展示的标准化 MiniMax 账号列表（失败或未登录时安全降级）"""
        if not is_service_enabled("minimax"):
            return []
        now = int(time.time())
        if refresh:
            try:
                self.auto_refresh_auth(force_visit=False, timeout=6)
            except Exception:
                pass
        elif not self.token:
            try:
                self.auto_refresh_auth(force_visit=False, timeout=4)
            except Exception:
                pass

        if not self.token:
            return []

        claims = self._decode_jwt_claims(self.token)
        jwt_user = claims.get("user") if isinstance(claims.get("user"), dict) else {}
        jwt_exp = claims.get("exp")
        jwt_expired = False
        try:
            if jwt_exp and int(jwt_exp) < now:
                jwt_expired = True
        except Exception:
            pass

        user_res = self.get_user_info(timeout=8)
        status_info = user_res.get("statusInfo") if isinstance(user_res.get("statusInfo"), dict) else {}
        status_code = status_info.get("code", 0)
        status_msg = str(status_info.get("message") or user_res.get("error") or "")

        # 若 token 失效且尚未在本次尝试过 Cookie Hub 刷新，静默拉取一次再重试
        is_auth_fail = (
            (status_code not in (0, None) and any(k in status_msg.lower() for k in ("token", "login", "auth", "expire", "unauth")))
            or status_code in (401, 1001, 1004, 10004)
        )
        if is_auth_fail and not refresh:
            try:
                ref = self.auto_refresh_auth(force_visit=False, timeout=5)
                if ref.get("success") and self.token:
                    user_res = self.get_user_info(timeout=8)
                    status_info = user_res.get("statusInfo") if isinstance(user_res.get("statusInfo"), dict) else {}
                    status_code = status_info.get("code", 0)
                    status_msg = str(status_info.get("message") or user_res.get("error") or "")
                    claims = self._decode_jwt_claims(self.token)
                    jwt_user = claims.get("user") if isinstance(claims.get("user"), dict) else {}
                    jwt_expired = False
            except Exception:
                pass

        user_data = user_res.get("data") if isinstance(user_res.get("data"), dict) else {}
        user_info = user_data.get("userInfo") if isinstance(user_data.get("userInfo"), dict) else {}
        if not user_info and isinstance(user_res.get("userInfo"), dict):
            user_info = user_res["userInfo"]

        if user_res.get("error") or (status_code not in (0, None) and not user_info):
            raw_id = str(jwt_user.get("id") or self.uuid or "").strip()
            name = str(jwt_user.get("name") or "").strip()
            if not raw_id and not name:
                return []
            err_msg = status_msg or str(user_res.get("error") or "未知错误")
            is_auth_err = jwt_expired or any(
                k in err_msg.lower() for k in ("401", "token", "login", "auth", "expire", "unauth")
            )
            return [
                {
                    "platform": "minimax",
                    "platform_name": "MiniMax",
                    "id": f"minimax:{raw_id or 'default'}",
                    "raw_id": raw_id or "default",
                    "name": name or (f"MiniMax ({raw_id[:8]})" if raw_id else "MiniMax 用户"),
                    "email": "",
                    "is_member": False,
                    "plan_tier": "FREE",
                    "membership": "FREE",
                    "membership_label": "免费版",
                    "quota_summary": "登录凭证已过期" if is_auth_err else "暂无法获取账户信息",
                    "status": "not_logged_in" if is_auth_err else "offline",
                    "visible": True,
                    "note": err_msg[:180],
                    "source": self.auth_source or "token_cache",
                    "login_url": "https://www.minimax.io/audio",
                    "updated_at": now,
                    "details": {
                        "user_id": raw_id,
                        "uuid": self.uuid,
                        "error": err_msg,
                    },
                }
            ]

        credit_res = self.get_billing_credit(timeout=8)
        credit_data = credit_res.get("data") if isinstance(credit_res.get("data"), dict) else {}

        remains_data: Dict[str, Any] = {}
        try:
            rem_res = self._api_get("/v1/api/audio/billing/remains_cnt", timeout=5)
            if isinstance(rem_res.get("data"), dict) and rem_res["data"]:
                remains_data = rem_res["data"]
        except Exception:
            pass

        raw_id = str(
            user_info.get("realUserID")
            or user_info.get("userID")
            or jwt_user.get("id")
            or self.uuid
            or "default"
        ).strip()
        email = str(user_info.get("email") or "").strip()
        name = (
            str(user_info.get("name") or user_info.get("subUserName") or jwt_user.get("name") or "").strip()
            or (email.split("@")[0] if email else "")
            or f"MiniMax ({raw_id[:8]})"
        )
        avatar_url = str(user_info.get("avatar") or jwt_user.get("avatar") or "").strip()

        membership = self._parse_minimax_membership(user_info, credit_data, remains_data)

        total_credit = credit_data.get("total_credit", 0)
        debit_credit = credit_data.get("debit_credit", 0)
        remains_val = remains_data.get("remains") or remains_data.get("remains_cnt")

        quota_parts = []
        if remains_val is not None:
            quota_parts.append(f"语音额度 {remains_val}")
        if credit_data:
            quota_parts.append(f"账户积分 {total_credit}")
            if debit_credit:
                quota_parts.append(f"余额 {debit_credit}")
        if membership.get("expire_at") and membership["expire_at"] > now:
            exp_str = time.strftime("%Y-%m-%d", time.localtime(membership["expire_at"]))
            quota_parts.append(f"到期 {exp_str}")
        quota_summary = " · ".join(quota_parts) if quota_parts else "Token 已就绪"

        note_parts = []
        if user_info.get("userID"):
            note_parts.append(f"ID: {user_info['userID']}")
        if self.device_id:
            note_parts.append("WebSocket/Bridge 就绪")

        return [
            {
                "platform": "minimax",
                "platform_name": "MiniMax",
                "id": f"minimax:{raw_id}",
                "raw_id": raw_id,
                "name": name,
                "email": email,
                "is_member": membership["is_member"],
                "plan_tier": membership["plan_tier"],
                "membership": membership["plan_tier"],
                "membership_label": membership["membership_label"],
                "quota_summary": quota_summary,
                "status": "ready",
                "visible": True,
                "note": " · ".join(note_parts),
                "source": self.auth_source or "token_cache",
                "login_url": "https://www.minimax.io/audio",
                "updated_at": now,
                "details": {
                    "user_id": user_info.get("userID") or raw_id,
                    "real_user_id": user_info.get("realUserID") or raw_id,
                    "uuid": self.uuid,
                    "avatar_url": avatar_url,
                    "vip_type": membership["vip_type"],
                    "expire_at": membership["expire_at"],
                    "total_credit": total_credit,
                    "debit_credit": debit_credit,
                    "sub_credits": credit_data.get("sub_credits", []),
                    "remains": remains_val,
                },
            }
        ]

    def refresh_dashboard_accounts(self) -> List[Dict[str, Any]]:
        """刷新 MiniMax Cookie/Token 并返回最新看板账号信息"""
        require_service_enabled("minimax")
        return self.get_dashboard_accounts(refresh=True)

    def get_voices(self) -> List[Dict[str, Any]]:
        """获取全部音色列表（预置优质音色 + 线上音色）"""
        return PRESET_VOICES


# 单例实例
minimax_service = MinimaxAudioService()
