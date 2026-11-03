#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bilibili 命令行工具 (基于浏览器实时 Cookie)
用法:
  python run_bili_cli.py user
  python run_bili_cli.py video BV1GJ411x7h7
  python run_bili_cli.py download BV1GJ411x7h7
"""

import sys
import json
from bilibili_service import BilibiliService

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    if len(sys.argv) < 2:
        print("📌 用法:")
        print("  python run_bili_cli.py user                  # 查看当前登录账号信息")
        print("  python run_bili_cli.py video <BV号>          # 查看视频信息与可用画质")
        print("  python run_bili_cli.py download <BV号/链接>  # 高清下载视频")
        return

    cmd = sys.argv[1].lower()
    bili = BilibiliService()

    if cmd == "user":
        print("🔍 正在通过浏览器 Cookie 获取 B 站个人中心数据...")
        data = bili.get_user_info()
        print(f"👤 用户昵称: {data.get('uname')}")
        print(f"🆔 用户 UID : {data.get('mid')}")
        print(f"⭐ 账号等级: Lv.{data.get('level_info', {}).get('current_level')}")
        print(f"🪙 硬币余额: {data.get('money')}")
        vip_type = data.get('vipType', 0)
        vip_label = "月度大会员" if vip_type == 1 else ("年度大会员" if vip_type == 2 else "普通用户")
        print(f"👑 会员状态: {vip_label}")

    elif cmd == "video":
        if len(sys.argv) < 3:
            print("❌ 请提供视频 BV 号，例如: python run_bili_cli.py video BV1GJ411x7h7")
            return
        bvid = sys.argv[2]
        print(f"🔍 正在查询视频 {bvid} 信息...")
        info = bili.get_video_info(bvid)
        print(f"🎬 标题: {info.get('title')}")
        print(f"👤 UP主: {info.get('owner', {}).get('name')}")
        print(f"👀 播放: {info.get('stat', {}).get('view')}")
        print(f"👍 点赞: {info.get('stat', {}).get('like')}")
        print(f"🪙 投币: {info.get('stat', {}).get('coin')}")

        play = bili.get_play_url(bvid, info.get("cid"))
        qualities = play.get("data", {}).get("accept_description", [])
        print(f"📺 提取到大会员最高画质选项: {', '.join(qualities)}")

    elif cmd == "download":
        if len(sys.argv) < 3:
            print("❌ 请提供视频 BV 号或完整链接")
            return
        target = sys.argv[2]
        if not target.startswith("http"):
            target = f"https://www.bilibili.com/video/{target}"
        bili.download_video_hd(target, "./downloads")
        print("✅ 视频下载完成，保存在 ./downloads 目录中！")

    else:
        print(f"未知子命令: {cmd}")


if __name__ == "__main__":
    main()
