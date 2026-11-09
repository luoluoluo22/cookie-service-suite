"""
Cookie Service Suite - Gemini 20+ Comprehensive Test Suite
测试至少 20 次真实请求，覆盖所有 4 个账号、不同模型与不同推理级别。
"""

import time
import json
import urllib.request
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://127.0.0.1:18800"
DB_PATH = "candidate_repos/gemini-web2api-go/gemini_pool.db"

TEST_CASES = [
    # 批次 1: 3.5-flash-lite 快速验证四账号轮转 (4次)
    {"model": "gemini-3.5-flash-lite", "prompt": "1+1等于几？只回答数字", "reasoning": "off"},
    {"model": "gemini-3.5-flash-lite", "prompt": "中国的首都是哪里？只回答城市名", "reasoning": "off"},
    {"model": "gemini-3.5-flash-lite", "prompt": "水的化学式是什么？只回答化学式", "reasoning": "off"},
    {"model": "gemini-3.5-flash-lite", "prompt": "光速大约是多少公里每秒？用一句话回答", "reasoning": "off"},

    # 批次 2: 3.5-flash-lite 带有 medium/high 推理级别 (4次)
    {"model": "gemini-3.5-flash-lite", "prompt": "简述牛顿第一定律的核心概念", "reasoning": "medium"},
    {"model": "gemini-3.5-flash-lite", "prompt": "为什么天空是蓝色的？用简短一句话解释瑞利散射", "reasoning": "medium"},
    {"model": "gemini-3.5-flash-lite", "prompt": "用一句话解释什么是快速排序算法", "reasoning": "high"},
    {"model": "gemini-3.5-flash-lite", "prompt": "请用一句话解释摩尔定律", "reasoning": "high"},

    # 批次 3: 3.1-pro 验证高级模型 (4次)
    {"model": "gemini-3.1-pro", "prompt": "写一首五言绝句关于春雨", "reasoning": "off"},
    {"model": "gemini-3.1-pro", "prompt": "用一句话总结莎士比亚《哈姆雷特》的核心主题", "reasoning": "off"},
    {"model": "gemini-3.1-pro", "prompt": "用两句话解释量子比特与经典比特的区别", "reasoning": "medium"},
    {"model": "gemini-3.1-pro", "prompt": "简述Python中生成器和列表推导式的区别", "reasoning": "off"},

    # 批次 4: 3.6-flash 验证多账号并发与轮换 (4次)
    {"model": "gemini-3.6-flash", "prompt": "写一句励志格言，不超过15个字", "reasoning": "off"},
    {"model": "gemini-3.6-flash", "prompt": "用一句话解释什么是区块链", "reasoning": "off"},
    {"model": "gemini-3.6-flash", "prompt": "什么是光合作用？请用一句话总结", "reasoning": "off"},
    {"model": "gemini-3.6-flash", "prompt": "太阳系最大的行星是哪一颗？", "reasoning": "off"},

    # 批次 5: 3.8-flash & 4-argon 深度验证 (4次)
    {"model": "gemini-3.8-flash", "prompt": "写一首七言绝句关于秋风", "reasoning": "off"},
    {"model": "gemini-4-argon", "prompt": "用一句话描述人工智能的定义", "reasoning": "off"},
    {"model": "gemini-3.8-flash", "prompt": "用一句话赞美清晨的阳光", "reasoning": "off"},
    {"model": "gemini-4-argon", "prompt": "解释什么是熵，用通俗语言说一句话", "reasoning": "off"},

    # 额外补充 2 次边界测试 (共计 22 次)
    {"model": "gemini-3.5-flash-lite", "prompt": "输出三个英文单词表示高兴", "reasoning": "off"},
    {"model": "gemini-3.5-flash-lite", "prompt": "请输出斐波那契数列前五项", "reasoning": "off"},
]

def run_tests():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    results = []
    
    print(f"==================================================")
    print(f"🚀 开始执行 Gemini 多模型多账号 22 次全链路自动化压测")
    print(f"==================================================")
    
    total = len(TEST_CASES)
    success_count = 0
    fail_count = 0
    
    for idx, tc in enumerate(TEST_CASES, 1):
        payload = {
            "prompt": tc["prompt"],
            "model": tc["model"],
            "reasoning_level": tc["reasoning"],
            "timeout": 360,
        }
        print(f"\n[{idx}/{total}] 测试请求: 模型={tc['model']} | 推理={tc['reasoning']}")
        print(f"      提示词: {tc['prompt'][:40]}...")
        
        req = urllib.request.Request(
            f"{BASE_URL}/api/gemini/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        t0 = time.time()
        try:
            with opener.open(req, timeout=400) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            
            if data.get("success") and data.get("reply"):
                success_count += 1
                reply_snip = data.get("reply").strip().replace("\n", " ")[:60]
                print(f"      ✅ 成功! 耗时: {elapsed:.2f}s | 命中账号: {data.get('account_label')} (authuser={data.get('authuser')})")
                print(f"      💬 回复: {reply_snip}...")
                results.append({
                    "index": idx,
                    "model": tc["model"],
                    "reasoning": tc["reasoning"],
                    "prompt": tc["prompt"],
                    "success": True,
                    "elapsed_sec": round(elapsed, 2),
                    "account": data.get("account_label"),
                    "authuser": data.get("authuser"),
                    "reply_len": len(data.get("reply", "")),
                    "reply_snippet": reply_snip,
                })
            else:
                fail_count += 1
                print(f"      ❌ 失败 (返回数据异常): {data}")
                results.append({
                    "index": idx,
                    "model": tc["model"],
                    "reasoning": tc["reasoning"],
                    "success": False,
                    "error": str(data),
                })
        except Exception as e:
            elapsed = time.time() - t0
            fail_count += 1
            print(f"      ❌ 请求异常! 耗时: {elapsed:.2f}s | 错误: {e}")
            results.append({
                "index": idx,
                "model": tc["model"],
                "reasoning": tc["reasoning"],
                "success": False,
                "elapsed_sec": round(elapsed, 2),
                "error": str(e),
            })
            
        # 适当缓冲 1 秒，保持健康调度节奏
        time.sleep(1.0)

    print("\n" + "=" * 50)
    print("📊 测试套件运行完毕！统计结果如下：")
    print(f"   总计测试: {total} 次")
    print(f"   成功次数: {success_count} 次")
    print(f"   失败次数: {fail_count} 次")
    print(f"   整体成功率: {(success_count / total) * 100:.1f}%")
    print("=" * 50)
    
    with open("test_results_22.json", "w", encoding="utf-8") as f:
        json.dump({
            "total": total,
            "success_count": success_count,
            "fail_count": fail_count,
            "success_rate": f"{(success_count / total) * 100:.1f}%",
            "results": results
        }, f, indent=2, ensure_ascii=False)
        
    return success_count, fail_count

if __name__ == "__main__":
    run_tests()
