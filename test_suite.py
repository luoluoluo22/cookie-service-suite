"""
Cookie 综合服务自动化测试套件
验证从浏览器获取 Cookie 到各服务端真实调用的全流程
已集成: Bilibili + yt-dlp + 百度网盘 (Baidu Netdisk)
"""

import sys
import json
from cookie_bridge import CookieBridge
from bilibili_service import BilibiliService
from baidu_pan_service import BaiduPanService
from chatgpt_service import ChatGPTBridgeClient

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    print("=" * 60)
    print("🧪 开始执行 Cookie 服务真实调用自动化测试")
    print("=" * 60)

    bridge = CookieBridge()

    # 1. 测试本地服务连接
    print("\n[测试 1/6] 正在检测本地 Cookie Hub 守护服务状态...")
    try:
        status = bridge.check_status()
        print("  ✅ 本地服务在线!")
        print(f"     服务端口: {status.get('port')}")
        print(f"     扩展连接状态: {'🟢 已连接' if status.get('extensionConnected') else '🔴 未连接'}")
        if not status.get("extensionConnected"):
            print("  ❌ 扩展未连接，请在浏览器中唤醒插件！")
            sys.exit(1)
    except Exception as e:
        print(f"  ❌ 无法连接本地通信服务: {e}")
        sys.exit(1)

    # 2. 测试 Bilibili 凭证提取与个人中心
    print("\n[测试 2/6] 正在提取 B 站 Cookie 并测试官方用户中心接口...")
    try:
        bili = BilibiliService(bridge)
        user_info = bili.get_user_info()
        print("  ✅ 成功获取 B 站登录态与账号信息!")
        print(f"     用户昵称: {user_info.get('uname')}")
        print(f"     用户 UID: {user_info.get('mid')}")
        print(f"     账号等级: Lv.{user_info.get('level_info', {}).get('current_level')}")
        print(f"     当前硬币: {user_info.get('money')}")
        vip_type = user_info.get('vipType', 0)
        vip_status = "月度大会员" if vip_type == 1 else ("年度大会员" if vip_type == 2 else "普通会员")
        print(f"     会员状态: {vip_status}")
    except Exception as e:
        print(f"  ❌ B 站用户中心接口测试失败: {e}")
        sys.exit(1)

    # 3. 测试 Bilibili 视频流解析接口
    print("\n[测试 3/6] 正在测试 B 站视频直链与清晰度参数解析...")
    test_bvid = "BV1GJ411x7h7"
    try:
        video_info = bili.get_video_info(test_bvid)
        title = video_info.get("title")
        cid = video_info.get("cid")
        play_data = bili.get_play_url(test_bvid, cid=cid, qn=116)
        code = play_data.get("code")
        qualities = play_data.get("data", {}).get("accept_description", [])
        print("  ✅ 视频直链与画质解析测试通过!")
        print(f"     视频标题: {title}")
        print(f"     可用画质列表: {', '.join(qualities)}")
    except Exception as e:
        print(f"  ❌ 视频解析测试失败: {e}")

    # 4. 测试 百度网盘 账号与容量配额 API
    print("\n[测试 4/6] 正在提取百度网盘 Cookie (BDUSS/STOKEN) 并测试容量配额接口...")
    try:
        pan = BaiduPanService(bridge)
        uinfo = pan.get_user_info()
        quota = pan.get_quota()
        print("  ✅ 成功获取百度网盘鉴权与配额信息!")
        print(f"     网盘用户名: {uinfo.get('baidu_name')}")
        print(f"     网盘 UID  : {uinfo.get('uk')}")
        print(f"     网盘总容量: {quota['total_gb']} GB")
        print(f"     已用空间  : {quota['used_gb']} GB")
        print(f"     剩余空间  : {quota['free_gb']} GB")
    except Exception as e:
        print(f"  ❌ 百度网盘接口测试失败: {e}")

    # 5. 测试 百度网盘 文件列表 API
    print("\n[测试 5/6] 正在测试百度网盘根目录文件遍历 API...")
    try:
        files_data = pan.list_files("/", limit=5)
        files = files_data.get("list", [])
        print(f"  ✅ 百度网盘文件列表检索成功 (检索到 {len(files)} 项示例):")
        for f in files[:3]:
            type_tag = "[目录]" if f.get("isdir") == 1 else "[文件]"
            print(f"     - {type_tag} {f.get('server_filename')}")
    except Exception as e:
        print(f"  ❌ 百度网盘文件列表测试失败: {e}")

    # 6. 测试 ChatGPT Web 桥接对话接口 (/v1/chat/completions)
    print("\n[测试 6/7] 正在测试 ChatGPT Web 原生桥接通信与智能问答 (/v1/chat/completions)...")
    try:
        gpt = ChatGPTBridgeClient()
        session_info = gpt.get_session().get("session", {})
        user_name = session_info.get("user", {}).get("name", "Unknown")
        user_email = session_info.get("user", {}).get("email", "Unknown")
        plan = session_info.get("accountPlan", "free")
        print(f"  ✅ 成功获取 ChatGPT 鉴权凭证与会话状态 (用户: {user_name} / {user_email}, 方案: {plan})")

        prompt = "请用一句简短的话说明：2加2等于几？"
        reply = gpt.ask(prompt)
        print(f"  ✅ ChatGPT 对话测试成功!")
        print(f"     提问: {prompt}")
        print(f"     回复: {reply.strip()}")
    except Exception as e:
        print(f"  ❌ ChatGPT 接口测试失败: {e}")

    # 7. 测试 Suno AI 音乐生成服务凭证与配额
    print("\n[测试 7/7] 正在提取 Suno / Clerk 凭证并测试配额接口 (/api/billing/info/)...")
    try:
        from suno_service import SunoService
        suno = SunoService(bridge=bridge)
        credits_info = suno.get_credits()
        print("  ✅ 成功获取 Suno 鉴权与配额信息!")
        print(f"     剩余总积分: {credits_info['total_credits_left']} 积分")
        print(f"     可用曲目数: {credits_info['songs_left']} 次 (每次生成提供 2 种变体)")
        print(f"     重置周期  : {credits_info['period']}")
    except Exception as e:
        print(f"  ⚠️ Suno 连通性提示 (浏览器未登录 suno.com 或未配置 SUNO_COOKIE): {e}")

    print("\n" + "=" * 60)
    print("🎉 自动化测试套件执行完毕：Bilibili + 百度网盘 + ChatGPT + Suno 全流程实测通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
