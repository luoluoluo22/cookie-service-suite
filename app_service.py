#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 统一本地 API 服务与管理中心
采用成熟企业级 FastAPI 框架封装：
- 提供 Gemini 4账号统一池、ChatGPT Web 桥接、B站、百度网盘与 Cookie Hub 全套 RESTful API
- 提供标准 OpenAI 兼容接口 (/v1/chat/completions, /v1/models)
- 提供自带交互式 Swagger UI (/docs) 与 ReDoc (/redoc)
- 提供现代化深色管理控制台 Web UI (/)
"""

import os
import sys
import time
import json
import sqlite3
import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# 保证本地通信不被外部代理拦截
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

from cookie_bridge import CookieBridge
from gemini_service import MultiAccountGeminiPool, GeminiService
from chatgpt_service import chatgpt_service, UnifiedChatGPTService, ChatGPTBridgeClient, ChatGPTReverseEngine
from bilibili_service import BilibiliService
from baidu_pan_service import BaiduPanService
from suno_service import SunoService, suno_service

# 初始化 FastAPI 应用
app = FastAPI(
    title="Cookie Service Suite API",
    description="浏览器实时 Cookie 动态提取与多平台 Web 服务统一本地调度中心",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 允许跨域（前端控制台与本地工具调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 单例业务客户端
bridge_hub = CookieBridge()
gemini_pool = MultiAccountGeminiPool(port=18083, account_count=4)
chatgpt_client = chatgpt_service
bili_service = BilibiliService()
baidu_service = BaiduPanService()
suno_client = suno_service

START_TIME = datetime.datetime.now()


# ==========================================
# Pydantic 请求与响应模型
# ==========================================
class ChatRequest(BaseModel):
    prompt: str = Field(..., description="提问正文或指令内容", example="量子纠缠的基本原理是什么？")
    model: Optional[str] = Field("gemini-3.5-flash-lite", description="模型名称 (gemini-3.5-flash-lite, gemini-3.1-pro 等)", example="gemini-3.5-flash-lite")
    reasoning_level: Optional[str] = Field("off", description="推理级别: 'off'(关闭思考/极速), 'medium'(中等推理), 'high'(深度扩展思考)", example="off")
    timeout: Optional[int] = Field(60, description="请求超时时间 (秒)", example=60)


class ChatGPTAccountImportRequest(BaseModel):
    tokens: List[str] = Field(..., description="OpenAI Access Token 列表 (JWT 字符串)")


class ChatGPTImageRequest(BaseModel):
    prompt: str = Field(..., description="图片生成提示词", example="一只在太空漂浮的赛博朋克猫咪")
    model: Optional[str] = Field("gpt-image-2", description="图片模型 (gpt-image-2, codex-gpt-image-2 等)")
    n: Optional[int] = Field(1, description="生成张数 (1-4)", ge=1, le=4)
    response_format: Optional[str] = Field("b64_json", description="返回格式 (b64_json 或 url)")


class OpenAIImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="图片生成提示词")
    model: Optional[str] = Field("gpt-image-2")
    n: Optional[int] = Field(1)
    response_format: Optional[str] = Field("b64_json")


class OpenAIMessage(BaseModel):
    role: str = Field(..., example="user")
    content: str = Field(..., example="Hello!")


class OpenAIChatRequest(BaseModel):
    model: Optional[str] = Field("gemini-3.5-flash-lite", example="gemini-3.5-flash-lite")
    messages: List[OpenAIMessage] = Field(..., description="对话历史消息列表")
    reasoning_effort: Optional[str] = Field(None, description="OpenAI 兼容推理强度: 'low', 'medium', 'high'", example="medium")
    reasoning_level: Optional[str] = Field(None, description="推理级别: 'off', 'medium', 'high'", example="off")
    stream: Optional[bool] = Field(False, description="是否启用流式输出")
    temperature: Optional[float] = Field(0.7, example=0.7)


class SunoGenerateRequest(BaseModel):
    prompt: str = Field(..., description="音乐描述词或歌词全文", example="一段欢快的夏日流行海滩音乐，带有原声吉他和轻快的鼓点")
    is_custom: Optional[bool] = Field(False, description="是否为自定义模式 (歌词+风格)")
    tags: Optional[str] = Field("pop, acoustic guitar, cheerful", description="音乐流派风格标签 (仅自定义模式)")
    title: Optional[str] = Field("My Suno Song", description="歌曲标题")
    make_instrumental: Optional[bool] = Field(False, description="是否生成纯器乐伴奏 (无主唱)")
    model: Optional[str] = Field("chirp-v3-5", description="模型版本: chirp-v3-5, chirp-v4, chirp-v3-0")
    wait: Optional[bool] = Field(False, description="是否等待渲染完成 (若为 False 则立即返回任务 clip ids)")
    download: Optional[bool] = Field(False, description="当 wait 为 True 时是否自动下载 MP3 到本地")


class SunoLyricsRequest(BaseModel):
    prompt: str = Field(..., description="歌词创作主题或提示词", example="写一首关于秋天落叶与远方思念的流行歌词")


# ==========================================
# 1. 核心系统概览与状态接口
# ==========================================
@app.get("/api/system/overview", summary="获取所有本地子服务运行总览", tags=["系统管理"])
def get_system_overview():
    """检测 Cookie Hub、Gemini 4账号池、ChatGPT 桥接及系统运行时间。"""
    hub_ok = False
    hub_info = {}
    try:
        hub_info = bridge_hub.check_status()
        hub_ok = hub_info.get("extensionConnected", False)
    except Exception:
        pass

    gemini_running = gemini_pool.is_running()
    gemini_accounts = []
    if gemini_running:
        try:
            gemini_accounts = gemini_pool.list_accounts()
        except Exception:
            pass

    uptime_sec = int((datetime.datetime.now() - START_TIME).total_seconds())
    chatgpt_status = chatgpt_client.get_status()

    return {
        "status": "online",
        "service_name": "Cookie Service Suite",
        "version": "2.0.0",
        "uptime_seconds": uptime_sec,
        "services": {
            "cookie_hub": {
                "port": 18888,
                "status": "connected" if hub_ok else "offline",
                "extension_connected": hub_ok,
                "clients": hub_info.get("connectedClients", 0),
            },
            "gemini_pool": {
                "port": gemini_pool.port,
                "status": "running" if gemini_running else "stopped",
                "account_count": len(gemini_accounts),
                "active_accounts": sum(1 for a in gemini_accounts if a.get("status") == "enabled"),
            },
            "chatgpt": {
                "mode": chatgpt_status.get("mode"),
                "reverse_running": chatgpt_status.get("reverse_engine", {}).get("running", False),
                "reverse_port": chatgpt_status.get("reverse_engine", {}).get("port", 18084),
                "reverse_health": chatgpt_status.get("reverse_engine", {}).get("health", {}),
                "bridge_connected": chatgpt_status.get("browser_bridge", {}).get("extension_connected", False),
            },
            "chatgpt_bridge": {
                "status": "ready" if hub_ok else "waiting_hub",
                "method": "in_page_hook_sse",
            },
        },
    }


# ==========================================
# 2. Google Gemini 多账号池统一调度接口
# ==========================================
@app.get("/api/gemini/accounts", summary="获取已接入的 4 个 Google 账号状态", tags=["Gemini 多账号调度"])
def list_gemini_accounts():
    """获取通过 /u/0, /u/1, /u/2, /u/3 区分的 4 个 Google 账号的最新池化状态与轮询统计。"""
    try:
        accounts = gemini_pool.list_accounts()
        return {
            "total": len(accounts),
            "accounts": accounts,
            "service_running": gemini_pool.is_running(),
            "pool_port": gemini_pool.port,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gemini/accounts/sync-profiles", summary="同步提取所有账号的真实 Google 昵称与邮箱", tags=["Gemini 多账号调度"])
def sync_gemini_profiles():
    """向 Google 上游拉取各 authuser 对应的真实用户显示昵称与 Gmail 邮箱并写入账号池。"""
    try:
        res = gemini_pool.sync_account_profiles()
        return {
            "success": True,
            "message": "已成功更新 4 个账号的真实昵称与邮箱信息！",
            "profiles": res,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步昵称邮箱失败: {str(e)}")


@app.post("/api/gemini/chat", summary="向 Gemini 发起提问 (自动 LRU 负载均衡轮换)", tags=["Gemini 多账号调度"])
def gemini_chat(req: ChatRequest):
    """
    底层通过最久未用 (LRU) 算法自动在已接入的 4 个账号之间分发请求，
    支持指定推理级别 ('off' 快速直出, 'medium' 中等推理, 'high' 深度长思考链)，
    遇凭证过期或网络异常自动触发 Cookie Hub 热刷新与重试自愈。
    """
    if not gemini_pool.is_running():
        gemini_pool.start()

    reasoning = req.reasoning_level or "off"
    try:
        res = gemini_pool.ask_with_details(
            prompt=req.prompt, model=req.model, reasoning_level=reasoning, timeout=req.timeout
        )
    except Exception as first_err:
        # 自动故障自愈：从 Cookie Hub 刷新凭证后重试一次
        try:
            gemini_pool.refresh_pool_cookies()
            res = gemini_pool.ask_with_details(
                prompt=req.prompt, model=req.model, reasoning_level=reasoning, timeout=req.timeout
            )
        except Exception as retry_err:
            raise HTTPException(status_code=502, detail=f"Gemini 调度调用失败 (自愈重试后仍失败): {str(retry_err)}")

    return {
        "success": True,
        "reply": res.get("reply"),
        "account_id": res.get("account_id"),
        "account_label": res.get("account_label"),
        "authuser": res.get("authuser"),
        "latency_ms": res.get("took_ms"),
        "model": res.get("model"),
        "reasoning_level": res.get("reasoning_level"),
    }


@app.post("/api/gemini/accounts/{account_id}/check", summary="检测指定账号凭证健康度", tags=["Gemini 多账号调度"])
def check_gemini_account(account_id: int = Path(..., description="账号自增 ID (1..4)")):
    """向 Google 上游验证指定账号会话有效性并更新健康状态。"""
    try:
        if not gemini_pool.is_running():
            gemini_pool.start()
        res = gemini_pool.check_account(account_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gemini/accounts/{account_id}/rotate", summary="触发指定账号会话令牌保活续期", tags=["Gemini 多账号调度"])
def rotate_gemini_account(account_id: int = Path(..., description="账号自增 ID (1..4)")):
    """向 Google accounts.google.com/RotateCookies 申请换发最新短命会话票据。"""
    try:
        if not gemini_pool.is_running():
            gemini_pool.start()
        res = gemini_pool.rotate_account(account_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gemini/refresh", summary="从前台浏览器提取最新凭证并热更新账号池", tags=["Gemini 多账号调度"])
def refresh_gemini_cookies():
    """从 Cookie Hub (18888) 提取浏览器内最新鉴权 Cookie 并批量写入 SQLite 数据库。"""
    try:
        cookie_str = gemini_pool.refresh_pool_cookies()
        return {
            "success": True,
            "message": "已从浏览器成功拉取最新 Google 凭证并更新多账号池！",
            "cookie_length": len(cookie_str),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"凭证刷新失败: {str(e)}")


@app.get("/api/gemini/requests", summary="获取最近请求调度轨迹与各账号响应历史", tags=["Gemini 多账号调度"])
def get_gemini_recent_requests(limit: int = Query(20, description="返回条数上限")):
    try:
        return {"requests": gemini_pool.list_recent_requests(limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 3. ChatGPT 逆向工程与原生桥接号池 API
# ==========================================
@app.get("/api/chatgpt/status", summary="获取 ChatGPT 运行模式与号池状态", tags=["ChatGPT 逆向与号池"])
def get_chatgpt_status():
    """检测当前 ChatGPT 服务状态（逆向服务端口、健康度、号池账号总数与浏览器桥接状态）。"""
    return chatgpt_client.get_status()


@app.post("/api/chatgpt/start", summary="启动 ChatGPT 本地独立逆向后台服务", tags=["ChatGPT 逆向与号池"])
def start_chatgpt_reverse():
    """手动按需启动基于 chatgpt2api 的独立无头逆向进程 (默认 18084 端口)。"""
    try:
        ok = chatgpt_client.reverse.start()
        return {"success": ok, "port": chatgpt_client.reverse.port, "is_running": chatgpt_client.reverse.is_running()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动 ChatGPT 逆向后台失败: {str(e)}")


@app.post("/api/chatgpt/stop", summary="停止 ChatGPT 本地独立逆向后台服务", tags=["ChatGPT 逆向与号池"])
def stop_chatgpt_reverse():
    """停止 ChatGPT 独立无头逆向进程。"""
    try:
        chatgpt_client.reverse.stop()
        return {"success": True, "is_running": chatgpt_client.reverse.is_running()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止 ChatGPT 逆向后台失败: {str(e)}")


@app.get("/api/chatgpt/session", summary="获取当前 ChatGPT 登录会话与邮箱", tags=["ChatGPT 逆向与号池"])
def get_chatgpt_session():
    """提取当前 ChatGPT 标签页或逆向号池中的已登录用户与 Access Token。"""
    try:
        return chatgpt_client.get_session()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"无法获取 ChatGPT 会话: {str(e)}")


@app.get("/api/chatgpt/models", summary="获取 ChatGPT 账号可用模型列表", tags=["ChatGPT 逆向与号池"])
def get_chatgpt_models():
    """拉取逆向暴露或浏览器同源支持的模型列表 (如 auto, gpt-5-6, gpt-image-2 等)。"""
    try:
        return chatgpt_client.get_models()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"无法获取模型列表: {str(e)}")


@app.get("/api/chatgpt/accounts", summary="获取当前 ChatGPT 逆向号池账号列表", tags=["ChatGPT 逆向与号池"])
def list_chatgpt_accounts():
    """查看已导入逆向引擎的账号列表、额度与健康状态。"""
    try:
        if not chatgpt_client.reverse.is_running():
            chatgpt_client.reverse.start()
        return {"items": chatgpt_client.reverse.list_accounts()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取账号列表失败: {str(e)}")


@app.post("/api/chatgpt/accounts", summary="向 ChatGPT 号池导入 AccessToken", tags=["ChatGPT 逆向与号池"])
def import_chatgpt_accounts(body: ChatGPTAccountImportRequest):
    """手动导入一个或多个 Access Token 进入号池并自动刷新有效性。"""
    try:
        if not chatgpt_client.reverse.is_running():
            chatgpt_client.reverse.start()
        res = chatgpt_client.reverse.import_tokens(body.tokens)
        return res
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"导入账号失败: {str(e)}")


@app.post("/api/chatgpt/accounts/sync-browser", summary="从浏览器 Cookie Hub 一键同步 Token 入池", tags=["ChatGPT 逆向与号池"])
def sync_chatgpt_browser_token():
    """通过 Cookie Hub 自动获取浏览器中当前 chatgpt.com 登录会话的 Access Token，并一键载入逆向号池。"""
    try:
        return chatgpt_client.sync_token_from_browser()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"从浏览器同步 Token 失败: {str(e)}")


@app.post("/api/chatgpt/chat", summary="向 ChatGPT 发起智能对话 (支持逆向与桥接双引擎)", tags=["ChatGPT 逆向与号池"])
def chatgpt_ask(req: ChatRequest):
    """优先使用无头逆向引擎直连，若未就绪则自动降级到浏览器同源扩展。"""
    try:
        reply = chatgpt_client.ask(req.prompt, model=req.model or "auto")
        return {"success": True, "reply": reply}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ChatGPT 提问失败: {str(e)}")


@app.post("/api/chatgpt/image", summary="ChatGPT 逆向图片生成 (gpt-image-2)", tags=["ChatGPT 逆向与号池"])
def chatgpt_image_generation(body: ChatGPTImageRequest):
    """基于 chatgpt2api 官方逆向实现文生图，支持 gpt-image-2 等模型。"""
    try:
        return chatgpt_client.generate_image(
            prompt=body.prompt,
            model=body.model or "gpt-image-2",
            n=body.n or 1,
            response_format=body.response_format or "b64_json"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ChatGPT 图片生成失败: {str(e)}")


# ==========================================
# 4. Bilibili 业务接口
# ==========================================
@app.get("/api/bilibili/user", summary="获取 B 站登录用户信息与大会员资产", tags=["Bilibili 视频特权"])
def get_bilibili_user():
    try:
        return bili_service.get_user_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 B 站用户失败: {str(e)}")


@app.get("/api/bilibili/video", summary="查询 B 站视频信息与最高画质流", tags=["Bilibili 视频特权"])
def get_bilibili_video(bvid: str = Query(..., description="视频 BV 号，如 BV1GJ411x7h7")):
    try:
        return bili_service.get_video_info(bvid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析视频失败: {str(e)}")


# ==========================================
# 5. 百度网盘业务接口
# ==========================================
@app.get("/api/baidupan/quota", summary="获取百度网盘存储容量与配额信息", tags=["百度网盘服务"])
def get_baidupan_quota():
    try:
        return baidu_service.get_quota()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询网盘配额失败: {str(e)}")


@app.get("/api/baidupan/user", summary="获取百度网盘账号资料与 VIP 等级", tags=["百度网盘服务"])
def get_baidupan_user():
    try:
        return baidu_service.get_user_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询网盘用户失败: {str(e)}")


@app.get("/api/baidupan/files", summary="遍历百度网盘指定目录下的文件", tags=["百度网盘服务"])
def list_baidupan_files(dir_path: str = Query("/", description="网盘目录路径，默认根目录 /")):
    try:
        return baidu_service.list_files(dir_path=dir_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"遍历网盘文件失败: {str(e)}")


# ==========================================
# 6. Cookie Hub 实时通信代理
# ==========================================
@app.get("/api/hub/status", summary="检测 Cookie Hub 扩展长连接状态", tags=["Cookie Hub 通信"])
def get_hub_status():
    try:
        return bridge_hub.check_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cookie Hub 连接失败: {str(e)}")


@app.get("/api/hub/cookies", summary="按域名动态提取实时 Cookie", tags=["Cookie Hub 通信"])
def get_hub_cookies(domain: str = Query("google.com", description="要提取 Cookie 的目标域名")):
    try:
        header_cookie = bridge_hub.get_cookies_header(domain=domain)
        cookies_dict = bridge_hub.get_cookies_dict(domain=domain)
        return {
            "domain": domain,
            "count": len(cookies_dict),
            "cookies": cookies_dict,
            "header": header_cookie,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 6.5. Suno AI 音乐生成服务
# ==========================================
@app.get("/api/suno/quota", summary="获取当前 Suno 账户积分与可用曲目数", tags=["Suno 音乐生成"])
def get_suno_quota():
    try:
        return suno_client.get_credits()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询 Suno 配额失败: {str(e)}")


@app.get("/api/suno/feed", summary="获取 Suno 历史作品曲库列表", tags=["Suno 音乐生成"])
def get_suno_feed(page: int = Query(1, ge=1, description="页码")):
    try:
        return suno_client.get_feed(page=page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Suno 历史曲库失败: {str(e)}")


@app.post("/api/suno/generate", summary="提交 Suno 音乐创作任务", tags=["Suno 音乐生成"])
def generate_suno_music(req: SunoGenerateRequest):
    try:
        if req.wait:
            if req.download:
                return suno_client.generate_and_download(
                    prompt=req.prompt,
                    is_custom=req.is_custom,
                    tags=req.tags,
                    title=req.title,
                    make_instrumental=req.make_instrumental,
                    model=req.model,
                )
            else:
                clips = suno_client.generate_music(
                    prompt=req.prompt,
                    is_custom=req.is_custom,
                    tags=req.tags,
                    title=req.title,
                    make_instrumental=req.make_instrumental,
                    model=req.model,
                )
                clip_ids = [c["id"] for c in clips]
                return suno_client.wait_for_completion(clip_ids, timeout=600)
        else:
            clips = suno_client.generate_music(
                prompt=req.prompt,
                is_custom=req.is_custom,
                tags=req.tags,
                title=req.title,
                make_instrumental=req.make_instrumental,
                model=req.model,
            )
            return {
                "success": True,
                "submitted_count": len(clips),
                "clip_ids": [c["id"] for c in clips],
                "clips": clips,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交 Suno 音乐生成失败: {str(e)}")


@app.get("/api/suno/status", summary="查询指定 clip ids 的生成状态与音频直链", tags=["Suno 音乐生成"])
def get_suno_status(clip_ids: str = Query(..., description="待查询的 clip ID，多个用英文逗号隔开")):
    try:
        id_list = [i.strip() for i in clip_ids.split(",") if i.strip()]
        return suno_client.fetch_clips_status(id_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询任务状态失败: {str(e)}")


@app.post("/api/suno/lyrics", summary="使用 Suno AI 单独创作歌词", tags=["Suno 音乐生成"])
def generate_suno_lyrics(req: SunoLyricsRequest):
    try:
        return suno_client.generate_lyrics(prompt=req.prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创作歌词失败: {str(e)}")


@app.post("/api/suno/refresh", summary="强制刷新 Suno 凭证与 Clerk JWT 令牌", tags=["Suno 音乐生成"])
def refresh_suno_auth():
    try:
        return suno_client.refresh_auth()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新 Suno 凭证失败: {str(e)}")


# ==========================================
# 7. 标准 OpenAI 兼容 API 路由 (/v1/*)
# ==========================================
@app.post("/v1/chat/completions", summary="OpenAI 兼容聊天接口", tags=["OpenAI 兼容接口"])
def openai_chat_completions(req: OpenAIChatRequest):
    """
    提供标准 OpenAI 规范接口，可无缝对接 NextChat、Chatbox、OpenCat、Cursor 等第三方大模型客户端。
    底层智能分流：
    - gemini-* 模型自动分发至 Google Gemini 4 账号统一均衡池；
    - gpt-* / chatgpt-* / auto 自动分发至 ChatGPT 逆向号池或同源扩展桥接；
    - 支持 stream=True 标准 SSE 流式输出。
    """
    last_user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    if not last_user_msg:
        raise HTTPException(status_code=400, detail="未包含有效的 user 消息")

    model_name = (req.model or "gemini-3.5-flash-lite").lower().strip()

    # 1. Gemini 分流
    if model_name.startswith("gemini"):
        if not gemini_pool.is_running():
            gemini_pool.start()

        target_model = req.model if req.model and "gemini" in req.model else "gemini-3.5-flash-lite"
        reasoning = req.reasoning_effort or req.reasoning_level or "off"
        try:
            res = gemini_pool.ask_with_details(
                prompt=last_user_msg, model=target_model, reasoning_level=reasoning
            )
        except Exception as first_err:
            try:
                gemini_pool.refresh_pool_cookies()
                res = gemini_pool.ask_with_details(
                    prompt=last_user_msg, model=target_model, reasoning_level=reasoning
                )
            except Exception as retry_err:
                raise HTTPException(status_code=502, detail=f"Gemini 兼容接口调用失败: {str(retry_err)}")

        cid = f"chatcmpl-gemini-{int(time.time()*1000)}"
        return {
            "id": cid,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": target_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": res.get("reply", "")},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(last_user_msg),
                "completion_tokens": len(res.get("reply", "")),
                "total_tokens": len(last_user_msg) + len(res.get("reply", "")),
            },
            "_meta": {
                "account_id": res.get("account_id"),
                "account_label": res.get("account_label"),
                "authuser": res.get("authuser"),
                "latency_ms": res.get("took_ms"),
            },
        }

    # 2. ChatGPT 分流 (逆向引擎 + 扩展桥接)
    target_gpt_model = req.model if req.model and req.model not in ("chatgpt-web", "gpt-4o", "gpt-3.5-turbo") else "auto"
    messages_payload = [{"role": m.role, "content": m.content} for m in req.messages]
    effort = req.reasoning_effort or req.reasoning_level or ""

    if req.stream:
        def _sse_generator():
            try:
                for chunk in chatgpt_client.chat(messages_payload, model=target_gpt_model, stream=True, thinking_effort=effort):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                err_data = {"error": {"message": str(e), "type": "chatgpt_error"}}
                yield f"data: {json.dumps(err_data, ensure_ascii=False)}\n\n"

        return StreamingResponse(_sse_generator(), media_type="text/event-stream")

    try:
        res = chatgpt_client.chat(messages_payload, model=target_gpt_model, stream=False, thinking_effort=effort)
        return res
    except Exception as e:
        # 降级尝试单句提问
        try:
            reply = chatgpt_client.ask(last_user_msg, model=target_gpt_model)
            cid = f"chatcmpl-gpt-{int(time.time()*1000)}"
            return {
                "id": cid,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": target_gpt_model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": reply},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": len(last_user_msg),
                    "completion_tokens": len(reply),
                    "total_tokens": len(last_user_msg) + len(reply),
                },
            }
        except Exception as fallback_err:
            raise HTTPException(status_code=502, detail=f"ChatGPT 兼容调用失败: {str(fallback_err)}")


@app.post("/v1/images/generations", summary="OpenAI 兼容图片生成接口", tags=["OpenAI 兼容接口"])
def openai_image_generations(body: OpenAIImageGenerationRequest):
    """
    提供标准 OpenAI POST /v1/images/generations 接口，
    底层自动路由到 chatgpt2api 官方逆向的 gpt-image-2 / DALL-E 3 生成能力。
    """
    try:
        return chatgpt_client.generate_image(
            prompt=body.prompt,
            model=body.model or "gpt-image-2",
            n=body.n or 1,
            response_format=body.response_format or "b64_json"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ChatGPT 图片生成失败: {str(e)}")


@app.get("/v1/models", summary="OpenAI 兼容模型列表", tags=["OpenAI 兼容接口"])
def openai_models():
    gpt_models = [
        {"id": "auto", "object": "model", "owned_by": "openai-reverse", "description": "ChatGPT 智能自动优选模型"},
        {"id": "gpt-5-6", "object": "model", "owned_by": "openai-reverse", "description": "ChatGPT Web 逆向旗舰模型"},
        {"id": "gpt-5-6-mini", "object": "model", "owned_by": "openai-reverse", "description": "ChatGPT Web 极速轻量模型"},
        {"id": "gpt-6", "object": "model", "owned_by": "openai-reverse", "description": "ChatGPT Web 新一代架构模型"},
        {"id": "gpt-image-2", "object": "model", "owned_by": "openai-reverse", "description": "ChatGPT 逆向文生图专用 (DALL-E 3)"},
        {"id": "codex-gpt-image-2", "object": "model", "owned_by": "openai-reverse", "description": "ChatGPT Codex 高清画图专用"},
        {"id": "chatgpt-web", "object": "model", "owned_by": "openai-cookie-suite", "description": "ChatGPT 浏览器同源桥接"},
        {"id": "gpt-4o", "object": "model", "owned_by": "openai-cookie-suite", "description": "OpenAI 兼容映射通道"},
    ]
    gemini_models = [
        {"id": "gemini-3.5-flash-lite", "object": "model", "owned_by": "google-cookie-suite", "description": "极速响应毫秒级，推荐默认"},
        {"id": "gemini-3.1-pro", "object": "model", "owned_by": "google-cookie-suite", "description": "高智力强推理，适合复杂任务"},
        {"id": "gemini-3.6-flash", "object": "model", "owned_by": "google-cookie-suite", "description": "多模态高通量，通用均衡"},
        {"id": "gemini-3.8-flash", "object": "model", "owned_by": "google-cookie-suite", "description": "新一代 Flash 架构"},
        {"id": "gemini-3.1-pro-thinking", "object": "model", "owned_by": "google-cookie-suite", "description": "扩展深度思考链模式"},
    ]
    return {
        "object": "list",
        "data": gpt_models + gemini_models,
    }


# ==========================================
# 8. 现代化 Web 控制台 (Management Dashboard)
# ==========================================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cookie Service Suite | 本地服务与 API 管理控制台</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .glass-card { background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.07); }
    pre::-webkit-scrollbar { height: 6px; width: 6px; }
    pre::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
  
  <!-- 顶部导航栏 -->
  <header class="sticky top-0 z-50 glass border-b border-slate-800/80 px-6 py-4 flex items-center justify-between shadow-2xl">
    <div class="flex items-center space-x-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-500/20">
        <i class="fa-solid fa-cookie-bite text-xl text-slate-950"></i>
      </div>
      <div>
        <h1 class="font-bold text-lg text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-sky-300 to-cyan-200">
          Cookie Service Suite
        </h1>
        <p class="text-xs text-slate-400">本地服务总线 & 多账号统一管理中心</p>
      </div>
    </div>
    <div class="flex items-center space-x-3">
      <a href="/docs" target="_blank" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/20 transition flex items-center gap-1.5">
        <i class="fa-solid fa-bolt"></i> Swagger 交互文档
      </a>
      <a href="/redoc" target="_blank" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1.5">
        <i class="fa-solid fa-book"></i> ReDoc 规范
      </a>
      <button onclick="refreshDashboard()" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition flex items-center gap-1.5">
        <i class="fa-solid fa-arrow-rotate-right" id="refresh-icon"></i> 刷新数据
      </button>
    </div>
  </header>

  <!-- 主体内容容器 -->
  <main class="max-w-7xl mx-auto px-6 py-8 space-y-8">

    <!-- 1. 服务运行指标卡片 -->
    <section class="grid grid-cols-1 md:grid-cols-4 gap-5">
      <!-- Cookie Hub -->
      <div class="glass-card rounded-2xl p-5 shadow-xl relative overflow-hidden group">
        <div class="flex justify-between items-start">
          <div>
            <div class="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">Cookie Hub 扩展桥</div>
            <div class="text-2xl font-bold text-slate-100 flex items-center gap-2" id="hub-status-text">
              <span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span> 正在连接
            </div>
          </div>
          <div class="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
            <i class="fa-solid fa-puzzle-piece text-lg"></i>
          </div>
        </div>
        <div class="mt-4 text-xs text-slate-400 flex justify-between">
          <span>端口: 18888</span>
          <span id="hub-clients">客户端: 1</span>
        </div>
      </div>

      <!-- Gemini 多账号池 -->
      <div class="glass-card rounded-2xl p-5 shadow-xl relative overflow-hidden group">
        <div class="flex justify-between items-start">
          <div>
            <div class="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">Gemini 统一池</div>
            <div class="text-2xl font-bold text-amber-300 flex items-center gap-2" id="gemini-status-text">
              4 账号在线
            </div>
          </div>
          <div class="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
            <i class="fa-solid fa-brain text-lg"></i>
          </div>
        </div>
        <div class="mt-4 text-xs text-slate-400 flex justify-between">
          <span>LRU 自动负载均衡</span>
          <span>端口: 18083</span>
        </div>
      </div>

      <!-- OpenAI 兼容端点 -->
      <div class="glass-card rounded-2xl p-5 shadow-xl relative overflow-hidden group">
        <div class="flex justify-between items-start">
          <div>
            <div class="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">OpenAI 兼容端点</div>
            <div class="text-2xl font-bold text-emerald-300">/v1 开放中</div>
          </div>
          <div class="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
            <i class="fa-solid fa-network-wired text-lg"></i>
          </div>
        </div>
        <div class="mt-4 text-xs text-slate-400 flex justify-between">
          <span>端口: 18800</span>
          <span>支持 Chatbox/Cursor</span>
        </div>
      </div>

      <!-- 系统运行时间 -->
      <div class="glass-card rounded-2xl p-5 shadow-xl relative overflow-hidden group">
        <div class="flex justify-between items-start">
          <div>
            <div class="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">系统运行时长</div>
            <div class="text-2xl font-bold text-indigo-300" id="uptime-text">0m</div>
          </div>
          <div class="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
            <i class="fa-solid fa-clock text-lg"></i>
          </div>
        </div>
        <div class="mt-4 text-xs text-slate-400 flex justify-between">
          <span>托盘状态: 驻留托盘</span>
          <span class="text-emerald-400">稳定自愈就绪</span>
        </div>
      </div>
    </section>

    <!-- 2. Gemini 4 账号槽位看板 -->
    <section class="glass-card rounded-2xl p-6 shadow-xl">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
            <i class="fa-solid fa-users-gear text-amber-400"></i> Google Gemini 4 账号槽位看板
          </h2>
          <p class="text-xs text-slate-400">基于浏览器 /u/0 ~ /u/3 多登录体系，自动分发、保活与熔断切换</p>
        </div>
        <div class="flex items-center gap-2.5">
          <button onclick="syncProfiles()" id="btn-sync-profiles" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 hover:bg-indigo-500/20 transition flex items-center gap-1.5" title="抓取各账号在 Google 的真实用户名与 Gmail 邮箱">
            <i class="fa-solid fa-id-card"></i> 同步真实名称与邮箱
          </button>
          <button onclick="refreshAllCookies()" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20 transition flex items-center gap-1.5">
            <i class="fa-solid fa-arrows-rotate"></i> 从 Cookie Hub 刷新全部凭证
          </button>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-900/60 text-xs uppercase text-slate-400 border-b border-slate-800">
            <tr>
              <th class="py-3 px-3">序号</th>
              <th class="py-3 px-4">Google 账号真实名称与邮箱</th>
              <th class="py-3 px-3">URL 前缀</th>
              <th class="py-3 px-4">5小时计算额度 (滚动窗口)</th>
              <th class="py-3 px-4">周累计额度 (每周上限)</th>
              <th class="py-3 px-3">会话健康</th>
              <th class="py-3 px-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody id="accounts-tbody" class="divide-y divide-slate-800/60">
            <tr><td colspan="7" class="py-6 text-center text-slate-500">正在获取账号数据...</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 3. 在线 API 交互调试工作台 (Live Playground) -->
    <section class="glass-card rounded-2xl p-6 shadow-xl grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div class="lg:col-span-6 space-y-4">
        <div>
          <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
            <i class="fa-solid fa-terminal text-cyan-400"></i> 在线 API 调试工作台
          </h2>
          <p class="text-xs text-slate-400">快速发起真实接口请求，支持自选模型与思考推理级别</p>
        </div>

        <div>
          <label class="text-xs font-semibold text-slate-300 uppercase block mb-1.5">选择预设 API 模板</label>
          <select id="api-selector" onchange="switchApiTemplate()" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-400">
            <option value="gemini_chat">[POST] /api/gemini/chat (Gemini 4账号轮询对话)</option>
            <option value="openai_chat">[POST] /v1/chat/completions (OpenAI 兼容对话)</option>
            <option value="gemini_accounts">[GET] /api/gemini/accounts (查看4账号状态与额度)</option>
            <option value="sync_profiles">[POST] /api/gemini/accounts/sync-profiles (同步各账号真实名称)</option>
            <option value="hub_status">[GET] /api/hub/status (Cookie Hub 状态)</option>
            <option value="hub_cookies">[GET] /api/hub/cookies?domain=google.com (提取实时Cookie)</option>
            <option value="bili_user">[GET] /api/bilibili/user (B站个人资料与大会员)</option>
            <option value="baidu_quota">[GET] /api/baidupan/quota (百度网盘总配额)</option>
            <option value="chatgpt_status">[GET] /api/chatgpt/status (ChatGPT 逆向号池状态)</option>
            <option value="chatgpt_models">[GET] /api/chatgpt/models (ChatGPT 逆向模型列表)</option>
            <option value="chatgpt_accounts">[GET] /api/chatgpt/accounts (ChatGPT 号池账号总览)</option>
            <option value="chatgpt_sync">[POST] /api/chatgpt/accounts/sync-browser (从浏览器一键同步Token)</option>
            <option value="chatgpt_chat">[POST] /api/chatgpt/chat (ChatGPT 逆向智能问答)</option>
            <option value="chatgpt_image">[POST] /api/chatgpt/image (ChatGPT 逆向文生图 gpt-image-2)</option>
            <option value="openai_image">[POST] /v1/images/generations (OpenAI兼容图片生成)</option>
            <option value="chatgpt_session">[GET] /api/chatgpt/session (ChatGPT 会话提取)</option>
            <option value="suno_quota">[GET] /api/suno/quota (Suno 账户积分与可用曲目)</option>
            <option value="suno_feed">[GET] /api/suno/feed (Suno 历史曲库作品)</option>
            <option value="suno_gen">[POST] /api/suno/generate (Suno 音乐创作任务)</option>
            <option value="suno_lyrics">[POST] /api/suno/lyrics (Suno 独立歌词创作)</option>
          </select>
        </div>

        <!-- 模型与推理级别双控网格 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3" id="model-controls-grid">
          <!-- 模型选择下拉控件 -->
          <div id="model-select-container">
            <label class="text-xs font-semibold text-slate-300 uppercase block mb-1.5 flex items-center justify-between">
              <span><i class="fa-solid fa-cube text-cyan-400 mr-1.5"></i> 选择模型 (Model)</span>
            </label>
            <select id="model-selector" onchange="onModelOrReasoningChange()" class="w-full bg-slate-900 border border-cyan-500/40 rounded-xl px-3 py-2 text-xs text-cyan-300 focus:outline-none focus:border-cyan-400 shadow-inner">
              <option value="gemini-3.5-flash-lite">gemini-3.5-flash-lite (极速响应 · 推荐)</option>
              <option value="gemini-3.1-pro">gemini-3.1-pro (强推理 · 复杂任务)</option>
              <option value="gemini-3.6-flash">gemini-3.6-flash (多模态高通量 · 均衡)</option>
              <option value="gemini-3.8-flash">gemini-3.8-flash (新版 3.8 Flash 架构)</option>
              <option value="gemini-4-argon">gemini-4-argon (4 Argon 复杂推理)</option>
              <option value="auto">auto (ChatGPT 逆向智能优选)</option>
              <option value="gpt-5-6">gpt-5-6 (ChatGPT Web 逆向旗舰)</option>
              <option value="gpt-image-2">gpt-image-2 (ChatGPT 逆向文生图专用)</option>
              <option value="chatgpt-web">chatgpt-web (ChatGPT 网页原生)</option>
              <option value="gpt-4o">gpt-4o (OpenAI 协议通道映射)</option>
              <option value="gpt-3.5-turbo">gpt-3.5-turbo (OpenAI 兼容协议)</option>
            </select>
          </div>

          <!-- 推理级别下拉控件 -->
          <div id="reasoning-level-container">
            <label class="text-xs font-semibold text-slate-300 uppercase block mb-1.5 flex items-center justify-between">
              <span><i class="fa-solid fa-brain text-purple-400 mr-1.5"></i> 推理级别 (Reasoning)</span>
              <span class="text-[10px] text-purple-300 font-mono">思考链</span>
            </label>
            <select id="reasoning-selector" onchange="onModelOrReasoningChange()" class="w-full bg-slate-900 border border-purple-500/40 rounded-xl px-3 py-2 text-xs text-purple-300 focus:outline-none focus:border-purple-400 shadow-inner">
              <option value="off">🟢 关闭思考 / 快速模式 (Off · 直出)</option>
              <option value="medium">🟡 中等推理 (Medium · 适度权衡)</option>
              <option value="high">🟣 深度扩展思考 (High · 长思维链)</option>
            </select>
          </div>
        </div>

        <div class="flex gap-2 items-center">
          <span id="req-method-badge" class="px-2.5 py-1 rounded-lg text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">POST</span>
          <input type="text" id="req-endpoint" class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-400" value="/api/gemini/chat" readonly>
        </div>

        <div id="req-body-container">
          <label class="text-xs font-semibold text-slate-300 uppercase block mb-1.5 flex items-center justify-between">
            <span>请求 Body (JSON)</span>
            <span class="text-[10px] text-slate-400 font-normal">已自动联动模型与推理级别</span>
          </label>
          <textarea id="req-body" rows="6" class="w-full bg-slate-900 font-mono text-xs border border-slate-700 rounded-xl p-3 text-cyan-300 focus:outline-none focus:border-cyan-400"></textarea>
        </div>

        <button onclick="executeApiCall()" id="btn-send" class="w-full py-2.5 rounded-xl font-medium text-sm bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold transition shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2">
          <i class="fa-solid fa-paper-plane"></i> 发送请求 (Send Request)
        </button>
      </div>

      <!-- 响应输出区 -->
      <div class="lg:col-span-6 flex flex-col space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-300 uppercase">响应结果 (Response)</span>
          <div class="flex items-center gap-2">
            <span id="resp-status" class="text-xs px-2 py-0.5 rounded font-mono hidden">200 OK</span>
            <span id="resp-time" class="text-xs text-slate-400 font-mono">耗时: 0ms</span>
          </div>
        </div>
        <pre id="resp-output" class="flex-1 bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs font-mono text-emerald-400 overflow-auto min-h-[260px] max-h-[380px]">点击左侧「发送请求」发起调用，结果将展示在此处...</pre>
      </div>
    </section>

    <!-- 4. 详细 API 接口列表与规范 -->
    <section class="glass-card rounded-2xl p-6 shadow-xl space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
            <i class="fa-solid fa-list-check text-emerald-400"></i> 完整 API 接口清单
          </h2>
          <p class="text-xs text-slate-400">基于 OpenAPI 规范提供的企业级模块化接口定义</p>
        </div>
        <span class="text-xs text-slate-400">总计 16 个标准化端点</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <!-- Gemini 组 -->
        <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-2.5">
          <div class="font-bold text-amber-300 text-sm flex items-center gap-1.5">
            <i class="fa-solid fa-brain"></i> Google Gemini 多账号统一池
          </div>
          <div class="space-y-1.5 font-mono">
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> <span>/api/gemini/accounts</span></div>
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">POST</span> <span>/api/gemini/chat</span></div>
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">POST</span> <span>/api/gemini/accounts/{id}/check</span></div>
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">POST</span> <span>/api/gemini/accounts/{id}/rotate</span></div>
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">POST</span> <span>/api/gemini/refresh</span></div>
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> <span>/api/gemini/requests</span></div>
          </div>
        </div>

        <!-- OpenAI 兼容与系统组 -->
        <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-2.5">
          <div class="font-bold text-emerald-300 text-sm flex items-center gap-1.5">
            <i class="fa-solid fa-network-wired"></i> OpenAI 兼容 & 系统接口
          </div>
          <div class="space-y-1.5 font-mono">
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">POST</span> <span>/v1/chat/completions</span></div>
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> <span>/v1/models</span></div>
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> <span>/api/system/overview</span></div>
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> <span>/api/hub/status</span></div>
            <div class="flex items-center gap-2"><span class="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> <span>/api/hub/cookies</span></div>
          </div>
        </div>

        <!-- 外部 Web 业务组 -->
        <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-2.5 md:col-span-2">
          <div class="font-bold text-cyan-300 text-sm flex items-center gap-1.5">
            <i class="fa-solid fa-globe"></i> ChatGPT Web / Bilibili / 百度网盘 / Suno AI 音乐
          </div>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-2 font-mono">
            <div>
              <div class="text-slate-400 font-semibold mb-1">ChatGPT Web 桥接:</div>
              <div class="flex items-center gap-1.5"><span class="px-1 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> /api/chatgpt/session</div>
              <div class="flex items-center gap-1.5"><span class="px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">POST</span> /api/chatgpt/chat</div>
            </div>
            <div>
              <div class="text-slate-400 font-semibold mb-1">Bilibili 视频特权:</div>
              <div class="flex items-center gap-1.5"><span class="px-1 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> /api/bilibili/user</div>
              <div class="flex items-center gap-1.5"><span class="px-1 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> /api/bilibili/video</div>
            </div>
            <div>
              <div class="text-slate-400 font-semibold mb-1">百度网盘免密:</div>
              <div class="flex items-center gap-1.5"><span class="px-1 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> /api/baidupan/quota</div>
              <div class="flex items-center gap-1.5"><span class="px-1 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> /api/baidupan/files</div>
            </div>
            <div>
              <div class="text-slate-400 font-semibold mb-1">Suno AI 音乐生成:</div>
              <div class="flex items-center gap-1.5"><span class="px-1 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">GET</span> /api/suno/quota</div>
              <div class="flex items-center gap-1.5"><span class="px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">POST</span> /api/suno/generate</div>
            </div>
          </div>
        </div>
      </div>
    </section>

  </main>

  <script>
    const TEMPLATES = {
      gemini_chat: {
        method: "POST",
        url: "/api/gemini/chat",
        body: JSON.stringify({ prompt: "请用一句话告诉我：量子纠缠是什么？", model: "gemini-3.5-flash-lite", reasoning_level: "off", timeout: 60 }, null, 2)
      },
      openai_chat: {
        method: "POST",
        url: "/v1/chat/completions",
        body: JSON.stringify({ model: "gemini-3.5-flash-lite", messages: [{ role: "user", content: "请只回复两个字母：OK。" }], reasoning_level: "off" }, null, 2)
      },
      gemini_accounts: {
        method: "GET",
        url: "/api/gemini/accounts",
        body: ""
      },
      sync_profiles: {
        method: "POST",
        url: "/api/gemini/accounts/sync-profiles",
        body: "{}"
      },
      hub_status: {
        method: "GET",
        url: "/api/hub/status",
        body: ""
      },
      hub_cookies: {
        method: "GET",
        url: "/api/hub/cookies?domain=google.com",
        body: ""
      },
      bili_user: {
        method: "GET",
        url: "/api/bilibili/user",
        body: ""
      },
      baidu_quota: {
        method: "GET",
        url: "/api/baidupan/quota",
        body: ""
      },
      chatgpt_status: {
        method: "GET",
        url: "/api/chatgpt/status",
        body: ""
      },
      chatgpt_models: {
        method: "GET",
        url: "/api/chatgpt/models",
        body: ""
      },
      chatgpt_accounts: {
        method: "GET",
        url: "/api/chatgpt/accounts",
        body: ""
      },
      chatgpt_sync: {
        method: "POST",
        url: "/api/chatgpt/accounts/sync-browser",
        body: ""
      },
      chatgpt_chat: {
        method: "POST",
        url: "/api/chatgpt/chat",
        body: JSON.stringify({
          prompt: "请用幽默风趣的一句话自我介绍，并确认你已连接成功！",
          model: "auto"
        }, null, 2)
      },
      chatgpt_image: {
        method: "POST",
        url: "/api/chatgpt/image",
        body: JSON.stringify({
          prompt: "一只戴着宇航头盔的橙色猫咪在火星表面漫步，水彩插画风格，柔和光影",
          model: "gpt-image-2",
          n: 1,
          response_format: "b64_json"
        }, null, 2)
      },
      openai_image: {
        method: "POST",
        url: "/v1/images/generations",
        body: JSON.stringify({
          prompt: "一只赛博朋克风格的机械水母，发光透明触须，深海背景，8k超清",
          model: "gpt-image-2",
          n: 1
        }, null, 2)
      },
      chatgpt_session: {
        method: "GET",
        url: "/api/chatgpt/session",
        body: ""
      },
      suno_quota: {
        method: "GET",
        url: "/api/suno/quota",
        body: ""
      },
      suno_feed: {
        method: "GET",
        url: "/api/suno/feed?page=1",
        body: ""
      },
      suno_gen: {
        method: "POST",
        url: "/api/suno/generate",
        body: JSON.stringify({
          prompt: "一段欢快阳光的夏日流行海滩音乐，带有原声吉他和轻快的鼓点",
          is_custom: false,
          model: "chirp-v3-5",
          wait: false
        }, null, 2)
      },
      suno_lyrics: {
        method: "POST",
        url: "/api/suno/lyrics",
        body: JSON.stringify({
          prompt: "关于海风、阳光与夏天恋爱的流行歌词"
        }, null, 2)
      }
    };

    function onModelOrReasoningChange() {
      const baseModel = document.getElementById("model-selector").value;
      const reasoning = document.getElementById("reasoning-selector").value;
      const bodyEl = document.getElementById("req-body");
      if (!bodyEl || !bodyEl.value) return;

      try {
        const data = JSON.parse(bodyEl.value);
        let targetModel = baseModel;
        if (baseModel.startsWith("gemini")) {
          let raw = baseModel.replace("-thinking-medium", "").replace("-thinking", "").replace("-thinking-lite", "");
          if (reasoning === "high") {
            if (raw === "gemini-4-argon") targetModel = "gemini-4-argon-thinking";
            else if (raw === "gemini-3.8-flash" || raw === "gemini-3.7-flash") targetModel = "gemini-3.8-flash-thinking";
            else targetModel = raw + "-thinking";
          } else if (reasoning === "medium") {
            if (raw === "gemini-4-argon") targetModel = "gemini-4-argon-thinking-medium";
            else if (raw === "gemini-3.6-flash") targetModel = "gemini-3.6-flash-thinking";
            else targetModel = raw;
          } else {
            targetModel = raw;
          }
        }

        data.model = targetModel;
        data.reasoning_level = reasoning;
        bodyEl.value = JSON.stringify(data, null, 2);
      } catch (e) {}
    }

    function switchApiTemplate() {
      const key = document.getElementById("api-selector").value;
      const t = TEMPLATES[key];
      if (!t) return;
      document.getElementById("req-method-badge").innerText = t.method;
      document.getElementById("req-endpoint").value = t.url;
      const container = document.getElementById("req-body-container");
      const controlsGrid = document.getElementById("model-controls-grid");

      if (t.method === "GET") {
        container.style.display = "none";
        if (controlsGrid) controlsGrid.style.display = "none";
      } else {
        container.style.display = "block";
        document.getElementById("req-body").value = t.body;
        // 仅对对话类请求展示模型与推理级别组合框
        if (key === "gemini_chat" || key === "openai_chat") {
          if (controlsGrid) controlsGrid.style.display = "grid";
          try {
            const data = JSON.parse(t.body);
            if (data.model && document.getElementById("model-selector")) {
              let m = data.model;
              if (m.endsWith("-thinking")) m = m.replace("-thinking", "");
              if (m.endsWith("-thinking-medium")) m = m.replace("-thinking-medium", "");
              document.getElementById("model-selector").value = m;
            }
            if (data.reasoning_level && document.getElementById("reasoning-selector")) {
              document.getElementById("reasoning-selector").value = data.reasoning_level;
            }
          } catch (e) {}
        } else {
          if (controlsGrid) controlsGrid.style.display = "none";
        }
      }
    }

    async function executeApiCall() {
      const btn = document.getElementById("btn-send");
      const method = document.getElementById("req-method-badge").innerText;
      const endpoint = document.getElementById("req-endpoint").value;
      const out = document.getElementById("resp-output");
      const statusSpan = document.getElementById("resp-status");
      const timeSpan = document.getElementById("resp-time");

      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 正在调用...`;
      out.innerText = "请求发送中，等待响应...";

      const t0 = performance.now();
      try {
        const opts = { method: method, headers: { "Content-Type": "application/json" } };
        if (method === "POST") {
          opts.body = document.getElementById("req-body").value;
        }
        const resp = await fetch(endpoint, opts);
        const took = Math.round(performance.now() - t0);
        timeSpan.innerText = `耗时: ${took}ms`;
        statusSpan.classList.remove("hidden");
        statusSpan.innerText = `${resp.status} ${resp.statusText}`;
        if (resp.ok) {
          statusSpan.className = "text-xs px-2 py-0.5 rounded font-mono bg-emerald-500/20 text-emerald-400";
        } else {
          statusSpan.className = "text-xs px-2 py-0.5 rounded font-mono bg-rose-500/20 text-rose-400";
        }
        const data = await resp.json();
        out.innerText = JSON.stringify(data, null, 2);
      } catch (err) {
        timeSpan.innerText = `失败`;
        statusSpan.innerText = "Error";
        statusSpan.className = "text-xs px-2 py-0.5 rounded font-mono bg-rose-500/20 text-rose-400";
        out.innerText = "调用异常: " + err.message;
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> 发送请求 (Send Request)`;
      }
    }

    async function refreshDashboard() {
      const icon = document.getElementById("refresh-icon");
      icon.classList.add("fa-spin");

      try {
        // 1. 系统概览
        const sysRes = await fetch("/api/system/overview");
        if (sysRes.ok) {
          const sys = await sysRes.json();
          document.getElementById("uptime-text").innerText = `${Math.round(sys.uptime_seconds / 60)}m`;
          const hubOk = sys.services.cookie_hub.extension_connected;
          document.getElementById("hub-status-text").innerHTML = hubOk
            ? `<span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400"></span> 扩展已连接`
            : `<span class="inline-block w-2.5 h-2.5 rounded-full bg-rose-400"></span> 扩展未连接`;
          document.getElementById("hub-clients").innerText = `客户端: ${sys.services.cookie_hub.clients}`;
          document.getElementById("gemini-status-text").innerText = `${sys.services.gemini_pool.active_accounts} 账号就绪`;
        }

        // 2. 账号列表 (真实名称、邮箱与 5小时/周额度双指标展示)
        const acctRes = await fetch("/api/gemini/accounts");
        if (acctRes.ok) {
          const data = await acctRes.json();
          const tbody = document.getElementById("accounts-tbody");
          tbody.innerHTML = "";
          (data.accounts || []).forEach(a => {
            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-900/40 transition";
            const lastUsed = a.last_used_at > 0 ? new Date(a.last_used_at * 1000).toLocaleTimeString() : "从未调用";
            
            // 头像与初始字符
            const displayName = a.name ? a.name : (a.label || `账号槽位 u/${a.auth_user}`);
            const displayEmail = a.email ? a.email : '未解析邮箱';
            const initialChar = (displayName || displayEmail || 'G').trim().charAt(0).toUpperCase();

            // 5小时与周额度渲染
            const q5hUsed = a.quota_5h_used !== undefined ? a.quota_5h_used : 0;
            const q5hLimit = a.quota_5h_limit || 50;
            const q5hRemaining = a.quota_5h_remaining !== undefined ? a.quota_5h_remaining : (q5hLimit - q5hUsed);
            const q5hReset = a.quota_5h_reset_str || "滚动重置就绪";

            const qWeekUsed = a.quota_weekly_used !== undefined ? a.quota_weekly_used : 0;
            const qWeekLimit = a.quota_weekly_limit || 500;
            const qStatus = a.quota_status || "充裕 🟢";

            tr.innerHTML = `
              <td class="py-3 px-3 font-mono text-cyan-400 font-bold">#${a.id}</td>
              <td class="py-3 px-4">
                <div class="flex items-center gap-2.5">
                  <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-amber-500 to-indigo-600 flex items-center justify-center text-xs font-bold text-white shadow-md shadow-indigo-500/20 shrink-0">
                    ${initialChar}
                  </div>
                  <div>
                    <div class="font-semibold text-slate-100 flex items-center gap-1.5">
                      <span>${displayName}</span>
                      <span class="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">u/${a.auth_user}</span>
                    </div>
                    <div class="text-xs text-slate-400 font-mono flex items-center gap-1.5 mt-0.5">
                      <i class="fa-regular fa-envelope text-[11px] text-cyan-400"></i> ${displayEmail}
                    </div>
                  </div>
                </div>
              </td>
              <td class="py-3 px-3 text-xs font-mono text-slate-400">u/${a.auth_user}</td>
              <td class="py-3 px-4">
                <div class="space-y-1">
                  <div class="flex items-center gap-1.5">
                    <span class="px-2 py-0.5 rounded text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">已用: ${q5hUsed}/${q5hLimit}</span>
                    <span class="text-[11px] text-slate-400 font-mono">余 ${q5hRemaining}</span>
                  </div>
                  <div class="text-[11px] text-slate-400 font-mono flex items-center gap-1">
                    <i class="fa-regular fa-clock text-slate-500 text-[10px]"></i> ${q5hReset}
                  </div>
                </div>
              </td>
              <td class="py-3 px-4">
                <div class="space-y-1">
                  <div class="flex items-center gap-1.5">
                    <span class="px-2 py-0.5 rounded text-xs font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30">周累计: ${qWeekUsed}/${qWeekLimit}</span>
                  </div>
                  <div class="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
                    <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400"></span> ${qStatus}
                  </div>
                </div>
              </td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">可用 (LRU)</span></td>
              <td class="py-3 px-3 text-right space-x-1">
                <button onclick="checkAccount(${a.id})" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 border border-slate-700 transition">检测</button>
                <button onclick="rotateAccount(${a.id})" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-amber-400 border border-slate-700 transition">保活</button>
              </td>
            `;
            tbody.appendChild(tr);
          });
        }
      } catch (e) {
        console.error("刷新失败:", e);
      } finally {
        icon.classList.remove("fa-spin");
      }
    }

    async function syncProfiles() {
      const btn = document.getElementById("btn-sync-profiles");
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 正在提取 Google 用户名与邮箱...`;
      try {
        const res = await fetch("/api/gemini/accounts/sync-profiles", { method: "POST" });
        const data = await res.json();
        alert(data.message || "账号真实用户名与邮箱已同步！");
        await refreshDashboard();
      } catch (err) {
        alert("同步异常: " + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-id-card"></i> 同步真实名称与邮箱`;
      }
    }

    async function checkAccount(id) {
      alert("正在向 Google 验证账号 #" + id + " 凭证，请稍候...");
      const res = await fetch(`/api/gemini/accounts/${id}/check`, { method: "POST" });
      const data = await res.json();
      alert("检测结论: " + JSON.stringify(data));
      refreshDashboard();
    }

    async function rotateAccount(id) {
      alert("正在为账号 #" + id + " 申请令牌保活，请稍候...");
      const res = await fetch(`/api/gemini/accounts/${id}/rotate`, { method: "POST" });
      const data = await res.json();
      alert("保活结果: " + JSON.stringify(data));
      refreshDashboard();
    }

    async function refreshAllCookies() {
      if (!confirm("确认从当前浏览器 Cookie Hub 重新提取 Google 全量会话凭证？")) return;
      const res = await fetch("/api/gemini/refresh", { method: "POST" });
      const data = await res.json();
      alert("更新成功！" + data.message);
      refreshDashboard();
    }

    // 初始化
    switchApiTemplate();
    refreshDashboard();
    setInterval(refreshDashboard, 15000); // 15秒自动刷新一次
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, summary="Web 管理控制台", tags=["系统管理"])
def dashboard():
    """返回可视化管理面板 HTML 页面。"""
    return HTMLResponse(content=DASHBOARD_HTML)


if __name__ == "__main__":
    uvicorn.run("app_service:app", host="127.0.0.1", port=18800, reload=False)
