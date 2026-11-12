#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Meta MusicGen 背景配乐生成服务客户端 (MusicGenService)
===================================================
基于 Meta 顶级开源 AudioCraft / MusicGen 模型封装。
支持免登录、零门槛、纯器乐、专精各类短视频与长视频背景配乐 (BGM)。

核心功能：
- 零成本纯器乐配乐生成（Lo-Fi 轻松解说、史诗电影混音、赛博朋克电子、治愈系钢琴吉他）
- 多引擎自动容灾轮换（aach456/music-gen-ai 稳定引擎 + sanchit-gandhi 流式引擎）
- 内置 ffmpeg 自动化流式转码，生成标准 MP3 格式
- 保存至本地 downloads/musicgen/ 目录
"""

import os
import sys
import time
import re
import subprocess
from typing import Optional, Dict, Any, List, Callable

os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

from gradio_client import Client

DEFAULT_PROXY = "http://127.0.0.1:7897"
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "musicgen")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class MusicGenService:
    def __init__(
        self,
        proxy: str = DEFAULT_PROXY,
        primary_space: str = "aach456/music-gen-ai",
        fallback_space: str = "sanchit-gandhi/musicgen-streaming",
    ):
        self.proxy = proxy
        self.primary_space = primary_space
        self.fallback_space = fallback_space
        self.client: Optional[Client] = None
        self.current_space: Optional[str] = None

    def _ensure_client(self, space_name: str):
        """延迟加载 Gradio Client 实例"""
        if self.client is None or self.current_space != space_name:
            if self.proxy:
                os.environ["HTTP_PROXY"] = self.proxy
                os.environ["HTTPS_PROXY"] = self.proxy
                os.environ["http_proxy"] = self.proxy
                os.environ["https_proxy"] = self.proxy
            self.client = Client(space_name, download_files=False)
            self.current_space = space_name

    def generate_music(
        self,
        prompt: str,
        duration: int = 15,
        title: Optional[str] = None,
        output_dir: str = DOWNLOAD_DIR,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        生成一首高品质背景配乐
        :param prompt: 配乐英文/风格描述词 (例如 'chill lo-fi hip hop beat with cozy piano')
        :param duration: 音乐时长 (秒)
        :param title: 文件命名标识
        :param output_dir: 本地存放目录
        :param progress_cb: 进度通知回调
        :return: 本地保存的 MP3 文件完整绝对路径
        """
        os.makedirs(output_dir, exist_ok=True)
        if not title:
            safe_sub = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]+', '_', prompt[:25]).strip('_')
            title = safe_sub or "musicgen_track"

        timestamp = int(time.time())
        filename = f"{title}_{timestamp}.mp3"
        output_path = os.path.join(output_dir, filename)

        # 尝试通道 1：aach456/music-gen-ai (免 ZeroGPU 额度限制)
        try:
            if progress_cb:
                progress_cb(f"🎵 正在通过 MusicGen 引擎生成配乐: {title}...")
            self._ensure_client(self.primary_space)
            wav_path = self.client.predict(
                prompt=prompt,
                use_gpu=False,
                unconditional=False,
                api_name="/generate_music"
            )
            # 转码为标准 MP3
            subprocess.run(
                ["ffmpeg", "-y", "-i", wav_path, "-c:a", "libmp3lame", "-q:a", "2", output_path],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if progress_cb:
                progress_cb(f"🎉 配乐制作完成并落盘: {output_path}")
            return output_path
        except Exception as e:
            if progress_cb:
                progress_cb(f"⚠️ 引擎 1 异常 ({e})，正在切换至备用引擎...")

        # 尝试通道 2：sanchit-gandhi/musicgen-streaming
        self._ensure_client(self.fallback_space)
        res = self.client.predict(
            text_prompt=prompt,
            audio_length_in_s=float(max(10, min(30, duration))),
            play_steps_in_s=1.5,
            seed=5.0,
            api_name="/generate_audio"
        )
        stream_url = res["url"]
        ffmpeg_cmd = ["ffmpeg", "-y"]
        if self.proxy:
            ffmpeg_cmd.extend(["-http_proxy", self.proxy])
        ffmpeg_cmd.extend([
            "-i", stream_url,
            "-c:a", "libmp3lame",
            "-q:a", "2",
            output_path,
        ])
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if progress_cb:
            progress_cb(f"🎉 备用引擎配乐制作完成: {output_path}")
        return output_path
