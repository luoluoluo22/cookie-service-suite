# -*- coding: utf-8 -*-
"""
ChatGPT Web In-Page Bridge Client
=================================
通过本地 Cookie Hub 桥接服务与浏览器已登录 ChatGPT Web 进行免封禁通信。
完美绕过 Cloudflare Turnstile 挑战、Arkose 验证码及 TLS 指纹风控，
并对外暴露标准的 OpenAI /v1/chat/completions 兼容接口（同时支持流式 SSE stream 与全量非流式返回）。
"""

import urllib.request
import urllib.parse
import json
import sys
from typing import Generator, Dict, Any, Union, List

DEFAULT_BRIDGE_URL = "http://127.0.0.1:18888"

class ChatGPTBridgeClient:
    def __init__(self, base_url: str = DEFAULT_BRIDGE_URL, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def check_health(self) -> dict:
        """检查本地桥接服务是否正常运行且扩展已连接"""
        url = f"{self.base_url}/status"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_session(self) -> dict:
        """获取浏览器中 ChatGPT 当前登录会话（包括 AccessToken、用户邮箱、Plus 会员状态）"""
        url = f"{self.base_url}/chatgpt/session"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_models(self) -> dict:
        """获取当前账号可用模型目录"""
        url = f"{self.base_url}/chatgpt/models"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
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
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
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
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
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


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    client = ChatGPTBridgeClient()

    print("🤖 正在连接 Cookie Hub ChatGPT 本地桥接...")
    try:
        health = client.check_health()
    except Exception as e:
        print(f"❌ 无法连接到桥接服务: {e}")
        sys.exit(1)

    if not health.get("extensionConnected"):
        print("❌ 浏览器扩展未在线，请在浏览器中确认 Cookie Hub 扩展已加载并启用。")
        sys.exit(1)

    print("✅ 桥接服务在线，正在拉取 ChatGPT 当前登录会话...")
    session_data = client.get_session()
    session = session_data.get("session", {})
    user = session.get("user", {})
    print(f"👤 当前登录用户: {user.get('name')} ({user.get('email')})")
    print(f"⭐ 账户类型: {session.get('accountPlan', 'free')} (expires: {session.get('expires', 'N/A')})")

    test_prompt = "请用幽默风趣的一句话自我介绍，并确认你已连接成功！"
    print(f"\n💬 发送测试流式对话 (stream=True): '{test_prompt}'\n" + "-" * 50)
    for delta in client.ask(test_prompt, stream=True):
        print(delta, end="", flush=True)
    print("\n" + "-" * 50)
