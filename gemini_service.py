"""
Google Gemini Web 服务调用与多账号统一调度模块
支持 Google 浏览器多账号登录机制（/u/0, /u/1, /u/2, /u/3...）
支持多账号自动轮转（Load Balancing）、故障熔断切换与 OpenAI 兼容接口
"""

import os
import sys
import time
import json
import sqlite3
import socket
import subprocess
import threading
import urllib.parse
import urllib.request
import re
import ssl
import asyncio
from typing import Optional, Dict, Any, List, Tuple

# 保证本地回环网络请求不走外部代理（Clash 等），避免 502 Bad Gateway
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"
_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _proxy_is_open(proxy_url: str) -> bool:
    raw = (proxy_url or "").strip()
    if not raw:
        return False
    if "://" not in raw:
        raw = "http://" + raw
    host_port = raw.split("://", 1)[1].split("/", 1)[0]
    if host_port.startswith("["):
        host, _, port_text = host_port.rpartition("]:")
        host = host[1:]
    elif ":" in host_port:
        host, port_text = host_port.rsplit(":", 1)
    else:
        return False
    try:
        port = int(port_text)
    except ValueError:
        return False
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except Exception:
        return False


def _windows_system_proxy() -> str:
    """读取本机 Windows 系统代理，避免沿用别的开发机写死的端口。"""
    if sys.platform != "win32":
        return ""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not enabled:
                return ""
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
    except Exception:
        return ""
    server = str(server or "").strip()
    if not server or "=" in server:
        parts = {}
        for item in server.split(";"):
            if "=" in item:
                name, value = item.split("=", 1)
                parts[name.strip().lower()] = value.strip()
        server = parts.get("https") or parts.get("http") or ""
    if not server:
        return ""
    if "://" not in server:
        server = "http://" + server
    return server


def _detect_local_proxy() -> str:
    """选用当前这台机器上真正在监听的代理。没有可用端口时不套用旧机器配置。"""
    candidates = []
    for key in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy"):
        value = (os.environ.get(key) or "").strip()
        if value:
            candidates.append(value)
    system_proxy = _windows_system_proxy()
    if system_proxy:
        candidates.append(system_proxy)
    for port in (7890, 7897, 10808, 10809, 1080, 7891):
        candidates.append(f"http://127.0.0.1:{port}")

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if _proxy_is_open(candidate):
            return candidate if "://" in candidate else "http://" + candidate
    return ""


def _cookie_value(cookie_str: str, name: str) -> str:
    prefix = f"{name}="
    for part in (cookie_str or "").split(";"):
        item = part.strip()
        if item.startswith(prefix):
            return item[len(prefix):]
    return ""

_CANDIDATE_SRC = os.path.join(
    os.path.dirname(__file__), "candidate_repos", "Gemini-API-HanaokaYuzu", "src"
)
if os.path.exists(_CANDIDATE_SRC) and _CANDIDATE_SRC not in sys.path:
    sys.path.insert(0, _CANDIDATE_SRC)

from cookie_bridge import CookieBridge
from login_status import GEMINI_BLOCK_SECONDS, GEMINI_MIN_INTERVAL_SECONDS, gemini_failure_kind


class GeminiService:
    """Gemini 网页端单账号服务客户端，支持通过本地 Cookie Hub 自动提取凭证调用。"""

    def __init__(
        self,
        bridge_url: str = "http://127.0.0.1:18888",
        proxy: Optional[str] = None,
    ):
        self.bridge = CookieBridge(bridge_url=bridge_url)
        self.proxy = proxy or _detect_local_proxy()
        self.client = None
        self._loop = None

    def _get_auth_cookies(self) -> Dict[str, str]:
        cookies_dict = self.bridge.get_cookies_dict("google.com")
        return {
            "psid": cookies_dict.get("__Secure-1PSID", ""),
            "psidts": cookies_dict.get("__Secure-1PSIDTS", ""),
        }

    async def _ensure_client(self):
        from gemini_webapi import GeminiClient

        curr_loop = asyncio.get_running_loop()
        if self.client is None or self._loop != curr_loop:
            self._loop = curr_loop
            auth = self._get_auth_cookies()
            if not auth["psid"]:
                raise RuntimeError(
                    "未能从浏览器中检测到 __Secure-1PSID，请确认浏览器中已登录 Google 账号！"
                )
            self.client = GeminiClient(
                secure_1psid=auth["psid"],
                secure_1psidts=auth["psidts"],
                proxy=self.proxy,
            )
            await self.client.init(timeout=30, auto_close=False, auto_refresh=False)
        return self.client

    async def async_ask(self, prompt: str, model: Optional[str] = None) -> str:
        """异步提问并获取回复文本。"""
        client = await self._ensure_client()
        response = await client.generate_content(prompt, model=model)
        return response.text

    def ask(self, prompt: str, model: Optional[str] = None) -> str:
        """同步提问快捷接口。"""
        return asyncio.run(self.async_ask(prompt, model=model))

    async def async_get_quota(self) -> Dict[str, Any]:
        """获取账号额度。"""
        client = await self._ensure_client()
        return client.quotas or {}

    def get_quota(self) -> Dict[str, Any]:
        """同步获取账号额度。"""
        return asyncio.run(self.async_get_quota())


class GeminiPace:
    """限制打到 Google 的频率。冷却期内直接拒绝，不再发出上游请求。"""

    def __init__(self, max_inflight_timeout: float = 60.0) -> None:
        self._lock = threading.Lock()
        self.last_finished_at = 0.0
        self.blocked_until = 0.0
        self.inflight = False
        self.inflight_started_at = 0.0
        self.max_inflight_timeout = max_inflight_timeout
        self.last_failure_reason = ""
        self.last_failure_at = 0.0

    def get_status(self) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            # 挂起超时自动解除
            if self.inflight and (now - self.inflight_started_at > self.max_inflight_timeout):
                self.inflight = False
                self.last_finished_at = now
                if not self.last_failure_reason:
                    self.last_failure_reason = f"上一轮调用挂起超时 ({int(self.max_inflight_timeout)}s 未返回，已自动解除锁定)"

            remain_seconds = 0
            state = "idle"
            if self.inflight:
                state = "inflight"
                elapsed = now - self.inflight_started_at
                remain_seconds = max(1, int(self.max_inflight_timeout - elapsed))
            elif now < self.blocked_until:
                state = "blocked"
                remain_seconds = max(1, int(self.blocked_until - now))
            elif self.last_finished_at and (now - self.last_finished_at < GEMINI_MIN_INTERVAL_SECONDS):
                state = "cooling"
                remain_seconds = max(1, int(self.last_finished_at + GEMINI_MIN_INTERVAL_SECONDS - now))

            return {
                "state": state,
                "can_call": (state == "idle"),
                "inflight": self.inflight,
                "inflight_seconds": int(now - self.inflight_started_at) if self.inflight else 0,
                "retry_after": remain_seconds,
                "last_finished_at": self.last_finished_at,
                "blocked_until": self.blocked_until,
                "last_failure_reason": self.last_failure_reason,
                "last_failure_at": self.last_failure_at,
            }

    def reset(self) -> None:
        """强制复位所有锁与冷却状态"""
        with self._lock:
            self.inflight = False
            self.inflight_started_at = 0.0
            self.blocked_until = 0.0
            self.last_finished_at = 0.0

    def _wait_message(self, remain: int, blocked: bool) -> str:
        remain = max(1, int(remain))
        fail_hint = f" 【上次失败原因: {self.last_failure_reason}】" if self.last_failure_reason else ""
        if blocked:
            reason = "上一次请求被 Google 风控页拦住了，服务端已暂停 Gemini 调用。"
        else:
            reason = f"两次 Gemini 调用需至少间隔 {GEMINI_MIN_INTERVAL_SECONDS} 秒（从上一轮结束起算）。"
        return (
            f"{reason}请等待倒计时 {remain} 秒后再试，这期间请勿重复点击。"
            f"账号仍是登录状态。{fail_hint}"
        )

    def acquire(self) -> None:
        # 本地间隔锁已撤掉，用来观察 Google 现在是否还要求两次调用之间留空。
        return

    def release(self, message: str = "") -> None:
        with self._lock:
            self.inflight = False
            self.inflight_started_at = 0.0
            now = time.time()
            self.last_finished_at = now
            if message:
                self.last_failure_reason = str(message)
                self.last_failure_at = now
                if gemini_failure_kind(message) == "blocked":
                    self.blocked_until = max(self.blocked_until, now + GEMINI_BLOCK_SECONDS)
            else:
                self.last_failure_reason = ""


def describe_upstream_error(exc: Exception) -> str:
    """把本地号池的 HTTP 502 换成响应正文里的真实原因。"""
    message = str(exc)
    body = ""
    if hasattr(exc, "read"):
        try:
            body = exc.read().decode("utf-8", "replace").strip()
        except Exception:
            body = ""
    if body:
        try:
            parsed = json.loads(body)
            err = parsed.get("error") if isinstance(parsed, dict) else None
            if isinstance(err, dict) and err.get("message"):
                body = str(err["message"])
            elif isinstance(err, str):
                body = err
        except Exception:
            pass
        return body[:500]
    return message


# 网页显示名已经换代。4 Hydrogen 沿用原 3.8 的线路，号池二进制仍叫 gemini-3.8-flash。
_WEB_BASE_TO_POOL = {
    "gemini-4-hydrogen": "gemini-3.8-flash",
    "gemini-3.7-flash": "gemini-3.8-flash",
    "gemini-3.6-flash": "gemini-3.8-flash",
}


def resolve_model_reasoning(model: str, reasoning_level: str = "off") -> str:
    """把网页模型名和思考档换成号池当前接受的模型 id。"""
    clean_level = (reasoning_level or "off").lower().strip()
    base_model = (model or "gemini-4-hydrogen").strip()
    if not base_model.startswith("gemini"):
        return base_model

    raw_base = base_model
    for suffix in ("-thinking-medium", "-thinking", "-thinking-lite"):
        if raw_base.endswith(suffix):
            raw_base = raw_base[: -len(suffix)]
            break
    if raw_base == "gemini-4-carbon":
        raise ValueError("4 Carbon（高难任务）在当前账号未开通")
    raw_base = _WEB_BASE_TO_POOL.get(raw_base, raw_base)

    if clean_level in ("high", "extended", "deep"):
        if raw_base == "gemini-4-argon":
            return "gemini-4-argon-thinking"
        return f"{raw_base}-thinking"
    if clean_level == "medium" and raw_base == "gemini-4-argon":
        return "gemini-4-argon-thinking-medium"
    return raw_base


_DISPLAY_TO_ID = {
    "3.5 flash-lite": "gemini-3.5-flash-lite",
    "4 hydrogen": "gemini-4-hydrogen",
    "3.1 pro": "gemini-3.1-pro",
    "4 argon": "gemini-4-argon",
    "4 carbon": "gemini-4-carbon",
}

_WEB_MODEL_FALLBACK = [
    {"id": "gemini-3.5-flash-lite", "name": "3.5 Flash-Lite", "role": "快速解答", "label": "3.5 Flash-Lite（快速解答）", "locked": False},
    {"id": "gemini-4-hydrogen", "name": "4 Hydrogen", "role": "日常帮助", "label": "4 Hydrogen（日常帮助）", "locked": False},
    {"id": "gemini-3.1-pro", "name": "3.1 Pro", "role": "深度研究", "label": "3.1 Pro（深度研究）", "locked": False},
    {"id": "gemini-4-argon", "name": "4 Argon", "role": "代码与分析", "label": "4 Argon（代码与分析）", "locked": False},
    {"id": "gemini-4-carbon", "name": "4 Carbon", "role": "高难任务", "label": "4 Carbon（高难任务 · 未开通）", "locked": True},
]


def _web_model_id(display: str) -> str:
    key = re.sub(r"\s+", " ", (display or "").strip().lower())
    if key in _DISPLAY_TO_ID:
        return _DISPLAY_TO_ID[key]
    slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    return f"gemini-{slug}" if slug else ""


def _web_model_label(display: str, role: str, locked: bool) -> str:
    display = (display or "").strip()
    role = (role or "").strip()
    if locked:
        role = f"{role} · 未开通" if role else "未开通"
    if role and role != display:
        return f"{display}（{role}）"
    return display


def _parse_web_model_payload(body: str) -> List[Dict[str, Any]]:
    inner = None
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("[["):
            continue
        try:
            arr = json.loads(line)
        except Exception:
            continue
        for item in arr:
            if (
                isinstance(item, list)
                and item
                and item[0] == "wrb.fr"
                and len(item) > 2
                and isinstance(item[2], str)
            ):
                try:
                    inner = json.loads(item[2])
                except Exception:
                    inner = None
                break
        if inner is not None:
            break
    if not isinstance(inner, list):
        return []

    models: List[Dict[str, Any]] = []
    seen = set()
    picker = None
    if len(inner) > 24 and isinstance(inner[24], list) and len(inner[24]) > 1:
        picker = inner[24][1]
    if isinstance(picker, list):
        for item in picker:
            head = item[0] if isinstance(item, list) and item and isinstance(item[0], list) else None
            if not head or len(head) < 6:
                continue
            display = str(head[5] or "").strip()
            role = str(head[12]).strip() if len(head) > 12 and isinstance(head[12], str) else ""
            mid = _web_model_id(display)
            if not mid or mid in seen:
                continue
            seen.add(mid)
            models.append({
                "id": mid,
                "name": display,
                "role": role,
                "label": _web_model_label(display, role, False),
                "locked": False,
            })

    catalog = inner[15] if len(inner) > 15 and isinstance(inner[15], list) else []
    for row in catalog:
        if not isinstance(row, list) or len(row) < 3:
            continue
        display = str(row[2] or row[1] or "").strip()
        role = str(row[11]).strip() if len(row) > 11 and isinstance(row[11], str) else ""
        mid = _web_model_id(display)
        if not mid or mid in seen:
            continue
        seen.add(mid)
        models.append({
            "id": mid,
            "name": display,
            "role": role,
            "label": _web_model_label(display, role, True),
            "locked": True,
        })
    return models


class MultiAccountGeminiPool:
    """
    Gemini 浏览器多账号池化调度管理器。
    
    统一接管浏览器中登录的多个 Google 账号（如 /u/0, /u/1, /u/2, /u/3）：
    1. 从 Cookie Hub 自动提取完整安全凭据；
    2. 按照 authuser 裂变为独立账号池，配置最久未用（LRU）轮转；
    3. 支持故障熔断换号与额度倍增（4x 额度）；
    4. 对外提供标准 OpenAI 兼容接口 (/v1/chat/completions) 与 Python 便捷调用。
    """

    def __init__(
        self,
        bridge_url: str = "http://127.0.0.1:18888",
        port: int = 18083,
        proxy: Optional[str] = None,
        account_count: int = 4,
        api_key: str = "sk-gemini-cookie-suite",
    ):
        self.bridge = CookieBridge(bridge_url=bridge_url)
        self.port = port
        self.proxy = proxy or _detect_local_proxy()
        self.account_count = account_count
        self.api_key = api_key
        
        self.base_dir = os.path.join(
            os.path.dirname(__file__), "candidate_repos", "gemini-web2api-go"
        )
        self.db_path = os.path.join(self.base_dir, "gemini_pool.db")
        self.config_path = os.path.join(self.base_dir, "config_pool.json")
        self.exe_path = os.path.join(self.base_dir, "gemini-web2api.exe")
        self.proc: Optional[subprocess.Popen] = None
        self._pace = GeminiPace()
        self._lifecycle_lock = threading.Lock()
        self._sync_thread: Optional[threading.Thread] = None
        self._web_models_cache: List[Dict[str, Any]] = []
        self._web_models_at = 0.0

    def _extract_cookie_header(self) -> str:
        """从 Cookie Hub 提取组装 Google 必要会话鉴权串。"""
        url = f"{self.bridge.bridge_url}/cookies?domain=google.com"
        try:
            with _LOCAL_OPENER.open(url, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cookies = data.get("cookies", [])
        except Exception as e:
            raise ConnectionError(f"无法连接本地 Cookie Hub 提取凭证 ({self.bridge.bridge_url}): {e}")

        target_keys = [
            "SID",
            "HSID",
            "SSID",
            "APISID",
            "SAPISID",
            "__Secure-1PSID",
            "__Secure-1PSIDTS",
            "__Secure-1PSIDCC",
        ]
        parts = []
        for k in target_keys:
            v = next((c["value"] for c in cookies if c.get("name") == k), "")
            if v:
                parts.append(f"{k}={v}")

        if not parts:
            raise RuntimeError("未能提取到有效的 Google 鉴权 Cookie！")
        return "; ".join(parts)

    def init_database(self, force_refresh: bool = False, cookie_str: Optional[str] = None):
        """初始化多账号数据库与池化配额表。"""
        if cookie_str is None:
            cookie_str = ""
            try:
                cookie_str = self._extract_cookie_header()
            except Exception as e:
                print(f"⚠️ 初始化账号池凭证提示: {e}", flush=True)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS accounts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            label         TEXT NOT NULL DEFAULT '',
            cookie        TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'enabled',
            note          TEXT NOT NULL DEFAULT '',
            created_at    INTEGER NOT NULL,
            last_used_at  INTEGER NOT NULL DEFAULT 0,
            last_ok_at    INTEGER NOT NULL DEFAULT 0,
            last_error    TEXT NOT NULL DEFAULT '',
            fail_count    INTEGER NOT NULL DEFAULT 0,
            proxy_id      INTEGER NOT NULL DEFAULT 0,
            authuser      INTEGER NOT NULL DEFAULT 0
        );
        """
        )
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS kv (
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        );
        """
        )
        cur.execute(
            "INSERT OR REPLACE INTO kv (k, v) VALUES ('api_key', ?)", (self.api_key,)
        )

        now = int(time.time())
        existing = cur.execute("SELECT authuser, cookie FROM accounts").fetchall()
        existing_users = {row[0]: row[1] or "" for row in existing}

        for u in range(self.account_count):
            if u not in existing_users:
                cur.execute(
                    """INSERT INTO accounts (label, cookie, status, note, created_at, authuser)
                       VALUES (?, ?, 'enabled', ?, ?, ?)""",
                    (
                        f"Google Account [u/{u}]",
                        cookie_str,
                        f"Browser Multi-Account Index {u}",
                        now,
                        u,
                    ),
                )
                continue
            # 扩展还没连上时不要用空串覆盖已经可用的凭证
            if cookie_str and (force_refresh or not _cookie_value(existing_users[u], "__Secure-1PSID")):
                cur.execute(
                    "UPDATE accounts SET cookie=?, status='enabled', fail_count=0 WHERE authuser=?",
                    (cookie_str, u),
                )

        conn.commit()
        conn.close()

    def generate_config(self):
        """生成服务的 runtime 配置文件。"""
        config = {
            "port": self.port,
            "host": "127.0.0.1",
            "db_path": self.db_path,
            "admin_enabled": True,
            "admin_token": "admin_gemini_pool",
            "impersonate": "chrome_146",
            "default_model": "gemini-3.5-flash-lite",
            "proxy": self.proxy,
            "web_channel": False,
            "log_requests": True,
            "request_timeout_sec": 120,
            "proxy_cooldown_min": 1,
            "retry_attempts": 3,
            "retry_delay_sec": 2,
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def is_running(self) -> bool:
        """检查多账号服务是否正在运行。"""
        try:
            with _LOCAL_OPENER.open(
                f"http://127.0.0.1:{self.port}/", timeout=2
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_upstream_models(self) -> list:
        """读取号池当前公布的 Gemini 网页模型 id。"""
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            with _LOCAL_OPENER.open(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            return []
        ids = []
        seen = set()
        for item in payload.get("data") or []:
            mid = str((item or {}).get("id") or "").strip()
            if not mid or mid in seen:
                continue
            seen.add(mid)
            ids.append(mid)
        return ids

    def list_web_models(self) -> List[Dict[str, Any]]:
        """读取 Gemini 网页选择器当前的模型，名字与页面一致。"""
        now = time.time()
        if self._web_models_cache and now - self._web_models_at < 600:
            return list(self._web_models_cache)
        parsed = self._fetch_web_models()
        models = parsed or list(_WEB_MODEL_FALLBACK)
        self._web_models_cache = list(models)
        self._web_models_at = now if parsed else now - 540
        return list(models)

    def _fetch_web_models(self) -> List[Dict[str, Any]]:
        cookie = ""
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT cookie FROM accounts WHERE authuser = 0 AND cookie != '' LIMIT 1"
            ).fetchone()
            conn.close()
            cookie = row[0] if row else ""
        except Exception:
            return []
        if not cookie or not self.proxy:
            return []
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy}),
            urllib.request.HTTPSHandler(context=ctx),
        )
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        try:
            page_req = urllib.request.Request(
                "https://gemini.google.com/app",
                headers={"Cookie": cookie, "User-Agent": ua},
            )
            with opener.open(page_req, timeout=20) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return []
        xsrf = (re.search(r'"SNlM0e":"([^"]+)"', html) or [None, ""])[1]
        bl = (re.search(r'"cfb2h":"([^"]+)"', html) or [None, ""])[1]
        if not xsrf or not bl:
            return []
        freq = json.dumps([[["otAQ7b", "[]", None, "generic"]]])
        form = urllib.parse.urlencode({"f.req": freq, "at": xsrf}).encode()
        url = (
            "https://gemini.google.com/_/BardChatUi/data/batchexecute"
            f"?rpcids=otAQ7b&bl={urllib.parse.quote(bl)}&hl=zh-CN&_reqid=123456&rt=c"
        )
        try:
            rpc_req = urllib.request.Request(
                url,
                data=form,
                headers={
                    "Cookie": cookie,
                    "User-Agent": ua,
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Origin": "https://gemini.google.com",
                    "Referer": "https://gemini.google.com/app",
                    "X-Same-Domain": "1",
                },
            )
            with opener.open(rpc_req, timeout=20) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return []
        return _parse_web_model_payload(body)

    def _config_proxy(self) -> str:
        try:
            with open(self.config_path, "r", encoding="utf-8") as fh:
                return str(json.load(fh).get("proxy") or "")
        except Exception:
            return ""

    def _release_port(self):
        """停掉自己拉起的进程，以及仍占用本端口的旧 gemini-web2api。"""
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

        try:
            out = subprocess.check_output(
                f'netstat -ano | findstr ":{self.port}" | findstr "LISTENING"',
                shell=True,
                text=True,
                errors="replace",
            )
        except Exception:
            out = ""
        pids = set()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[1].endswith(f":{self.port}"):
                try:
                    pid = int(parts[-1])
                except ValueError:
                    continue
                if pid > 0 and pid != os.getpid():
                    pids.add(pid)
        for pid in pids:
            subprocess.run(
                f"taskkill /F /PID {pid}",
                shell=True,
                capture_output=True,
            )
        for _ in range(10):
            if not self.is_running():
                return
            time.sleep(0.3)

    def _launch_process(self, wait_timeout: int = 15) -> bool:
        if not os.path.exists(self.exe_path):
            raise FileNotFoundError(f"未找到 gemini-web2api.exe 核心二进制: {self.exe_path}")

        self.generate_config()
        log_path = os.path.join(self.base_dir, "gemini_pool.log")
        log_file = open(log_path, "a", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(
            [self.exe_path, "-config", self.config_path],
            cwd=self.base_dir,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        for _ in range(wait_timeout):
            time.sleep(1)
            if self.is_running():
                return True
        return False

    def _cookies_out_of_date(self, cookie_str: str) -> bool:
        hub_psid = _cookie_value(cookie_str, "__Secure-1PSID")
        if not hub_psid or not os.path.exists(self.db_path):
            return True
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT cookie FROM accounts WHERE status!='deleted'").fetchall()
        conn.close()
        if len(rows) < self.account_count:
            return True
        return any(_cookie_value(row[0] or "", "__Secure-1PSID") != hub_psid for row in rows)

    def _write_cookies(self, cookie_str: str):
        if not cookie_str:
            return
        self.init_database(force_refresh=True, cookie_str=cookie_str)

    def _schedule_account_sync(self):
        """扩展可能晚于服务启动。连上后再写入 Cookie，并补全邮箱显示。"""
        if self._sync_thread and self._sync_thread.is_alive():
            return

        def _worker():
            deadline = time.time() + 90
            synced_cookie = ""
            while time.time() < deadline:
                try:
                    synced_cookie = self._extract_cookie_header()
                    break
                except Exception as exc:
                    print(f"⚠️ [Gemini] Cookie Hub 尚未就绪，稍后重试: {exc}", flush=True)
                    time.sleep(5)
            if synced_cookie and self._cookies_out_of_date(synced_cookie):
                print("🔄 [Gemini] 浏览器凭证已更新，正在写回账号池并重载服务...", flush=True)
                with self._lifecycle_lock:
                    self._write_cookies(synced_cookie)
                    self.proxy = _detect_local_proxy()
                    if self.is_running():
                        self._release_port()
                    self._launch_process()
            try:
                time.sleep(2)
                profiles = self.sync_account_profiles()
                named = []
                for item in profiles.values():
                    email = item.get("email") or ""
                    if email and email not in named and "同一登录" not in (item.get("note") or ""):
                        named.append(email)
                if not named:
                    time.sleep(4)
                    profiles = self.sync_account_profiles()
                    named = []
                    for item in profiles.values():
                        email = item.get("email") or ""
                        if email and email not in named and "同一登录" not in (item.get("note") or ""):
                            named.append(email)
                print(f"✅ [Gemini] 已识别 {len(named)} 个 Google 账号: {', '.join(named)}", flush=True)
            except Exception as exc:
                print(f"⚠️ [Gemini] 账号资料同步失败: {exc}", flush=True)

        self._sync_thread = threading.Thread(target=_worker, name="gemini-account-sync", daemon=True)
        self._sync_thread.start()

    def start(self, wait_timeout: int = 15) -> bool:
        """启动多账号统一代理服务，并在后台把浏览器账号同步到看板上。"""
        self.proxy = _detect_local_proxy()
        with self._lifecycle_lock:
            proxy_changed = self.is_running() and self._config_proxy() != self.proxy
            if proxy_changed:
                print(f"🔄 [Gemini] 代理已从 {self._config_proxy()} 切换到 {self.proxy}，正在重载号池...", flush=True)
                self._release_port()
            if not self.is_running():
                self.init_database(force_refresh=True)
                ok = self._launch_process(wait_timeout=wait_timeout)
            else:
                ok = True
        self._schedule_account_sync()
        return ok

    def stop(self):
        """停止多账号统一服务。"""
        with self._lifecycle_lock:
            self._release_port()

    def fetch_account_profile(
        self, authuser: int, cookie_override: Optional[str] = None
    ) -> Tuple[str, str]:
        """通过抓取 Google Gemini /u/{authuser}/app 页面，提取该槽位的 Google 真实用户昵称与 Gmail 邮箱。"""
        cookie = cookie_override
        if not cookie:
            try:
                conn = sqlite3.connect(self.db_path)
                row = conn.execute(
                    "SELECT cookie FROM accounts WHERE authuser = ?", (authuser,)
                ).fetchone()
                conn.close()
                if row and row[0]:
                    cookie = row[0]
            except Exception:
                pass

        if not cookie:
            return "", ""

        url = f"https://gemini.google.com/u/{authuser}/app"
        req = urllib.request.Request(
            url,
            headers={
                "Cookie": cookie,
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
            },
        )
        proxy_handler = (
            urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy})
            if self.proxy
            else urllib.request.ProxyHandler({})
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))

        html = ""
        last_error = None
        for attempt in range(3):
            try:
                with opener.open(req, timeout=15) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                time.sleep(1.2 * (attempt + 1))
        if last_error is not None or not html:
            print(f"⚠️ [Profile 获取] u/{authuser} 提取失败: {last_error}")
            return "", ""

        try:
            # 匹配 aria-label="Google Account: Alena Bray  &#10;(wargowskytom404@gmail.com)" 或中文 帐号：
            m = re.search(
                r'Google\s*[^:："]*[:：]\s*([^&"\(]+?)\s*(?:&#10;|\n)?\(([^)]+@gmail\.com)\)',
                html,
            )
            if m:
                name = m.group(1).strip()
                email = m.group(2).strip()
                return name, email

            # 兜底匹配 aria-label 中任何邮箱
            m2 = re.search(r'aria-label="[^"]*?\(([^)]+@gmail\.com)\)"', html)
            if m2:
                return "", m2.group(1).strip()

            # 兜底全页面正则提取 Gmail
            gm = re.findall(r"[\w\.-]+@gmail\.com", html)
            if gm:
                return "", gm[0]
        except Exception as e:
            print(f"⚠️ [Profile 获取] u/{authuser} 解析失败: {e}")

        return "", ""

    def sync_account_profiles(self) -> Dict[int, Dict[str, str]]:
        """批量同步并更新 SQLite 数据库中所有 Google 账号的真实昵称与邮箱。"""
        results = {}
        if not os.path.exists(self.db_path):
            self.init_database()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        rows = cur.execute("SELECT authuser FROM accounts ORDER BY authuser ASC").fetchall()
        conn.close()

        seen_emails = {}
        for (u,) in rows:
            name, email = self.fetch_account_profile(u)
            email = (email or "").strip()
            email_key = email.lower()
            if email and email_key in seen_emails:
                owner = seen_emails[email_key]
                new_label = f"{name} ({email})" if name else email
                note = f"authuser={u} | 与 u/{owner} 为同一登录"
                status = "disabled"
            elif email:
                seen_emails[email_key] = u
                new_label = f"{name} ({email})" if name else email
                note = f"authuser={u} | {email}"
                status = "enabled"
            else:
                new_label = ""
                note = ""
                status = ""

            if email:
                conn = sqlite3.connect(self.db_path)
                conn.execute(
                    "UPDATE accounts SET label = ?, note = ?, status = ? WHERE authuser = ?",
                    (new_label, note, status, u),
                )
                conn.commit()
                conn.close()

            results[u] = {"name": name, "email": email, "label": new_label, "note": note}

        return results

    def list_accounts(self) -> List[Dict[str, Any]]:
        """获取账号池内所有账号的状态、真实名称与 5 小时 / 周度额度统计。"""
        if not os.path.exists(self.db_path):
            self.init_database()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT id, label, authuser, status, last_used_at, fail_count, note 
               FROM accounts ORDER BY authuser ASC"""
        ).fetchall()

        now = int(time.time())
        five_hours_ago = now - 5 * 3600
        one_week_ago = now - 7 * 86400

        res = []
        for r in rows:
            acc_id = r[0]
            label_val = r[1]
            name = ""
            email = ""
            if "(" in label_val and label_val.endswith(")"):
                parts = label_val.rsplit("(", 1)
                name = parts[0].strip()
                email = parts[1].rstrip(")").strip()
            elif "@" in label_val:
                email = label_val.strip()
            note = r[6] or ""

            # 查询该账号 5 小时内与本周内的精确调用轨迹
            row_5h = cur.execute(
                """SELECT COUNT(1), MIN(ts), MAX(ts) 
                   FROM requests WHERE account_id = ? AND ts >= ?""",
                (acc_id, five_hours_ago),
            ).fetchone()
            count_5h = row_5h[0] if row_5h else 0
            earliest_5h = row_5h[1] if row_5h and row_5h[1] else None

            count_weekly = cur.execute(
                "SELECT COUNT(1) FROM requests WHERE account_id = ? AND ts >= ?",
                (acc_id, one_week_ago),
            ).fetchone()[0]

            # 计算 5 小时滚动重置倒计时
            reset_str = "滚动窗口充裕"
            if count_5h > 0 and earliest_5h:
                secs_left = max(0, (earliest_5h + 5 * 3600) - now)
                hours = secs_left // 3600
                mins = (secs_left % 3600) // 60
                if secs_left > 0:
                    reset_str = f"{hours:02d}h {mins:02d}m 后滚动释放"
                else:
                    reset_str = "首批额度已释放"

            limit_5h = 50
            rem_5h = max(0, limit_5h - count_5h)
            limit_weekly = 500
            rem_weekly = max(0, limit_weekly - count_weekly)

            # 额度健康度状态判定
            if count_5h >= 45:
                quota_status = "高负荷 🔴"
                status_color = "rose"
            elif count_5h >= 25:
                quota_status = "适中 🟡"
                status_color = "amber"
            else:
                quota_status = "充裕 🟢"
                status_color = "emerald"

            res.append(
                {
                    "id": acc_id,
                    "label": label_val,
                    "name": name,
                    "email": email,
                    "auth_user": r[2],
                    "url_prefix": f"https://gemini.google.com/u/{r[2]}",
                    "status": r[3],
                    "last_used_at": r[4],
                    "fail_count": r[5],
                    "note": note,
                    "quota_5h_used": count_5h,
                    "quota_5h_limit": limit_5h,
                    "quota_5h_remaining": rem_5h,
                    "quota_5h_reset_str": reset_str,
                    "quota_weekly_used": count_weekly,
                    "quota_weekly_limit": limit_weekly,
                    "quota_weekly_remaining": rem_weekly,
                    "quota_status": quota_status,
                    "quota_status_color": status_color,
                }
            )
        seen_emails = set()
        for item in res:
            email_key = (item.get("email") or "").strip().lower()
            duplicate = "同一登录" in (item.get("note") or "")
            if email_key and email_key not in seen_emails and not duplicate:
                seen_emails.add(email_key)
                item["visible"] = True
            else:
                item["visible"] = False
        conn.close()
        return res

    def ask(
        self,
        prompt: str,
        model: str = "gemini-3.5-flash-lite",
        reasoning_level: str = "off",
        timeout: int = 300,
    ) -> str:
        """
        通过统一池化通道提问。
        底层自动在已接入的 4 个账号之间执行 LRU 轮转调用。
        """
        details = self.ask_with_details(
            prompt=prompt, model=model, reasoning_level=reasoning_level, timeout=timeout
        )
        return details["reply"]

    def ask_with_details(
        self,
        prompt: str,
        model: str = "gemini-3.5-flash-lite",
        reasoning_level: str = "off",
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        通过统一池化通道提问，支持选择推理级别，并返回包含实际调用账号、耗时等详细元数据。
        """
        if not self.is_running():
            started = self.start()
            if not started:
                raise RuntimeError("无法启动本地 Gemini 多账号池代理服务！")
        self._pace.acquire()
        described = ""

        target_model = resolve_model_reasoning(model, reasoning_level)

        # 记录调用前最大的 requests 表 ID，用于匹配本次请求实际使用的账号
        prev_max_id = 0
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute("SELECT MAX(id) FROM requests").fetchone()
            if row and row[0]:
                prev_max_id = row[0]
            conn.close()
        except Exception:
            pass

        req_data = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/chat/completions",
            data=json.dumps(req_data).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        t0 = time.time()
        try:
            with _LOCAL_OPENER.open(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                reply = data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            described = describe_upstream_error(exc)
            raise RuntimeError(described) from exc
        finally:
            self._pace.release(described)
        took_ms = int((time.time() - t0) * 1000)

        # 从 requests 表查询调度详情 (稍作等待确保 Go 异步协程完成写入)
        account_id = None
        account_label = None
        authuser = None
        time.sleep(0.3)
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                """SELECT account_id, account_label, total_ms, status 
                   FROM requests WHERE id > ? ORDER BY id DESC LIMIT 1""",
                (prev_max_id,),
            ).fetchone()
            if row:
                account_id = row[0]
                account_label = row[1]
                if row[2]:
                    took_ms = row[2]
            if account_id:
                acct_row = conn.execute(
                    "SELECT authuser FROM accounts WHERE id = ?", (account_id,)
                ).fetchone()
                if acct_row:
                    authuser = acct_row[0]
            conn.close()
        except Exception:
            pass

        return {
            "reply": reply,
            "account_id": account_id,
            "account_label": account_label,
            "authuser": authuser,
            "took_ms": took_ms,
            "model": target_model,
            "base_model": model,
            "reasoning_level": reasoning_level,
        }

    def stream_chat(
        self,
        prompt: str,
        model: str = "gemini-3.8-flash",
        reasoning_level: str = "off",
        timeout: int = 180,
    ):
        """
        通过统一池化通道发起实时流式提问 (SSE)，逐行 yield SSE 事件。
        首字延迟 (TTFB) 仅需 1~2 秒。
        """
        if not self.is_running():
            self.start()
        try:
            self._pace.acquire()
        except Exception as e:
            yield self._stream_error_event(e)
            yield "data: [DONE]\n\n"
            return

        described = ""
        try:
            target_model = resolve_model_reasoning(model, reasoning_level)
            req_data = {
                "model": target_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            }
            req = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/v1/chat/completions",
                data=json.dumps(req_data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            resp = None
            try:
                resp = _LOCAL_OPENER.open(req, timeout=timeout)
            except Exception as first_err:
                print(f"⚠️ [Gemini Stream] 连接 Go 核心池异常: {first_err}，尝试自愈刷新凭证并重试...", flush=True)
                try:
                    self.reset_proxies()
                    self.refresh_pool_cookies()
                    resp = _LOCAL_OPENER.open(req, timeout=timeout)
                except Exception as retry_err:
                    described = describe_upstream_error(retry_err)
                    yield self._stream_error_event(RuntimeError(f"Gemini 调度流式失败: {described}"))
                    yield "data: [DONE]\n\n"
                    return

            buffer = b""
            stream_done = False
            while not stream_done:
                chunk = resp.read1(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    decoded_line = line.decode("utf-8", errors="replace")
                    yield decoded_line + "\n"
                    if decoded_line.strip() == "data: [DONE]":
                        stream_done = True
                        break
            if buffer and not stream_done:
                yield buffer.decode("utf-8", errors="replace") + "\n"
            try:
                resp.close()
            except Exception:
                pass
        except Exception as e:
            described = describe_upstream_error(e)
            yield self._stream_error_event(RuntimeError(described))
            yield "data: [DONE]\n\n"
        finally:
            self._pace.release(described)

    def _stream_error_event(self, exc: Exception) -> str:
        from login_status import failure_payload
        pace_status = self._pace.get_status()
        err_text = describe_upstream_error(exc)
        payload = failure_payload(err_text, "gemini")
        payload["type"] = "gemini_stream_error"
        if pace_status.get("retry_after"):
            payload["retry_after"] = pace_status["retry_after"]
        if pace_status.get("last_failure_reason"):
            payload["last_failure_reason"] = pace_status["last_failure_reason"]
        return f"data: {json.dumps({'error': payload}, ensure_ascii=False)}\n\n"

    def stream_chat_messages(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gemini-3.8-flash",
        reasoning_level: str = "off",
        timeout: int = 180,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = None,
    ):
        """
        向 Go 核心池发送 messages 列表的实时流式提问 (SSE)。
        tools / tool_choice 原样交给号池，由它转成网页能执行的 tool_call。
        """
        if not self.is_running():
            self.start()
        try:
            self._pace.acquire()
        except Exception as e:
            yield self._stream_error_event(e)
            yield "data: [DONE]\n\n"
            return

        described = ""
        try:
            target_model = resolve_model_reasoning(model, reasoning_level)
            req_data = {
                "model": target_model,
                "messages": messages,
                "stream": True,
            }
            if tools:
                req_data["tools"] = tools
            if tool_choice is not None:
                req_data["tool_choice"] = tool_choice
            req = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/v1/chat/completions",
                data=json.dumps(req_data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            resp = None
            try:
                resp = _LOCAL_OPENER.open(req, timeout=timeout)
            except Exception as first_err:
                print(f"⚠️ [Gemini Stream] 连接 Go 核心池异常: {first_err}，尝试自愈刷新凭证并重试...", flush=True)
                try:
                    self.reset_proxies()
                    self.refresh_pool_cookies()
                    resp = _LOCAL_OPENER.open(req, timeout=timeout)
                except Exception as retry_err:
                    described = describe_upstream_error(retry_err)
                    yield self._stream_error_event(RuntimeError(f"Gemini 调度流式失败: {described}"))
                    yield "data: [DONE]\n\n"
                    return

            buffer = b""
            stream_done = False
            while not stream_done:
                chunk = resp.read1(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    decoded_line = line.decode("utf-8", errors="replace")
                    yield decoded_line + "\n"
                    if decoded_line.strip() == "data: [DONE]":
                        stream_done = True
                        break
            if buffer and not stream_done:
                yield buffer.decode("utf-8", errors="replace") + "\n"
            try:
                resp.close()
            except Exception:
                pass
        except Exception as e:
            described = describe_upstream_error(e)
            yield self._stream_error_event(RuntimeError(described))
            yield "data: [DONE]\n\n"
        finally:
            self._pace.release(described)

    def pace_status(self) -> Dict[str, Any]:
        """获取当前 Gemini 并发与频率控制状态。"""
        return self._pace.get_status()

    def reset_pace(self) -> None:
        """强制解除 Gemini 频率与并发保护锁。"""
        self._pace.reset()

    def check_account(self, account_id: int) -> Dict[str, Any]:
        """调用管理接口检测单个账号的会话凭证健康状态。"""
        url = f"http://127.0.0.1:{self.port}/admin/api/cookies/{account_id}/check"
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer admin_gemini_pool",
            },
        )
        with _LOCAL_OPENER.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def rotate_account(self, account_id: int) -> Dict[str, Any]:
        """强制触发单个账号的会话令牌主动保活轮换。"""
        url = f"http://127.0.0.1:{self.port}/admin/api/cookies/{account_id}/rotate"
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer admin_gemini_pool",
            },
        )
        with _LOCAL_OPENER.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def reset_proxies(self) -> bool:
        """重置所有代理的熔断与失败计数器，确保不会因偶发超时被锁定。"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE proxies SET fail_count=0, last_error=''")
            conn.commit()
            conn.close()
        except Exception:
            pass

        if self.is_running():
            try:
                url = f"http://127.0.0.1:{self.port}/admin/api/proxies/1/reset"
                req = urllib.request.Request(
                    url,
                    data=b"{}",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer admin_gemini_pool",
                    },
                )
                with _LOCAL_OPENER.open(req, timeout=5) as resp:
                    pass
            except Exception:
                pass
        return True

    def refresh_pool_cookies(self, reload: bool = False) -> str:
        """从前台 Cookie Hub 重新拉取最新凭证并更新多账号数据库。"""
        self.reset_proxies()
        self.proxy = _detect_local_proxy()
        cookie_str = self._extract_cookie_header()
        self._write_cookies(cookie_str)
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE proxies SET fail_count=0, last_error=''")
        conn.commit()
        conn.close()
        if reload:
            with self._lifecycle_lock:
                if self.is_running():
                    self._release_port()
                self._launch_process()
            self.sync_account_profiles()
        return cookie_str

    def list_recent_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近请求调度记录。"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT id, ts, model, account_id, account_label, status, total_ms, error 
               FROM requests ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()
        res = []
        for r in rows:
            res.append(
                {
                    "id": r[0],
                    "timestamp": r[1],
                    "model": r[2],
                    "account_id": r[3],
                    "account_label": r[4],
                    "status": r[5],
                    "total_ms": r[6],
                    "error": r[7],
                }
            )
        return res


if __name__ == "__main__":
    print("=== 初始化并测试 Google 4 账号统一池服务 ===")
    pool = MultiAccountGeminiPool(port=18083, account_count=4)
    print("1. 同步账号池状态...")
    pool.init_database(force_refresh=True)
    
    accounts = pool.list_accounts()
    print(f"已接入 {len(accounts)} 个 Google 账号槽位:")
    for a in accounts:
        print(f"  - [{a['auth_user']}] {a['label']} -> {a['url_prefix']} (状态: {a['status']})")
        
    print("\n2. 启动/校验多账号后台服务...")
    if pool.start():
        print(f"多账号统一服务已在 http://127.0.0.1:{pool.port} 运行！")
        print("\n3. 模拟连续问答测试多账号负载均衡...")
        for i in range(2):
            q = f"请用一句话回答：当前是第 {i+1} 次多账号轮询测试，状态正常吗？"
            print(f"\n提问 {i+1}: {q}")
            t0 = time.time()
            reply = pool.ask(q)
            print(f"回复 ({time.time()-t0:.2f}s):\n{reply}")
            
        print("\n4. 查看最新轮转状态:")
        for a in pool.list_accounts():
            print(f"  - [{a['auth_user']}] 上次调用时间戳: {a['last_used_at']}, 失败计数: {a['fail_count']}")
    else:
        print("服务启动失败，请检查端口与代理连接！")
