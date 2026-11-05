#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Suno AI 独立免服务命令行客户端 (Standalone Suno CLI)
=================================================
特点:
- ⚡ 零服务依赖：即便不启动本地 Cookie Hub (18888) 或 FastAPI 服务，也能直接独立运行
- 💾 自动持久化凭证：首次交互粘贴或配置后，自动存入本地安全缓存 (.suno_cookie)，后续永久免密调用
- 🛡️ TLS 指纹伪装：基于 curl_cffi 原生模拟 Edge 浏览器，完美突破 Cloudflare 拦截
- 🎵 功能全覆盖：查积分、查历史曲库、灵感生成、自定义歌词、纯伴奏模式、自动流式下载 MP3

常用命令示例:
  python suno_cli.py quota                          # 查询积分额度与可用曲目数
  python suno_cli.py gen "欢快的夏日海滩吉他流行乐"       # 灵感生成并自动下载 MP3
  python suno_cli.py custom "歌词正文" --tags "民谣, 治愈" # 自定义歌词模式
  python suno_cli.py lyrics "关于秋天与落叶的歌词"        # 单独让 AI 创作歌词
  python suno_cli.py feed                           # 查看历史曲目列表
  python suno_cli.py login                          # 交互式配置/更新 Suno Cookie
"""

import sys
import os
import argparse
import time

# 统一 Windows 终端 UTF-8 编码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from suno_service import SunoService, COOKIE_CACHE_FILE


def prompt_for_cookie() -> str:
    """引导用户在终端直接粘贴 Cookie 并自动持久化"""
    print("\n" + "=" * 65)
    print("🍪 [Suno 凭证提示] 插件已尝试自动唤醒，但检测到浏览器中可能尚未完成登录。")
    print("=" * 65)
    print("支持以下两种方式获取凭证：")
    print("  方式 1: 直接在打开的 Edge/Chrome 浏览器中登录 https://suno.com，插件将自动完成提取；")
    print("  方式 2: 或直接在下方粘贴含有 '__client' 字段的 Cookie 字符串（自动持久化保存）：")
    print("-" * 65 + "\n")

    try:
        cookie_input = input("👉 请直接粘贴 Cookie 字符串后按回车 (或在浏览器登录后重试): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n❌ 操作已取消。")
        sys.exit(1)

    if not cookie_input:
        print("❌ 输入为空，无法继续。")
        sys.exit(1)

    # 规范化清理
    if cookie_input.lower().startswith("cookie:"):
        cookie_input = cookie_input[7:].strip()

    SunoService.save_cookie_cache(cookie_input)
    print(f"✅ 凭证已成功保存至本地安全缓存: {COOKIE_CACHE_FILE}")
    return cookie_input


def ensure_service_ready(args) -> SunoService:
    """创建并保证 SunoService 拥有可用凭证"""
    manual_cookie = getattr(args, "cookie", None)
    proxy = getattr(args, "proxy", None)

    service = SunoService(cookie=manual_cookie, proxy=proxy)

    # 检查是否能够成功获取 Cookie
    try:
        service.get_raw_cookies()
    except Exception:
        # 降级：触发交互式粘贴引导
        if sys.stdin.isatty():
            new_cookie = prompt_for_cookie()
            service = SunoService(cookie=new_cookie, proxy=proxy)
        else:
            raise

    return service


def main():
    parser = argparse.ArgumentParser(
        description="Suno AI 独立免服务命令行客户端 (Standalone CLI - 支持离线与直接调用)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cookie", type=str, default=None, help="临时指定本次使用的 Cookie 字符串")
    parser.add_argument("--proxy", type=str, default=None, help="指定 HTTP/HTTPS 代理 (默认: http://127.0.0.1:7897)")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. 登录 / 设置 Cookie
    login_parser = subparsers.add_parser("login", help="交互式配置或更新本地 Suno Cookie 凭证")
    login_parser.add_argument("cookie_value", nargs="?", default=None, help="直接传入 Cookie 字符串 (可选)")

    # 2. 配额与积分查询
    subparsers.add_parser("quota", help="查询当前账号积分与剩余可用生成次数")
    subparsers.add_parser("credits", help="查询积分 (quota 别名)")

    # 3. 历史作品曲库
    feed_parser = subparsers.add_parser("feed", help="查看历史生成的音乐作品列表")
    feed_parser.add_argument("--page", type=int, default=1, help="页码 (默认: 1)")

    # 4. 灵感描述模式快速生成
    gen_parser = subparsers.add_parser("gen", help="描述模式快速生成音乐 (自动流式下载)")
    gen_parser.add_argument("prompt", type=str, help="音乐风格或情境描述文本")
    gen_parser.add_argument("--instrumental", action="store_true", help="纯伴奏模式 (无主唱人声)")
    gen_parser.add_argument("--model", type=str, default="chirp-v3-5", choices=["chirp-v3-5", "chirp-v4", "chirp-v3-0"], help="模型版本")
    gen_parser.add_argument("--out", type=str, default="./downloads/suno", help="音频保存目录")
    gen_parser.add_argument("--no-download", action="store_true", help="仅轮询生成结果，不自动下载 MP3 文件")

    # 5. 自定义歌词模式生成
    custom_parser = subparsers.add_parser("custom", help="自定义模式：指定歌词、风格标签与歌名")
    custom_parser.add_argument("prompt", type=str, help="歌词全文 (支持分段标签 如 [Verse] [Chorus])")
    custom_parser.add_argument("--tags", type=str, default="pop, acoustic guitar", help="风格标签 (如 'r&b, soulful, bpm 80')")
    custom_parser.add_argument("--title", type=str, default="My Custom Song", help="歌曲标题")
    custom_parser.add_argument("--instrumental", action="store_true", help="纯伴奏模式")
    custom_parser.add_argument("--model", type=str, default="chirp-v3-5", help="模型版本")
    custom_parser.add_argument("--out", type=str, default="./downloads/suno", help="音频保存目录")
    custom_parser.add_argument("--no-download", action="store_true", help="不自动下载 MP3 文件")

    # 6. 单独创作歌词
    lyrics_parser = subparsers.add_parser("lyrics", help="利用 Suno AI 单独创作歌词")
    lyrics_parser.add_argument("prompt", type=str, help="歌词灵感提示词")

    # 7. 下载单首歌曲
    dl_parser = subparsers.add_parser("download", help="通过音频直链或 Clip ID 下载歌曲 MP3")
    dl_parser.add_argument("target", type=str, help="音频直链 URL 或 歌曲 Clip ID")
    dl_parser.add_argument("--out", type=str, default="./downloads/suno", help="保存目录")

    # 8. 帮助说明
    help_parser = subparsers.add_parser("help", help="显示全局帮助说明或指定子命令的详细用法")
    help_parser.add_argument("subcmd", nargs="?", default=None, help="指定要查看帮助的子命令名称 (例如: gen, custom, feed, quota)")

    subparser_map = {
        "login": login_parser,
        "quota": subparsers.choices.get("quota"),
        "credits": subparsers.choices.get("credits"),
        "feed": feed_parser,
        "gen": gen_parser,
        "custom": custom_parser,
        "lyrics": lyrics_parser,
        "download": dl_parser,
        "help": help_parser,
    }

    args = parser.parse_args()

    # 处理无参数调用 或 help 子命令
    if not args.command or args.command.lower() == "help":
        target_subcmd = getattr(args, "subcmd", None)
        if target_subcmd and target_subcmd.lower() in subparser_map:
            sub = subparser_map[target_subcmd.lower()]
            if sub:
                sub.print_help()
                return

        parser.print_help()
        print("\n" + "=" * 65)
        print("💡 常用命令示例 (PowerShell / CMD 均可直接运行):")
        print("=" * 65)
        print("  1. 查询额度与可用次数:")
        print("     .\\suno_cli.ps1 quota")
        print("  2. 查看历史生成的曲库作品:")
        print("     .\\suno_cli.ps1 feed")
        print("  3. 灵感模式生成音乐 (自动下载 MP3 到本地):")
        print("     .\\suno_cli.ps1 gen \"一段欢快的夏日海滩吉他流行乐\"")
        print("  4. 纯伴奏模式 (无主唱人声):")
        print("     .\\suno_cli.ps1 gen \"雨夜咖啡厅爵士钢琴\" --instrumental")
        print("  5. 自定义歌词模式:")
        print("     .\\suno_cli.ps1 custom \"[Verse] 阳光洒在海平面 [Chorus] 我们奔向远方\" --tags \"民谣, 治愈\" --title \"夏日旅途\"")
        print("  6. 单独让 AI 创作歌词:")
        print("     .\\suno_cli.ps1 lyrics \"写一首关于赛博朋克都市与迷失夜行者的歌词\"")
        print("  7. 查看特定子命令的详细参数:")
        print("     .\\suno_cli.ps1 help gen")
        print("     .\\suno_cli.ps1 help custom")
        print("=" * 65)
        return

    cmd = args.command.lower()

    # 处理手动 login / set-cookie
    if cmd in ("login", "set-cookie"):
        cookie_val = args.cookie_value
        if not cookie_val:
            cookie_val = prompt_for_cookie()
        else:
            if cookie_val.lower().startswith("cookie:"):
                cookie_val = cookie_val[7:].strip()
            SunoService.save_cookie_cache(cookie_val)
            print(f"✅ 凭证已保存至本地安全缓存: {COOKIE_CACHE_FILE}")

        print("🔍 正在测试 Clerk 令牌兑换与 Suno 连通性...")
        try:
            srv = SunoService(cookie=cookie_val, proxy=args.proxy)
            res = srv.refresh_auth()
            quota = res.get("quota", {})
            print("🎉 凭证验证成功！Suno 账号信息如下:")
            print(f"  💰 剩余积分: {quota.get('total_credits_left')} (约可生成 {quota.get('songs_left')} 次)")
            print(f"  🔑 会话 ID:   {res.get('session_id')}")
            print(f"  🎫 JWT 预览:  {res.get('jwt_preview')}")
        except Exception as e:
            print(f"⚠️ 凭证测试提示: {e}")
        return

    # 针对其他命令，自动保证凭证可用
    try:
        service = ensure_service_ready(args)
    except Exception as e:
        print(f"❌ 客户端准备失败: {e}")
        return

    # 命令路由执行
    if cmd in ("quota", "credits"):
        print("🔍 正在查询当前 Suno 账户额度与积分...")
        try:
            q = service.get_credits()
            print("=" * 45)
            print(f"💰 剩余总积分  : {q['total_credits_left']} 积分")
            print(f"🎵 剩余可生成  : 约 {q['songs_left']} 次 (每次提供 2 首候选变体)")
            print(f"📅 额度重置周期: {q['period']}")
            print(f"📊 月度配额限制: {q['monthly_limit']}")
            print(f"📈 本月已消耗  : {q['monthly_usage']}")
            print("=" * 45)
        except Exception as e:
            print(f"❌ 查询配额失败: {e}")

    elif cmd == "feed":
        print(f"🔍 正在获取第 {args.page} 页历史音乐作品...")
        try:
            feed = service.get_feed(page=args.page)
            if not feed:
                print("📭 暂无历史作品。")
                return

            print(f"🎶 检索到 {len(feed)} 首曲目:\n")
            for idx, item in enumerate(feed, 1):
                title = item.get("title") or "无标题"
                status = item.get("status", "unknown")
                duration = round(item.get("metadata", {}).get("duration", 0), 1)
                audio_url = item.get("audio_url") or "尚未就绪"
                print(f"[{idx}] {title} ({status}) - 时长: {duration}s")
                print(f"    🔗 音频直链: {audio_url}")
                if item.get("metadata", {}).get("tags"):
                    print(f"    🏷️ 风格标签: {item['metadata']['tags']}")
                print("-" * 50)
        except Exception as e:
            print(f"❌ 获取作品列表失败: {e}")

    elif cmd == "gen":
        print(f"🎼 [灵感模式] 提示词: \"{args.prompt}\"")
        print(f"⚙️ 模型: {args.model} | 纯乐器: {'是' if args.instrumental else '否'}")

        def log_progress(msg):
            print(f"  {msg}")

        try:
            if args.no_download:
                clips = service.generate_music(
                    prompt=args.prompt,
                    is_custom=False,
                    make_instrumental=args.instrumental,
                    model=args.model,
                )
                ids = [c["id"] for c in clips]
                print(f"✅ 任务已提交，Clip IDs: {ids}")
                print("⏳ 正在等待渲染完成...")
                completed = service.wait_for_completion(ids, progress_callback=lambda c: print(".", end="", flush=True))
                print("\n🎉 生成完成！")
                for c in completed:
                    print(f"🎵 {c.get('title')}: {c.get('audio_url')}")
            else:
                results = service.generate_and_download(
                    prompt=args.prompt,
                    output_dir=args.out,
                    is_custom=False,
                    make_instrumental=args.instrumental,
                    model=args.model,
                    progress_callback=log_progress,
                )
                print("\n🎉 音乐生成与下载全部完成！")
                for r in results:
                    print(f"⭐ 标题: {r.get('title')}")
                    print(f"   🎧 本地文件: {r.get('local_file')}")
                    print(f"   🔗 在线试听: {r.get('audio_url')}")
                    if r.get("video_url"):
                        print(f"   🎬 视频直链: {r.get('video_url')}")
        except Exception as e:
            print(f"\n❌ 生成失败: {e}")

    elif cmd == "custom":
        print(f"🎼 [自定义歌词模式] 标题: \"{args.title}\" | 风格: \"{args.tags}\"")

        def log_progress(msg):
            print(f"  {msg}")

        try:
            results = service.generate_and_download(
                prompt=args.prompt,
                output_dir=args.out,
                is_custom=True,
                tags=args.tags,
                title=args.title,
                make_instrumental=args.instrumental,
                model=args.model,
                progress_callback=log_progress,
            )
            print("\n🎉 自定义音乐生成与下载全部完成！")
            for r in results:
                print(f"⭐ 标题: {r.get('title')}")
                print(f"   🎧 本地文件: {r.get('local_file')}")
                print(f"   🔗 在线试听: {r.get('audio_url')}")
        except Exception as e:
            print(f"\n❌ 生成失败: {e}")

    elif cmd == "lyrics":
        print(f"📝 正在根据灵感创作歌词: \"{args.prompt}\"...")
        try:
            lyric_obj = service.generate_lyrics(args.prompt)
            print(f"\n✨ 歌词标题: {lyric_obj['title']}\n")
            print("=" * 40)
            print(lyric_obj["text"])
            print("=" * 40)
        except Exception as e:
            print(f"❌ 歌词创作失败: {e}")

    elif cmd == "download":
        target = args.target.strip()
        print(f"📥 正在准备下载: {target}...")
        try:
            if target.startswith("http://") or target.startswith("https://"):
                url = target
                save_name = f"suno_track_{int(time.time())}.mp3"
            else:
                # 假设为 clip ID
                clips = service.fetch_clips_status([target])
                if not clips or not clips[0].get("audio_url"):
                    print(f"❌ 未能找到 Clip ID [{target}] 的有效音频链接")
                    return
                url = clips[0]["audio_url"]
                title = clips[0].get("title", f"track_{target[:6]}")
                save_name = f"{title}_{target[:6]}.mp3"

            out_path = os.path.join(args.out, save_name)
            downloaded = service.download_song(url, out_path)
            print(f"✅ 下载成功！本地文件: {downloaded}")
        except Exception as e:
            print(f"❌ 下载失败: {e}")


if __name__ == "__main__":
    main()
