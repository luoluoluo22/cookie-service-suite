#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
百度网盘命令行工具 (基于浏览器实时 Cookie)
用法:
  python run_baidu_cli.py user
  python run_baidu_cli.py quota
  python run_baidu_cli.py list [/目录路径]
"""

import sys
from baidu_pan_service import BaiduPanService

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    if len(sys.argv) < 2:
        print("📌 用法:")
        print("  python run_baidu_cli.py user          # 获取网盘账号与会员状态")
        print("  python run_baidu_cli.py quota         # 查看网盘总容量与已用空间")
        print("  python run_baidu_cli.py list [/path]  # 查看网盘目录文件列表")
        return

    cmd = sys.argv[1].lower()
    pan = BaiduPanService()

    if cmd == "user":
        print("🔍 正在通过浏览器 Cookie 获取百度网盘用户信息...")
        data = pan.get_user_info()
        vip_type = data.get("vip_type", 0)
        vip_label = "超级会员 (SVIP)" if vip_type == 2 else ("普通会员 (VIP)" if vip_type == 1 else "普通用户")
        print(f"👤 网盘用户名: {data.get('baidu_name')}")
        print(f"⭐ 账号类型  : {vip_label}")
        print(f"🆔 用户 UID  : {data.get('uk')}")

    elif cmd == "quota":
        print("🔍 正在查询网盘容量配额...")
        q = pan.get_quota()
        print(f"💾 总容量  : {q['total_gb']} GB")
        print(f"📊 已使用  : {q['used_gb']} GB")
        print(f"🟢 剩余空间: {q['free_gb']} GB")

    elif cmd == "list":
        dir_path = sys.argv[2] if len(sys.argv) > 2 else "/"
        print(f"🔍 正在列出目录 [{dir_path}] 文件...")
        res = pan.list_files(dir_path)
        files = res.get("list", [])
        if not files:
            print("📭 该目录下暂无文件或文件夹。")
        else:
            print(f"📂 检索到 {len(files)} 项内容:")
            for item in files:
                is_dir = "📁 [目录]" if item.get("isdir") == 1 else "📄 [文件]"
                size_mb = round(item.get("size", 0) / (1024 * 1024), 2)
                size_str = f"({size_mb} MB)" if item.get("isdir") == 0 else ""
                print(f"   {is_dir} {item.get('server_filename')} {size_str}")

    else:
        print(f"未知指令: {cmd}")


if __name__ == "__main__":
    main()
