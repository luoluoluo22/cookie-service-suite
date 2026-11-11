# -*- coding: utf-8 -*-
"""
ChatGPT Service Suite: 浏览器原生桥接与网页逆向号池双引擎
=========================================================
1. ChatGPTReverseEngine:
   基于 chatgpt2api 深度逆向核心（模拟 Chrome TLS 指纹、Sentinel PoW 算力证明生成、
   Direct /backend-api/conversation 对话流、DALL-E 3 / gpt-image-2 图片生成与号池管理），
   由本地独立进程调度（默认端口 18084），支持通过 AccessToken 鉴权直连 OpenAI。

2. ChatGPTBridgeClient:
   通过本地 Cookie Hub 桥接服务与浏览器已登录 ChatGPT Web 标签页进行同源免封禁通信。

3. UnifiedChatGPTService:
   统一门面类，优先使用高速逆向引擎（支持多模型、SSE 流式、生图），在无账号或逆向服务停用时
   自动降级至浏览器扩展同源桥接。
"""

import os
import secrets
import sys
import time
import json
import shutil
import subprocess
import urllib.request
import urllib.parse
from typing import Generator, Dict, Any, Union, List, Optional

# 强制本地 127.0.0.1 回环通信不走外部代理
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"
_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

DEFAULT_BRIDGE_URL = "http://127.0.0.1:18888"
DEFAULT_REVERSE_PORT = 18084
def _load_reverse_auth_key() -> str:
    """Load a private, per-user local key; never commit or log its value."""
    override = os.getenv("CHATGPT2API_AUTH_KEY", "").strip()
    if override:
        return override
    local_data = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(local_data, "CookieServiceSuite", "reverse-auth-key.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.isfile(path):
        key = secrets.token_urlsafe(48)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(key + "\n")
    with open(path, encoding="utf-8") as f:
        key = f.read().strip()
    if len(key) < 32:
        raise RuntimeError("local reverse engine key file is invalid")
    return key


DEFAULT_REVERSE_AUTH_KEY = _load_reverse_auth_key()


class ChatGPTBridgeClient:
    """ChatGPT 浏览器 In-Page DOM 扩展桥接客户端"""

    def __init__(self, base_url: str = DEFAULT_BRIDGE_URL, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.opener = _LOCAL_OPENER

    def check_health(self) -> dict:
        """检查本地桥接服务是否正常运行且扩展已连接"""
        url = f"{self.base_url}/status"
        req = urllib.request.Request(url)
        with self.opener.open(req, timeout=1.5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_session(self) -> dict:
        """获取浏览器中 ChatGPT 当前登录会话（包括 AccessToken、用户邮箱、Plus 会员状态）"""
        url = f"{self.base_url}/chatgpt/session"
        req = urllib.request.Request(url)
        with self.opener.open(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_models(self) -> dict:
        """获取当前账号可用模型目录"""
        url = f"{self.base_url}/chatgpt/models"
        req = urllib.request.Request(url)
        with self.opener.open(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def ask(self, prompt: str, model: str = "chatgpt-web", stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """发送单句提示词并等待 ChatGPT 回复（支持 stream=True 流式逐字返回）"""
        messages = [{"role": "user", "content": prompt}]
        if stream:
            return self.stream_chat(messages, model=model)
        else:
            resp = self.chat(messages, model=model, stream=False)
            return resp["choices"][0]["message"]["content"]

    def chat(self, messages: List[Dict[str, str]], model: str = "chatgpt-web", stream: bool = False) -> Union[dict, Generator[dict, None, None]]:
        """标准 OpenAI 兼容 /v1/chat/completions 调用"""
        if stream:
            return self._stream_generator(messages, model)

        url = f"{self.base_url}/v1/chat/completions"
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "stream": False
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        with self.opener.open(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def stream_chat(self, messages: List[Dict[str, str]], model: str = "chatgpt-web") -> Generator[str, None, None]:
        """流式生成器：仅逐字产出 delta content 文本"""
        for chunk in self._stream_generator(messages, model):
            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if delta:
                yield delta

    def _stream_generator(self, messages: List[Dict[str, str]], model: str = "chatgpt-web") -> Generator[dict, None, None]:
        """底层 SSE 流式读取与 OpenAI chunk 字典产出"""
        url = f"{self.base_url}/v1/chat/completions"
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "stream": True
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        with self.opener.open(req, timeout=self.timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    yield chunk
                except Exception:
                    continue


class ChatGPTReverseEngine:
    """ChatGPT 独立网页逆向引擎管理器（包装 chatgpt2api 后端）"""

    def __init__(
        self,
        port: int = DEFAULT_REVERSE_PORT,
        auth_key: str = DEFAULT_REVERSE_AUTH_KEY,
        proxy: str = "http://127.0.0.1:7890",
    ):
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self.auth_key = auth_key
        self.proxy = proxy
        self.base_dir = os.path.join(
            os.path.dirname(__file__), "candidate_repos", "basketikun-chatgpt2api"
        )
        self.proc: Optional[subprocess.Popen] = None
        self.opener = _LOCAL_OPENER

    def _auth_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.auth_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def is_running(self) -> bool:
        """检查逆向后台服务是否健康运行"""
        try:
            req = urllib.request.Request(f"{self.base_url}/version")
            with self.opener.open(req, timeout=0.8) as resp:
                return resp.status == 200
        except Exception:
            return False

    def start(self, wait_timeout: int = 15) -> bool:
        """启动独立逆向后台服务进程"""
        if self.is_running():
            return True

        env = os.environ.copy()
        if self.proxy:
            env["HTTP_PROXY"] = self.proxy
            env["HTTPS_PROXY"] = self.proxy
            env["ALL_PROXY"] = self.proxy
        env["NO_PROXY"] = "127.0.0.1,localhost,::1"
        # The child requires this setting at import time; the manager uses
        # precisely the same key for authenticated loopback requests.
        env["CHATGPT2API_AUTH_KEY"] = self.auth_key

        venv_python = os.path.join(self.base_dir, ".venv", "Scripts", "python.exe")
        if os.path.isfile(venv_python):
            cmd = [
                venv_python,
                "-m",
                "uvicorn",
                "api.app:create_app",
                "--factory",
                "--port",
                str(self.port),
                "--host",
                "127.0.0.1",
                "--log-level",
                "warning",
            ]
        else:
            uv_bin = shutil.which("uv") or r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Links\uv.exe"
            if not os.path.exists(uv_bin) and not shutil.which("uv"):
                raise RuntimeError(f"未找到 uv 可执行文件，无法启动逆向服务 (查找路径: {uv_bin})")
            cmd = [
                uv_bin,
                "run",
                "python",
                "-m",
                "uvicorn",
                "api.app:create_app",
                "--factory",
                "--port",
                str(self.port),
                "--host",
                "127.0.0.1",
                "--log-level",
                "warning",
            ]

        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NO_WINDOW

        self.proc = subprocess.Popen(
            cmd,
            cwd=self.base_dir,
            env=env,
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 轮询等待端口就绪
        deadline = time.time() + wait_timeout
        while time.time() < deadline:
            if self.is_running():
                self.apply_proxy()
                return True
            time.sleep(0.5)

        raise TimeoutError(f"ChatGPT 逆向后台服务启动超时（等待 {wait_timeout} 秒后端口 {self.port} 未响应）")

    def stop(self) -> None:
        """停止逆向服务进程"""
        if self.proc:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    self.proc.terminate()
                    self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

    def get_health(self) -> dict:
        """获取逆向服务号池监控状态（健康度、账号统计等）"""
        url = f"{self.base_url}/health?format=json"
        req = urllib.request.Request(url)
        with self.opener.open(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_models(self) -> dict:
        """获取逆向暴露的可用模型列表"""
        url = f"{self.base_url}/v1/models"
        req = urllib.request.Request(url, headers=self._auth_headers())
        with self.opener.open(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def list_accounts(self) -> list:
        """获取当前号池中的全部账号"""
        url = f"{self.base_url}/api/accounts"
        req = urllib.request.Request(url, headers=self._auth_headers())
        with self.opener.open(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("items", [])

    def import_tokens(self, tokens: List[str]) -> dict:
        """向号池导入一个或多个 Access Token 并自动刷新验证"""
        clean_tokens = [t.strip() for t in tokens if t and t.strip()]
        if not clean_tokens:
            raise ValueError("至少需要提供一个有效的 Access Token")
        url = f"{self.base_url}/api/accounts"
        payload = json.dumps({"tokens": clean_tokens}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers())
        with self.opener.open(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def delete_account(self, token: str) -> dict:
        """从号池中移除指定账号"""
        url = f"{self.base_url}/api/accounts"
        payload = json.dumps({"tokens": [token]}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers(), method="DELETE")
        with self.opener.open(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def apply_proxy(self) -> bool:
        """把本地代理写进逆向引擎自己的出口配置。仅设置环境变量不会改变它的直连模式。"""
        if not self.proxy or not self.is_running():
            return False
        url = f"{self.base_url}/api/proxy/runtime"
        payload = json.dumps({
            "enabled": True,
            "egress_mode": "single_proxy",
            "proxy_url": self.proxy,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers())
        try:
            with self.opener.open(req, timeout=8) as resp:
                return resp.status == 200
        except Exception:
            return False

    def update_account(self, token: str, updates: Dict[str, Any]) -> dict:
        """按浏览器读到的真实方案修正号池账号，例如把过期的 Plus 改成免费。"""
        url = f"{self.base_url}/api/accounts/update"
        payload = json.dumps({"access_token": token, **updates}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers())
        with self.opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "auto",
        stream: bool = False,
        thinking_effort: str = "",
        timeout: int = 180,
    ) -> Union[dict, Generator[dict, None, None]]:
        """调用逆向 /v1/chat/completions 接口对话"""
        if stream:
            return self._stream_generator(messages, model, thinking_effort, timeout)

        url = f"{self.base_url}/v1/chat/completions"
        payload_dict = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if thinking_effort:
            payload_dict["thinking_effort"] = thinking_effort

        payload = json.dumps(payload_dict).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers())
        with self.opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _stream_generator(
        self,
        messages: List[Dict[str, Any]],
        model: str = "auto",
        thinking_effort: str = "",
        timeout: int = 180,
    ) -> Generator[dict, None, None]:
        url = f"{self.base_url}/v1/chat/completions"
        payload_dict = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if thinking_effort:
            payload_dict["thinking_effort"] = thinking_effort

        payload = json.dumps(payload_dict).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers())
        with self.opener.open(req, timeout=timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    yield chunk
                except Exception:
                    continue

    def generate_image(
        self,
        prompt: str,
        model: str = "gpt-image-2",
        n: int = 1,
        response_format: str = "b64_json",
        timeout: int = 240,
    ) -> dict:
        """调用逆向 /v1/images/generations 生成图片"""
        url = f"{self.base_url}/v1/images/generations"
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "n": n,
            "response_format": response_format,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers())
        with self.opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


class UnifiedChatGPTService:
    """ChatGPT 统一门面服务，优先调度无头逆向引擎，必要时自动降级至浏览器同源桥接"""

    def __init__(
        self,
        reverse_port: int = DEFAULT_REVERSE_PORT,
        bridge_url: str = DEFAULT_BRIDGE_URL,
        proxy: str = "http://127.0.0.1:7890",
    ):
        self.reverse = ChatGPTReverseEngine(port=reverse_port, proxy=proxy)
        self.bridge = ChatGPTBridgeClient(base_url=bridge_url)
        self.live_plan = ""
        self.live_plan_label = ""
        self._resyncing = False

    def is_reverse_available(self) -> bool:
        """逆向引擎在线，且号池里至少有一个不是异常/禁用的账号。"""
        if not self.reverse.is_running():
            return False
        try:
            health = self.reverse.get_health()
            accounts = health.get("accounts", {})
            return int(accounts.get("active") or 0) > 0
        except Exception:
            return False

    @staticmethod
    def plan_from_session(session: dict) -> str:
        account = session.get("account") if isinstance(session, dict) else {}
        raw = ""
        if isinstance(account, dict):
            raw = str(account.get("planType") or account.get("plan_type") or "")
        raw = raw or str((session or {}).get("accountPlan") or "")
        key = raw.strip().lower().replace("-", "_").replace(" ", "_")
        return {
            "free": "free",
            "plus": "Plus",
            "pro": "Pro",
            "prolite": "ProLite",
            "pro_lite": "ProLite",
            "team": "Team",
        }.get(key, raw or "free")

    @staticmethod
    def plan_label(plan: str) -> str:
        return {"free": "免费", "Plus": "Plus", "Pro": "Pro", "ProLite": "ProLite", "Team": "Team"}.get(plan, plan or "免费")

    def get_status(self) -> dict:
        """获取综合健康状态"""
        reverse_running = self.reverse.is_running()
        reverse_health = {}
        if reverse_running:
            try:
                reverse_health = self.reverse.get_health()
            except Exception:
                pass

        bridge_online = False
        bridge_ext = False
        try:
            b_health = self.bridge.check_health()
            bridge_online = True
            bridge_ext = b_health.get("extensionConnected", False)
        except Exception:
            pass

        return {
            "mode": "reverse_engine" if self.is_reverse_available() else ("browser_bridge" if bridge_ext else "unready"),
            "reverse_engine": {
                "running": reverse_running,
                "port": self.reverse.port,
                "health": reverse_health,
            },
            "browser_bridge": {
                "server_online": bridge_online,
                "extension_connected": bridge_ext,
            },
            "browser_account": self.public_account(),
        }

    def check_health(self) -> dict:
        """兼容原有 bridge.check_health() 接口"""
        status = self.get_status()
        return {
            "status": "ok" if (self.is_reverse_available() or status["browser_bridge"]["extension_connected"]) else "offline",
            "extensionConnected": status["browser_bridge"]["extension_connected"],
            "reverseEngineRunning": status["reverse_engine"]["running"],
            "mode": status["mode"],
        }

    def _open_chatgpt_tab(self) -> None:
        req = urllib.request.Request(f"{self.bridge.base_url}/chatgpt/open")
        with self.bridge.opener.open(req, timeout=20) as resp:
            json.loads(resp.read().decode("utf-8"))

    def read_live_session(self, open_if_missing: bool = True) -> dict:
        """直接问扩展要浏览器里的真实会话。没有 chatgpt.com 标签时才在后台打开一个。"""
        data = {}
        opened = False
        for attempt in range(6):
            try:
                data = self.bridge.get_session()
            except Exception as exc:
                data = {"success": False, "error": str(exc)}
            session = data.get("session") if isinstance(data, dict) else None
            if isinstance(session, dict) and session.get("accessToken"):
                return data
            err = str((data or {}).get("error") or "")
            needs_tab = ("标签" in err) or ("未找到" in err) or ("chatgpt.com" in err)
            if open_if_missing and needs_tab and not opened:
                opened = True
                try:
                    self._open_chatgpt_tab()
                except Exception as exc:
                    data = {"success": False, "error": str(exc)}
                    break
            elif not needs_tab:
                break
            time.sleep(1.2)
        return data if isinstance(data, dict) else {"success": False, "error": "无法读取浏览器会话"}

    def public_account(self) -> dict:
        if self.live_plan:
            return {"plan": self.live_plan, "plan_label": self.live_plan_label}
        if not self.reverse.is_running():
            return {}
        try:
            accounts = self.reverse.list_accounts()
        except Exception:
            return {}
        usable = [item for item in accounts if item.get("status") not in ("异常", "禁用")]
        chosen = usable[0] if usable else (accounts[0] if accounts else None)
        if not chosen:
            return {}
        plan = self.plan_from_session({"accountPlan": chosen.get("type") or "free"})
        return {"plan": plan, "plan_label": self.plan_label(plan)}

    def get_session(self) -> dict:
        """读取浏览器扩展里的真实登录态。不返回令牌，也不再用过期的 Plus 号池冒充当前账号。"""
        data = self.read_live_session(open_if_missing=True)
        session = data.get("session") if isinstance(data, dict) else None
        if not isinstance(session, dict) or not session.get("accessToken"):
            err = str((data or {}).get("error") or "浏览器里没有可用的 ChatGPT 登录态")
            raise RuntimeError(
                f"{err}。请在已加载 Cookie Hub 的浏览器打开并登录 https://chatgpt.com/ ，免费账号也可以。"
            )
        plan = self.plan_from_session(session)
        user = session.get("user") if isinstance(session.get("user"), dict) else {}
        self.live_plan = plan
        self.live_plan_label = self.plan_label(plan)
        return {
            "success": True,
            "logged_in": True,
            "source": "browser",
            "plan": plan,
            "plan_label": self.live_plan_label,
            "email": user.get("email") or "",
            "name": user.get("name") or "",
        }

    def get_models(self) -> dict:
        """获取模型列表，优先从逆向引擎拉取"""
        if self.reverse.is_running():
            try:
                return self.reverse.get_models()
            except Exception:
                pass
        return self.bridge.get_models()

    def sync_token_from_browser(self) -> dict:
        """从扩展读取真实会话，按免费/Plus 等方案写入号池，并清掉已经失效的旧令牌。"""
        data = self.read_live_session(open_if_missing=True)
        session = data.get("session") if isinstance(data, dict) else None
        token = session.get("accessToken") if isinstance(session, dict) else ""
        if not token:
            err = str((data or {}).get("error") or "浏览器里没有可用的 ChatGPT 登录态")
            raise RuntimeError(
                f"{err}。请在已加载 Cookie Hub 的浏览器打开并登录 https://chatgpt.com/ ，免费账号也可以。"
            )

        plan = self.plan_from_session(session)
        user = session.get("user") if isinstance(session.get("user"), dict) else {}
        self.live_plan = plan
        self.live_plan_label = self.plan_label(plan)
        if not self.reverse.is_running():
            self.reverse.start()

        before = set()
        try:
            before = {
                str(account.get("access_token") or "")
                for account in self.reverse.list_accounts()
                if account.get("access_token")
            }
        except Exception:
            before = set()

        self.reverse.import_tokens([token])
        after = []
        try:
            after = self.reverse.list_accounts()
        except Exception:
            after = []

        kept = []
        for account in after:
            current = str(account.get("access_token") or "")
            if current and (current == token or current not in before):
                kept.append(current)
        if not kept:
            for account in after:
                current = str(account.get("access_token") or "")
                if current and account.get("email") and account.get("email") == user.get("email"):
                    kept.append(current)

        removed = 0
        for account in after:
            current = str(account.get("access_token") or "")
            if current and current not in kept:
                try:
                    self.reverse.delete_account(current)
                    removed += 1
                except Exception:
                    pass
        for current in kept:
            try:
                self.reverse.update_account(current, {"type": plan, "status": "正常"})
            except Exception:
                pass

        return {
            "success": True,
            "source": "browser",
            "email": user.get("email") or "",
            "name": user.get("name") or "",
            "plan": plan,
            "plan_label": self.live_plan_label,
            "replaced_stale_accounts": removed,
            "message": f"已按浏览器真实登录态同步，当前是{self.live_plan_label}账号。",
        }

    def ensure_live_account(self) -> dict:
        """号池里没有可用账号时，用扩展里的当前登录态替换掉失效的旧 Plus 令牌。"""
        if not self.reverse.is_running():
            self.reverse.start()
        else:
            self.reverse.apply_proxy()
        usable = []
        try:
            usable = [
                account for account in self.reverse.list_accounts()
                if account.get("status") not in ("异常", "禁用")
            ]
        except Exception:
            usable = []
        if usable:
            return {"synced": False, "plan": usable[0].get("type") or self.live_plan or "free"}
        synced = self.sync_token_from_browser()
        synced["synced"] = True
        return synced

    def ask(self, prompt: str, model: str = "auto", stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """统一提问接口：
        - 若模型显式包含 moni 或为 chatgpt-web / chatgpt-web-moni，强制走浏览器 DOM 模拟输入
        - 其他模型 (gpt-6, gpt-5-6, auto 等) 走 Web API 协议逆向直连，绝不静默降级到浏览器输入！
        """
        model_lower = (model or "").lower().strip()
        if "moni" in model_lower or model_lower in ("chatgpt-web", "chatgpt-web-moni"):
            return self.bridge.ask(prompt, model="chatgpt-web", stream=stream)

        if stream:
            def _gen():
                for chunk in self.chat([{"role": "user", "content": prompt}], model=model, stream=True):
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta
            return _gen()
        res = self.chat([{"role": "user", "content": prompt}], model=model, stream=False)
        return res["choices"][0]["message"]["content"]

    def chat(self, messages: List[Dict[str, Any]], model: str = "auto", stream: bool = False, thinking_effort: str = "") -> Union[dict, Generator[dict, None, None]]:
        """OpenAI 兼容对话调用接口：
        - 若模型显式包含 moni 或为 chatgpt-web / chatgpt-web-moni，强制走浏览器 DOM 模拟输入
        - 其他模型 (gpt-6, gpt-5-6, auto 等) 走 Web API 协议逆向直连，绝不静默降级到浏览器输入！
        """
        model_lower = (model or "").lower().strip()
        if "moni" in model_lower or model_lower in ("chatgpt-web", "chatgpt-web-moni"):
            return self.bridge.chat(messages, model="chatgpt-web", stream=stream)

        self.ensure_live_account()
        try:
            return self.reverse.chat(messages, model=model, stream=stream, thinking_effort=thinking_effort)
        except Exception as first_err:
            err_msg = str(first_err).lower()
            retryable = any(k in err_msg for k in ("429", "401", "403", "502", "quota", "token", "unauthorized", "anon", "invalid"))
            if retryable and not self._resyncing:
                self._resyncing = True
                try:
                    self.sync_token_from_browser()
                    return self.reverse.chat(messages, model=model, stream=stream, thinking_effort=thinking_effort)
                finally:
                    self._resyncing = False
            raise first_err

    def generate_image(
        self,
        prompt: str,
        model: str = "gpt-image-2",
        n: int = 1,
        response_format: str = "b64_json",
        timeout: int = 240,
    ) -> dict:
        """文生图接口 (支持自动从浏览器同步 Token 并自愈重试)"""
        if not self.reverse.is_running():
            self.reverse.start()
        try:
            return self.reverse.generate_image(
                prompt, model=model, n=n, response_format=response_format, timeout=timeout
            )
        except Exception as first_err:
            err_msg = str(first_err).lower()
            if any(k in err_msg for k in ("429", "401", "quota", "token", "unauthorized", "too many requests")):
                try:
                    sync_res = self.sync_token_from_browser()
                    if sync_res.get("success"):
                        return self.reverse.generate_image(
                            prompt, model=model, n=n, response_format=response_format, timeout=timeout
                        )
                except Exception:
                    pass
            raise first_err


# 单例导出
chatgpt_service = UnifiedChatGPTService()
chatgpt_reverse_engine = chatgpt_service.reverse
ChatGPTService = UnifiedChatGPTService
