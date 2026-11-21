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

import base64
import os
import secrets
import sys
import threading
import time
import json
import shutil
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator, Dict, Any, Union, List, Optional

from web_api_switches import is_service_enabled, require_service_enabled

# 强制本地 127.0.0.1 回环通信不走外部代理
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"
_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

DEFAULT_BRIDGE_URL = "http://127.0.0.1:18888"
DEFAULT_REVERSE_PORT = 18084

def _proxy_is_open(proxy_url: str) -> bool:
    raw = (proxy_url or "").strip()
    if not raw:
        return False
    if "://" not in raw:
        raw = "http://" + raw
    parsed = urllib.parse.urlsplit(raw)
    if not parsed.hostname or not parsed.port:
        return False
    try:
        import socket
        with socket.create_connection((parsed.hostname, parsed.port), timeout=0.25):
            return True
    except Exception:
        return False


def _system_http_proxy(fallback: str = "") -> str:
    """Prefer the reachable Windows system proxy to a stale hardcoded port."""
    if sys.platform != "win32":
        return fallback
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            enabled = int(winreg.QueryValueEx(key, "ProxyEnable")[0])
            raw = str(winreg.QueryValueEx(key, "ProxyServer")[0]).strip()
        if not enabled or not raw:
            return fallback
        parts = [part.strip() for part in raw.split(";") if part.strip()]
        choice = next((part.split("=", 1)[1] for part in parts if part.lower().startswith("https=")), None)
        if choice is None:
            choice = next((part.split("=", 1)[1] for part in parts if part.lower().startswith("http=")), None)
        choice = choice or parts[0]
        if "=" in choice:
            return fallback
        if not choice.startswith(("http://", "https://")):
            choice = "http://" + choice
        parsed = urllib.parse.urlsplit(choice)
        if parsed.hostname not in ("127.0.0.1", "localhost") or not parsed.port:
            return fallback
        if _proxy_is_open(choice):
            return choice
        return fallback
    except Exception:
        return fallback


def _detect_local_proxy(fallback: str = "") -> str:
    """Detect the currently open local proxy (Windows system proxy -> env -> common ports)."""
    candidates: List[str] = []
    sys_proxy = _system_http_proxy("")
    if sys_proxy:
        candidates.append(sys_proxy)
    for key in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy"):
        val = (os.environ.get(key) or "").strip()
        if val:
            candidates.append(val if "://" in val else "http://" + val)
    for port in (7900, 7890, 7897, 10808, 10809, 1080, 7891):
        candidates.append(f"http://127.0.0.1:{port}")
    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if _proxy_is_open(candidate):
            return candidate
    return fallback


def _find_pids_on_port(port: int) -> List[int]:
    """Find TCP listening PIDs bound to the given local port (excluding current PID)."""
    if sys.platform != "win32":
        return []
    try:
        out = subprocess.check_output(
            ["netstat", "-ano", "-p", "TCP"],
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        return []
    pids: List[int] = []
    suffix = f":{port}"
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[3].upper() == "LISTENING":
            if parts[1].endswith(suffix):
                try:
                    pid = int(parts[4])
                    if pid > 0 and pid != os.getpid() and pid not in pids:
                        pids.append(pid)
                except ValueError:
                    pass
    return pids


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

    def get_session(self, refresh: bool = False, auto_open: bool = False) -> dict:
        """获取浏览器中 ChatGPT 当前登录会话（包括 AccessToken、用户邮箱、Plus 会员状态）"""
        params = []
        if refresh:
            params.append("refresh=true")
        if auto_open:
            params.append("auto_open=true")
        qs = ("?" + "&".join(params)) if params else ""
        url = f"{self.base_url}/chatgpt/session{qs}"
        req = urllib.request.Request(url)
        timeout_sec = 25 if (refresh or auto_open) else 10
        with self.opener.open(req, timeout=timeout_sec) as resp:
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
        proxy: Optional[str] = None,
    ):
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self.auth_key = auth_key
        self._explicit_proxy = proxy
        self.proxy = proxy or _detect_local_proxy("http://127.0.0.1:7890")
        self._last_applied_proxy = ""
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

    def start(self, wait_timeout: int = 45) -> bool:
        """启动独立逆向后台服务进程"""
        require_service_enabled("chatgpt")
        if self.is_running():
            self.apply_proxy()
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
        """停止逆向服务进程（包括外部遗留占用端口的旧进程）"""
        if self.proc:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
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

        if sys.platform == "win32":
            for pid in _find_pids_on_port(self.port):
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                except Exception:
                    pass
        self._last_applied_proxy = ""
        deadline = time.time() + 3.0
        while time.time() < deadline and self.is_running():
            time.sleep(0.2)

    def restart(self, wait_timeout: int = 45) -> bool:
        """重启逆向服务进程，确保最新代理环境变量与配置生效。"""
        require_service_enabled("chatgpt")
        if not self._explicit_proxy:
            detected = _detect_local_proxy(self.proxy)
            if detected:
                self.proxy = detected
        self.stop()
        return self.start(wait_timeout=wait_timeout)

    @staticmethod
    def _format_http_error(exc: urllib.error.HTTPError) -> str:
        body = ""
        try:
            raw = exc.read()
            if raw:
                body = raw.decode("utf-8", errors="replace").strip()
        except Exception:
            pass
        if body:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    err = parsed.get("error")
                    if isinstance(err, dict) and err.get("message"):
                        body = str(err["message"])
                    elif parsed.get("detail"):
                        detail = parsed["detail"]
                        if isinstance(detail, dict) and detail.get("error"):
                            body = str(detail["error"])
                        else:
                            body = str(detail)
            except Exception:
                pass
        return f"HTTP {exc.code}: {body}" if body else f"HTTP {exc.code}: {exc.reason}"

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

    def import_account_items(self, accounts: List[Dict[str, Any]]) -> dict:
        """向号池导入完整账号对象（含 access_token / refresh_token / type 等）"""
        clean_items = [item for item in (accounts or []) if isinstance(item, dict) and (item.get("access_token") or item.get("accessToken"))]
        if not clean_items:
            raise ValueError("至少需要提供一个包含 access_token 的账号对象")
        url = f"{self.base_url}/api/accounts"
        payload = json.dumps({"accounts": clean_items}).encode("utf-8")
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

    def apply_proxy(self, force: bool = False) -> bool:
        """同步最新可用代理到逆向引擎的 legacy proxy 与 proxy_runtime，避免沿用旧端口。"""
        if not self._explicit_proxy:
            detected = _detect_local_proxy(self.proxy)
            if detected:
                self.proxy = detected
        if not self.proxy or not self.is_running():
            return False
        if not force and self._last_applied_proxy == self.proxy:
            return True

        # 同时更新 legacy `proxy` 与 `proxy_runtime.proxy_url`，因为部分内部请求未传 upstream=True
        settings_url = f"{self.base_url}/api/settings"
        payload = json.dumps({
            "proxy": self.proxy,
            "proxy_runtime": {
                "enabled": True,
                "egress_mode": "single_proxy",
                "proxy_url": self.proxy,
            },
        }).encode("utf-8")
        req = urllib.request.Request(settings_url, data=payload, headers=self._auth_headers())
        try:
            with self.opener.open(req, timeout=8) as resp:
                if resp.status == 200:
                    self._last_applied_proxy = self.proxy
                    return True
        except Exception:
            pass

        # 兜底仅更新 /api/proxy/runtime
        runtime_url = f"{self.base_url}/api/proxy/runtime"
        runtime_payload = json.dumps({
            "enabled": True,
            "egress_mode": "single_proxy",
            "proxy_url": self.proxy,
        }).encode("utf-8")
        req = urllib.request.Request(runtime_url, data=runtime_payload, headers=self._auth_headers())
        try:
            with self.opener.open(req, timeout=8) as resp:
                if resp.status == 200:
                    self._last_applied_proxy = self.proxy
                    return True
                return False
        except Exception:
            return False

    def update_account(self, token: str, updates: Dict[str, Any]) -> dict:
        """按浏览器读到的真实方案修正号池账号，例如把过期的 Plus 改成免费。"""
        url = f"{self.base_url}/api/accounts/update"
        payload = json.dumps({"access_token": token, **updates}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers())
        with self.opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def refresh_accounts(self, access_tokens: Optional[List[str]] = None) -> dict:
        """触发逆向号池账号状态与额度刷新（异步任务，返回 progress_id）。"""
        url = f"{self.base_url}/api/accounts/refresh"
        tokens = [str(t).strip() for t in (access_tokens or []) if str(t or "").strip()]
        payload = json.dumps({"access_tokens": tokens}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers())
        with self.opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _extract_http_error(exc: urllib.error.HTTPError) -> RuntimeError:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            body = ""
        detail = body or str(exc)
        if body:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    err = parsed.get("error")
                    if isinstance(err, dict) and err.get("message"):
                        detail = str(err["message"])
                    elif isinstance(parsed.get("detail"), dict) and parsed["detail"].get("error"):
                        detail = str(parsed["detail"]["error"])
                    elif parsed.get("detail"):
                        detail = str(parsed["detail"])
            except Exception:
                pass
        return RuntimeError(f"ChatGPT 逆向服务返回 HTTP {exc.code}: {detail}")

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "auto",
        stream: bool = False,
        thinking_effort: str = "",
        timeout: int = 600,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = None,
    ) -> Union[dict, Generator[dict, None, None]]:
        """调用逆向 /v1/chat/completions 接口对话"""
        if stream:
            return self._stream_generator(
                messages,
                model,
                thinking_effort,
                timeout,
                tools=tools,
                tool_choice=tool_choice,
            )

        url = f"{self.base_url}/v1/chat/completions"
        payload_dict: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if thinking_effort:
            payload_dict["thinking_effort"] = thinking_effort
        if tools:
            payload_dict["tools"] = tools
        if tool_choice is not None:
            payload_dict["tool_choice"] = tool_choice

        payload = json.dumps(payload_dict).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers())
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise self._extract_http_error(exc) from exc

    def _stream_generator(
        self,
        messages: List[Dict[str, Any]],
        model: str = "auto",
        thinking_effort: str = "",
        timeout: int = 600,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = None,
    ) -> Generator[dict, None, None]:
        url = f"{self.base_url}/v1/chat/completions"
        payload_dict: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if thinking_effort:
            payload_dict["thinking_effort"] = thinking_effort
        if tools:
            payload_dict["tools"] = tools
        if tool_choice is not None:
            payload_dict["tool_choice"] = tool_choice

        payload = json.dumps(payload_dict).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._auth_headers())
        try:
            resp = self.opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            raise self._extract_http_error(exc) from exc

        with resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except Exception:
                    continue
                if isinstance(chunk, dict) and isinstance(chunk.get("error"), dict):
                    err_msg = chunk["error"].get("message") or json.dumps(chunk["error"], ensure_ascii=False)
                    raise RuntimeError(str(err_msg))
                yield chunk

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
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(self._format_http_error(exc)) from exc


class UnifiedChatGPTService:
    """ChatGPT 统一门面服务，优先调度无头逆向引擎，必要时自动降级至浏览器同源桥接"""

    def __init__(
        self,
        reverse_port: int = DEFAULT_REVERSE_PORT,
        bridge_url: str = DEFAULT_BRIDGE_URL,
        proxy: Optional[str] = None,
    ):
        self.reverse = ChatGPTReverseEngine(port=reverse_port, proxy=proxy)
        self.bridge = ChatGPTBridgeClient(base_url=bridge_url)
        self.live_plan = ""
        self.live_plan_label = ""
        self._resyncing = False
        self._auto_sync_stop = threading.Event()
        self._auto_sync_thread: Optional[threading.Thread] = None

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

    LOGIN_URL = "https://chatgpt.com/"

    @staticmethod
    def decode_jwt_payload(token: str) -> Dict[str, Any]:
        """安全解码 JWT payload（不校验签名），失败时返回空字典。"""
        raw = str(token or "").strip()
        if not raw or "." not in raw:
            return {}
        parts = raw.split(".")
        if len(parts) < 2 or not parts[1]:
            return {}
        try:
            payload_b64 = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            decoded = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
            data = json.loads(decoded.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def normalize_plan_info(
        raw_plan: Any,
        *,
        has_active_subscription: Optional[bool] = None,
        subscription_plan: str = "",
    ) -> Dict[str, Any]:
        """将各类 ChatGPT 套餐标识归一化为统一展示结构。"""
        raw = str(raw_plan or "").strip()
        if (not raw or raw.lower() in ("free", "none")) and subscription_plan:
            if has_active_subscription is not False:
                raw = str(subscription_plan).strip()
        if has_active_subscription is False and raw.lower() in ("", "free", "none"):
            raw = "free"

        key = raw.strip().lower().replace("-", "_").replace(" ", "_")
        compact = key.replace("_", "")
        mapping = {
            "": ("free", "FREE", "Free", False, "免费版"),
            "none": ("free", "FREE", "Free", False, "免费版"),
            "free": ("free", "FREE", "Free", False, "免费版"),
            "chatgptfree": ("free", "FREE", "Free", False, "免费版"),
            "chatgptfreeplan": ("free", "FREE", "Free", False, "免费版"),
            "plus": ("Plus", "PLUS", "Plus", True, "ChatGPT Plus"),
            "chatgptplus": ("Plus", "PLUS", "Plus", True, "ChatGPT Plus"),
            "chatgptplusplan": ("Plus", "PLUS", "Plus", True, "ChatGPT Plus"),
            "pro": ("Pro", "PRO", "Pro", True, "ChatGPT Pro"),
            "chatgptpro": ("Pro", "PRO", "Pro", True, "ChatGPT Pro"),
            "chatgptproplan": ("Pro", "PRO", "Pro", True, "ChatGPT Pro"),
            "prolite": ("ProLite", "PRO_LITE", "ProLite", True, "ChatGPT Pro Lite"),
            "chatgptprolite": ("ProLite", "PRO_LITE", "ProLite", True, "ChatGPT Pro Lite"),
            "team": ("Team", "TEAM", "Team", True, "ChatGPT Team"),
            "business": ("Team", "TEAM", "Team", True, "ChatGPT Team"),
            "chatgptteam": ("Team", "TEAM", "Team", True, "ChatGPT Team"),
            "chatgptteamplan": ("Team", "TEAM", "Team", True, "ChatGPT Team"),
            "chatgptbusiness": ("Team", "TEAM", "Team", True, "ChatGPT Team"),
            "enterprise": ("Enterprise", "ENTERPRISE", "Enterprise", True, "ChatGPT Enterprise"),
            "edu": ("Enterprise", "ENTERPRISE", "Enterprise", True, "ChatGPT Enterprise"),
            "chatgptenterprise": ("Enterprise", "ENTERPRISE", "Enterprise", True, "ChatGPT Enterprise"),
            "chatgptenterpriseplan": ("Enterprise", "ENTERPRISE", "Enterprise", True, "ChatGPT Enterprise"),
            "chatgptedu": ("Enterprise", "ENTERPRISE", "Enterprise", True, "ChatGPT Enterprise"),
            "go": ("Go", "GO", "Go", True, "ChatGPT Go"),
            "chatgptgo": ("Go", "GO", "Go", True, "ChatGPT Go"),
            "chatgptgoplan": ("Go", "GO", "Go", True, "ChatGPT Go"),
        }
        hit = mapping.get(compact) or mapping.get(key)
        if hit:
            plan, tier, membership, is_member, label = hit
        else:
            tier = key.upper() or "FREE"
            is_member = tier != "FREE"
            plan = raw if is_member else "free"
            membership = raw if is_member else "Free"
            label = f"ChatGPT {raw}" if is_member else "免费版"
        return {
            "plan": plan,
            "plan_tier": tier,
            "membership": membership,
            "is_member": is_member,
            "membership_label": label,
        }

    @classmethod
    def _extract_accounts_check_entry(cls, payload: Any) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """从 /backend-api/accounts/check 响应中提取 default 账号与 entitlement。"""
        if not isinstance(payload, dict):
            return {}, {}
        accounts_map = payload.get("accounts")
        if not isinstance(accounts_map, dict) or not accounts_map:
            return {}, {}
        entry = accounts_map.get("default")
        if not isinstance(entry, dict):
            ordering = payload.get("account_ordering")
            if isinstance(ordering, list):
                for key in ordering:
                    if isinstance(accounts_map.get(key), dict):
                        entry = accounts_map.get(key)
                        break
        if not isinstance(entry, dict):
            for val in accounts_map.values():
                if isinstance(val, dict) and ("account" in val or "entitlement" in val):
                    entry = val
                    break
        if not isinstance(entry, dict):
            return {}, {}
        acc = entry.get("account") if isinstance(entry.get("account"), dict) else {}
        ent = entry.get("entitlement") if isinstance(entry.get("entitlement"), dict) else {}
        return acc, ent

    @classmethod
    def parse_account_info(
        cls,
        session: Optional[Dict[str, Any]] = None,
        *,
        me: Optional[Dict[str, Any]] = None,
        accounts_check: Optional[Dict[str, Any]] = None,
        pool_account: Optional[Dict[str, Any]] = None,
        access_token: str = "",
        id_token: str = "",
    ) -> Dict[str, Any]:
        """统一解析 JWT、/api/auth/session、/backend-api/me 与 /backend-api/accounts/check 中的账号字段。"""
        sess_raw = session if isinstance(session, dict) else {}
        sess_obj = sess_raw.get("session") if isinstance(sess_raw.get("session"), dict) else sess_raw
        me_obj = me if isinstance(me, dict) else (
            sess_raw.get("me") if isinstance(sess_raw.get("me"), dict) else {}
        )
        check_src = accounts_check if isinstance(accounts_check, dict) else (
            sess_raw.get("accounts_check") if isinstance(sess_raw.get("accounts_check"), dict) else (
                sess_obj if isinstance(sess_obj.get("accounts"), dict) else {}
            )
        )
        pool_obj = pool_account if isinstance(pool_account, dict) else {}

        tok = (
            str(access_token or "").strip()
            or str(sess_obj.get("accessToken") or sess_obj.get("access_token") or "").strip()
            or str(pool_obj.get("access_token") or "").strip()
        )
        id_tok = (
            str(id_token or "").strip()
            or str(sess_obj.get("idToken") or sess_obj.get("id_token") or "").strip()
            or str(pool_obj.get("id_token") or "").strip()
        )

        access_claims = cls.decode_jwt_payload(tok)
        id_claims = cls.decode_jwt_payload(id_tok)
        auth_claim = access_claims.get("https://api.openai.com/auth")
        auth_claim = auth_claim if isinstance(auth_claim, dict) else {}
        profile_claim = access_claims.get("https://api.openai.com/profile")
        profile_claim = profile_claim if isinstance(profile_claim, dict) else {}

        sess_user = sess_obj.get("user") if isinstance(sess_obj.get("user"), dict) else {}
        sess_account = sess_obj.get("account") if isinstance(sess_obj.get("account"), dict) else {}
        me_account = me_obj.get("account") if isinstance(me_obj.get("account"), dict) else {}
        check_account, check_entitlement = cls._extract_accounts_check_entry(check_src)

        def _first_nonempty(*values: Any) -> str:
            for v in values:
                s = str(v or "").strip()
                if s:
                    return s
            return ""

        email = _first_nonempty(
            pool_obj.get("email"),
            me_obj.get("email"),
            sess_user.get("email"),
            sess_obj.get("email"),
            profile_claim.get("email"),
            access_claims.get("email"),
            id_claims.get("email"),
        )
        name = _first_nonempty(
            pool_obj.get("name"),
            me_obj.get("name"),
            sess_user.get("name"),
            sess_obj.get("name"),
            profile_claim.get("name"),
            profile_claim.get("nickname"),
            access_claims.get("name"),
            access_claims.get("nickname"),
            id_claims.get("name"),
            id_claims.get("nickname"),
            id_claims.get("preferred_username"),
            check_account.get("name"),
        )
        user_id = _first_nonempty(
            pool_obj.get("user_id"),
            me_obj.get("id"),
            sess_user.get("id"),
            auth_claim.get("chatgpt_user_id"),
            auth_claim.get("user_id"),
            access_claims.get("sub"),
            id_claims.get("sub"),
        )
        account_id = _first_nonempty(
            pool_obj.get("account_id"),
            check_account.get("account_id"),
            me_account.get("account_id"),
            sess_account.get("account_id"),
            sess_account.get("id"),
            auth_claim.get("chatgpt_account_id"),
        )

        # 实时接口（accounts/check、/api/auth/session、/backend-api/me）优先于号池字段，号池字段优先于旧 JWT 声明
        raw_plan = _first_nonempty(
            check_account.get("plan_type"),
            sess_account.get("planType"),
            sess_account.get("plan_type"),
            sess_obj.get("accountPlan"),
            sess_obj.get("plan_type"),
            me_account.get("plan_type"),
            me_obj.get("plan_type"),
            pool_obj.get("plan_type"),
            pool_obj.get("type"),
            auth_claim.get("chatgpt_plan_type"),
            access_claims.get("chatgpt_plan_type"),
            id_claims.get("chatgpt_plan_type"),
        )
        has_active_sub = check_entitlement.get("has_active_subscription")
        if not isinstance(has_active_sub, bool):
            has_active_sub = None
        subscription_plan = str(check_entitlement.get("subscription_plan") or "").strip()
        plan_info = cls.normalize_plan_info(
            raw_plan,
            has_active_subscription=has_active_sub,
            subscription_plan=subscription_plan,
        )

        exp_raw = access_claims.get("exp") or id_claims.get("exp") or sess_obj.get("expires")
        return {
            "name": name,
            "email": email,
            "user_id": user_id,
            "account_id": account_id,
            "has_token": bool(tok),
            "token_expires_at": exp_raw,
            "subscription_active_until": (
                check_entitlement.get("expires_at")
                or auth_claim.get("chatgpt_subscription_active_until")
                or None
            ),
            "is_deactivated": bool(check_account.get("is_deactivated")) if "is_deactivated" in check_account else False,
            **plan_info,
        }

    @classmethod
    def plan_from_session(cls, session: dict) -> str:
        if not isinstance(session, dict):
            return "free"
        parsed = cls.parse_account_info(session)
        return parsed["plan"]

    @staticmethod
    def plan_label(plan: str) -> str:
        return {
            "free": "免费",
            "Plus": "Plus",
            "Pro": "Pro",
            "ProLite": "ProLite",
            "Team": "Team",
            "Enterprise": "Enterprise",
            "Go": "Go",
        }.get(plan, plan or "免费")

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

    def read_live_session(self, open_if_missing: bool = True, refresh_tab: bool = False) -> dict:
        """直接问扩展要浏览器里的真实会话。没有 chatgpt.com 标签或需要刷新时由扩展自动打开/重载。"""
        require_service_enabled("chatgpt")
        data = {}
        opened = False
        for attempt in range(6):
            try:
                data = self.bridge.get_session(
                    refresh=(refresh_tab and attempt == 0),
                    auto_open=(open_if_missing and attempt == 0),
                )
            except Exception as exc:
                data = {"success": False, "error": str(exc)}
            session = data.get("session") if isinstance(data, dict) else None
            if isinstance(session, dict) and session.get("accessToken"):
                return data
            err = str((data or {}).get("error") or "")
            diag_loc = str((data or {}).get("diagnostics", {}).get("location") or "")
            wrong_tab = bool(diag_loc) and not diag_loc.startswith("https://chatgpt.com")
            needs_tab = ("标签" in err) or ("未找到" in err) or ("chatgpt.com" in err) or wrong_tab
            if open_if_missing and needs_tab and not opened:
                opened = True
                try:
                    self._open_chatgpt_tab()
                except Exception as exc:
                    data = {"success": False, "error": str(exc)}
                    break
            elif not open_if_missing or not needs_tab:
                break
            time.sleep(1.2)
        return data if isinstance(data, dict) else {"success": False, "error": "无法读取浏览器会话"}

    def public_account(self) -> dict:
        if not is_service_enabled("chatgpt"):
            return {}
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
        parsed = self.parse_account_info(session)
        plan = parsed["plan"]
        self.live_plan = plan
        self.live_plan_label = self.plan_label(plan)
        return {
            "success": True,
            "logged_in": True,
            "source": "browser",
            "plan": plan,
            "plan_label": self.live_plan_label,
            "email": parsed["email"],
            "name": parsed["name"],
        }

    def get_models(self) -> dict:
        """获取模型列表，优先从逆向引擎拉取"""
        if self.reverse.is_running():
            try:
                return self.reverse.get_models()
            except Exception:
                pass
        return self.bridge.get_models()

    def sync_token_from_browser(self, open_if_missing: bool = True, refresh_tab: bool = False) -> dict:
        """从扩展读取真实会话，按免费/Plus 等方案写入号池，并清掉已经失效的旧令牌。"""
        require_service_enabled("chatgpt")
        data = self.read_live_session(open_if_missing=open_if_missing, refresh_tab=refresh_tab)
        session = data.get("session") if isinstance(data, dict) else None
        token = session.get("accessToken") if isinstance(session, dict) else ""
        if not token:
            err = str((data or {}).get("error") or "浏览器里没有可用的 ChatGPT 登录态")
            raise RuntimeError(
                f"{err}。请在已加载 Cookie Hub 的浏览器打开并登录 https://chatgpt.com/ ，免费账号也可以。"
            )

        parsed = self.parse_account_info(session)
        plan = parsed["plan"]
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
        if not kept and parsed["email"]:
            for account in after:
                current = str(account.get("access_token") or "")
                if current and account.get("email") and account.get("email") == parsed["email"]:
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
            "email": parsed["email"],
            "name": parsed["name"],
            "plan": plan,
            "plan_label": self.live_plan_label,
            "replaced_stale_accounts": removed,
            "message": f"已按浏览器真实登录态同步，当前是{self.live_plan_label}账号。",
        }

    def sync_token_from_codex(self) -> Optional[dict]:
        """优先从本机桌面端 Codex (~/.codex/auth.json) 读取 Plus 凭证（含 refresh_token）并导入号池。"""
        require_service_enabled("chatgpt")
        codex_path = os.path.expanduser(os.getenv("CODEX_AUTH_PATH", "~/.codex/auth.json"))
        if not os.path.isfile(codex_path):
            return None
        try:
            with open(codex_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception:
            return None
        if not isinstance(raw, dict):
            return None
        tokens = raw.get("tokens") if isinstance(raw.get("tokens"), dict) else {}
        access_token = str(tokens.get("access_token") or "").strip()
        refresh_token = str(tokens.get("refresh_token") or "").strip()
        account_id = str(tokens.get("account_id") or "").strip()
        if not access_token:
            return None

        claims = self.decode_jwt_payload(access_token)
        auth_claim = claims.get("https://api.openai.com/auth") if isinstance(claims.get("https://api.openai.com/auth"), dict) else {}
        prof_claim = claims.get("https://api.openai.com/profile") if isinstance(claims.get("https://api.openai.com/profile"), dict) else {}
        email = str(prof_claim.get("email") or "").strip()
        raw_plan = str(auth_claim.get("chatgpt_plan_type") or "").strip()
        plan_info = self.normalize_plan_info(
            raw_plan,
            has_active_subscription=bool(raw_plan and raw_plan.lower() != "free"),
        )
        plan = plan_info["plan"]
        self.live_plan = plan
        self.live_plan_label = self.plan_label(plan)

        if not self.reverse.is_running():
            self.reverse.start()

        payload_item: Dict[str, Any] = {
            "access_token": access_token,
            "type": plan,
            "status": "正常",
            "source_type": "codex",
        }
        if refresh_token:
            payload_item["refresh_token"] = refresh_token
        if email:
            payload_item["email"] = email
        if account_id:
            payload_item["account_id"] = account_id

        self.reverse.import_account_items([payload_item])
        try:
            self.reverse.update_account(access_token, {"type": plan, "status": "正常"})
        except Exception:
            pass

        # Clean up stale browser-only tokens that have no refresh_token when Codex Plus token is present
        removed = 0
        try:
            for acct in self.reverse.list_accounts():
                tok = str(acct.get("access_token") or "")
                if tok and tok != access_token and not acct.get("refresh_token") and acct.get("status") in ("异常", "禁用"):
                    try:
                        self.reverse.delete_account(tok)
                        removed += 1
                    except Exception:
                        pass
        except Exception:
            pass

        return {
            "success": True,
            "source": "codex_auth",
            "email": email,
            "plan": plan,
            "plan_label": self.live_plan_label,
            "has_refresh_token": bool(refresh_token),
            "replaced_stale_accounts": removed,
            "message": f"已优先从桌面端 Codex auth.json 同步 {self.live_plan_label} 凭证（含自动续期 refresh_token）。",
        }

    def sync_best_available_token(self, open_if_missing: bool = True, refresh_tab: bool = False) -> dict:
        """优先从桌面端 Codex auth.json 同步；不可用时回退到浏览器扩展同步。"""
        codex_res = self.sync_token_from_codex()
        if codex_res and codex_res.get("success"):
            return codex_res
        return self.sync_token_from_browser(open_if_missing=open_if_missing, refresh_tab=refresh_tab)

    def _has_browser_login_cookie(self) -> Optional[bool]:
        """检查 Cookie Hub 中是否存在 ChatGPT 会话 Cookie（不打开标签页）。"""
        url = f"{self.bridge.base_url}/cookies?domain=chatgpt.com"
        try:
            req = urllib.request.Request(url)
            with self.bridge.opener.open(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            cookies = data.get("cookies") if isinstance(data, dict) else []
            names = {str(item.get("name") or "") for item in (cookies or []) if isinstance(item, dict)}
            return any(name.startswith("__Secure-next-auth.session-token") for name in names)
        except Exception:
            return None

    @staticmethod
    def _map_reverse_status(raw_status: str) -> str:
        text = str(raw_status or "").strip()
        if text in ("正常", "enabled", "ok", "active"):
            return "enabled"
        if text in ("禁用", "disabled"):
            return "disabled"
        if text in ("限流", "异常", "error", "rate_limited", "invalid"):
            return "error"
        return "enabled" if not text else "error"

    @staticmethod
    def _format_reverse_quota(account: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        quota_val = account.get("quota")
        try:
            image_remaining: Optional[int] = max(0, int(quota_val)) if quota_val is not None else None
        except (TypeError, ValueError):
            image_remaining = None
        limits_progress = account.get("limits_progress")
        limits_list = limits_progress if isinstance(limits_progress, list) else []
        success = int(account.get("success") or 0)
        fail = int(account.get("fail") or 0)
        restore_at = str(account.get("restore_at") or "").strip() or None
        default_model = str(account.get("default_model_slug") or "").strip() or None
        raw_status = str(account.get("status") or "").strip()

        parts: List[str] = []
        img_limit = None
        for item in limits_list:
            if isinstance(item, dict) and item.get("feature_name") == "image_gen":
                img_limit = item.get("limit")
                if image_remaining is None and item.get("remaining") is not None:
                    try:
                        image_remaining = max(0, int(item.get("remaining")))
                    except (TypeError, ValueError):
                        pass
                break
        if image_remaining is not None:
            if img_limit is not None:
                parts.append(f"生图余 {image_remaining}/{img_limit}")
            else:
                parts.append(f"生图余 {image_remaining}")
        if success > 0 or fail > 0:
            parts.append(f"成功 {success} / 失败 {fail}")
        if raw_status == "限流":
            parts.append(f"已限流（恢复: {restore_at}）" if restore_at else "已限流")
        if not parts:
            parts.append("对话就绪" if raw_status in ("", "正常") else raw_status)

        quota_info = {
            "image_remaining": image_remaining,
            "limits_progress": limits_list,
            "success": success,
            "fail": fail,
            "restore_at": restore_at,
            "default_model_slug": default_model,
        }
        return " · ".join(parts), quota_info

    def get_dashboard_accounts(self, include_unauthenticated: bool = False) -> List[Dict[str, Any]]:
        """返回供账号看板展示的标准化 ChatGPT 账号列表（合并逆向号池与浏览器会话并去重）。"""
        if not is_service_enabled("chatgpt"):
            return []
        now_ts = int(time.time())
        entries: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()
        # 记录每个条目的匹配键，避免同一账号在逆向号池与浏览器会话中重复出现
        match_keys: List[Dict[str, str]] = []

        def _unique_id(base_id: str) -> str:
            candidate = base_id
            suffix = 2
            while candidate in seen_ids:
                candidate = f"{base_id}:{suffix}"
                suffix += 1
            seen_ids.add(candidate)
            return candidate

        # 1. 读取逆向号池账号
        reverse_running = False
        try:
            reverse_running = self.reverse.is_running()
        except Exception:
            reverse_running = False

        if reverse_running:
            try:
                pool_items = self.reverse.list_accounts()
            except Exception:
                pool_items = []
            for idx, item in enumerate(pool_items or [], start=1):
                if not isinstance(item, dict):
                    continue
                parsed = self.parse_account_info(pool_account=item)
                email = parsed["email"]
                user_id = parsed["user_id"]
                account_id = parsed["account_id"]
                raw_token = str(item.get("access_token") or "").strip()

                raw_id = account_id or user_id or email or f"pool-{idx}"
                entry_id = _unique_id(f"chatgpt:{raw_id}")
                raw_status = str(item.get("status") or "正常").strip()
                mapped_status = self._map_reverse_status(raw_status)
                quota_summary, quota_info = self._format_reverse_quota(item)

                display_name = (
                    parsed["name"]
                    or (email.split("@")[0] if email and "@" in email else "")
                    or (f"ChatGPT ({user_id[-6:]})" if user_id else f"ChatGPT 号池 #{idx}")
                )

                note_parts = [f"逆向号池（{item.get('source_type') or 'web'}）"]
                if raw_status and raw_status != "正常":
                    note_parts.append(f"状态: {raw_status}")
                if item.get("last_refresh_error"):
                    note_parts.append(f"刷新异常: {str(item.get('last_refresh_error'))[:80]}")

                entry = {
                    "platform": "chatgpt",
                    "platform_name": "ChatGPT",
                    "id": entry_id,
                    "raw_id": raw_id,
                    "name": display_name,
                    "email": email,
                    "membership": parsed["membership"],
                    "plan_tier": parsed["plan_tier"],
                    "is_member": parsed["is_member"],
                    "membership_label": parsed["membership_label"],
                    "quota_summary": quota_summary,
                    "quota": quota_info,
                    "status": mapped_status,
                    "visible": True,
                    "note": " · ".join(note_parts),
                    "source": "reverse_pool",
                    "login_url": self.LOGIN_URL,
                    "updated_at": now_ts,
                    "details": {
                        "raw_name": parsed["name"],
                        "user_id": user_id,
                        "account_id": account_id,
                        "raw_status": raw_status,
                        "source_type": item.get("source_type") or "web",
                        "invalid_count": int(item.get("invalid_count") or 0),
                        "image_inflight": int(item.get("image_inflight") or 0),
                        "last_used_at": item.get("last_used_at"),
                        "last_refresh_error": item.get("last_refresh_error"),
                        "created_at": item.get("created_at"),
                        "token_expires_at": parsed["token_expires_at"],
                        "has_token": parsed["has_token"],
                        "sources": ["reverse_pool"],
                    },
                }
                entries.append(entry)
                match_keys.append({
                    "email": email.lower(),
                    "account_id": account_id,
                    "user_id": user_id,
                    "token": raw_token,
                })

        # 2. 读取浏览器 Cookie Hub 会话（不主动弹新标签页）
        bridge_online = False
        bridge_ext = False
        try:
            b_health = self.bridge.check_health()
            bridge_online = True
            bridge_ext = bool(b_health.get("extensionConnected", False))
        except Exception:
            bridge_online = False
            bridge_ext = False

        browser_session_data: Dict[str, Any] = {}
        if bridge_online and bridge_ext:
            try:
                browser_session_data = self.bridge.get_session()
            except Exception as exc:
                browser_session_data = {"success": False, "error": str(exc)}

        session_obj = browser_session_data.get("session") if isinstance(browser_session_data, dict) else None
        if isinstance(session_obj, dict) and (
            session_obj.get("accessToken")
            or session_obj.get("user")
            or session_obj.get("account")
            or browser_session_data.get("me")
            or browser_session_data.get("accounts_check")
        ):
            parsed = self.parse_account_info(browser_session_data)
            self.live_plan = parsed["plan"]
            self.live_plan_label = self.plan_label(parsed["plan"])

            email = parsed["email"]
            user_id = parsed["user_id"]
            account_id = parsed["account_id"]
            raw_token = str(session_obj.get("accessToken") or session_obj.get("access_token") or "").strip()

            # 去重：检查是否已存在于逆向号池中
            matched_idx: Optional[int] = None
            for i, keys in enumerate(match_keys):
                if (
                    (email and keys["email"] and email.lower() == keys["email"])
                    or (account_id and keys["account_id"] and account_id == keys["account_id"])
                    or (user_id and keys["user_id"] and user_id == keys["user_id"])
                    or (raw_token and keys["token"] and raw_token == keys["token"])
                ):
                    matched_idx = i
                    break

            if matched_idx is not None:
                existing = entries[matched_idx]
                if parsed["name"]:
                    existing["name"] = parsed["name"]
                    existing["details"]["raw_name"] = parsed["name"]
                if email and not existing["email"]:
                    existing["email"] = email
                if user_id and not existing["details"].get("user_id"):
                    existing["details"]["user_id"] = user_id
                if account_id and not existing["details"].get("account_id"):
                    existing["details"]["account_id"] = account_id
                # 浏览器会话反映当前真实套餐等级
                if existing["plan_tier"] != parsed["plan_tier"]:
                    existing["details"]["pool_plan_tier"] = existing["plan_tier"]
                    existing["membership"] = parsed["membership"]
                    existing["plan_tier"] = parsed["plan_tier"]
                    existing["is_member"] = parsed["is_member"]
                    existing["membership_label"] = parsed["membership_label"]
                existing["details"]["browser_session_matched"] = True
                if "browser_session" not in existing["details"]["sources"]:
                    existing["details"]["sources"].append("browser_session")
                if "浏览器会话在线" not in existing["note"]:
                    existing["note"] = f"{existing['note']} · 浏览器会话在线"
            else:
                raw_id = account_id or user_id or email or "browser"
                base_id = "chatgpt:browser" if raw_id == "browser" else f"chatgpt:browser:{raw_id}"
                entry_id = _unique_id(base_id)
                display_name = (
                    parsed["name"]
                    or (email.split("@")[0] if email and "@" in email else "")
                    or (f"ChatGPT ({user_id[-6:]})" if user_id else "浏览器 ChatGPT 会话")
                )
                status = "error" if parsed.get("is_deactivated") else "ready"
                note = "浏览器账号已停用" if parsed.get("is_deactivated") else "浏览器同源桥接会话在线"
                entries.append({
                    "platform": "chatgpt",
                    "platform_name": "ChatGPT",
                    "id": entry_id,
                    "raw_id": raw_id,
                    "name": display_name,
                    "email": email,
                    "membership": parsed["membership"],
                    "plan_tier": parsed["plan_tier"],
                    "is_member": parsed["is_member"],
                    "membership_label": parsed["membership_label"],
                    "quota_summary": "浏览器同源会话就绪",
                    "quota": {
                        "image_remaining": None,
                        "limits_progress": [],
                        "success": 0,
                        "fail": 0,
                        "restore_at": None,
                        "default_model_slug": None,
                    },
                    "status": status,
                    "visible": True,
                    "note": note,
                    "source": "browser_session",
                    "login_url": self.LOGIN_URL,
                    "updated_at": now_ts,
                    "details": {
                        "raw_name": parsed["name"],
                        "user_id": user_id,
                        "account_id": account_id,
                        "subscription_active_until": parsed["subscription_active_until"],
                        "is_deactivated": parsed["is_deactivated"],
                        "token_expires_at": parsed["token_expires_at"],
                        "has_token": parsed["has_token"],
                        "sources": ["browser_session"],
                    },
                })
        elif not entries and bridge_online:
            # 没有号池账号也没打开 chatgpt.com 标签时，通过 Cookie 判断浏览器是否已登录
            has_cookie = self._has_browser_login_cookie()
            if has_cookie:
                plan_info = self.normalize_plan_info(self.live_plan or "")
                entries.append({
                    "platform": "chatgpt",
                    "platform_name": "ChatGPT",
                    "id": _unique_id("chatgpt:browser"),
                    "raw_id": "browser",
                    "name": "浏览器 ChatGPT 会话",
                    "email": "",
                    "membership": plan_info["membership"] if self.live_plan else "",
                    "plan_tier": plan_info["plan_tier"] if self.live_plan else "",
                    "is_member": plan_info["is_member"] if self.live_plan else False,
                    "membership_label": plan_info["membership_label"] if self.live_plan else "待同步",
                    "quota_summary": "已有登录 Cookie（点击刷新同步详情）",
                    "quota": {
                        "image_remaining": None,
                        "limits_progress": [],
                        "success": 0,
                        "fail": 0,
                        "restore_at": None,
                        "default_model_slug": None,
                    },
                    "status": "ready",
                    "visible": True,
                    "note": "浏览器存在 ChatGPT 登录 Cookie，尚未打开 chatgpt.com 标签页",
                    "source": "browser_session",
                    "login_url": self.LOGIN_URL,
                    "updated_at": now_ts,
                    "details": {
                        "cookie_present": True,
                        "extension_connected": bridge_ext,
                        "sources": ["browser_session"],
                    },
                })
            elif include_unauthenticated:
                entries.append({
                    "platform": "chatgpt",
                    "platform_name": "ChatGPT",
                    "id": _unique_id("chatgpt:unauthenticated"),
                    "raw_id": "unauthenticated",
                    "name": "ChatGPT 未登录",
                    "email": "",
                    "membership": "Free",
                    "plan_tier": "FREE",
                    "is_member": False,
                    "membership_label": "未登录",
                    "quota_summary": "未登录或未连接",
                    "quota": {},
                    "status": "not_logged_in" if bridge_ext else "offline",
                    "visible": False,
                    "note": "请在已加载 Cookie Hub 的浏览器登录 https://chatgpt.com/",
                    "source": "browser_session",
                    "login_url": self.LOGIN_URL,
                    "updated_at": now_ts,
                    "details": {
                        "cookie_present": bool(has_cookie),
                        "extension_connected": bridge_ext,
                    },
                })
        elif not entries and include_unauthenticated:
            entries.append({
                "platform": "chatgpt",
                "platform_name": "ChatGPT",
                "id": _unique_id("chatgpt:offline"),
                "raw_id": "offline",
                "name": "ChatGPT 服务离线",
                "email": "",
                "membership": "Free",
                "plan_tier": "FREE",
                "is_member": False,
                "membership_label": "离线",
                "quota_summary": "逆向服务与 Cookie Hub 均未连接",
                "quota": {},
                "status": "offline",
                "visible": False,
                "note": "请启动 Cookie Hub 扩展或 ChatGPT 逆向号池",
                "source": "browser_session",
                "login_url": self.LOGIN_URL,
                "updated_at": now_ts,
                "details": {
                    "reverse_running": reverse_running,
                    "bridge_online": bridge_online,
                    "extension_connected": bridge_ext,
                },
            })

        return entries

    def refresh_dashboard_accounts(self, open_if_missing: bool = False) -> Dict[str, Any]:
        """刷新 ChatGPT 账号状态（浏览器会话与逆向号池），安全降级不抛出未捕获异常。"""
        require_service_enabled("chatgpt")
        errors: List[str] = []
        synced_browser = False

        try:
            codex_res = self.sync_token_from_codex()
            if codex_res and codex_res.get("success"):
                synced_browser = True
        except Exception as exc:
            errors.append(f"Codex 凭证同步提示: {exc}")

        bridge_ext = False
        try:
            b_health = self.bridge.check_health()
            bridge_ext = bool(b_health.get("extensionConnected", False))
        except Exception as exc:
            errors.append(f"Cookie Hub 离线: {exc}")

        if bridge_ext:
            try:
                session_res = self.read_live_session(open_if_missing=open_if_missing, refresh_tab=True)
                session_obj = session_res.get("session") if isinstance(session_res, dict) else None
                if isinstance(session_obj, dict) and session_obj.get("accessToken"):
                    parsed = self.parse_account_info(session_res)
                    self.live_plan = parsed["plan"]
                    self.live_plan_label = self.plan_label(parsed["plan"])
                    synced_browser = True
                    if self.reverse.is_running():
                        tok = str(session_obj.get("accessToken") or "").strip()
                        try:
                            self.reverse.import_tokens([tok])
                            self.reverse.update_account(tok, {"type": parsed["plan"], "status": "正常"})
                        except Exception as exc:
                            errors.append(f"同步号池失败: {exc}")
                elif isinstance(session_res, dict) and session_res.get("error"):
                    errors.append(str(session_res.get("error")))
            except Exception as exc:
                errors.append(str(exc))

        try:
            if self.reverse.is_running():
                self.reverse.refresh_accounts()
        except Exception as exc:
            errors.append(f"刷新号池失败: {exc}")

        accounts = self.get_dashboard_accounts()
        return {
            "success": bool(accounts or synced_browser or not errors),
            "refreshed": len(accounts),
            "accounts": accounts,
            "error": "; ".join(errors) if (errors and not accounts) else None,
            "message": (
                f"已刷新 ChatGPT 账号（共 {len(accounts)} 个）"
                if accounts
                else ("; ".join(errors) if errors else "未检测到可用的 ChatGPT 账号")
            ),
        }

    def ensure_live_account(self) -> dict:
        """号池里没有可用账号时，用扩展里的当前登录态替换掉失效的旧 Plus 令牌。"""
        require_service_enabled("chatgpt")
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
        synced = self.sync_best_available_token()
        synced["synced"] = True
        return synced

    def start_auto_sync(self, interval_sec: Optional[int] = None) -> None:
        """启动后台定时保活同步：号池为空或无可用账号时，自动从 Cookie Hub 回填最新令牌。"""
        if self._auto_sync_thread and self._auto_sync_thread.is_alive():
            return
        self._auto_sync_stop.clear()
        if interval_sec is None:
            try:
                interval_sec = int(os.getenv("CHATGPT_SYNC_INTERVAL_SEC", "600") or "600")
            except ValueError:
                interval_sec = 600
        interval_sec = max(60, int(interval_sec))

        def _worker() -> None:
            if self._auto_sync_stop.wait(3.0):
                return
            while not self._auto_sync_stop.is_set():
                try:
                    if is_service_enabled("chatgpt"):
                        if not self.reverse.is_running():
                            self.reverse.start()
                        if self.reverse.is_running():
                            usable = [
                                account for account in self.reverse.list_accounts()
                                if account.get("status") not in ("异常", "禁用")
                            ]
                            has_codex_plus = any(
                                bool(account.get("refresh_token")) and account.get("status") not in ("异常", "禁用")
                                for account in usable
                            )
                            if not usable or not has_codex_plus:
                                res = self.sync_best_available_token(open_if_missing=False, refresh_tab=not usable)
                                if res.get("success"):
                                    print(
                                        f"🔄 [ChatGPT] 后台已自动同步账号 ({res.get('source', 'auto')}): {res.get('email') or 'unknown'} [{res.get('plan_label') or ''}]",
                                        flush=True,
                                    )
                except Exception as exc:
                    print(f"⚠️ [ChatGPT] 后台自动同步提示: {exc}", flush=True)
                if self._auto_sync_stop.wait(interval_sec):
                    break

        self._auto_sync_thread = threading.Thread(
            target=_worker, name="chatgpt-auto-sync", daemon=True
        )
        self._auto_sync_thread.start()

    def stop_auto_sync(self) -> None:
        self._auto_sync_stop.set()

    def ask(self, prompt: str, model: str = "auto", stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """统一提问接口：
        - 若模型显式包含 moni 或为 chatgpt-web / chatgpt-web-moni，强制走浏览器 DOM 模拟输入
        - 其他模型 (gpt-6, gpt-5-6, auto 等) 走 Web API 协议逆向直连，绝不静默降级到浏览器输入！
        """
        require_service_enabled("chatgpt")
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

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "auto",
        stream: bool = False,
        thinking_effort: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = None,
    ) -> Union[dict, Generator[dict, None, None]]:
        """OpenAI 兼容对话调用接口：
        - 若模型显式包含 moni 或为 chatgpt-web / chatgpt-web-moni，强制走浏览器 DOM 模拟输入
        - 其他模型 (gpt-6, gpt-5-6, auto 等) 走 Web API 协议逆向直连，绝不静默降级到浏览器输入！
        """
        require_service_enabled("chatgpt")
        model_lower = (model or "").lower().strip()
        if "moni" in model_lower or model_lower in ("chatgpt-web", "chatgpt-web-moni"):
            return self.bridge.chat(messages, model="chatgpt-web", stream=stream)

        self.ensure_live_account()
        auth_retry_keywords = ("429", "401", "403", "quota", "token", "unauthorized", "anon", "invalid")

        if stream:
            def _stream_with_retry():
                emitted = False
                try:
                    for chunk in self.reverse.chat(
                        messages,
                        model=model,
                        stream=True,
                        thinking_effort=thinking_effort,
                        tools=tools,
                        tool_choice=tool_choice,
                    ):
                        emitted = True
                        yield chunk
                except Exception as first_err:
                    err_msg = str(first_err).lower()
                    retryable = (not emitted) and any(k in err_msg for k in auth_retry_keywords)
                    if retryable and not self._resyncing:
                        self._resyncing = True
                        try:
                            self.sync_token_from_browser()
                            yield from self.reverse.chat(
                                messages,
                                model=model,
                                stream=True,
                                thinking_effort=thinking_effort,
                                tools=tools,
                                tool_choice=tool_choice,
                            )
                            return
                        finally:
                            self._resyncing = False
                    raise first_err

            return _stream_with_retry()

        try:
            return self.reverse.chat(
                messages,
                model=model,
                stream=False,
                thinking_effort=thinking_effort,
                tools=tools,
                tool_choice=tool_choice,
            )
        except Exception as first_err:
            err_msg = str(first_err).lower()
            is_env_proxy_err = any(
                k in err_msg for k in ("proxyerror", "unable to connect to proxy", "winerror 10061", "tiktoken")
            )
            is_proxy_err = is_env_proxy_err or any(
                k in err_msg for k in ("failed to connect", "proxyconnect", "curl: (7)", "connection refused")
            )
            if is_env_proxy_err:
                if self.reverse.restart():
                    try:
                        return self.reverse.chat(
                            messages,
                            model=model,
                            stream=False,
                            thinking_effort=thinking_effort,
                            tools=tools,
                            tool_choice=tool_choice,
                        )
                    except Exception as restart_retry_err:
                        first_err = restart_retry_err
                        err_msg = str(restart_retry_err).lower()
            elif is_proxy_err or "502" in err_msg:
                if self.reverse.apply_proxy(force=True):
                    try:
                        return self.reverse.chat(
                            messages,
                            model=model,
                            stream=False,
                            thinking_effort=thinking_effort,
                            tools=tools,
                            tool_choice=tool_choice,
                        )
                    except Exception as proxy_retry_err:
                        first_err = proxy_retry_err
                        err_msg = str(proxy_retry_err).lower()
                        if any(k in err_msg for k in ("proxyerror", "unable to connect to proxy", "winerror 10061", "failed to connect", "proxyconnect", "curl: (7)")):
                            if self.reverse.restart():
                                try:
                                    return self.reverse.chat(
                                        messages,
                                        model=model,
                                        stream=False,
                                        thinking_effort=thinking_effort,
                                        tools=tools,
                                        tool_choice=tool_choice,
                                    )
                                except Exception as restart_retry_err:
                                    first_err = restart_retry_err
                                    err_msg = str(restart_retry_err).lower()
            retryable = any(k in err_msg for k in auth_retry_keywords) or ("502" in err_msg)
            if retryable and not self._resyncing:
                self._resyncing = True
                try:
                    self.sync_token_from_browser()
                    return self.reverse.chat(
                        messages,
                        model=model,
                        stream=False,
                        thinking_effort=thinking_effort,
                        tools=tools,
                        tool_choice=tool_choice,
                    )
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
        require_service_enabled("chatgpt")
        self.ensure_live_account()
        try:
            return self.reverse.generate_image(
                prompt, model=model, n=n, response_format=response_format, timeout=timeout
            )
        except Exception as first_err:
            err_msg = str(first_err).lower()
            if any(k in err_msg for k in ("proxyerror", "unable to connect to proxy", "winerror 10061")):
                if self.reverse.restart():
                    try:
                        return self.reverse.generate_image(
                            prompt, model=model, n=n, response_format=response_format, timeout=timeout
                        )
                    except Exception as restart_retry_err:
                        first_err = restart_retry_err
                        err_msg = str(restart_retry_err).lower()
            elif any(k in err_msg for k in ("failed to connect", "proxyconnect", "curl: (7)", "connection refused")):
                if self.reverse.apply_proxy(force=True):
                    try:
                        return self.reverse.generate_image(
                            prompt, model=model, n=n, response_format=response_format, timeout=timeout
                        )
                    except Exception as proxy_retry_err:
                        first_err = proxy_retry_err
                        err_msg = str(proxy_retry_err).lower()
            if any(k in err_msg for k in ("429", "401", "quota", "token", "unauthorized", "too many requests")):
                try:
                    sync_res = self.sync_best_available_token()
                    if sync_res.get("success"):
                        return self.reverse.generate_image(
                            prompt, model=model, n=n, response_format=response_format, timeout=timeout
                        )
                except Exception:
                    pass
            if any(k in err_msg for k in ('502', 'timed out', 'timeout', 'connection closed abruptly', 'curl: (56)', 'upstream connection', 'no available image quota')):
                for _delay in (2.0, 5.0, 10.0):
                    time.sleep(_delay)
                    try:
                        return self.reverse.generate_image(prompt, model=model, n=n, response_format=response_format, timeout=timeout)
                    except Exception as _re:
                        first_err = _re
                        if not any(k in str(_re).lower() for k in ('502', 'timed out', 'timeout', 'connection closed abruptly', 'curl: (56)', 'upstream connection', 'no available image quota')):
                            raise
                raise first_err
            raise first_err

    def generate_images_concurrent(self, prompts: Optional[List[str]] = None, prompt: Optional[str] = None, count: int = 1, model: str = 'gpt-image-2', n: int = 1, response_format: str = 'b64_json', max_concurrency: int = 3, timeout: int = 240) -> dict:
        require_service_enabled('chatgpt')
        tasks = [str(x).strip() for x in (prompts or []) if str(x or '').strip()]
        if not tasks and prompt and str(prompt).strip():
            tasks = [str(prompt).strip()] * max(1, min(int(count or 1), 20))
        if not tasks:
            raise ValueError('prompts 或 prompt 不能为空')
        workers = max(1, min(int(max_concurrency or 3), 10, len(tasks)))
        self.ensure_live_account()
        t0 = time.time()
        results = [None] * len(tasks)
        def _run_one(idx, item_prompt):
            it0 = time.time()
            try:
                res = self.generate_image(prompt=item_prompt, model=model, n=n, response_format=response_format, timeout=timeout)
                return {'index': idx, 'prompt': item_prompt, 'success': True, 'latency_ms': int((time.time() - it0) * 1000), 'created': res.get('created'), 'data': res.get('data', [])}
            except Exception as exc:
                return {'index': idx, 'prompt': item_prompt, 'success': False, 'latency_ms': int((time.time() - it0) * 1000), 'error': str(exc), 'data': []}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for fut in as_completed([ex.submit(_run_one, i, tp) for i, tp in enumerate(tasks)]):
                r = fut.result()
                results[r['index']] = r
        ordered = [r for r in results if r is not None]
        ok = sum(1 for r in ordered if r.get('success'))
        imgs = [img for r in ordered if r.get('success') for img in r.get('data', []) if isinstance(img, dict)]
        return {'success': ok > 0, 'model': model, 'total_tasks': len(ordered), 'succeeded': ok, 'failed': len(ordered) - ok, 'max_concurrency': workers, 'latency_ms': int((time.time() - t0) * 1000), 'data': imgs, 'results': ordered}


# 单例导出
chatgpt_service = UnifiedChatGPTService()
chatgpt_reverse_engine = chatgpt_service.reverse
ChatGPTService = UnifiedChatGPTService
