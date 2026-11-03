# -*- coding: utf-8 -*-
"""
ChatGPT Web In-Page Bridge Client
=================================
通过本地 Cookie Hub 桥接服务与浏览器已登录 ChatGPT Web 进行免封禁通信。
完美绕过 Cloudflare Turnstile 挑战、Arkose 验证码及 TLS 指纹风控，
并对外暴露标准的 OpenAI /v1/chat/completions 兼容接口。
"""

import urllib.request
import urllib.parse
import json
import sys

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

    def ask(self, prompt: str, model: str = "chatgpt-web") -> str:
        """发送单句提示词并等待 ChatGPT 回复"""
        url = f"{self.base_url}/v1/chat/completions"
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

    def chat(self, messages: list, model: str = "chatgpt-web") -> dict:
        """标准 OpenAI 格式调用"""
        url = f"{self.base_url}/v1/chat/completions"
        payload = json.dumps({
            "model": model,
            "messages": messages
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    client = ChatGPTBridgeClient()

    print("🤖 正在连接 Cookie Hub ChatGPT 本地桥接...")
    health = client.check_health()
    if not health.get("extensionConnected"):
        print("❌ 浏览器扩展未在线，请确保 Ego / Chrome 浏览器已打开。")
        sys.exit(1)

    print("✅ 桥接服务在线，正在拉取 ChatGPT 当前登录会话...")
    session_data = client.get_session()
    session = session_data.get("session", {})
    user = session.get("user", {})
    print(f"👤 当前登录用户: {user.get('name')} ({user.get('email')})")
    print(f"⭐ 账户类型: {session.get('accountPlan', 'free')} (expires: {session.get('expires', 'N/A')})")

    test_prompt = "请用幽默风趣的一句话自我介绍，并确认你已连接成功！"
    print(f"\n💬 发送测试对话: '{test_prompt}'")
    reply = client.ask(test_prompt)
    print("\n💡 ChatGPT 回复内容:")
    print("-" * 50)
    print(reply)
    print("-" * 50)
