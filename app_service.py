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
import subprocess
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Path, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 保证本地通信不被外部代理拦截
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

from cookie_bridge import CookieBridge
from gemini_service import MultiAccountGeminiPool, GeminiService
from chatgpt_service import chatgpt_service, UnifiedChatGPTService, ChatGPTBridgeClient, ChatGPTReverseEngine
from bilibili_service import BilibiliService
from baidu_pan_service import BaiduPanService
from suno_service import SunoService, suno_service
from login_status import collect_login_status, failure_payload, gemini_failure_should_retry
from minimax_service import MinimaxAudioService, minimax_service, PRESET_VOICES, OPENAI_VOICE_MAP
from aistudio_service import aistudio_service, AIStudioService
from autostart import (
    is_autostart_enabled,
    enable_autostart,
    disable_autostart,
    toggle_autostart,
    get_autostart_entry,
)

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
    allow_origins=["http://127.0.0.1:18800", "http://localhost:18800", "http://127.0.0.1:18888", "http://localhost:18888"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态资源挂载 (网站图标与媒体文件)
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Reject DNS rebinding and cross-site browser requests before reaching sensitive Cookie/Token APIs.
@app.middleware("http")
async def restrict_local_api_origins(request: Request, call_next):
    host = request.headers.get("host", "").split(":")[0].lower()
    origin = request.headers.get("origin")
    allowed_origins = {"http://127.0.0.1:18800", "http://localhost:18800", "http://127.0.0.1:18888", "http://localhost:18888"}
    if host not in ("127.0.0.1", "localhost") or (origin is not None and origin not in allowed_origins):
        return PlainTextResponse("Forbidden local API access", status_code=403)
    return await call_next(request)

# 单例业务客户端
bridge_hub = CookieBridge()
gemini_pool = MultiAccountGeminiPool(port=18083, account_count=4)
chatgpt_client = chatgpt_service
bili_service = BilibiliService()
baidu_service = BaiduPanService()
suno_client = suno_service
minimax_client = minimax_service
aistudio_client = aistudio_service

START_TIME = datetime.datetime.now()


# ==========================================
# Pydantic 请求与响应模型
# ==========================================
class ChatRequest(BaseModel):
    prompt: str = Field(..., description="提问正文或指令内容", example="量子纠缠的基本原理是什么？")
    model: Optional[str] = Field("gemini-3.5-flash-lite", description="模型名称 (gemini-3.5-flash-lite, gemini-3.6-flash, gemini-3.1-pro 等)", example="gemini-3.5-flash-lite")
    reasoning_level: Optional[str] = Field("off", description="推理级别: 'off'(关闭思考/极速), 'medium'(中等推理), 'high'(深度扩展思考)", example="off")
    stream: Optional[bool] = Field(True, description="是否启用实时流式输出 (SSE)，默认为 True (首字秒出)", example=True)
    timeout: Optional[int] = Field(300, description="请求超时时间 (秒)，默认 300 秒", example=300)


class AIStudioChatRequest(BaseModel):
    prompt: str = Field(..., description="提问正文或指令内容", example="量子纠缠的基本原理是什么？")
    model: Optional[str] = Field("gemini-4-argon", description="模型名称 (gemini-4-argon, gemini-3.8-flash 等)", example="gemini-4-argon")
    stream: Optional[bool] = Field(True, description="是否启用实时流式输出 (SSE)，默认为 True (首字秒出)", example=True)
    timeout: Optional[int] = Field(120, description="请求超时时间 (秒)，默认 120 秒", example=120)


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
    stream: Optional[bool] = Field(True, description="是否启用流式输出，默认为 True (首字秒级直出)")
    temperature: Optional[float] = Field(0.7, example=0.7)


class SunoGenerateRequest(BaseModel):
    prompt: str = Field(..., description="音乐描述词或歌词全文", example="一段欢快的夏日流行海滩音乐，带有原声吉他和轻快的鼓点")
    is_custom: Optional[bool] = Field(False, description="是否为自定义模式 (歌词+风格)")
    tags: Optional[str] = Field("pop, acoustic guitar, cheerful", description="音乐流派风格标签 (仅自定义模式)")
    title: Optional[str] = Field("My Suno Song", description="歌曲标题")
    make_instrumental: Optional[bool] = Field(False, description="是否生成纯器乐伴奏 (无主唱)")
    model: Optional[str] = Field("chirp-goose", description="模型版本: chirp-goose (v6-mini 免费推荐), chirp-v3-5, chirp-v4 (需Pro)")
    wait: Optional[bool] = Field(False, description="是否等待渲染完成 (若为 False 则立即返回任务 clip ids)")
    download: Optional[bool] = Field(False, description="当 wait 为 True 时是否自动下载 MP3 到本地")


class SunoLyricsRequest(BaseModel):
    prompt: str = Field(..., description="歌词创作主题或提示词", example="写一首关于秋天落叶与远方思念的流行歌词")


class OpenAISpeechRequest(BaseModel):
    model: Optional[str] = Field("speech-01-hd", description="模型名称 (speech-01-hd, speech-02-hd, tts-1, tts-1-hd 等)", example="speech-01-hd")
    input: str = Field(..., description="要合成语音的文本内容", example="你好，这是通过 MiniMax 海螺语音实时生成的语音。")
    voice: Optional[str] = Field("alloy", description="音色名称或 ID (支持 alloy, nova, onyx, shimmer, fable, echo 或特定 voice_id)", example="alloy")
    response_format: Optional[str] = Field("mp3", description="音频格式 (mp3, wav 等)", example="mp3")
    speed: Optional[float] = Field(1.0, description="语速 (0.5 - 2.0)", ge=0.5, le=2.0)


class MinimaxSpeechRequest(BaseModel):
    text: str = Field(..., description="合成文本内容", example="欢迎使用 MiniMax 语音合成服务")
    voice_id: Optional[str] = Field("226869000163456", description="音色 ID 或别名")
    speed: Optional[float] = Field(1.0, description="语速 (0.5 - 2.0)", ge=0.5, le=2.0)
    vol: Optional[float] = Field(1.0, description="音量 (0.1 - 2.0)")
    pitch: Optional[float] = Field(0.0, description="语调音高 (-12 - 12)")
    format: Optional[str] = Field("mp3", description="音频格式 (mp3, wav)")


# ==========================================
# 1. 核心系统概览与状态接口
# ==========================================
def _service_error(status_code: int, message: str, service_id: str) -> None:
    raise HTTPException(status_code=status_code, detail=failure_payload(message, service_id))


def _gemini_stop(message: str) -> None:
    from login_status import gemini_failure_kind

    kind = gemini_failure_kind(message)
    _service_error(429 if kind in {"pace", "blocked"} else 502, message, "gemini")


@app.get("/api/system/logins", summary="检查各站点是否已在浏览器登录", tags=["系统管理"])
def get_login_status():
    """通过 Cookie Hub 判断 Gemini、ChatGPT、百度网盘、Suno、哔哩哔哩哪些还没登录。"""
    status = collect_login_status()
    hint = chatgpt_client.public_account()
    if not hint and chatgpt_client.reverse.is_running():
        try:
            usable = [
                account for account in chatgpt_client.reverse.list_accounts()
                if account.get("status") not in ("异常", "禁用")
            ]
            if usable:
                plan = str(usable[0].get("type") or "free")
                hint = {"plan": plan, "plan_label": chatgpt_client.plan_label(plan)}
        except Exception:
            hint = {}
    if hint:
        for item in status.get("services") or []:
            if item.get("id") == "chatgpt" and item.get("logged_in"):
                item["plan"] = hint.get("plan")
                item["plan_label"] = hint.get("plan_label")
                item["hint"] = f"浏览器已登录 ChatGPT，当前是{hint.get('plan_label')}账号。"
                if str(hint.get("plan") or "").lower() == "free":
                    item["free_models"] = {
                        "thinking": {"id": "gpt-6-t-mini", "label": "思考（Thinking mini / 6 Thinking）"},
                        "instant": {"id": "gpt-6", "label": "不思考（Instant / 6 Instant，日常聊天）"},
                    }
    return status


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

    gemini_running = False
    gemini_accounts = []
    try:
        gemini_running = gemini_pool.is_running()
        if gemini_running:
            gemini_accounts = gemini_pool.list_accounts()
    except Exception:
        pass

    uptime_sec = int((datetime.datetime.now() - START_TIME).total_seconds())
    chatgpt_status = {}
    try:
        chatgpt_status = chatgpt_client.get_status()
    except Exception:
        pass

    aistudio_status = {}
    try:
        aistudio_status = aistudio_client.get_status()
    except Exception:
        pass

    autostart_ok = False
    autostart_desc = None
    try:
        autostart_ok = is_autostart_enabled()
        autostart_desc = get_autostart_entry()
    except Exception:
        pass

    return {
        "status": "online",
        "service_name": "Cookie Service Suite",
        "version": "2.0.0",
        "uptime_seconds": uptime_sec,
        "autostart": {
            "enabled": autostart_ok,
            "status": "enabled" if autostart_ok else "disabled",
            "entry": autostart_desc,
        },
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
            "aistudio": {
                "port": aistudio_client.port,
                "status": "running" if aistudio_status.get("running") else "stopped",
                "running": aistudio_status.get("running", False),
                "data_plane_ready": aistudio_status.get("data_plane_ready", False),
                "state": aistudio_status.get("state", "STOPPED"),
                "accounts_total": aistudio_status.get("accounts_total", 0),
                "accounts_ready": aistudio_status.get("accounts_ready", 0),
                "models_count": aistudio_status.get("models_count", 0),
            },
            "minimax_audio": {
                "status": "ready" if bool(minimax_client.token) else ("connected" if hub_ok else "idle"),
                "token_ready": bool(minimax_client.token),
                "voices_count": len(PRESET_VOICES),
            },
        },
    }


@app.get("/api/system/autostart", summary="获取 Windows 开机自启状态", tags=["系统管理"])
def get_system_autostart():
    """检测当前套件是否已在 Windows 注册表 Run 或开始菜单 Startup 注册开机自启。"""
    try:
        enabled = is_autostart_enabled()
        return {
            "enabled": enabled,
            "status": "enabled" if enabled else "disabled",
            "entry": get_autostart_entry(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/autostart/toggle", summary="一键切换 Windows 开机自启动开启/关闭状态", tags=["系统管理"])
def toggle_system_autostart():
    """在开启 (双重保障: 注册表+开始菜单) 与关闭之间一键切换。"""
    try:
        ok, msg = toggle_autostart()
        enabled = is_autostart_enabled()
        return {
            "success": ok,
            "enabled": enabled,
            "status": "enabled" if enabled else "disabled",
            "message": msg,
            "entry": get_autostart_entry(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/open-directory", summary="在系统资源管理器中打开项目根目录", tags=["系统管理"])
def open_project_directory():
    """在 Windows 资源管理器中打开当前项目所在目录。"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if sys.platform == "win32":
            try:
                os.startfile(base_dir)
            except Exception:
                subprocess.Popen(["explorer.exe", base_dir])
        else:
            subprocess.Popen(["xdg-open", base_dir])
        return {"success": True, "message": "已在资源管理器中打开项目目录", "path": base_dir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开项目目录失败: {str(e)}")


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


def is_upstream_refusal(text: Optional[str]) -> bool:
    """检测 Google Gemini 网页端返回的是否为通用拒绝文案而非真正成稿。"""
    if not text:
        return False
    blob = text.strip().lower()
    if len(blob) > 200:
        return False
    refusal_keywords = [
        "我无法提供这方面的帮助，因为我只是一个语言模型",
        "我只是一个语言模型，理解不了这个问题",
        "我无法提供这方面的帮助",
        "我只是一个语言模型",
        "cannot fulfill this request",
        "can't fulfill this request",
        "i am unable to help with that as i am only a language model",
        "i'm unable to help with that as i am only a language model",
        "cannot help with that as i am only a language model",
        "can't help with that as i am only a language model",
    ]
    return any(k in blob for k in refusal_keywords)


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
    model_name = (req.model or "gemini-3.8-flash").lower().strip()
    # 动态适配充足安全超时时间：根据模型复杂度智能调整下限，避免因客户端超时过短切断连接
    if any(m in model_name for m in ["3.8", "3.6", "4-", "pro", "thinking"]):
        min_timeout = 600
    else:
        min_timeout = 180
    effective_timeout = max(req.timeout or min_timeout, min_timeout)

    # 1. 默认优先走实时流式输出 (SSE)：首字毫秒级直出，体验与真实网页端一致
    if req.stream:
        return StreamingResponse(
            gemini_pool.stream_chat(
                prompt=req.prompt, model=req.model, reasoning_level=reasoning, timeout=effective_timeout
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    # 2. 非流式聚合调用

    try:
        res = gemini_pool.ask_with_details(
            prompt=req.prompt, model=req.model, reasoning_level=reasoning, timeout=effective_timeout
        )
        # 拦截上游软拒绝（如"我无法提供这方面的帮助，因为我只是一个语言模型"），自动触发轮换换号重试
        if is_upstream_refusal(res.get("reply")):
            refusal_text = res.get("reply")
            print(f"⚠️ [Gemini Chat] 账号 {res.get('account_label')} 返回通用拒绝文案: '{refusal_text}'，自动切换下一个账号重试...", flush=True)
            raise RuntimeError(f"Google 上游会话软拒绝: {refusal_text}")
    except Exception as first_err:
        if not gemini_failure_should_retry(str(first_err)):
            _gemini_stop(str(first_err))
        print(f"⚠️ [Gemini Chat] 调度异常: {first_err}，尝试自愈并轮换至下一账号重试...", flush=True)
        # 自动故障自愈：重置代理熔断计数 + 刷新最新 Cookie 凭证后重试一次
        try:
            gemini_pool.reset_proxies()
            gemini_pool.refresh_pool_cookies()
            res = gemini_pool.ask_with_details(
                prompt=req.prompt, model=req.model, reasoning_level=reasoning, timeout=effective_timeout
            )
            # 若重试仍然返回通用拒绝，再次尝试轮换
            if is_upstream_refusal(res.get("reply")):
                print(f"⚠️ [Gemini Chat] 账号 {res.get('account_label')} 依然返回拒绝，发起备用轮转...", flush=True)
                res = gemini_pool.ask_with_details(
                    prompt=req.prompt, model=req.model, reasoning_level=reasoning, timeout=effective_timeout
                )
        except Exception as retry_err:
            detail_msg = f"Gemini 调度调用失败: {first_err} (自愈重试亦未成功: {retry_err})"
            _service_error(502, detail_msg, "gemini")

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


@app.get("/api/gemini/pace-status", summary="获取当前 Gemini 调用频率与并发状态", tags=["Gemini 多账号调度"])
def get_gemini_pace_status():
    """获取当前 Gemini 并发与频率控制状态 (是否允许调用、倒计时秒数、上次错误原因)。"""
    return gemini_pool.pace_status()


@app.post("/api/gemini/reset-pace", summary="强制复位 Gemini 频率与并发保护锁", tags=["Gemini 多账号调度"])
def reset_gemini_pace():
    """管理员或用户一键强制解锁并发保护，立即恢复可调用状态。"""
    gemini_pool.reset_pace()
    return {"success": True, "message": "Gemini 调用锁与冷却状态已成功强制复位！"}


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
        _service_error(502, f"无法获取 ChatGPT 会话: {str(e)}", "chatgpt")


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
        _service_error(502, f"从浏览器同步 Token 失败: {str(e)}", "chatgpt")


@app.post("/api/chatgpt/chat", summary="向 ChatGPT 发起智能对话 (支持逆向与桥接双引擎)", tags=["ChatGPT 逆向与号池"])
def chatgpt_ask(req: ChatRequest):
    """优先使用无头逆向引擎直连，若未就绪则自动降级到浏览器同源扩展。支持流式与非流式。"""
    try:
        if req.stream:
            def _chatgpt_sse_gen():
                messages = [{"role": "user", "content": req.prompt}]
                try:
                    for chunk in chatgpt_client.chat(messages, model=req.model or "auto", stream=True):
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    err_data = {"error": {"message": str(e), "type": "chatgpt_error"}}
                    yield f"data: {json.dumps(err_data, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                _chatgpt_sse_gen(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )

        reply = chatgpt_client.ask(req.prompt, model=req.model or "auto")
        return {"success": True, "reply": reply}
    except Exception as e:
        _service_error(502, f"ChatGPT 提问失败: {str(e)}", "chatgpt")


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
# 3.5. Google AI Studio 逆向工程与模型直连
# ==========================================
@app.get("/api/aistudio/status", summary="获取 Google AI Studio 逆向服务全景状态", tags=["Google AI Studio 逆向"])
def aistudio_get_status():
    """检测 aistudio2api 进程状态、数据面就绪情况、导入账号与可用模型清单。"""
    try:
        return aistudio_client.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 AI Studio 状态异常: {str(e)}")


@app.post("/api/aistudio/start", summary="启动 Google AI Studio 逆向后台服务", tags=["Google AI Studio 逆向"])
def aistudio_start_service():
    """手动启动 aistudio2api 核心引擎并激活数据面。"""
    try:
        ok = aistudio_client.start()
        return {
            "success": ok,
            "message": "AI Studio 逆向服务已成功启动并就绪" if ok else "启动失败，请检查控制台日志",
            "status": aistudio_client.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动 AI Studio 服务失败: {str(e)}")


@app.post("/api/aistudio/stop", summary="停止 Google AI Studio 逆向后台服务", tags=["Google AI Studio 逆向"])
def aistudio_stop_service():
    """停止 aistudio2api 核心引擎与数据面。"""
    try:
        ok = aistudio_client.stop()
        return {
            "success": ok,
            "message": "AI Studio 逆向服务已停止",
            "status": aistudio_client.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止 AI Studio 服务失败: {str(e)}")


@app.post("/api/aistudio/restart", summary="重启 Google AI Studio 逆向服务", tags=["Google AI Studio 逆向"])
def aistudio_restart_service():
    """重启 aistudio2api 引擎并重新加载账号凭证与 BotGuard 引擎。"""
    try:
        ok = aistudio_client.restart()
        return {
            "success": ok,
            "message": "AI Studio 逆向服务已重启并重新就绪" if ok else "重启失败",
            "status": aistudio_client.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启 AI Studio 服务失败: {str(e)}")


@app.get("/api/aistudio/accounts", summary="获取已导入的 AI Studio 账号列表", tags=["Google AI Studio 逆向"])
def aistudio_list_accounts():
    """查看已绑定的 Google 账号列表及健康状态。"""
    try:
        accounts = aistudio_client.list_accounts()
        return {"accounts": accounts, "total": len(accounts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取账号列表失败: {str(e)}")


@app.get("/api/aistudio/models", summary="获取 AI Studio 可用原生模型列表", tags=["Google AI Studio 逆向"])
def aistudio_list_models():
    """获取 AI Studio 原生暴露的 78+ 模型清单（包括 gemini-4-argon 等最新实验模型）。"""
    try:
        models = aistudio_client.list_models()
        return {"models": models, "total": len(models)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@app.post("/api/aistudio/sync-cookies", summary="从浏览器 Cookie Hub 一键同步 Google 凭证入池", tags=["Google AI Studio 逆向"])
def aistudio_sync_cookies():
    """从本地 Cookie Hub 提取最新 google.com 登录凭证并自动生成 account.json 入池。"""
    try:
        res = aistudio_client.sync_cookies_from_hub()
        return res
    except Exception as e:
        _service_error(500, f"同步 AI Studio 凭证失败: {str(e)}", "aistudio")


@app.post("/api/aistudio/chat", summary="向 Google AI Studio 发起原生智能对话", tags=["Google AI Studio 逆向"])
def aistudio_chat(req: AIStudioChatRequest):
    """
    通过 Google AI Studio Playground 逆向原生通道调用 Gemini 大模型，
    支持 gemini-4-argon, gemini-3.8-flash 等全系列模型，支持流式 SSE 打字机输出。
    """
    try:
        if req.stream:
            stream_gen = aistudio_client.chat(
                prompt=req.prompt,
                model=req.model or "gemini-4-argon",
                stream=True,
                timeout=req.timeout or 120,
            )
            return StreamingResponse(
                stream_gen,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            result = aistudio_client.chat(
                prompt=req.prompt,
                model=req.model or "gemini-4-argon",
                stream=False,
                timeout=req.timeout or 120,
            )
            return {"success": True, "result": result}
    except Exception as e:
        _service_error(502, f"AI Studio 对话请求失败: {str(e)}", "aistudio")


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
        _service_error(500, f"查询网盘配额失败: {str(e)}", "baidu")


@app.get("/api/baidupan/user", summary="获取百度网盘账号资料与 VIP 等级", tags=["百度网盘服务"])
def get_baidupan_user():
    try:
        return baidu_service.get_user_info()
    except Exception as e:
        _service_error(500, f"查询网盘用户失败: {str(e)}", "baidu")


@app.get("/api/baidupan/files", summary="遍历百度网盘指定目录下的文件", tags=["百度网盘服务"])
def list_baidupan_files(dir_path: str = Query("/", description="网盘目录路径，默认根目录 /")):
    try:
        return baidu_service.list_files(dir_path=dir_path)
    except Exception as e:
        _service_error(500, f"遍历网盘文件失败: {str(e)}", "baidu")


@app.post("/api/baidupan/refresh", summary="强制从浏览器刷新百度网盘凭证", tags=["百度网盘服务"])
def refresh_baidupan_auth():
    try:
        return baidu_service.refresh_auth()
    except Exception as e:
        _service_error(500, f"刷新网盘凭证失败: {str(e)}", "baidu")


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
        _service_error(500, f"查询 Suno 配额失败: {str(e)}", "suno")


def _enrich_suno_clips(clips_data: Any) -> Any:
    """自动将 Suno 加密的 forbidden audio_url 重写为本地无缝代理流，并保留原始直链"""
    if isinstance(clips_data, list):
        for item in clips_data:
            if isinstance(item, dict):
                cid = item.get("id")
                if cid:
                    item["local_audio_url"] = f"/api/suno/audio/{cid}"
                    raw_audio = str(item.get("audio_url", ""))
                    if "forbidden" in raw_audio or not raw_audio:
                        item["raw_audio_url"] = raw_audio
                        item["audio_url"] = f"/api/suno/audio/{cid}"
    return clips_data


@app.get("/api/suno/feed", summary="获取 Suno 历史作品曲库列表", tags=["Suno 音乐生成"])
def get_suno_feed(page: int = Query(1, ge=1, description="页码")):
    try:
        clips = suno_client.get_feed(page=page)
        return _enrich_suno_clips(clips)
    except Exception as e:
        _service_error(500, f"获取 Suno 历史曲库失败: {str(e)}", "suno")


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
        _service_error(500, f"提交 Suno 音乐生成失败: {str(e)}", "suno")


@app.get("/api/suno/status", summary="查询指定 clip ids 的生成状态与音频直链", tags=["Suno 音乐生成"])
def get_suno_status(clip_ids: str = Query(..., description="待查询的 clip ID，多个用英文逗号隔开")):
    try:
        id_list = [i.strip() for i in clip_ids.split(",") if i.strip()]
        clips = suno_client.fetch_clips_status(id_list)
        return _enrich_suno_clips(clips)
    except Exception as e:
        _service_error(500, f"查询任务状态失败: {str(e)}", "suno")


@app.post("/api/suno/lyrics", summary="使用 Suno AI 单独创作歌词", tags=["Suno 音乐生成"])
def generate_suno_lyrics(req: SunoLyricsRequest):
    try:
        return suno_client.generate_lyrics(prompt=req.prompt)
    except Exception as e:
        _service_error(500, f"创作歌词失败: {str(e)}", "suno")


@app.post("/api/suno/refresh", summary="强制刷新 Suno 凭证与 Clerk JWT 令牌", tags=["Suno 音乐生成"])
def refresh_suno_auth():
    try:
        return suno_client.refresh_auth()
    except Exception as e:
        _service_error(500, f"刷新 Suno 凭证失败: {str(e)}", "suno")


@app.get("/api/suno/audio/{clip_id}", summary="解密并流式播放/下载指定 Clip 音频", tags=["Suno 音乐生成"])
def get_suno_audio(clip_id: str = Path(..., description="Suno 歌曲 Clip ID")):
    try:
        file_path = suno_client.get_or_decrypt_clip(clip_id)
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="音频文件未能成功解密")

        media_type = "audio/mp4" if file_path.lower().endswith(".m4a") else "audio/mpeg"
        filename = os.path.basename(file_path)
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename,
            headers={"Accept-Ranges": "bytes"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解密音频流失败: {str(e)}")


# ==========================================
# 6.8. MiniMax / 海螺语音服务 (/api/minimax/*)
# ==========================================
@app.get("/api/minimax/status", summary="获取 MiniMax 登录态与会话就绪状态", tags=["MiniMax 语音合成"])
def get_minimax_status():
    is_ready = bool(minimax_client.token)
    return {
        "status": "ready" if is_ready else "not_configured",
        "token_ready": is_ready,
        "uuid": minimax_client.uuid,
        "device_id": minimax_client.device_id,
        "cached_time": minimax_client.last_fetch_time,
        "preset_voices_count": len(PRESET_VOICES)
    }


@app.get("/api/minimax/voices", summary="获取 MiniMax 预置及可用音色列表", tags=["MiniMax 语音合成"])
def get_minimax_voices():
    return {"success": True, "voices": minimax_client.get_voices()}


@app.get("/api/minimax/quota", summary="获取 MiniMax 账户剩余字符配额与积分", tags=["MiniMax 语音合成"])
def get_minimax_quota():
    return minimax_client.get_quota()


@app.post("/api/minimax/speech", summary="MiniMax 高级语音合成", tags=["MiniMax 语音合成"])
def post_minimax_speech(req: MinimaxSpeechRequest):
    import io
    try:
        audio_bytes = minimax_client.synthesize(
            text=req.text,
            voice=req.voice_id or "226869000163456",
            speed=req.speed or 1.0,
            vol=req.vol or 1.0,
            pitch=req.pitch or 0.0,
            format=req.format or "mp3"
        )
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'attachment; filename="minimax_{int(time.time())}.mp3"',
                "Content-Length": str(len(audio_bytes))
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MiniMax 语音合成失败: {str(e)}")


@app.post("/api/minimax/auto_fetch", summary="通知浏览器扩展唤醒并自动拉取 MiniMax 登录态", tags=["MiniMax 语音合成"])
def post_minimax_auto_fetch(force: bool = Query(True, description="是否强制后台打开页面以唤醒会话")):
    res = minimax_client.auto_refresh_auth(force_visit=force, timeout=20)
    return res


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

    # 0. Google AI Studio 逆向分流
    if model_name.startswith("aistudio") or model_name.startswith("gemini-4") or "argon" in model_name:
        actual_model = req.model.replace("aistudio/", "").replace("aistudio-", "") if req.model else "gemini-4-argon"
        messages_payload = [{"role": m.role, "content": m.content} for m in req.messages]
        req_timeout = getattr(req, "timeout", None) or 120
        if req.stream:
            return StreamingResponse(
                aistudio_client.chat(
                    prompt=last_user_msg,
                    model=actual_model,
                    stream=True,
                    messages=messages_payload,
                    timeout=req_timeout,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            try:
                res = aistudio_client.chat(
                    prompt=last_user_msg,
                    model=actual_model,
                    stream=False,
                    messages=messages_payload,
                    timeout=req_timeout,
                )
                return res
            except Exception as e:
                _service_error(502, f"AI Studio 兼容接口调用失败: {str(e)}", "aistudio")

    # 1. Gemini 分流
    if model_name.startswith("gemini"):
        if not gemini_pool.is_running():
            gemini_pool.start()

        target_model = req.model if req.model and "gemini" in req.model else "gemini-3.8-flash"
        reasoning = req.reasoning_effort or req.reasoning_level or "off"
        messages_payload = [{"role": m.role, "content": m.content} for m in req.messages]

        if req.stream:
            return StreamingResponse(
                gemini_pool.stream_chat_messages(
                    messages=messages_payload, model=target_model, reasoning_level=reasoning
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )

        try:
            res = gemini_pool.ask_with_details(
                prompt=last_user_msg, model=target_model, reasoning_level=reasoning
            )
        except Exception as first_err:
            if not gemini_failure_should_retry(str(first_err)):
                _gemini_stop(str(first_err))
            try:
                gemini_pool.refresh_pool_cookies()
                res = gemini_pool.ask_with_details(
                    prompt=last_user_msg, model=target_model, reasoning_level=reasoning
                )
            except Exception as retry_err:
                _service_error(502, f"Gemini 兼容接口调用失败: {str(retry_err)}", "gemini")

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

    # 2. ChatGPT 分流 (逆向引擎 + 扩展模拟桥接)
    req_model_lower = (req.model or "").lower().strip()
    if "moni" in req_model_lower or req_model_lower in ("chatgpt-web", "chatgpt-web-moni"):
        target_gpt_model = "chatgpt-web-moni"
    elif req_model_lower in ("gpt-4o", "gpt-3.5-turbo"):
        target_gpt_model = "auto"  # 已下线模型平滑过渡至 auto
    elif req.model:
        target_gpt_model = req.model
    else:
        target_gpt_model = "auto"

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
            _service_error(502, f"ChatGPT 兼容调用失败: {str(fallback_err)}", "chatgpt")


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


@app.post("/v1/audio/speech", summary="OpenAI 兼容语音合成接口", tags=["OpenAI 兼容接口"])
def openai_audio_speech(body: OpenAISpeechRequest):
    """
    提供标准 OpenAI POST /v1/audio/speech 接口，
    底层自动路由到 MiniMax / 海螺语音平台原生 WebSocket 与模型进行超自然高保真语音渲染。
    返回标准 audio/mpeg 二进制音频流。
    """
    import io
    try:
        audio_bytes = minimax_client.synthesize(
            text=body.input,
            voice=body.voice or "alloy",
            speed=body.speed or 1.0,
            format=body.response_format or "mp3"
        )
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'attachment; filename="speech_{int(time.time())}.mp3"',
                "Content-Length": str(len(audio_bytes))
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


# 模型元数据中文描述字典 (区分日常聊天 Chat 与工作台 Work 专有模型)
REVERSE_MODEL_DESCRIPTIONS = {
    # --- 语音合成模型 (MiniMax TTS: OpenAI 兼容) ---
    "speech-01-hd": "[超自然语音/TTS] MiniMax 海螺语音 HD 高保真自然拟真模型",
    "speech-02-hd": "[超自然语音/TTS] MiniMax 旗舰超自然语音合成模型",
    "tts-1": "[语音合成/TTS] OpenAI 兼容快速语音合成 (由 MiniMax 驱动)",
    "tts-1-hd": "[语音合成/TTS] OpenAI 兼容高保真语音合成 (由 MiniMax 驱动)",
    # --- 日常聊天专有模型 (Chat Mode: is_work_mode_model = false) ---
    "auto": "[日常聊天/Auto] ChatGPT 智能自动优选模型",
    "gpt-6-thinking": "[思考/旧标识] 当前免费账号的模型列表里没有这个 slug，请改用 gpt-6-t-mini",
    "gpt-6": "[免费账号/不思考] Instant，选择器短名「6 Instant」，适用于日常聊天。官方备注会自动决定思考时长，不是专用思考模型。",
    "gpt-6-instant": "[极速响应/Chat] GPT-6 极速即时响应模型",
    "gpt-6-mini": "[不思考] reasoning_type=none。当前免费选择器没有单独露出这一项。",
    "gpt-6-t-mini": "[免费账号/思考] Thinking mini，选择器短名「6 Thinking」，官方说明是快速思考。这是当前免费账号里的思考模型。",
    "gpt-6-t-mini-mini": "[思考] 更小的思考档。当前免费选择器没有单独露出，露出的思考模型是 gpt-6-t-mini。",
    "gpt-5-6-thinking": "[思考/旧标识] 当前免费账号的模型列表里没有这个 slug",
    "gpt-5-6": "[自动] reasoning_type=auto。账号列表里有，不是免费选择器的两个主模型。",
    "gpt-5-6-instant": "[极速响应/Chat] GPT-5.6 极速即时响应模型",
    "gpt-5-6-mini": "[不思考] reasoning_type=none。不是免费选择器里的两个主模型。",
    "gpt-5-6-t-mini": "[思考] reasoning_type=reasoning。不是免费选择器当前露出的思考档。",
    "gpt-5-6-t-mini-mini": "[思考] reasoning_type=reasoning。不是免费选择器当前露出的思考档。",
    "research": "[学术研报/Research] ChatGPT 全网深度学术与研报挖掘模型 (Deep Research)",
    "gpt-image-2": "[文生图/Image] ChatGPT 官方逆向绘图专用 (DALL-E 3)",
    "codex-gpt-image-2": "[高清绘图/Codex] ChatGPT Codex 高清画图专用",

    # --- Work 协同工作台专有模型 (Work Mode: is_work_mode_model = true, 官方带 -wm 后缀) ---
    "gpt-6-sol-wm": "[工作台专有/Work] GPT-6 Sol 协同工作区模型",
    "gpt-6-luna-wm": "[工作台专有/Work] GPT-6 Luna 协同工作区模型",
    "gpt-6-astra-wm": "[工作台专有/Work] GPT-6 Astra 协同工作区模型",
    "gpt-6.1-sol-wm": "[工作台专有/Work] GPT-6.1 Sol 演进工作区模型",
    "gpt-6.1-terra-wm": "[工作台专有/Work] GPT-6.1 Terra 演进工作区模型",
    "gpt-5.6-sol-wm": "[工作台专有/Work] GPT-5.6 Sol 协同工作区模型",
    "gpt-5.6-luna-wm": "[工作台专有/Work] GPT-5.6 Luna 协同工作区模型",
    "gpt-5.6-terra-wm": "[工作台专有/Work] GPT-5.6 Terra 协同工作区模型",
}


def _chatgpt_reasoning(model_id: str) -> str:
    """免费账号实探：思考是 gpt-6-t-mini，不思考是 gpt-6。"""
    return {
        "gpt-6-t-mini": "thinking",
        "gpt-6-t-mini-mini": "thinking",
        "gpt-5-6-t-mini": "thinking",
        "gpt-5-6-t-mini-mini": "thinking",
        "gpt-6": "instant",
        "auto": "auto",
        "gpt-5-6": "auto",
        "gpt-6-mini": "none",
        "gpt-5-6-mini": "none",
        "research": "none",
    }.get(model_id, "")


@app.get("/v1/models", summary="OpenAI 兼容模型列表", tags=["OpenAI 兼容接口"])
def openai_models():
    """返回 OpenAI 兼容模型列表，动态同步逆向引擎真实可用模型并打标：
    - moni (网页模拟输入): 基于浏览器 DOM 模拟键盘输入与发送 (chatgpt-web, chatgpt-web-moni)
    - reverse (协议逆向直连): 包含 GPT-6 / GPT-5.6 的 thinking、instant、mini 系列及深度研究模型
    - pool (谷歌号池直连): Google Gemini 多账号自动轮询直连
    - 已彻底移除官方下线的过时 gpt-4o 模型
    """
    reverse_models = []
    seen_ids = set()

    # 1. 优先从运行中的逆向引擎动态提取实时模型
    if chatgpt_client.reverse.is_running():
        try:
            raw_res = chatgpt_client.reverse.get_models()
            for item in raw_res.get("data", []):
                mid = str(item.get("id") or "").strip()
                if not mid or mid in seen_ids:
                    continue
                # 过滤内部 gate 占位符
                if "reserved_gate" in mid:
                    continue
                seen_ids.add(mid)
                desc = REVERSE_MODEL_DESCRIPTIONS.get(mid, f"[协议逆向直连] ChatGPT 官方模型 ({mid})")
                is_wm = "-wm" in mid.lower()
                row = {
                    "id": mid,
                    "object": "model",
                    "owned_by": "openai-reverse",
                    "tag": "reverse",
                    "type": "api_reverse",
                    "scene": "work" if is_wm else "chat",
                    "description": desc,
                }
                reasoning = _chatgpt_reasoning(mid)
                if reasoning:
                    row["reasoning"] = reasoning
                reverse_models.append(row)
        except Exception:
            pass

    # 兜底回退：若逆向引擎暂时未拉取到，使用内建全量逆向清单 (包含 thinking，无 4o)
    if not reverse_models:
        for mid, desc in REVERSE_MODEL_DESCRIPTIONS.items():
            is_wm = "-wm" in mid.lower()
            row = {
                "id": mid,
                "object": "model",
                "owned_by": "openai-reverse",
                "tag": "reverse",
                "type": "api_reverse",
                "scene": "work" if is_wm else "chat",
                "description": desc,
            }
            reasoning = _chatgpt_reasoning(mid)
            if reasoning:
                row["reasoning"] = reasoning
            reverse_models.append(row)

    # 2. 网页模拟输入模型 (专属 moni 标签)
    moni_models = [
        {"id": "chatgpt-web-moni", "object": "model", "owned_by": "moni", "tag": "moni", "type": "dom_simulated", "description": "[网页模拟输入/moni] 浏览器扩展 DOM 按键与点击输入模拟"},
        {"id": "chatgpt-web", "object": "model", "owned_by": "moni", "tag": "moni", "type": "dom_simulated", "description": "[网页模拟输入/moni] ChatGPT 浏览器同源页面输入桥接"},
    ]

    # 3. Google 多账号池直连模型
    gemini_models = [
        {"id": "gemini-3.5-flash-lite", "object": "model", "owned_by": "google-cookie-suite", "tag": "pool", "type": "gemini_pool", "description": "[号池协议直连] 极速响应毫秒级，推荐默认"},
        {"id": "gemini-3.1-pro", "object": "model", "owned_by": "google-cookie-suite", "tag": "pool", "type": "gemini_pool", "description": "[号池协议直连] 高智力强推理，适合复杂任务"},
        {"id": "gemini-3.6-flash", "object": "model", "owned_by": "google-cookie-suite", "tag": "pool", "type": "gemini_pool", "description": "[号池协议直连] 多模态高通量，通用均衡"},
        {"id": "gemini-3.8-flash", "object": "model", "owned_by": "google-cookie-suite", "tag": "pool", "type": "gemini_pool", "description": "[号池协议直连] 新一代 Flash 架构"},
        {"id": "gemini-3.1-pro-thinking", "object": "model", "owned_by": "google-cookie-suite", "tag": "pool", "type": "gemini_pool", "description": "[号池协议直连] 扩展深度思考链模式"},
    ]

    # 4. Google AI Studio 逆向原生模型
    aistudio_models = []
    try:
        raw_ai_models = aistudio_client.list_models()
        for mid in raw_ai_models[:15]:
            aistudio_models.append({
                "id": mid,
                "object": "model",
                "owned_by": "google-aistudio-reverse",
                "tag": "aistudio_reverse",
                "type": "playground_waa_rpc",
                "description": f"[AI Studio 逆向直连] 官方 Playground 原生模型 ({mid})",
            })
    except Exception:
        pass

    return {
        "object": "list",
        "data": reverse_models + moni_models + gemini_models + aistudio_models,
    }


# ==========================================
# 8. 现代化 Web 控制台 (Management Dashboard)
# ==========================================
from dashboard_template import DASHBOARD_HTML


@app.get("/", response_class=HTMLResponse, summary="Web 管理控制台", tags=["系统管理"])
def dashboard():
    """返回可视化管理面板 HTML 页面。"""
    return HTMLResponse(content=DASHBOARD_HTML)


def generate_responses_text(model, messages):
    completion = chatgpt_client.chat(messages, model=model, stream=False)
    return completion["choices"][0]["message"]["content"]


try:
    from gpt6_responses_api import make_responses_router
except ModuleNotFoundError as error:
    if error.name != "jsonschema":
        raise

    @app.post("/v1/responses")
    def responses_dependency_unavailable():
        raise HTTPException(status_code=503, detail="Install requirements-responses.txt to enable GPT-6 Responses")
else:
    app.include_router(make_responses_router(generate_responses_text))


if __name__ == "__main__":
    uvicorn.run("app_service:app", host="127.0.0.1", port=18800, reload=False)
