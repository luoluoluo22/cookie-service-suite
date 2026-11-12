#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Udio 音乐生成命令行交互工具 (udio_cli.py)
"""
import os
import sys
import argparse
from udio_service import UdioService, DOWNLOAD_DIR

def main():
    parser = argparse.ArgumentParser(description="Udio AI 音乐生成 CLI")
    parser.add_argument("-p", "--prompt", type=str, help="音乐风格/场景描述词")
    parser.add_argument("-i", "--instrumental", action="store_true", default=True, help="是否纯伴奏模式 (默认开启)")
    parser.add_argument("-l", "--lyrics", type=str, default="", help="自定义歌词 (伴奏模式下忽略)")
    parser.add_argument("-c", "--check", action="store_true", help="检查登录状态与账户额度")
    args = parser.parse_args()

    service = UdioService()

    if args.check or not args.prompt:
        print("\n🔍 正在检查 Udio 账号鉴权状态...")
        auth = service.check_auth()
        if auth.get("authenticated"):
            user = auth.get("user", {})
            print("🟢 Udio 登录态有效！")
            print(f"👤 用户ID: {user.get('id', 'N/A')}")
            print(f"📧 邮箱: {user.get('email', 'N/A')}")
        else:
            print("🔴 当前尚未检测到有效 Udio 官方登录态！")
            print(f"原因: {auth.get('error')}")
            print("💡 请在已打开的 Chrome / Edge 浏览器中访问官方网站: https://www.udio.com 并完成登录。")
            print("   登录后重新运行此脚本，系统将自动通过 Cookie Hub 提取登录凭据。")
        if not args.prompt:
            return

    print(f"\n🚀 正在向 Udio 提交生成任务...")
    print(f"🎵 Prompt: {args.prompt}")
    print(f"🎼 纯伴奏模式: {args.instrumental}")

    try:
        res = service.create_music(
            prompt=args.prompt,
            is_instrumental=args.instrumental,
            lyrics=args.lyrics
        )
        print("✅ 任务提交成功！正在等待音频渲染...")
        tracks = service.wait_for_tracks(progress_cb=print)
        for t in tracks:
            print(f"\n📥 正在下载: {t.get('title', 'track')}")
            path = service.download_track(t)
            print(f"🎉 已保存到本地: {path}")
    except Exception as e:
        print(f"❌ 生成失败: {e}")

if __name__ == "__main__":
    main()
