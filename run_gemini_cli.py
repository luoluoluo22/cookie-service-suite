#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Gemini 命令行工具 (基于浏览器实时 Cookie 与多账号池)
用法:
  python run_gemini_cli.py list            # 查看已接入的 4 个 Google 账号状态
  python run_gemini_cli.py ask "你的问题"  # 提问（自动在 4 个账号间负载均衡轮转）
  python run_gemini_cli.py start           # 后台启动多账号 OpenAI 兼容服务 (18083)
  python run_gemini_cli.py stop            # 停止多账号后台服务
  python run_gemini_cli.py quota           # 查询 Gemini 额度信息
"""

import sys
import json
from gemini_service import MultiAccountGeminiPool, GeminiService

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    if len(sys.argv) < 2:
        print("📌 用法:")
        print("  python run_gemini_cli.py list            # 查看已接入的 4 个 Google 账号状态")
        print("  python run_gemini_cli.py ask <问题>      # 提问（自动在 4 个账号间轮转）")
        print("  python run_gemini_cli.py quota           # 查看当前账号配额与套餐等级")
        print("  python run_gemini_cli.py start           # 启动多账号统一 API 服务 (端口 18083)")
        print("  python run_gemini_cli.py stop            # 停止多账号统一 API 服务")
        return

    cmd = sys.argv[1].lower()
    pool = MultiAccountGeminiPool(port=18083, account_count=4)

    if cmd == "list":
        print("🔍 正在检查 Google 多账号池配置...")
        pool.init_database()
        accounts = pool.list_accounts()
        print(f"📊 当前池中共接入 {len(accounts)} 个 Google 账号槽位:\n")
        print(f"{'序号':<6} {'标识':<24} {'路径前缀':<32} {'状态':<10} {'失败数':<8}")
        print("-" * 80)
        for a in accounts:
            print(
                f"u/{a['auth_user']:<4} {a['label']:<24} {a['url_prefix']:<32} {a['status']:<10} {a['fail_count']:<8}"
            )
        print("-" * 80)
        print(f"服务运行状态: {'🟢 正在运行 (http://127.0.0.1:18083)' if pool.is_running() else '⚪ 未运行'}")

    elif cmd == "ask":
        if len(sys.argv) < 3:
            print("❌ 请提供要提问的内容，例如: python run_gemini_cli.py ask '量子纠缠是什么？'")
            return
        prompt = sys.argv[2]
        print(f"🤖 正在向 Gemini 发起提问（自动选择最优可用账号）: '{prompt}'...")
        answer = pool.ask(prompt)
        print("\n💬 Gemini 回复:")
        print(answer)

    elif cmd == "quota":
        print("🔍 正在获取当前账号可用配额...")
        service = GeminiService()
        quotas = service.get_quota()
        print(json.dumps(quotas, indent=2, ensure_ascii=False))

    elif cmd == "start":
        print("🚀 正在启动 Gemini 多账号统一代理服务...")
        if pool.start():
            print(f"✅ 服务启动成功！监听端口: http://127.0.0.1:{pool.port}")
            print(f"🔑 OpenAI 兼容 API Key: {pool.api_key}")
            print(f"🌐 接口地址: http://127.0.0.1:{pool.port}/v1/chat/completions")
        else:
            print("❌ 服务启动失败，请查看 candidate_repos/gemini-web2api-go/gemini_pool.log 日志。")

    elif cmd == "stop":
        print("🛑 正在停止 Gemini 多账号统一代理服务...")
        pool.stop()
        print("✅ 服务已停止。")

    else:
        print(f"❌ 未知命令: {cmd}")


if __name__ == "__main__":
    main()
