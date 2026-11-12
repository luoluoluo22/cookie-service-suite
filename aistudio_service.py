# -*- coding: utf-8 -*-
"""
Google AI Studio Service (AIStudioService)
=========================================
将 Google AI Studio (aistudio.google.com) 网页端私有 RPC 逆向封装为高可用统一 API。
底层基于 aistudio2api 核心引擎：
- 官方 WAA (Web Attestation / BotGuard) 签名自动计算（基于进程内 SpiderMonkey JS 引擎）
- 全面走 Playground 原生生成通道与 SSE 流式打字机响应
- 支持 78+ Google 原生前沿模型（包含最新的 gemini-4-argon, gemini-3.8-flash 等）
- 自动从本地 Cookie Hub 提取并同步 Google 鉴权凭证入池
- 统一暴露标准 OpenAI ChatCompletions 与专属调用接口
"""

import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error
from typing import Generator, Dict, Any, Union, List, Optional

os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"
_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

DEFAULT_AISTUDIO_PORT = 2048
DEFAULT_PROXY = "http://127.0.0.1:7897"


class AIStudioService:
    """Google AI Studio 网页端逆向服务管理与调用门面"""

    def __init__(
        self,
        port: int = DEFAULT_AISTUDIO_PORT,
        proxy: str = DEFAULT_PROXY,
        base_dir: Optional[str] = None,
        bridge_url: str = "http://127.0.0.1:18888",
    ):
        self.port = port
        self.proxy = proxy or os.environ.get("HTTP_PROXY") or DEFAULT_PROXY
        self.bridge_url = bridge_url.rstrip("/")
        
        # 默认二进制位于 candidate_repos/aistudio2api-go/aistudio2api-v0.3.5-windows-amd64
        if base_dir is None:
            self.base_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "candidate_repos",
                "aistudio2api-go",
                "aistudio2api-v0.3.5-windows-amd64",
            )
        else:
            self.base_dir = base_dir

        self.exe_path = os.path.join(self.base_dir, "aistudio2api.exe")
        self.process: Optional[subprocess.Popen] = None
        self._cached_models: List[str] = []
        self._last_models_fetch: float = 0.0

    # -------------------------------------------------------------
    # 进程与生命周期管理
    # -------------------------------------------------------------
    def is_running(self) -> bool:
        """检查 aistudio2api 管理端是否正在监听且健康响应。"""
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/status")
            with _LOCAL_OPENER.open(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def is_data_plane_ready(self) -> bool:
        """检查数据面 (生成服务) 是否已处于 RUNNING 状态。"""
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/status")
            with _LOCAL_OPENER.open(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("running", False) or data.get("state") == "RUNNING"
        except Exception:
            return False

    def start(self, timeout: int = 15) -> bool:
        """启动 aistudio2api 进程并激活数据面。"""
        if not os.path.isfile(self.exe_path):
            raise FileNotFoundError(f"未找到 aistudio2api 核心程序: {self.exe_path}")

        # 如果进程未在运行，则拉起
        if not self.is_running():
            env = os.environ.copy()
            env["PROXY"] = self.proxy
            env["WAA_BACKEND"] = "spidermonkey"
            env["NO_PROXY"] = "127.0.0.1,localhost,::1"

            # 在 Windows 上以后台无控制台进程拉起
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0x08000000

            self.process = subprocess.Popen(
                [self.exe_path],
                cwd=self.base_dir,
                env=env,
                creationflags=creation_flags,
            )

            # 等待管理端口就绪
            t0 = time.time()
            started = False
            while time.time() - t0 < timeout:
                time.sleep(0.5)
                if self.is_running():
                    started = True
                    break
            if not started:
                return False

        # 如果管理端在线，但数据面未就绪，调用 /api/control/start 启动并探测模型
        if not self.is_data_plane_ready():
            try:
                start_req = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/api/control/start",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                )
                with _LOCAL_OPENER.open(start_req, timeout=30) as resp:
                    pass
            except Exception as e:
                print(f"[AIStudio] 激活数据面通知: {e}", flush=True)

        return True

    def stop(self) -> bool:
        """停止数据面与核心进程。"""
        # 1. 尝试通知控制面优雅停止
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/control/stop",
                data=b"{}",
                headers={"Content-Type": "application/json"},
            )
            with _LOCAL_OPENER.open(req, timeout=3) as resp:
                pass
        except Exception:
            pass

        # 2. 如果存在子进程句柄，进行终止
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        # 3. 兜底扫描端口或进程名进行清理
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "aistudio2api.exe", "/T"],
                    capture_output=True,
                    timeout=3,
                )
            except Exception:
                pass

        # 4. 清理残留锁文件
        leases_dir = os.path.join(self.base_dir, "auth", ".leases")
        if os.path.exists(leases_dir):
            for lf in os.listdir(leases_dir):
                if lf.endswith(".lock"):
                    try:
                        os.remove(os.path.join(leases_dir, lf))
                    except Exception:
                        pass

        return True

    def restart(self) -> bool:
        """重启服务"""
        self.stop()
        time.sleep(1)
        return self.start()

    def ensure_ready(self) -> None:
        """确保服务已就绪并可接收推理请求"""
        if not self.is_running() or not self.is_data_plane_ready():
            ok = self.start()
            if not ok:
                raise RuntimeError("无法启动 Google AI Studio (aistudio2api) 核心逆向服务！")

    # -------------------------------------------------------------
    # 状态与账号信息查询
    # -------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        """获取服务当前全景状态"""
        running = self.is_running()
        data_plane = False
        status_info = {}
        if running:
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/status")
                with _LOCAL_OPENER.open(req, timeout=2) as resp:
                    status_info = json.loads(resp.read().decode("utf-8"))
                    data_plane = status_info.get("running", False) or status_info.get("state") == "RUNNING"
            except Exception:
                pass

        accounts = self.list_accounts() if running else []
        models = self.list_models() if (running and data_plane) else []

        return {
            "service_name": "Google AI Studio Reverse Engine",
            "running": running,
            "data_plane_ready": data_plane,
            "state": status_info.get("state", "STOPPED" if not running else "IDLE"),
            "port": self.port,
            "version": status_info.get("version", "v0.3.5"),
            "waa_backend": "spidermonkey",
            "proxy": self.proxy,
            "accounts_total": len(accounts),
            "accounts_ready": sum(1 for a in accounts if a.get("state") == "ready" and a.get("enabled")),
            "accounts": accounts,
            "models_count": len(models),
            "available_models": models[:20],
        }

    def list_accounts(self) -> List[Dict[str, Any]]:
        """获取所有已导入的 Google 账号"""
        if not self.is_running():
            return []
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/accounts")
            with _LOCAL_OPENER.open(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("accounts", [])
        except Exception:
            return []

    def list_models(self) -> List[str]:
        """获取已探测到的 AI Studio 原生模型列表"""
        now = time.time()
        if self._cached_models and (now - self._last_models_fetch < 60):
            return self._cached_models

        if not self.is_running():
            return self._cached_models or [
                "gemini-4-argon",
                "gemini-3.8-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.1-pro-preview",
            ]

        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/models")
            with _LOCAL_OPENER.open(req, timeout=5) as resp:
                model_data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("id") for m in model_data.get("data", []) if m.get("id")]
                if models:
                    self._cached_models = models
                    self._last_models_fetch = now
                return models
        except Exception:
            return self._cached_models or ["gemini-4-argon", "gemini-3.8-flash", "gemini-3.5-flash-lite"]

    # -------------------------------------------------------------
    # Cookie 同步与凭证自动入池
    # -------------------------------------------------------------
    @staticmethod
    def _hub_to_storage_cookie(c: dict) -> dict:
        """将 Chrome / Edge 扩展 Cookie 转换为 Playwright storage-state 标准格式"""
        samesite_map = {
            "no_restriction": "None",
            "lax": "Lax",
            "strict": "Strict",
        }
        raw_samesite = str(c.get("sameSite", "")).lower()
        samesite = samesite_map.get(raw_samesite, "")

        expires = c.get("expirationDate")
        if expires is None or c.get("session", False):
            expires = -1
        else:
            try:
                expires = float(expires)
            except Exception:
                expires = -1

        return {
            "name": str(c.get("name", "")),
            "value": str(c.get("value", "")),
            "domain": str(c.get("domain", "")),
            "path": str(c.get("path", "/")),
            "expires": expires,
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", False)),
            "sameSite": samesite,
        }

    def sync_cookies_from_hub(self) -> Dict[str, Any]:
        """从本地 Cookie Hub 提取浏览器已登录的 Google Cookie 并一键导入/更新 AI Studio 号池"""
        hub_url = f"{self.bridge_url}/cookies?domain=google.com"
        req = urllib.request.Request(hub_url)
        try:
            with _LOCAL_OPENER.open(req, timeout=5) as resp:
                hub_data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"连接本地 Cookie Hub 失败: {e}，请确保扩展正常运行。")

        cookies_list = hub_data.get("cookies", [])
        if not cookies_list:
            raise RuntimeError("未能从 Cookie Hub 获取到任何 google.com Cookie，请确认浏览器中已登录 Google 账号。")

        auth_dir = os.path.join(self.base_dir, "auth")
        os.makedirs(auth_dir, exist_ok=True)

        existing_accs = [
            item for item in os.listdir(auth_dir)
            if os.path.isdir(os.path.join(auth_dir, item)) and not item.startswith(".") and not item.endswith(".bak")
        ]

        converted_cookies = [self._hub_to_storage_cookie(c) for c in cookies_list]
        saved_accounts = []
        raw_output = ""

        if existing_accs:
            # 针对现有账号，直接刷新其 storage-state.json 和 account.json，规避 setup "账户已存在" 失败问题
            for acc in existing_accs:
                acc_dir = os.path.join(auth_dir, acc)
                storage_file = os.path.join(acc_dir, "storage-state.json")
                acc_file = os.path.join(acc_dir, "account.json")
                rstate_file = os.path.join(acc_dir, "runtime-state.json")

                # 保留已有的 origins 字段
                origins = []
                if os.path.isfile(storage_file):
                    try:
                        with open(storage_file, "r", encoding="utf-8") as sf:
                            old_data = json.load(sf)
                            origins = old_data.get("origins", [])
                    except Exception:
                        origins = []

                # 注入最新转换的浏览器 Cookie
                with open(storage_file, "w", encoding="utf-8") as sf:
                    json.dump({"cookies": converted_cookies, "origins": origins}, sf, indent=2)

                # 更新 account.json 代理与启用状态
                acc_data = {"label": acc, "enabled": True, "proxy": self.proxy, "locale": "zh-CN", "timezone": "Asia/Shanghai"}
                if os.path.isfile(acc_file):
                    try:
                        with open(acc_file, "r", encoding="utf-8") as af:
                            acc_data = json.load(af)
                    except Exception:
                        pass
                acc_data["enabled"] = True
                acc_data["proxy"] = self.proxy
                with open(acc_file, "w", encoding="utf-8") as af:
                    json.dump(acc_data, af, indent=2)

                # 重置 runtime-state 中的失效与模型错误状态
                if os.path.isfile(rstate_file):
                    try:
                        with open(rstate_file, "r", encoding="utf-8") as rf:
                            rstate = json.load(rf)
                        if "state" in rstate and rstate["state"] == "auth_required":
                            del rstate["state"]
                        with open(rstate_file, "w", encoding="utf-8") as rf:
                            json.dump(rstate, rf, indent=2)
                    except Exception:
                        pass

                saved_accounts.append(acc)
            raw_output = f"已直接热刷新 {len(saved_accounts)} 个现有账户的 storage-state.json 凭证。"
        else:
            # 首次导入：调用 aistudio2api setup
            cookies_json_path = os.path.join(self.base_dir, "cookies.json")
            with open(cookies_json_path, "w", encoding="utf-8") as f:
                json.dump(cookies_list, f, indent=2)

            env = os.environ.copy()
            env["PROXY"] = self.proxy
            env["WAA_BACKEND"] = "spidermonkey"
            env["NO_PROXY"] = "127.0.0.1,localhost,::1"

            cmd = [self.exe_path, "setup", "-cookie-file", "cookies.json"]
            proc = subprocess.run(cmd, cwd=self.base_dir, env=env, capture_output=True, text=True, timeout=15)
            raw_output = (proc.stdout or "") + (proc.stderr or "")

            if os.path.exists(auth_dir):
                for item in os.listdir(auth_dir):
                    acc_path = os.path.join(auth_dir, item, "account.json")
                    if os.path.isfile(acc_path):
                        saved_accounts.append(item)
                        try:
                            with open(acc_path, "r", encoding="utf-8") as af:
                                acc_data = json.load(af)
                            acc_data["proxy"] = self.proxy
                            with open(acc_path, "w", encoding="utf-8") as af:
                                json.dump(acc_data, af, indent=2)
                        except Exception:
                            pass

        # 重启 aistudio2api 进程并激活数据面，确保内存中加载新凭证
        if self.is_running():
            self.restart()
        else:
            self.start()

        return {
            "success": True,
            "message": f"Cookie 凭证同步成功！已绑定并更新账号: {', '.join(saved_accounts) if saved_accounts else '已更新'}",
            "accounts": saved_accounts,
            "raw_output": raw_output.strip(),
        }

    # -------------------------------------------------------------
    # 对话生成（支持流式 SSE 与完整非流式，内置凭证失效自愈重试）
    # -------------------------------------------------------------
    def _build_request(self, model: str, messages: List[Dict[str, str]], stream: bool) -> urllib.request.Request:
        req_payload = {
            "model": model or "gemini-4-argon",
            "messages": messages,
            "stream": stream,
        }
        url = f"http://127.0.0.1:{self.port}/v1/chat/completions"
        return urllib.request.Request(
            url,
            data=json.dumps(req_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

    def chat(
        self,
        prompt: str,
        model: str = "gemini-4-argon",
        stream: bool = False,
        messages: Optional[List[Dict[str, str]]] = None,
        timeout: int = 120,
        _retry_auth: bool = True,
    ) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """
        调用 Google AI Studio 逆向接口发起推理。
        :param prompt: 提问正文（若提供了 messages 则以 messages 为主）
        :param model: 模型名称（如 gemini-4-argon, gemini-3.8-flash 等）
        :param stream: 是否启用 SSE 流式传输
        :param messages: 兼容 OpenAI 格式的历史消息列表
        :param timeout: 超时时间 (秒)
        :param _retry_auth: 是否在 401 凭证过期时自动从 Cookie Hub 同步并重试
        """
        self.ensure_ready()

        if not messages:
            messages = [{"role": "user", "content": prompt}]

        req = self._build_request(model, messages, stream)

        if stream:
            return self._stream_generator(req, model=model, messages=messages, timeout=timeout, _retry_auth=_retry_auth)
        else:
            t0 = time.time()
            try:
                with _LOCAL_OPENER.open(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    took_ms = int((time.time() - t0) * 1000)
                    data["latency_ms"] = took_ms
                    return data
            except urllib.error.HTTPError as he:
                body = he.read().decode("utf-8", errors="replace")
                # 遇到 401 / 503 账号凭证失效时，自动尝试从 Cookie Hub 热更新凭证并重试一次
                if _retry_auth and (he.code == 401 or ("invalid authentication credentials" in body or "需要重新登录" in body or "account_unavailable" in body)):
                    print("[AIStudio] 遇到 Google 凭证失效 (401/auth_required)，正在自动从 Cookie Hub 同步并重试...", flush=True)
                    try:
                        self.sync_cookies_from_hub()
                        time.sleep(1)
                        return self.chat(
                            prompt=prompt,
                            model=model,
                            stream=stream,
                            messages=messages,
                            timeout=timeout,
                            _retry_auth=False,
                        )
                    except Exception as sync_err:
                        print(f"[AIStudio] 凭证自愈重试失败: {sync_err}", flush=True)
                raise RuntimeError(f"AI Studio 上游接口返回 HTTP {he.code}: {body}")
            except Exception as e:
                raise RuntimeError(f"AI Studio 请求失败: {e}")

    def _stream_generator(
        self,
        req: urllib.request.Request,
        model: str = "gemini-4-argon",
        messages: Optional[List[Dict[str, str]]] = None,
        timeout: int = 120,
        _retry_auth: bool = True,
    ) -> Generator[str, None, None]:
        """流式生成器：直接转发并产出上游 SSE 事件流（内置 401 自动同步重试）"""
        try:
            resp = _LOCAL_OPENER.open(req, timeout=timeout)
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace")
            # 流式握手阶段若遇到凭证失效，自动从 Cookie Hub 热同步并重试
            if _retry_auth and (he.code == 401 or ("invalid authentication credentials" in err_body or "需要重新登录" in err_body or "account_unavailable" in err_body)):
                print("[AIStudio] 流式请求检测到 Google 凭证失效，正在自动从 Cookie Hub 同步并重试...", flush=True)
                try:
                    self.sync_cookies_from_hub()
                    time.sleep(1)
                    retry_req = self._build_request(model, messages or [], True)
                    retry_gen = self._stream_generator(retry_req, model=model, messages=messages, timeout=timeout, _retry_auth=False)
                    for chunk in retry_gen:
                        yield chunk
                    return
                except Exception as sync_err:
                    print(f"[AIStudio] 流式凭证自愈重试失败: {sync_err}", flush=True)
            yield f"data: {json.dumps({'error': f'HTTP {he.code}: {err_body}'})}\n\n"
            return
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        buffer = b""
        try:
            while True:
                chunk = resp.read1(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line_bytes, buffer = buffer.split(b"\n", 1)
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    yield f"{line}\n\n"
        finally:
            resp.close()


# 单例实例
aistudio_service = AIStudioService()
