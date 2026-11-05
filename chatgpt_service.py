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
DEFAULT_REVERSE_AUTH_KEY = "chatgpt2api"


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
        proxy: str = "http://127.0.0.1:7897",
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

        uv_bin = shutil.which("uv") or r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Links\uv.exe"
        if not os.path.exists(uv_bin) and not shutil.which("uv"):
            raise RuntimeError(f"未找到 uv 可执行文件，无法启动逆向服务 (查找路径: {uv_bin})")

        env = os.environ.copy()
        if self.proxy:
            env["HTTP_PROXY"] = self.proxy
            env["HTTPS_PROXY"] = self.proxy
        env["NO_PROXY"] = "127.0.0.1,localhost,::1"

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
        proxy: str = "http://127.0.0.1:7897",
    ):
        self.reverse = ChatGPTReverseEngine(port=reverse_port, proxy=proxy)
        self.bridge = ChatGPTBridgeClient(base_url=bridge_url)

    def is_reverse_available(self) -> bool:
        """判断逆向引擎是否在线且有可用账号"""
        if not self.reverse.is_running():
            return False
        try:
            health = self.reverse.get_health()
            accounts = health.get("accounts", {})
            return (accounts.get("active", 0) > 0) or (accounts.get("total", 0) > 0)
        except Exception:
            return False

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

    def get_session(self) -> dict:
        """提取会话信息，优先返回浏览器扩展登录态"""
        try:
            return self.bridge.get_session()
        except Exception as e:
            if self.reverse.is_running():
                accounts = self.reverse.list_accounts()
                if accounts:
                    first = accounts[0]
                    return {
                        "success": True,
                        "session": {
                            "user": {"email": first.get("email", "unknown@chatgpt2api.local"), "name": first.get("name", "Pool User")},
                            "accountPlan": first.get("type", "free"),
                            "expires": "N/A (Managed Pool)",
                        }
                    }
            raise RuntimeError(f"无法获取 ChatGPT 会话: {e}")

    def get_models(self) -> dict:
        """获取模型列表，优先从逆向引擎拉取"""
        if self.reverse.is_running():
            try:
                return self.reverse.get_models()
            except Exception:
                pass
        return self.bridge.get_models()

    def sync_token_from_browser(self) -> dict:
        """从浏览器 Cookie Hub 自动提取 AccessToken 并导入到逆向号池"""
        session_info = self.bridge.get_session()
        session = session_info.get("session", {})
        token = session.get("accessToken")
        if not token:
            raise RuntimeError("未能从浏览器会话中提取到 accessToken，请确认浏览器中已打开并登录 chatgpt.com！")

        if not self.reverse.is_running():
            self.reverse.start()

        res = self.reverse.import_tokens([token])
        return {
            "success": True,
            "email": session.get("user", {}).get("email"),
            "plan": session.get("accountPlan", "free"),
            "import_result": res,
        }

    def ask(self, prompt: str, model: str = "auto", stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """统一提问接口：
        - 若模型显式包含 moni 或为 chatgpt-web / chatgpt-web-moni，强制走浏览器 DOM 模拟输入
        - 其他模型 (gpt-6, gpt-5-6, auto 等) 走 Web API 协议逆向直连，绝不静默降级到浏览器输入！
        """
        model_lower = (model or "").lower().strip()
        if "moni" in model_lower or model_lower in ("chatgpt-web", "chatgpt-web-moni"):
            return self.bridge.ask(prompt, model="chatgpt-web", stream=stream)

        # 协议逆向直连通道 (绝不回退到浏览器 DOM 输入，两者严格物理隔离)
        if not self.reverse.is_running():
            self.reverse.start()

        if stream:
            def _gen():
                for chunk in self.reverse.chat([{"role": "user", "content": prompt}], model=model, stream=True):
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta
            return _gen()
        else:
            res = self.reverse.chat([{"role": "user", "content": prompt}], model=model, stream=False)
            return res["choices"][0]["message"]["content"]

    def chat(self, messages: List[Dict[str, Any]], model: str = "auto", stream: bool = False, thinking_effort: str = "") -> Union[dict, Generator[dict, None, None]]:
        """OpenAI 兼容对话调用接口：
        - 若模型显式包含 moni 或为 chatgpt-web / chatgpt-web-moni，强制走浏览器 DOM 模拟输入
        - 其他模型 (gpt-6, gpt-5-6, auto 等) 走 Web API 协议逆向直连，绝不静默降级到浏览器输入！
        """
        model_lower = (model or "").lower().strip()
        if "moni" in model_lower or model_lower in ("chatgpt-web", "chatgpt-web-moni"):
            return self.bridge.chat(messages, model="chatgpt-web", stream=stream)

        # 协议逆向直连通道 (严格隔离，若报错直接抛出真实异常，禁止篡改用户意图偷调浏览器)
        if not self.reverse.is_running():
            self.reverse.start()
        return self.reverse.chat(messages, model=model, stream=stream, thinking_effort=thinking_effort)

    def generate_image(self, prompt: str, model: str = "gpt-image-2", n: int = 1) -> dict:
        """文生图接口"""
        if not self.reverse.is_running():
            self.reverse.start()
        return self.reverse.generate_image(prompt, model=model, n=n)


# 单例导出
chatgpt_service = UnifiedChatGPTService()
chatgpt_reverse_engine = chatgpt_service.reverse
ChatGPTService = UnifiedChatGPTService
