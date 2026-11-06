#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化测试脚本：验证逆向 Gemini 与 ChatGPT (GPT) 模型的真实推理响应与内容质量
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import urllib.request
import json
import time

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def test_gemini():
    print("=" * 60)
    print("🤖 [测试 1/4] Gemini 专属接口 (/api/gemini/chat)")
    print("=" * 60)
    
    question = "请用中文回答：唐诗《静夜思》的作者是谁？生活在哪个朝代？（严格在一句话内回答完毕）"
    print(f"提问内容: {question}")
    
    payload = json.dumps({
        "prompt": question,
        "model": "gemini-3.5-flash-lite",
        "reasoning_level": "off",
        "timeout": 30
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://127.0.0.1:18800/api/gemini/chat",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    t0 = time.time()
    try:
        with opener.open(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = round(time.time() - t0, 2)
            print(f"🟢 接口调用成功! HTTP {resp.status} (耗时: {elapsed}s)")
            print(f"  - 调度账号: {data.get('account_label')} (authuser={data.get('authuser')})")
            print(f"  - 服务端耗时: {data.get('latency_ms')} ms")
            print(f"  - 使用模型: {data.get('model')}")
            print(f"  - 模型回答: {data.get('reply')}")
            
            reply = data.get("reply", "")
            if "李白" in reply and "唐" in reply:
                print("  ✅ 内容校验: 通过 (准确识别出李白与唐代)")
            else:
                print("  ⚠️ 内容校验: 未包含预期核心关键词")
    except Exception as e:
        print(f"🔴 Gemini 专属接口调用失败: {e}")

def test_gemini_openai_compat():
    print("\n" + "=" * 60)
    print("🌐 [测试 2/4] Gemini OpenAI 标准兼容接口 (/v1/chat/completions)")
    print("=" * 60)
    
    question = "计算 25 * 4 等于多少？只输出最终数字结果。"
    print(f"提问内容: {question}")
    
    payload = json.dumps({
        "model": "gemini-3.5-flash-lite",
        "messages": [{"role": "user", "content": question}]
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://127.0.0.1:18800/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    t0 = time.time()
    try:
        with opener.open(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = round(time.time() - t0, 2)
            reply = data["choices"][0]["message"]["content"].strip()
            print(f"🟢 OpenAI 兼容接口成功! HTTP {resp.status} (耗时: {elapsed}s)")
            print(f"  - ID: {data.get('id')}")
            print(f"  - 模型回答: {reply}")
            if "100" in reply:
                print("  ✅ 内容校验: 通过 (计算结果正确为 100)")
            else:
                print("  ⚠️ 内容校验: 结果不符合预期")
    except Exception as e:
        print(f"🔴 Gemini OpenAI 兼容接口调用失败: {e}")

def test_chatgpt():
    print("\n" + "=" * 60)
    print("⚡ [测试 3/4] ChatGPT 逆向专属接口 (/api/chatgpt/chat)")
    print("=" * 60)
    
    question = "请用一句话回答：中国空间站的中文名称是什么？"
    print(f"提问内容: {question}")
    
    payload = json.dumps({
        "prompt": question,
        "model": "auto",
        "timeout": 30
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://127.0.0.1:18800/api/chatgpt/chat",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    t0 = time.time()
    try:
        with opener.open(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = round(time.time() - t0, 2)
            print(f"🟢 ChatGPT 接口成功! HTTP {resp.status} (耗时: {elapsed}s)")
            print(f"  - 响应模式: {data.get('mode')}")
            reply = data.get("reply", "")
            print(f"  - 模型回答: {reply}")
            if "天宫" in reply:
                print("  ✅ 内容校验: 通过 (准确识别出天宫空间站)")
            else:
                print("  ⚠️ 内容校验: 未包含预期核心关键词")
    except Exception as e:
        print(f"🔴 ChatGPT 接口调用失败: {e}")

def test_chatgpt_openai_compat():
    print("\n" + "=" * 60)
    print("⚡ [测试 4/4] ChatGPT OpenAI 标准兼容接口 (/v1/chat/completions)")
    print("=" * 60)
    
    question = "地球的卫星是什么天体？请只回答两个字。"
    print(f"提问内容: {question}")
    
    payload = json.dumps({
        "model": "auto",
        "messages": [{"role": "user", "content": question}]
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://127.0.0.1:18800/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    t0 = time.time()
    try:
        with opener.open(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = round(time.time() - t0, 2)
            reply = data["choices"][0]["message"]["content"].strip()
            print(f"🟢 ChatGPT OpenAI 兼容接口成功! HTTP {resp.status} (耗时: {elapsed}s)")
            print(f"  - ID: {data.get('id')}")
            print(f"  - 模型回答: {reply}")
            if "月球" in reply or "月亮" in reply:
                print("  ✅ 内容校验: 通过 (回答正确)")
            else:
                print("  ⚠️ 内容校验: 结果不符合预期")
    except Exception as e:
        print(f"🔴 ChatGPT OpenAI 兼容接口调用失败: {e}")

if __name__ == "__main__":
    test_gemini()
    test_gemini_openai_compat()
    test_chatgpt()
    test_chatgpt_openai_compat()
