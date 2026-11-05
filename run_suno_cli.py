#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Suno AI 音乐生成命令行工具 (基于浏览器实时 Cookie)
==============================================
用法:
  python run_suno_cli.py quota                          # 查询当前 Suno 积分额度与可用歌曲次数
  python run_suno_cli.py feed                           # 列出历史生成的曲目列表
  python run_suno_cli.py gen "一段轻快阳光的流行吉他弹唱"    # 灵感描述模式生成并自动下载 MP3
  python run_suno_cli.py custom "歌词正文" --tags "民谣, 治愈" --title "歌名" # 自定义歌词模式生成
  python run_suno_cli.py lyrics "关于秋天与落叶的歌词"       # 单独调用 AI 创作歌词
"""

import sys
import os
import argparse
from suno_service import SunoService

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Suno AI 音乐生成命令行工具 (Cookie Hub 自动化联动)")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. 配额查询
    subparsers.add_parser("quota", help="查询当前账号积分与剩余可用生成次数")
    subparsers.add_parser("credits", help="查询积分 (quota 别名)")

    # 2. 历史作品
    feed_parser = subparsers.add_parser("feed", help="查看历史生成的音乐作品列表")
    feed_parser.add_argument("--page", type=int, default=1, help="页码 (默认: 1)")

    # 3. 灵感描述模式生成
    gen_parser = subparsers.add_parser("gen", help="描述模式快速生成音乐 (自动流式下载)")
    gen_parser.add_argument("prompt", type=str, help="音乐风格或情境描述文本")
    gen_parser.add_argument("--instrumental", action="store_true", help="纯伴奏模式 (无主唱人声)")
    gen_parser.add_argument("--model", type=str, default="chirp-v3-5", choices=["chirp-v3-5", "chirp-v4", "chirp-v3-0"], help="模型版本")
    gen_parser.add_argument("--out", type=str, default="./downloads/suno", help="音频保存目录")
    gen_parser.add_argument("--no-download", action="store_true", help="仅轮询生成结果，不自动下载 MP3 文件")

    # 4. 自定义歌词模式生成
    custom_parser = subparsers.add_parser("custom", help="自定义模式：指定歌词、风格标签与歌名")
    custom_parser.add_argument("prompt", type=str, help="歌词全文 (支持分段标签 如 [Verse] [Chorus])")
    custom_parser.add_argument("--tags", type=str, default="pop, acoustic guitar", help="风格标签 (如 'r&b, soulful, bpm 80')")
    custom_parser.add_argument("--title", type=str, default="My Custom Song", help="歌曲标题")
    custom_parser.add_argument("--instrumental", action="store_true", help="纯伴奏模式")
    custom_parser.add_argument("--model", type=str, default="chirp-v3-5", help="模型版本")
    custom_parser.add_argument("--out", type=str, default="./downloads/suno", help="音频保存目录")
    custom_parser.add_argument("--no-download", action="store_true", help="不自动下载 MP3 文件")

    # 5. 歌词创作
    lyrics_parser = subparsers.add_parser("lyrics", help="利用 Suno AI 生成歌词文本")
    lyrics_parser.add_argument("prompt", type=str, help="歌词灵感提示词")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        service = SunoService()
    except Exception as e:
        print(f"❌ 客户端初始化错误: {e}")
        return

    cmd = args.command.lower()

    if cmd in ("quota", "credits"):
        print("🔍 正在通过 Cookie 获取 Suno 账号配额与积分...")
        try:
            q = service.get_credits()
            print(f"💰 剩余总积分  : {q['total_credits_left']} 积分")
            print(f"🎵 剩余可生成曲目: 约 {q['songs_left']} 次 (每次生成提供 2 种变体)")
            print(f"📅 额度重置周期: {q['period']}")
            print(f"📊 月度配额限制: {q['monthly_limit']}")
            print(f"📈 本月已消耗  : {q['monthly_usage']}")
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


if __name__ == "__main__":
    main()
