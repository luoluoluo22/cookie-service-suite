#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import io
import time
import json
import urllib.request

# Ensure UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def test_api_gemini_chat_stream():
    url = "http://127.0.0.1:18800/api/gemini/chat"
    req_data = {
        "prompt": "请用一句话告诉我：什么是量子纠缠？",
        "model": "gemini-3.5-flash-lite",
        "reasoning_level": "off",
        "stream": True,
        "timeout": 60
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(req_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    print("\n" + "="*60)
    print("【测试 1: 验证 /api/gemini/chat 默认实时流式输出】")
    print("="*60)
    t0 = time.time()
    ttfb = None
    chunks_received = 0
    full_text = []

    print(f"发送请求至 {url} (stream=True)...")
    try:
        with opener.open(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "")
            print(f"响应 Content-Type: {content_type}")
            assert "text/event-stream" in content_type, f"预期为 text/event-stream, 实际为 {content_type}"

            buffer = b""
            done = False
            while not done:
                chunk = resp.read1(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line_bytes, buffer = buffer.split(b"\n", 1)
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line or line.startswith("event:"):
                        continue
                    if ttfb is None:
                        ttfb = (time.time() - t0) * 1000
                        print(f"⚡ 首字毫秒级直出 (TTFB): {ttfb:.1f} ms")
                        print("实时打字流输出: ", end="", flush=True)

                    if line.startswith("data: "):
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            print("\n🏁 [流式传输结束标记 [DONE] 收到]")
                            done = True
                            break
                        try:
                            parsed = json.loads(payload)
                            delta = (parsed.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                     or parsed.get("delta", "") or parsed.get("text", "") or "")
                            if delta:
                                full_text.append(delta)
                                print(delta, end="", flush=True)
                                chunks_received += 1
                        except Exception:
                            pass
        total_ms = (time.time() - t0) * 1000
        print(f"\n✅ /api/gemini/chat 流式测试通过! 收到 {chunks_received} 个文本块 | 首字耗时: {ttfb:.1f}ms | 总耗时: {total_ms:.1f}ms")
        print(f"💬 完整输出文本: {''.join(full_text)}")
        return True
    except Exception as e:
        print(f"\n❌ /api/gemini/chat 流式测试异常: {e}")
        return False

def test_v1_openai_chat_stream():
    url = "http://127.0.0.1:18800/v1/chat/completions"
    req_data = {
        "model": "gemini-3.5-flash-lite",
        "messages": [{"role": "user", "content": "请用一句话告诉我：什么是光速？"}],
        "reasoning_level": "off",
        "stream": True
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(req_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    print("\n" + "="*60)
    print("【测试 2: 验证 /v1/chat/completions (OpenAI兼容规范) 实时流式输出】")
    print("="*60)
    t0 = time.time()
    ttfb = None
    chunks_received = 0
    full_text = []

    print(f"发送请求至 {url} (stream=True)...")
    try:
        with opener.open(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "")
            print(f"响应 Content-Type: {content_type}")
            assert "text/event-stream" in content_type, f"预期为 text/event-stream, 实际为 {content_type}"

            buffer = b""
            done = False
            while not done:
                chunk = resp.read1(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line_bytes, buffer = buffer.split(b"\n", 1)
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line or line.startswith("event:"):
                        continue
                    if ttfb is None:
                        ttfb = (time.time() - t0) * 1000
                        print(f"⚡ 首字毫秒级直出 (TTFB): {ttfb:.1f} ms")
                        print("实时打字流输出: ", end="", flush=True)

                    if line.startswith("data: "):
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            print("\n🏁 [流式传输结束标记 [DONE] 收到]")
                            done = True
                            break
                        try:
                            parsed = json.loads(payload)
                            delta = (parsed.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                     or parsed.get("delta", "") or parsed.get("text", "") or "")
                            if delta:
                                full_text.append(delta)
                                print(delta, end="", flush=True)
                                chunks_received += 1
                        except Exception:
                            pass
        total_ms = (time.time() - t0) * 1000
        print(f"\n✅ /v1/chat/completions 流式测试通过! 收到 {chunks_received} 个文本块 | 首字耗时: {ttfb:.1f}ms | 总耗时: {total_ms:.1f}ms")
        print(f"💬 完整输出文本: {''.join(full_text)}")
        return True
    except Exception as e:
        print(f"\n❌ /v1/chat/completions 流式测试异常: {e}")
        return False

if __name__ == "__main__":
    t1 = test_api_gemini_chat_stream()
    time.sleep(2)
    t2 = test_v1_openai_chat_stream()
    print("\n" + "="*60)
    print(f"综合测试结果: 测试1={'通过' if t1 else '失败'}, 测试2={'通过' if t2 else '失败'}")
    print("="*60)
