# -*- coding: utf-8 -*-
"""
ChatGPT Web 项目自动化监督执行脚本
==================================
监听当前 ChatGPT 网页任务进展，每隔约 5 分钟观察一次最新回复：
- 若 AI 仍在生成中，则静候其完成；
- 若 AI 生成结束且判断项目尚未全部完成，自动在页面输入并发送「继续」；
- 若 AI 明确汇报项目已全部完成，则停止追发「继续」，并输出完成总结。
"""

import sys
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime

TARGET_TAB_ID = 39180255
BRIDGE_URL = "http://127.0.0.1:18888"
CHECK_INTERVAL_SECONDS = 300  # 5 分钟

# 强制本地 127.0.0.1 直连
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def inspect_tab(tab_id=TARGET_TAB_ID):
    """查询指定 ChatGPT 标签页的当前状态与最新回复"""
    url = f"{BRIDGE_URL}/chatgpt/inspect?tabId={tab_id}"
    req = urllib.request.Request(url)
    try:
        with _opener.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e), "isBusy": False}

def send_prompt(prompt="继续", tab_id=TARGET_TAB_ID):
    """向目标标签页发送指令"""
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"{BRIDGE_URL}/chatgpt/send_prompt?tabId={tab_id}&prompt={encoded_prompt}"
    req = urllib.request.Request(url)
    try:
        with _opener.open(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

def is_project_completed(text):
    """判断项目是否已经全部完成"""
    if not text:
        return False
    lower = text.lower()
    
    # 明确完成标志
    finish_keywords = [
        "全部完成", "项目已完成", "所有任务已完成", "全部封装完毕", 
        "所有功能均已就绪", "全部核验通过，已交付", "没有其他待办事项",
        "已经全部实现完毕", "流程已经全部打通"
    ]
    # 进行中/未完成标志
    in_progress_keywords = [
        "正在", "下一步", "准备开始", "还差", "未完成", "待办", 
        "我将继续", "正在进行", "后续", "请回复继续", "继续推进"
    ]
    
    for kw in finish_keywords:
        if kw in text:
            # 确认没有强烈的进行中信号
            has_pending = any(p in text[-200:] for p in ["正在", "下一步", "接下来"])
            if not has_pending:
                return True
                
    return False

def run_single_check():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{now_str}] 🔍 正在观察当前 ChatGPT 任务进展 (Tab {TARGET_TAB_ID})...")
    data = inspect_tab()
    
    if "error" in data:
        print(f"  ⚠️ 连接异常: {data['error']}")
        return False, "error"
        
    is_busy = data.get("isBusy", False)
    title = data.get("title", "")
    latest = data.get("latestMarkdown", "").strip()
    
    print(f"  📌 标签页标题: {title}")
    print(f"  ⚡ 生成状态: {'🔥 正在生成中 (Busy)...' if is_busy else '💤 已空闲/等待输入'}")
    
    if latest:
        preview = latest[-300:] if len(latest) > 300 else latest
        print(f"  📝 最新回复片段 (尾部):\n  " + "-" * 40)
        for line in preview.split("\n"):
            print(f"  | {line}")
        print("  " + "-" * 40)
    else:
        print("  📝 暂无最新文本内容")
        
    if is_busy:
        print("  ⏳ AI 仍在深度生成中，本次不干预，待下一轮观察。")
        return False, "busy"
        
    completed = is_project_completed(latest)
    if completed:
        print("  🎉 判断结果: 项目核心任务已全部宣布完成！不发送「继续」。")
        return True, "completed"
    else:
        print("  🔄 判断结果: 项目尚未全部结束，正在向 ChatGPT 发送指令:「继续」...")
        res = send_prompt("继续")
        if res.get("success"):
            print("  ✅ 已成功发送「继续」，AI 将继续执行下一阶段任务！")
        else:
            print(f"  ⚠️ 发送反馈: {res}")
        return False, "continued"

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print("🤖 ChatGPT Web 自动化巡检守护进程已启动")
    print(f"🎯 监听目标: Tab {TARGET_TAB_ID} (每 5 分钟巡检一次)")
    print("=" * 60)
    
    # 第一次立即检查
    completed, status = run_single_check()
    if completed:
        print("\n✅ 项目已圆满完成，巡检结束。")
        return
        
    # 定时循环
    while True:
        print(f"\n⏱️ 等待 {CHECK_INTERVAL_SECONDS} 秒 (5 分钟) 后进行下一次巡检...")
        time.sleep(CHECK_INTERVAL_SECONDS)
        completed, status = run_single_check()
        if completed:
            print("\n🎉 项目已圆满完成，守护进程自动退出！")
            break

if __name__ == "__main__":
    main()
