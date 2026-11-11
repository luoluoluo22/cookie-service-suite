#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MiniMax / 海螺语音 TTS 命令行工具 (基于浏览器实时 Cookie / WebSocket)
==================================================================
用法:
  python run_minimax_cli.py status                       # 查询当前 MiniMax 登录态与会话就绪情况
  python run_minimax_cli.py voices                       # 查看预置及可用音色列表
  python run_minimax_cli.py quota                        # 查询当前账号剩余配额字符数
  python run_minimax_cli.py refresh                      # 从 Chrome/Edge 扩展自动唤醒并刷新 Token
  python run_minimax_cli.py speech "你好世界，欢迎使用海螺语音" # 快速合成 MP3 音频并保存到本地
  python run_minimax_cli.py speech "Today is a great day" --voice fable --speed 1.1
"""

import sys
import os
import time
import json
import argparse

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from minimax_service import MinimaxAudioService, PRESET_VOICES, OPENAI_VOICE_MAP

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="MiniMax / 海螺语音 TTS 命令行工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. 状态查询
    subparsers.add_parser("status", help="查询本地 Token 凭证与连接状态")

    # 2. 音色列表
    subparsers.add_parser("voices", help="列出预置高品质音色列表及 OpenAI 别名")

    # 3. 额度配额
    subparsers.add_parser("quota", help="查询当前账户可用字符额度与权益")

    # 4. 刷新凭证
    refresh_parser = subparsers.add_parser("refresh", help="通知 Cookie Hub 自动提取或刷新 Token")
    refresh_parser.add_argument("--force", action="store_true", help="强制后台访问 https://www.minimax.io/audio 唤醒")

    # 5. 语音合成
    speech_parser = subparsers.add_parser("speech", help="文本语音合成 (生成 MP3 文件)")
    speech_parser.add_argument("text", type=str, help="需要合成的文本内容")
    speech_parser.add_argument("--voice", type=str, default="355622221676659", help="音色 ID 或别名 (documentary, alloy, nova, onyx, shimmer, fable, echo)")
    speech_parser.add_argument("--speed", type=float, default=1.0, help="语速 (0.5 - 2.0，默认 1.0)")
    speech_parser.add_argument("--vol", type=float, default=1.0, help="音量 (0.1 - 2.0，默认 1.0)")
    speech_parser.add_argument("--pitch", type=float, default=0.0, help="音高 (-12.0 - 12.0，默认 0.0)")
    speech_parser.add_argument("--out", type=str, default=None, help="自定义保存的 mp3 文件路径")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    service = MinimaxAudioService()

    if args.command == "status":
        print("=" * 60)
        print("  MiniMax Audio / 海螺语音 本地服务状态")
        print("=" * 60)
        is_ready = bool(service.token)
        print(f"  Token 状态     : {'🟢 就绪' if is_ready else '🔴 未配置 (请先在浏览器登录或运行 refresh)'}")
        if is_ready:
            print(f"  Token 摘要     : {service.token[:12]}...{service.token[-8:]}")
            print(f"  UUID 用户标识  : {service.uuid}")
            print(f"  设备 Device ID : {service.device_id}")
            if service.last_fetch_time:
                t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(service.last_fetch_time))
                print(f"  上次同步时间   : {t_str}")
        print(f"  预置音色库     : {len(PRESET_VOICES)} 个官方高保真音色")
        print("=" * 60)

    elif args.command == "voices":
        print("=" * 70)
        print("  MiniMax 官方优质预置音色库")
        print("=" * 70)
        print(f"{'OpenAI 别名':<14} | {'音色 ID':<18} | {'名称 / 语言':<22} | {'特点描述'}")
        print("-" * 70)
        for v in service.get_voices():
            alias = v.get("openai_alias", "-")
            vid = v.get("id")
            name = f"{v.get('name')} [{v.get('language')}]"
            desc = v.get("description", "")
            print(f"{alias:<14} | {vid:<18} | {name:<22} | {desc}")
        print("=" * 70)

    elif args.command == "quota":
        print("正在向 MiniMax 上游查询账户额度...")
        res = service.get_quota()
        print(json.dumps(res, indent=2, ensure_ascii=False))

    elif args.command == "refresh":
        print("正在通过本地 Cookie Hub 提取 MiniMax / 海螺语音登录态...")
        res = service.auto_refresh_auth(force_visit=args.force, timeout=25)
        if res.get("success"):
            print("🟢 刷新成功！")
            print(f"  Token Ready: {res.get('token_ready')}")
            print(f"  Has Auth   : {res.get('has_auth')}")
        else:
            print(f"🔴 刷新失败: {res.get('error', '未知错误')}")
            print("提示：请确认 Chrome/Edge 扩展已开启，且浏览器已访问并登录 https://www.minimax.io/audio")

    elif args.command == "speech":
        print(f"🎙️ 正在合成语音: '{args.text}' ...")
        t0 = time.time()
        try:
            audio_bytes = service.synthesize(
                text=args.text,
                voice=args.voice,
                speed=args.speed,
                vol=args.vol,
                pitch=args.pitch
            )
            cost = time.time() - t0
            out_path = args.out
            if not out_path:
                out_dir = os.path.join(PROJECT_DIR, "downloads", "minimax")
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, f"cli_speech_{int(time.time())}.mp3")

            with open(out_path, "wb") as f:
                f.write(audio_bytes)

            print(f"🎉 合成完成！耗时: {cost:.2f} 秒")
            print(f"💾 音频文件已保存: {out_path} (大小: {len(audio_bytes) / 1024:.1f} KB)")
        except Exception as e:
            print(f"❌ 合成失败: {e}")


if __name__ == "__main__":
    main()
