#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 GPT 逆向生图模型：
1. 测试生成一张静态图片 (PNG / JPG / WEBP)
2. 测试生成一张 GIF 动图 (检查模型是否支持原生生成 GIF，或分析其输出格式)
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import os
import json
import base64
import time
import urllib.request

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def detect_image_format(data_bytes: bytes) -> str:
    """通过文件头魔数检测真实图片格式"""
    if data_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    elif data_bytes.startswith(b"GIF87a") or data_bytes.startswith(b"GIF89a"):
        return "GIF"
    elif data_bytes.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    elif data_bytes.startswith(b"RIFF") and b"WEBP" in data_bytes[:16]:
        return "WEBP"
    else:
        return "UNKNOWN"

def test_static_image():
    print("=" * 60)
    print("🎨 [测试 1/2] 调用 gpt-image-2 生成静态图片")
    print("=" * 60)
    prompt = "一只戴着金色护目镜的赛博朋克机械猫咪，面部发光电路，高清细节，3D渲染"
    print(f"提示词: {prompt}")
    
    payload = json.dumps({
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "response_format": "b64_json"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://127.0.0.1:18800/v1/images/generations",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    t0 = time.time()
    try:
        print("⏳ 正在请求生成静态图片 (通常耗时 15-40 秒)...")
        with opener.open(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            elapsed = round(time.time() - t0, 2)
            print(f"🟢 生图接口返回成功! HTTP {resp.status} (耗时: {elapsed}s)")
            
            items = data.get("data", [])
            if not items:
                print("❌ 未获取到图片数据:", data)
                return False, None
            
            first_item = items[0]
            b64_str = first_item.get("b64_json", "")
            img_url = first_item.get("url", "")
            
            if b64_str:
                img_bytes = base64.b64decode(b64_str)
                fmt = detect_image_format(img_bytes)
                ext = fmt.lower() if fmt != "UNKNOWN" else "png"
                out_path = os.path.join(OUTPUT_DIR, f"gpt_static_cat.{ext}")
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                print(f"✅ 静态图片生成成功!")
                print(f"  - 真实格式: {fmt}")
                print(f"  - 文件大小: {len(img_bytes) / 1024:.2f} KB")
                print(f"  - 保存路径: {out_path}")
                return True, out_path
            elif img_url:
                print(f"✅ 获取到图片直链 URL: {img_url}")
                return True, img_url
            else:
                print("⚠️ 返回结构未知:", first_item)
                return False, None
    except Exception as e:
        print(f"❌ 静态图片生成失败: {e}")
        return False, None

def test_gif_image():
    print("\n" + "=" * 60)
    print("🎬 [测试 2/2] 调用 gpt-image-2 请求生成 GIF 动图")
    print("=" * 60)
    prompt = "一只奔跑的小猫咪动画，从左跑到右，必须是动态可播放的 GIF 动图 (animated GIF)"
    print(f"提示词: {prompt}")
    
    payload = json.dumps({
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "response_format": "b64_json"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://127.0.0.1:18800/v1/images/generations",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    t0 = time.time()
    try:
        print("⏳ 正在请求生成 GIF 动图 (通常耗时 15-40 秒)...")
        with opener.open(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            elapsed = round(time.time() - t0, 2)
            print(f"🟢 生图接口返回成功! HTTP {resp.status} (耗时: {elapsed}s)")
            
            items = data.get("data", [])
            if not items:
                print("❌ 未获取到数据:", data)
                return False, None
            
            first_item = items[0]
            b64_str = first_item.get("b64_json", "")
            img_url = first_item.get("url", "")
            
            if b64_str:
                img_bytes = base64.b64decode(b64_str)
                fmt = detect_image_format(img_bytes)
                out_path = os.path.join(OUTPUT_DIR, f"gpt_gif_attempt.{fmt.lower()}")
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                print(f"  - 返回文件实际格式: {fmt}")
                print(f"  - 文件大小: {len(img_bytes) / 1024:.2f} KB")
                print(f"  - 保存路径: {out_path}")
                
                if fmt == "GIF":
                    print("🎉 结果: 模型成功输出了原生 GIF 格式动图！")
                else:
                    print(f"ℹ️ 结果分析: 模型返回的是静止的 {fmt} 格式图片（DALL-E 3 底层为静态扩散模型，不支持直接渲染动态帧 GIF）。")
                return True, (fmt, out_path)
            elif img_url:
                print(f"获取到 URL: {img_url}")
                return True, ("URL", img_url)
    except Exception as e:
        print(f"❌ GIF 图片请求失败: {e}")
        return False, None

if __name__ == "__main__":
    test_static_image()
    test_gif_image()
