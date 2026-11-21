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
from pydantic import BaseModel, ConfigDict, Field

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Path, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 保证本地通信不被外部代理拦截
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

from access_token import AccessTokenStore
from chat_template import render_chat_html
from cookie_bridge import CookieBridge
from gemini_service import GeminiService, MultiAccountGeminiPool, resolve_model_reasoning
from gemini_conversation_manager import gemini_conv_manager
from chatgpt_service import chatgpt_service, UnifiedChatGPTService, ChatGPTBridgeClient, ChatGPTReverseEngine
from bilibili_service import BilibiliService
from baidu_pan_service import BaiduPanService
from suno_service import SunoService, suno_service
from login_status import collect_login_status, failure_payload, gemini_failure_should_retry, gemini_failure_kind
from minimax_service import MinimaxAudioService, minimax_service, PRESET_VOICES, OPENAI_VOICE_MAP
from aistudio_service import aistudio_service, AIStudioService
from accounts_aggregator import aggregate_accounts, refresh_accounts
from chat_history_manager import chat_history_manager, wrap_chat_stream
from opencode_export import export_to_file, PLUS_EXCLUSIVE_MODELS, INTERNAL_HIDDEN_MODELS, MODEL_DISPLAY_NAMES
from gpt_tool_bridge import (
    has_tool_protocol,
    prepare_tool_messages,
    normalize_tool_definitions,
    stream_tool_bridge,
    adapt_completion_response,
    ToolLimitReachedError,
    append_tool_limit_override,
    sanitize_tool_limit_history,
    intercept_openai_sse_tool_limit,
    MAX_TOOL_LIMIT_RETRIES,
)
from autostart import (
    is_autostart_enabled,
    enable_autostart,
    disable_autostart,
    toggle_autostart,
    get_autostart_entry,
)
from web_api_switches import (
    ServiceDisabledError,
    get_google_sync_settings,
    is_domain_cookie_allowed,
    is_service_enabled,
    is_aistudio_remote_sync_configured,
    is_aistudio_remote_sync_running,
    require_service_enabled,
    start_aistudio_remote_sync,
    stop_aistudio_remote_sync,
    switch_store,
    update_google_sync_settings,
)

COOKIE_SUITE_HOST = os.environ.get("COOKIE_SUITE_HOST", "0.0.0.0").strip() or "0.0.0.0"
COOKIE_SUITE_PORT = int(os.environ.get("COOKIE_SUITE_PORT", "18800"))
AUTH_COOKIE_NAME = "css_auth_token"
token_store = AccessTokenStore()

# 初始化 FastAPI 应用
app = FastAPI(
    title="Cookie Service Suite API",
    description="浏览器实时 Cookie 动态提取与多平台 Web 服务统一调度中心",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 允许跨域（前端控制台、本地工具与带 Token 的外部 OpenAI 客户端）
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ServiceDisabledError)
async def handle_service_disabled(request: Request, exc: ServiceDisabledError):
    if request.url.path.startswith("/v1/"):
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": str(exc),
                    "type": "service_disabled",
                    "code": "service_disabled",
                    "service_id": exc.service_id,
                }
            },
        )
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "message": str(exc),
                "type": "service_disabled",
                "service_id": exc.service_id,
            }
        },
    )

# 静态资源挂载 (网站图标与媒体文件)
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


def _extract_header_token(request: Request) -> str:
    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    for header_name in ("x-api-key", "x-access-token"):
        val = request.headers.get(header_name, "").strip()
        if val:
            return val
    return ""


def _extract_request_token(request: Request) -> str:
    header_tok = _extract_header_token(request)
    if header_tok:
        return header_tok
    for param_name in ("token", "api_key"):
        val = (request.query_params.get(param_name) or "").strip()
        if val:
            return val
    cookie_tok = (request.cookies.get(AUTH_COOKIE_NAME) or "").strip()
    if cookie_tok:
        return cookie_tok
    return ""


def _is_trusted_local_request(request: Request) -> bool:
    client_host = (request.client.host if request.client else "").strip().lower()
    req_host = request.headers.get("host", "").split(":")[0].strip("[]").lower()
    return client_host in ("127.0.0.1", "::1", "localhost") and req_host in ("127.0.0.1", "localhost", "::1")


def _is_public_path(path: str) -> bool:
    if path in ("/", "/chat", "/manifest.webmanifest", "/sw.js", "/favicon.ico", "/api/system/auth/status", "/api/system/auth/verify"):
        return True
    return path.startswith("/assets/")


# Protect remote access with API Token while preventing cross-site browser CSRF on sensitive Cookie/Token APIs.
@app.middleware("http")
async def enforce_access_and_origins(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    host_header = request.headers.get("host", "").strip().lower()
    origin = request.headers.get("origin")
    header_token_valid = token_store.verify(_extract_header_token(request))

    if origin is not None:
        origin_norm = origin.strip().rstrip("/").lower()
        local_origins = {
            "http://127.0.0.1:18800",
            "http://localhost:18800",
            "http://127.0.0.1:18888",
            "http://localhost:18888",
        }
        same_origin = bool(host_header) and origin_norm in {f"http://{host_header}", f"https://{host_header}"}
        if not (same_origin or origin_norm in local_origins or header_token_valid):
            return PlainTextResponse("Forbidden cross-origin API access", status_code=403)

    if not _is_trusted_local_request(request) and not _is_public_path(request.url.path):
        if not token_store.verify(_extract_request_token(request)):
            if request.url.path.startswith("/v1/"):
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "message": "Invalid or missing API token. Pass Authorization: Bearer <token>.",
                            "type": "invalid_request_error",
                            "code": "invalid_api_key",
                        }
                    },
                )
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: missing or invalid access token"},
            )

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
udio_client = None


@app.on_event("startup")
def _startup_background_sync():
    try:
        if is_service_enabled("chatgpt"):
            chatgpt_client.start_auto_sync()
    except Exception:
        pass


def _get_udio_client():
    global udio_client
    if udio_client is not None:
        return udio_client
    try:
        import udio_service as udio_mod
        udio_client = getattr(udio_mod, "udio_service", None) or udio_mod.UdioService()
    except Exception:
        return None
    return udio_client


def _get_account_services() -> Dict[str, Any]:
    return {
        "gemini": gemini_pool,
        "chatgpt": chatgpt_client,
        "suno": suno_client,
        "minimax": minimax_client,
        "baidupan": baidu_service,
        "bilibili": bili_service,
        "udio": _get_udio_client(),
    }

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

class ChatGPTConcurrentImageRequest(BaseModel):
    prompts: Optional[List[str]] = Field(None, description='并发提示词列表')
    prompt: Optional[str] = Field(None, description='单提示词并发生成时使用')
    count: Optional[int] = Field(1, description='单提示词并发张数 (1-20)', ge=1, le=20)
    model: Optional[str] = Field('gpt-image-2', description='图片模型')
    n: Optional[int] = Field(1, description='每次请求张数 (1-4)', ge=1, le=4)
    max_concurrency: Optional[int] = Field(3, description='最大并发数 (1-10)', ge=1, le=10)
    response_format: Optional[str] = Field('b64_json', description='返回格式 (b64_json 或 url)')
    timeout: Optional[int] = Field(240, description='单任务超时秒数', ge=30, le=600)


def _format_image_history_summary(res: Any, response_format: str = 'b64_json'):
    items = res.get('data', []) if isinstance(res, dict) else []
    lines, urls = [], []
    for idx, item in enumerate(items, 1):
        if not isinstance(item, dict): continue
        url = str(item.get('url') or '').strip()
        b64 = str(item.get('b64_json') or '').strip()
        rev = str(item.get('revised_prompt') or '').strip()
        if url:
            urls.append(url)
            d = f'图片 #{idx}: {url}'
        elif b64:
            d = f'图片 #{idx}: [base64 图片, ~{(len(b64)*3/4)/1024.0:.1f} KB]'
        else:
            d = f'图片 #{idx}: [已生成]'
        if rev: d += f' (revised_prompt: {rev[:160]})'
        lines.append(d)
    return ('\n'.join(lines) if lines else '[未返回图片数据]'), {'type': 'image_generation', 'response_format': response_format, 'image_count': len(items), 'urls': urls}



class OpenAIMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str = Field(..., example="user")
    content: Optional[Any] = Field(None, example="Hello!")
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    extra_content: Optional[Dict[str, Any]] = None


class OpenAIChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: Optional[str] = Field("gemini-3.5-flash-lite", example="gemini-3.5-flash-lite")
    messages: List[OpenAIMessage] = Field(..., description="对话历史消息列表")
    reasoning_effort: Optional[str] = Field(None, description="OpenAI 兼容推理强度: 'low', 'medium', 'high'", example="medium")
    reasoning_level: Optional[str] = Field(None, description="推理级别: 'off', 'medium', 'high'", example="off")
    stream: Optional[bool] = Field(True, description="是否启用流式输出，默认为 True (首字秒级直出)")
    temperature: Optional[float] = Field(0.7, example=0.7)
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    timeout: Optional[int] = None


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


class AccountsRefreshRequest(BaseModel):
    platform: Optional[str] = Field(None, description="可选平台过滤: gemini, chatgpt, suno, minimax, baidupan, bilibili, udio")


class WebApiToggleRequest(BaseModel):
    enabled: Optional[bool] = Field(None, description="目标启停状态；省略时在开启与关闭之间自动切换")


def _get_web_api_items(
    aistudio_local_running: Optional[bool] = None,
    aistudio_remote_sync_running: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """Build Web API switch metadata enriched with live dependent daemon status."""
    items = switch_store.list_specs()
    for item in items:
        sid = item["id"]
        daemon_running = False
        daemon_details: Dict[str, Any] = {}
        try:
            if sid == "gemini":
                daemon_running = bool(gemini_pool.is_running())
                daemon_details = {"port": gemini_pool.port}
            elif sid == "aistudio":
                local_running = bool(aistudio_client.is_running()) if aistudio_local_running is None else bool(aistudio_local_running)
                remote_sync_running = bool(is_aistudio_remote_sync_running()) if aistudio_remote_sync_running is None else bool(aistudio_remote_sync_running)
                daemon_running = local_running or remote_sync_running
                daemon_details = {
                    "port": aistudio_client.port,
                    "local_running": local_running,
                    "remote_sync_running": remote_sync_running,
                    "remote_sync_configured": is_aistudio_remote_sync_configured(),
                }
            elif sid == "chatgpt":
                daemon_running = bool(chatgpt_client.reverse.is_running())
                daemon_details = {"port": chatgpt_client.reverse.port}
        except Exception:
            daemon_running = False
        item["daemon_running"] = daemon_running
        item["daemon_details"] = daemon_details
        item["cookie_fetching_allowed"] = bool(item["enabled"])
    return items


def _apply_web_api_toggle(service_id: str, enabled: Optional[bool] = None) -> Dict[str, Any]:
    """Persist Web API switch state and synchronously stop/start dependent background processes."""
    result = switch_store.toggle(service_id, enabled=enabled)
    sid = result["id"]
    new_enabled = bool(result["enabled"])
    actions: List[str] = []
    warnings: List[str] = []

    if not new_enabled:
        if sid == "gemini":
            was_running = False
            try:
                was_running = bool(gemini_pool.is_running() or getattr(gemini_pool, "proc", None) is not None)
                gemini_pool.stop()
            except Exception as exc:
                warnings.append(f"停止 Gemini 后台池提示: {exc}")
            actions.append(
                "已停止 Gemini 4账号池后台程序 (18083) 并禁止获取/刷新 Cookie"
                if was_running
                else "已关闭 Gemini 网页 API，禁止获取/刷新 Cookie"
            )
        elif sid == "aistudio":
            was_local = False
            stopped_sync = 0
            try:
                was_local = bool(aistudio_client.is_running() or getattr(aistudio_client, "process", None) is not None)
                aistudio_client.stop()
            except Exception as exc:
                warnings.append(f"停止 AI Studio 本地服务提示: {exc}")
            try:
                stopped_sync = stop_aistudio_remote_sync()
            except Exception as exc:
                warnings.append(f"停止 AI Studio 远端同步提示: {exc}")
            parts = []
            if was_local:
                parts.append("aistudio2api (2048)")
            if stopped_sync:
                parts.append("远端同步守护进程")
            actions.append(
                f"已停止 {' 与 '.join(parts)} 并禁止获取/刷新 Cookie"
                if parts
                else "已关闭 AI Studio 网页 API，禁止获取/刷新 Cookie"
            )
        elif sid == "chatgpt":
            was_running = False
            try:
                chatgpt_client.stop_auto_sync()
                was_running = bool(chatgpt_client.reverse.is_running() or getattr(chatgpt_client.reverse, "proc", None) is not None)
                chatgpt_client.reverse.stop()
            except Exception as exc:
                warnings.append(f"停止 ChatGPT 逆向后台提示: {exc}")
            actions.append(
                "已停止 ChatGPT 逆向后台程序 (18084) 并禁止获取/刷新 Cookie"
                if was_running
                else "已关闭 ChatGPT 网页 API，禁止获取/刷新 Cookie"
            )
        else:
            actions.append(f"已关闭 {result['name']} 网页 API，不再获取或刷新对应 Cookie")
    else:
        if sid == "gemini":
            try:
                ok = gemini_pool.start(wait_timeout=8)
                if ok:
                    actions.append("已开启 Gemini 网页 API 并拉起 4账号池后台服务 (18083)")
                else:
                    warnings.append("Gemini 4账号池启动未就绪，请检查本地代理或日志")
                    actions.append("已开启 Gemini 网页 API，允许获取/刷新 Cookie")
            except Exception as exc:
                warnings.append(f"拉起 Gemini 后台池提示: {exc}")
                actions.append("已开启 Gemini 网页 API，允许获取/刷新 Cookie")
        elif sid == "aistudio":
            if is_aistudio_remote_sync_configured():
                try:
                    if start_aistudio_remote_sync():
                        actions.append("已开启 AI Studio 网页 API 并恢复远端同步守护进程")
                    else:
                        actions.append("已开启 AI Studio 网页 API，允许获取/刷新 Cookie")
                except Exception as exc:
                    warnings.append(f"恢复 AI Studio 远端同步提示: {exc}")
                    actions.append("已开启 AI Studio 网页 API")
            else:
                actions.append("已开启 AI Studio 网页 API，允许获取/刷新 Cookie（按需启动服务）")
        elif sid == "chatgpt":
            chatgpt_client.start_auto_sync()
            actions.append("已开启 ChatGPT 网页 API 并恢复后台定时保活同步")
        else:
            actions.append(f"已开启 {result['name']} 网页 API，允许获取/刷新 Cookie")

    return {
        "success": True,
        **result,
        "actions": actions,
        "warnings": warnings,
        "message": "；".join(actions),
        "items": _get_web_api_items(),
    }


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
    hint = chatgpt_client.public_account() if is_service_enabled("chatgpt") else {}
    if not hint and is_service_enabled("chatgpt") and chatgpt_client.reverse.is_running():
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

    gemini_enabled = is_service_enabled("gemini")
    gemini_running = False
    gemini_accounts = []
    try:
        gemini_running = gemini_pool.is_running()
        if gemini_enabled and gemini_running:
            gemini_accounts = gemini_pool.list_accounts()
    except Exception:
        pass

    uptime_sec = int((datetime.datetime.now() - START_TIME).total_seconds())
    chatgpt_enabled = is_service_enabled("chatgpt")
    chatgpt_status = {}
    try:
        chatgpt_status = chatgpt_client.get_status()
    except Exception:
        pass

    aistudio_enabled = is_service_enabled("aistudio")
    aistudio_status = {}
    try:
        aistudio_status = aistudio_client.get_status()
    except Exception:
        pass
    aistudio_remote_sync_running = False
    try:
        aistudio_remote_sync_running = bool(is_aistudio_remote_sync_running())
    except Exception:
        pass

    minimax_enabled = is_service_enabled("minimax")
    web_api_items = _get_web_api_items(
        aistudio_local_running=bool(aistudio_status.get("running", False)),
        aistudio_remote_sync_running=aistudio_remote_sync_running,
    )

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
        "listen_host": COOKIE_SUITE_HOST,
        "listen_port": COOKIE_SUITE_PORT,
        "uptime_seconds": uptime_sec,
        "web_api_switches": switch_store.get_states(),
        "web_apis": web_api_items,
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
                "enabled": gemini_enabled,
                "port": gemini_pool.port,
                "status": ("disabled" if not gemini_enabled else ("running" if gemini_running else "stopped")),
                "account_count": sum(1 for a in gemini_accounts if a.get("visible")),
                "active_accounts": sum(1 for a in gemini_accounts if a.get("visible") and a.get("status") == "enabled"),
            },
            "chatgpt": {
                "enabled": chatgpt_enabled,
                "mode": ("disabled" if not chatgpt_enabled else chatgpt_status.get("mode")),
                "reverse_running": chatgpt_status.get("reverse_engine", {}).get("running", False),
                "reverse_port": chatgpt_status.get("reverse_engine", {}).get("port", 18084),
                "reverse_health": chatgpt_status.get("reverse_engine", {}).get("health", {}),
                "bridge_connected": chatgpt_status.get("browser_bridge", {}).get("extension_connected", False),
            },
            "chatgpt_bridge": {
                "enabled": chatgpt_enabled,
                "status": ("disabled" if not chatgpt_enabled else ("ready" if hub_ok else "waiting_hub")),
                "method": "in_page_hook_sse",
            },
            "aistudio": {
                "enabled": aistudio_enabled,
                "port": aistudio_client.port,
                "status": ("disabled" if not aistudio_enabled else ("running" if aistudio_status.get("running") else "stopped")),
                "running": aistudio_status.get("running", False),
                "data_plane_ready": aistudio_status.get("data_plane_ready", False),
                "state": ("DISABLED" if not aistudio_enabled else aistudio_status.get("state", "STOPPED")),
                "accounts_total": aistudio_status.get("accounts_total", 0),
                "accounts_ready": aistudio_status.get("accounts_ready", 0),
                "models_count": aistudio_status.get("models_count", 0),
                "remote_sync_running": aistudio_remote_sync_running,
            },
            "minimax_audio": {
                "enabled": minimax_enabled,
                "status": ("disabled" if not minimax_enabled else ("ready" if bool(minimax_client.token) else ("connected" if hub_ok else "idle"))),
                "token_ready": bool(minimax_client.token),
                "voices_count": len(PRESET_VOICES),
            },
        },
    }


@app.get("/api/system/web-apis", summary="获取各个网页 API 的启停开关与后台进程状态", tags=["系统管理"])
def get_system_web_apis():
    """查看所有网页 API 的启停开关状态、关联域名与依赖后台程序运行情况。"""
    return {
        "items": _get_web_api_items(),
        "states": switch_store.get_states(),
    }


@app.post("/api/system/web-apis/{service_id}/toggle", summary="切换或设置指定网页 API 的启停开关", tags=["系统管理"])
def toggle_system_web_api(
    service_id: str = Path(..., description="网页 API 标识: gemini, aistudio, chatgpt, suno, minimax, baidupan, bilibili, udio"),
    enabled: Optional[bool] = Query(None, description="可选显式状态 true/false；省略时自动反转"),
    body: Optional[WebApiToggleRequest] = None,
):
    """开启或关闭指定网页 API；关闭后立即停止获取/刷新对应 Cookie 并同步停止关联后台程序。"""
    target_enabled = enabled if enabled is not None else (body.enabled if body else None)
    try:
        return _apply_web_api_toggle(service_id, enabled=target_enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"切换网页 API 状态失败: {exc}")


class GoogleSyncSettingsRequest(BaseModel):
    auto_sync_enabled: Optional[bool] = Field(None, description="一键开关：是否允许后台自动监听 Google Cookie 与刷新额度")
    usage_sync_interval_sec: Optional[int] = Field(None, description="Gemini 官网额度自动刷新间隔（秒），0 表示仅手动刷新")
    cookie_sync_interval_sec: Optional[int] = Field(None, description="Google Cookie 监听与远端同步间隔（秒），0 表示仅手动")
    allow_auto_fetch_tab: Optional[bool] = Field(None, description="是否允许自动唤醒浏览器标签页拉取 Google Cookie")


@app.get("/api/system/google-sync", summary="获取 Google 防风控同步频率与静默开关配置", tags=["系统管理"])
def get_system_google_sync():
    return {"settings": get_google_sync_settings()}


@app.post("/api/system/google-sync", summary="更新 Google 防风控同步频率或一键关闭所有自动监听", tags=["系统管理"])
def update_system_google_sync(req: GoogleSyncSettingsRequest):
    updated = update_google_sync_settings(req.model_dump(exclude_none=True))
    return {"success": True, "settings": updated}


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


class TokenVerifyRequest(BaseModel):
    token: str = Field(..., description="访问令牌")


@app.get("/api/system/auth/status", summary="检查当前请求是否已通过访问鉴权", tags=["系统管理"])
def get_system_auth_status(request: Request):
    """供管理控制台判断是否需要弹出令牌解锁界面。"""
    is_local = _is_trusted_local_request(request)
    authorized = is_local or token_store.verify(_extract_request_token(request))
    return {
        "authorized": authorized,
        "requires_token": not is_local,
        "is_local": is_local,
    }


@app.post("/api/system/auth/verify", summary="验证并写入控制面板访问令牌 Cookie", tags=["系统管理"])
def verify_system_auth_token(body: TokenVerifyRequest, response: Response):
    """校验访问令牌并设置 HttpOnly 会话 Cookie，便于控制台与 Swagger 访问。"""
    candidate = (body.token or "").strip()
    if not token_store.verify(candidate):
        raise HTTPException(status_code=401, detail="访问令牌无效")
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=candidate,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=30 * 24 * 3600,
    )
    return {"success": True, "authorized": True}


@app.get("/api/system/token", summary="获取当前 API 访问令牌", tags=["系统管理"])
def get_system_token():
    """返回当前生效的 API Token 及更新时间戳。"""
    return token_store.get_info()


@app.post("/api/system/token/generate", summary="重新生成并持久化 API 访问令牌", tags=["系统管理"])
def generate_system_token(request: Request, response: Response):
    """生成新的随机 API Token 并立即生效；若当前为已鉴权浏览器会话则同步刷新会话 Cookie。"""
    info = token_store.rotate()
    if request.cookies.get(AUTH_COOKIE_NAME):
        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=str(info["token"]),
            httponly=True,
            samesite="lax",
            path="/",
            max_age=30 * 24 * 3600,
        )
    return {"success": True, **info}


# ==========================================
# 2. Google Gemini 多账号池统一调度接口
# ==========================================
@app.get("/manifest.webmanifest", include_in_schema=False)
def pwa_manifest():
    return JSONResponse({
        "name": "Gemini Chat",
        "short_name": "Gemini",
        "start_url": "/chat",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0b101b",
        "theme_color": "#0b101b",
        "icons": [
            {"src": "/assets/app_icon.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            {"src": "/assets/icons/gemini.svg", "sizes": "any", "type": "image/svg+xml"}
        ]
    }, media_type="application/manifest+json")

@app.get("/sw.js", include_in_schema=False)
def pwa_sw():
    return PlainTextResponse("self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('fetch',()=>{});", media_type="application/javascript")

@app.get("/chat", response_class=HTMLResponse, include_in_schema=False)
def chat_page():
    return HTMLResponse(render_chat_html())

@app.get("/api/gemini/models", summary="读取 Gemini 网页当前模型选择器 (支持对话与任务模式)", tags=["Gemini 多账号调度"])
def list_gemini_models():
    raw_chat = gemini_pool.list_web_models()
    chat_models = []
    for m in raw_chat:
        if m.get("locked"):
            continue
        item = dict(m)
        lbl = str(item.get("label") or item.get("name") or item.get("id") or "")
        if not lbl.startswith("["):
            item["label"] = f"[聊天] {lbl}"
        item["mode"] = "chat"
        chat_models.append(item)
    task_models = gemini_pool.list_task_models()
    return {
        "source": "web",
        "models": chat_models + task_models,
        "chat_models": chat_models,
        "task_models": task_models,
        "active_modes": ["chat", "task"],
        "service_running": gemini_pool.is_running(),
    }


# ==========================================
# 1.5. 全平台统一账号看板 API
# ==========================================
@app.get("/api/accounts", summary="获取全平台统一账号看板数据", tags=["全平台账号看板"])
def list_unified_accounts(
    platform: Optional[str] = Query(None, description="可选平台过滤: gemini, chatgpt, suno, minimax, baidupan, bilibili, udio")
):
    """聚合 Google Gemini、ChatGPT、Suno、MiniMax、百度网盘、哔哩哔哩与 Udio 的归一化账号、会员与额度状态。"""
    try:
        return aggregate_accounts(
            services=_get_account_services(),
            platform=platform,
            collect_login_status_fn=collect_login_status,
            timeout_seconds=9.0,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取全平台账号失败: {str(exc)}")


@app.post("/api/accounts/refresh", summary="刷新全平台或指定平台账号状态与额度", tags=["全平台账号看板"])
def refresh_unified_accounts(
    platform: Optional[str] = Query(None, description="可选平台过滤: gemini, chatgpt, suno, minimax, baidupan, bilibili, udio"),
    body: Optional[AccountsRefreshRequest] = None,
):
    """刷新全平台或指定平台的浏览器会话/凭证/额度，并返回最新归一化账号快照。"""
    target_platform = platform if platform is not None else (body.platform if body else None)
    try:
        return refresh_accounts(
            services=_get_account_services(),
            platform=target_platform,
            collect_login_status_fn=collect_login_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"刷新全平台账号失败: {str(exc)}")


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


@app.post('/api/gemini/accounts/{account_id}/status', tags=['Gemini 多账号调度'])
def set_gemini_account_status(account_id: int, status: str = Query(...)):
    try:
        gemini_pool.set_account_status(account_id, status)
        return {'success': True, 'status': status}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/gemini/accounts/sync-profiles", summary="同步提取所有账号的真实 Google 昵称与邮箱", tags=["Gemini 多账号调度"])
def sync_gemini_profiles():
    """向 Google 上游拉取各 authuser 对应的真实用户显示昵称与 Gmail 邮箱并写入账号池。"""
    require_service_enabled("gemini")
    try:
        res = gemini_pool.sync_account_profiles()
        return {
            "success": True,
            "message": "已成功更新账号真实昵称、邮箱与官网额度信息！",
            "profiles": res,
        }
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步昵称邮箱失败: {str(e)}")


@app.post("/api/gemini/accounts/sync-usage", summary="同步 Google Gemini 官网 /usage 实时用量百分比与重置时间", tags=["Gemini 多账号调度"])
def sync_gemini_usage():
    """直接请求 Gemini 网页 /usage GraphQL 接口，同步每个独立账号的真实套餐等级、5 小时与周限额百分比及重置时间。"""
    require_service_enabled("gemini")
    try:
        res = gemini_pool.sync_account_usage()
        ok_count = sum(1 for v in res.values() if isinstance(v, dict) and not v.get("error"))
        return {
            "success": ok_count > 0,
            "synced_count": ok_count,
            "message": f"已同步 {ok_count} 个账号的官网实时用量限额！" if ok_count else "未能拉取到官网用量限额，请检查账号 Cookie 或代理状态。",
            "usage": res,
        }
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步官网额度失败: {str(e)}")


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


def _resolve_gemini_timeout(model_name: str, reasoning_level: str = "off", requested_timeout: Optional[int] = None) -> int:
    """Calculate a safe timeout floor for Gemini requests based on model complexity and reasoning."""
    is_complex = (reasoning_level or "off").lower() != "off" or any(
        m in (model_name or "").lower() for m in ["3.8", "3.6", "4-", "pro", "thinking"]
    )
    min_timeout = 600 if is_complex else 300
    return max(requested_timeout or min_timeout, min_timeout)


@app.post("/api/gemini/chat", summary="向 Gemini 发起提问 (自动 LRU 负载均衡轮换)", tags=["Gemini 多账号调度"])
@app.post("/api/pool/chat", summary="向号池发起提问 (自动 LRU 负载均衡轮换)", tags=["Gemini 多账号调度"])
def gemini_chat(req: ChatRequest):
    """
    底层通过最久未用 (LRU) 算法自动在已接入的 4 个账号之间分发请求，
    支持指定推理级别 ('off' 快速直出, 'medium' 中等推理, 'high' 深度长思考链)，
    遇凭证过期或网络异常自动触发 Cookie Hub 热刷新与重试自愈。
    """
    require_service_enabled("gemini")
    start_t = time.time()

    reasoning = req.reasoning_level or "off"
    model_name = (req.model or "gemini-4-hydrogen").lower().strip()
    try:
        resolve_model_reasoning(model_name, reasoning)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    effective_timeout = _resolve_gemini_timeout(model_name, reasoning, req.timeout)

    # 1. 默认优先走实时流式输出 (SSE)：首字毫秒级直出，体验与真实网页端一致
    if req.stream:
        def _pool_chat_stream_with_fallback():
            mdl = (req.model or "gemini-4-hydrogen").strip() or "gemini-4-hydrogen"
            if mdl.endswith("-task") or not gemini_pool.is_running():
                try:
                    yield from gemini_conv_manager.stream_openai_task_chat(
                        messages=[{"role": "user", "content": req.prompt}], model=mdl, timeout=effective_timeout
                    )
                except Exception as exc:
                    err_chunk = {"id": f"chatcmpl-err-{int(time.time()*1000)}", "object": "chat.completion.chunk", "created": int(time.time()), "model": mdl, "choices": [{"index": 0, "delta": {"role": "assistant", "content": f"[流式异常] {exc}"}, "finish_reason": "stop"}]}
                    yield f"data: {json.dumps(err_chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                return
            emitted = False
            try:
                for chunk in gemini_pool.stream_chat(
                    prompt=req.prompt, model=mdl, reasoning_level=reasoning, timeout=effective_timeout
                ):
                    if "HTTP Error 502" in chunk or "HTTP Error 429" in chunk or "流式异常" in chunk:
                        if not emitted:
                            raise RuntimeError(chunk)
                    emitted = True
                    yield chunk
            except Exception:
                if emitted:
                    raise
                yield from gemini_conv_manager.stream_openai_task_chat(
                    messages=[{"role": "user", "content": req.prompt}], model=mdl, timeout=effective_timeout
                )

        stream_gen = _pool_chat_stream_with_fallback()
        wrapped_gen = wrap_chat_stream(
            stream_gen,
            endpoint="/api/gemini/chat",
            model=req.model or "gemini-4-hydrogen",
            messages=req.prompt,
            actual_model=req.model or "gemini-4-hydrogen",
            meta={"reasoning_level": reasoning},
            start_time=start_t,
        )
        return StreamingResponse(
            wrapped_gen,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    # 2. 非流式聚合调用

    if model_name.endswith("-task") or not gemini_pool.is_running():
        parts = []
        for sse_line in gemini_conv_manager.stream_openai_task_chat(
            messages=[{"role": "user", "content": req.prompt}], model=req.model or "gemini-4-hydrogen", timeout=effective_timeout
        ):
            st = sse_line.strip()
            if not st.startswith("data:") or st == "data: [DONE]": continue
            try:
                dl = ((json.loads(st[5:].strip()).get("choices") or [{}])[0].get("delta") or {})
                if dl.get("content"): parts.append(dl["content"])
            except Exception: pass
        reply_txt = "".join(parts)
        return {"status": "ok", "model": req.model or "gemini-4-hydrogen", "reply": reply_txt, "took_ms": int((time.time() - start_t) * 1000)}

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
        failure_kind = gemini_failure_kind(str(first_err))
        if failure_kind in {"login", "unbound"}:
            print(f"[Gemini Chat] 检测到上游异常 ({failure_kind})，正在从 Cookie Hub 自动刷新凭证...", flush=True)
        elif not gemini_failure_should_retry(str(first_err)):
            _gemini_stop(str(first_err))
        print(f"[Gemini Chat] 调度异常 ({failure_kind})，尝试自愈并重试...", flush=True)
        try:
            if failure_kind in {"login", "unbound"}:
                refreshed = gemini_pool.recover_from_failure(failure_kind)
                if failure_kind == "unbound" and not refreshed:
                    _gemini_stop(str(first_err))
            else:
                gemini_pool.reset_proxies()
            res = gemini_pool.ask_with_details(
                prompt=req.prompt, model=req.model, reasoning_level=reasoning, timeout=effective_timeout
            )
            if is_upstream_refusal(res.get("reply")):
                _service_error(502, f"Gemini 上游拒绝请求: {res.get('reply')}", "gemini")
        except HTTPException:
            raise
        except Exception as retry_err:
            detail_msg = f"Gemini 调度调用失败: {first_err} (自愈重试亦未成功: {retry_err})"
            _service_error(502, detail_msg, "gemini")

    chat_history_manager.record_chat(
        endpoint="/api/gemini/chat",
        model=res.get("model") or req.model or "gemini-4-hydrogen",
        messages=req.prompt,
        response_text=res.get("reply", ""),
        status=200,
        latency_ms=res.get("took_ms", 0),
        is_stream=False,
        actual_model=res.get("model") or req.model or "gemini-4-hydrogen",
        meta={
            "account_id": res.get("account_id"),
            "account_label": res.get("account_label"),
            "authuser": res.get("authuser"),
            "reasoning_level": res.get("reasoning_level")
        }
    )

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
    require_service_enabled("gemini")
    try:
        res = gemini_pool.check_account(account_id)
        return res
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gemini/accounts/{account_id}/rotate", summary="触发指定账号会话令牌保活续期", tags=["Gemini 多账号调度"])
def rotate_gemini_account(account_id: int = Path(..., description="账号自增 ID (1..4)")):
    """向 Google accounts.google.com/RotateCookies 申请换发最新短命会话票据。"""
    require_service_enabled("gemini")
    try:
        res = gemini_pool.rotate_account(account_id)
        return res
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gemini/accounts/refresh-all", summary="强制获取一次 Cookie 并同步账号名称、邮箱与官网额度", tags=["Gemini 多账号调度"])
def refresh_gemini_accounts_all(account_id: Optional[int] = Query(None, ge=1, description="可选：只验证并刷新指定启用账号 ID")):
    """一键强制从 Cookie Hub 获取最新凭证、解析账号真实名称与邮箱，并同步官网实时额度。"""
    require_service_enabled("gemini")
    try:
        res = gemini_pool.refresh_and_sync_all(account_id=account_id)
        updated_ids = res.get("updated_account_ids", [])
        return {
            "success": True,
            "message": f"已完成凭证刷新（{len(updated_ids)} 个账号）、账号信息解析与官网额度同步！",
            "updated_account_ids": updated_ids,
            "profiles": res.get("profiles", {}),
        }
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新失败: {str(e)}")


@app.post("/api/gemini/refresh", summary="按 Google 登录身份验证后刷新匹配的 Gemini 账号", tags=["Gemini 多账号调度"])
def refresh_gemini_cookies(account_id: Optional[int] = Query(None, ge=1, description="可选：只验证并刷新指定启用账号 ID")):
    """先读取浏览器 Cookie，再逐个核验 authuser/邮箱；只更新身份匹配的启用账号。"""
    require_service_enabled("gemini")
    try:
        gemini_pool.refresh_pool_cookies(account_id=account_id)
        updated_ids = getattr(gemini_pool, "_last_cookie_refresh_ids", [])
        return {
            "success": True,
            "message": f"浏览器登录态已验证；仅更新身份匹配的启用账号（{len(updated_ids)} 个）。",
            "updated_account_ids": updated_ids,
        }
    except ServiceDisabledError:
        raise
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


class GeminiConvCreateRequest(BaseModel):
    prompt: str = Field(..., description="首轮提问内容")
    model: Optional[str] = Field("gemini-3.6-flash", description="模型名称")
    account_id: Optional[int] = Field(None, description="可选指定账号 ID")


class GeminiConvMessageRequest(BaseModel):
    prompt: str = Field(..., description="续聊消息内容")
    model: Optional[str] = Field(None, description="可选切换模型")


@app.get("/api/gemini/conversations", summary="获取落盘的 Gemini 对话列表与实时状态", tags=["Gemini 多账号调度"])
def list_gemini_conversations(limit: int = Query(50, description="返回对话条数上限")):
    try:
        items = gemini_conv_manager.list_conversations(limit=limit)
        return {"conversations": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gemini/conversations/sync", summary="从 Gemini 官网同步历史对话列表 (MaZiqc)", tags=["Gemini 多账号调度"])
def sync_gemini_conversations(
    account_id: Optional[int] = Query(None, description="可选仅同步指定账号 ID"),
    limit: int = Query(20, description="每个账号拉取条数"),
):
    try:
        res = gemini_conv_manager.sync_conversations(account_id=account_id, limit=limit)
        return {"success": True, **res}
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/gemini/conversations/events", summary="订阅所有 Gemini 对话状态与完成通知 (SSE)", tags=["Gemini 多账号调度"])
def stream_gemini_conversation_events():
    import queue as _q

    q = gemini_conv_manager.subscribe_global()

    def _gen():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    msg = q.get(timeout=15.0)
                    yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'], ensure_ascii=False)}\n\n"
                except _q.Empty:
                    yield ": keepalive\n\n"
        finally:
            gemini_conv_manager.unsubscribe_global(q)

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/gemini/conversations/{cid}", summary="获取单个 Gemini 对话详情与消息历史", tags=["Gemini 多账号调度"])
def get_gemini_conversation(
    cid: str,
    refresh: bool = Query(False, description="是否向官网 hNvQHb 拉取最新轮次"),
):
    try:
        if refresh:
            item = gemini_conv_manager.sync_conversation_detail(cid)
        else:
            item = gemini_conv_manager.get_conversation(cid, include_messages=True)
        if not item:
            raise HTTPException(status_code=404, detail=f"未找到对话 {cid}")
        return {"conversation": item}
    except HTTPException:
        raise
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.delete("/api/gemini/conversations/{cid}", summary="删除本地落盘的 Gemini 对话", tags=["Gemini 多账号调度"])
def delete_gemini_conversation(
    cid: str,
    upstream: bool = Query(False, description="是否同时删除官网对话 (GzXR5e)"),
):
    try:
        ok = gemini_conv_manager.delete_local_conversation(cid, delete_upstream=upstream)
        if not ok:
            raise HTTPException(status_code=404, detail=f"未找到对话 {cid}")
        return {"success": True, "cid": cid}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gemini/conversations", summary="发起新的可控 Gemini 对话", tags=["Gemini 多账号调度"])
def create_gemini_conversation(req: GeminiConvCreateRequest):
    try:
        res = gemini_conv_manager.start_run(
            prompt=req.prompt,
            cid=None,
            model=req.model or "gemini-3.6-flash",
            account_id=req.account_id,
        )
        return {"success": True, **res}
    except ServiceDisabledError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/gemini/conversations/{cid}/messages", summary="向指定 Gemini 对话续发消息", tags=["Gemini 多账号调度"])
def send_gemini_conversation_message(cid: str, req: GeminiConvMessageRequest):
    try:
        res = gemini_conv_manager.start_run(
            prompt=req.prompt,
            cid=cid,
            model=req.model or "",
        )
        return {"success": True, **res}
    except ServiceDisabledError:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/gemini/conversations/{cid}/stop", summary="停止指定 Gemini 对话正在输出的回复", tags=["Gemini 多账号调度"])
def stop_gemini_conversation(cid: str):
    try:
        res = gemini_conv_manager.stop_conversation(cid)
        return {"success": True, **res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gemini/runs/{run_id}", summary="查询单次 Gemini 生成任务状态与已输出内容", tags=["Gemini 多账号调度"])
def get_gemini_run(run_id: str):
    run = gemini_conv_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"未找到任务 {run_id}")
    return {"run": run}


@app.post("/api/gemini/runs/{run_id}/stop", summary="停止指定 Gemini 生成任务", tags=["Gemini 多账号调度"])
def stop_gemini_run(run_id: str):
    res = gemini_conv_manager.stop_run(run_id)
    return {"success": True, **res}


@app.get("/api/gemini/runs/{run_id}/events", summary="订阅单次 Gemini 生成任务实时增量与结束通知 (SSE)", tags=["Gemini 多账号调度"])
def stream_gemini_run_events(run_id: str):
    import queue as _q

    q = gemini_conv_manager.subscribe_run(run_id)

    def _gen():
        try:
            snap = gemini_conv_manager.get_run(run_id)
            if snap:
                yield f"event: snapshot\ndata: {json.dumps(snap, ensure_ascii=False)}\n\n"
                if snap.get("status") != "running":
                    yield f"event: run_finished\ndata: {json.dumps(snap, ensure_ascii=False)}\n\n"
                    return
            while True:
                try:
                    msg = q.get(timeout=15.0)
                    yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'], ensure_ascii=False)}\n\n"
                    if msg["event"] == "run_finished":
                        break
                except _q.Empty:
                    yield ": keepalive\n\n"
        finally:
            gemini_conv_manager.unsubscribe_run(run_id, q)

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
    require_service_enabled("chatgpt")
    try:
        ok = chatgpt_client.reverse.start()
        return {"success": ok, "port": chatgpt_client.reverse.port, "is_running": chatgpt_client.reverse.is_running()}
    except ServiceDisabledError:
        raise
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
    require_service_enabled("chatgpt")
    try:
        return chatgpt_client.get_session()
    except ServiceDisabledError:
        raise
    except Exception as e:
        _service_error(502, f"无法获取 ChatGPT 会话: {str(e)}", "chatgpt")


@app.get("/api/chatgpt/models", summary="获取 ChatGPT 账号可用模型列表", tags=["ChatGPT 逆向与号池"])
def get_chatgpt_models():
    """拉取逆向暴露或浏览器同源支持的模型列表，并按当前账号方案区分免费版与 Plus/Pro 专享模型。"""
    require_service_enabled("chatgpt")
    try:
        raw_res = chatgpt_client.get_models()
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"无法获取模型列表: {str(e)}")
    return _build_chatgpt_model_catalog(raw_res)


@app.get("/api/chatgpt/accounts", summary="获取当前 ChatGPT 逆向号池账号列表", tags=["ChatGPT 逆向与号池"])
def list_chatgpt_accounts():
    """查看已导入逆向引擎的账号列表、额度与健康状态。"""
    require_service_enabled("chatgpt")
    try:
        if not chatgpt_client.reverse.is_running():
            chatgpt_client.reverse.start()
        return {"items": chatgpt_client.reverse.list_accounts()}
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取账号列表失败: {str(e)}")


@app.post("/api/chatgpt/accounts", summary="向 ChatGPT 号池导入 AccessToken", tags=["ChatGPT 逆向与号池"])
def import_chatgpt_accounts(body: ChatGPTAccountImportRequest):
    """手动导入一个或多个 Access Token 进入号池并自动刷新有效性。"""
    require_service_enabled("chatgpt")
    try:
        if not chatgpt_client.reverse.is_running():
            chatgpt_client.reverse.start()
        res = chatgpt_client.reverse.import_tokens(body.tokens)
        return res
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"导入账号失败: {str(e)}")


@app.post("/api/chatgpt/accounts/sync-browser", summary="从浏览器 Cookie Hub 一键同步 Token 入池", tags=["ChatGPT 逆向与号池"])
def sync_chatgpt_browser_token():
    """通过 Cookie Hub 自动获取浏览器中当前 chatgpt.com 登录会话的 Access Token，并一键载入逆向号池。"""
    require_service_enabled("chatgpt")
    try:
        return chatgpt_client.sync_token_from_browser()
    except ServiceDisabledError:
        raise
    except Exception as e:
        _service_error(502, f"从浏览器同步 Token 失败: {str(e)}", "chatgpt")


@app.post("/api/chatgpt/chat", summary="向 ChatGPT 发起智能对话 (支持逆向与桥接双引擎)", tags=["ChatGPT 逆向与号池"])
def chatgpt_ask(req: ChatRequest):
    """优先使用无头逆向引擎直连，若未就绪则自动降级到浏览器同源扩展。支持流式与非流式。"""
    require_service_enabled("chatgpt")
    start_t = time.time()
    target_model = req.model or "auto"
    try:
        if req.stream:
            def _chatgpt_sse_gen():
                messages = [{"role": "user", "content": req.prompt}]
                try:
                    for chunk in chatgpt_client.chat(messages, model=target_model, stream=True):
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    err_data = {"error": {"message": str(e), "type": "chatgpt_error"}}
                    yield f"data: {json.dumps(err_data, ensure_ascii=False)}\n\n"

            wrapped_gen = wrap_chat_stream(
                _chatgpt_sse_gen(),
                endpoint="/api/chatgpt/chat",
                model=target_model,
                messages=req.prompt,
                actual_model=target_model,
                start_time=start_t,
            )

            return StreamingResponse(
                wrapped_gen,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )

        reply = chatgpt_client.ask(req.prompt, model=target_model)
        latency = int((time.time() - start_t) * 1000)
        chat_history_manager.record_chat(
            endpoint="/api/chatgpt/chat",
            model=target_model,
            messages=req.prompt,
            response_text=reply,
            status=200,
            latency_ms=latency,
            is_stream=False,
            actual_model=target_model
        )
        return {"success": True, "reply": reply}
    except Exception as e:
        _service_error(502, f"ChatGPT 提问失败: {str(e)}", "chatgpt")


@app.post('/api/chatgpt/image', summary='ChatGPT 逆向图片生成 (gpt-image-2)', tags=['ChatGPT 逆向与号池'])
def chatgpt_image_generation(body: ChatGPTImageRequest):
    require_service_enabled('chatgpt')
    start_t = time.time()
    target_model = body.model or 'gpt-image-2'
    fmt = body.response_format or 'b64_json'
    n_val = body.n or 1
    chat_id = chat_history_manager.start_chat(endpoint='/api/chatgpt/image', model=target_model, messages=body.prompt, is_stream=False, actual_model=target_model, meta={'type': 'image_generation', 'n': n_val, 'response_format': fmt})
    try:
        res = chatgpt_client.generate_image(prompt=body.prompt, model=target_model, n=n_val, response_format=fmt)
        latency = int((time.time() - start_t) * 1000)
        summary_text, meta = _format_image_history_summary(res, response_format=fmt)
        meta['n'] = n_val
        chat_history_manager.finish_chat(chat_id, response_text=summary_text, status=200, latency_ms=latency, actual_model=target_model, meta=meta)
        return res
    except ServiceDisabledError:
        raise
    except Exception as e:
        latency = int((time.time() - start_t) * 1000)
        chat_history_manager.finish_chat(chat_id, response_text='', status=502, latency_ms=latency, actual_model=target_model, error_message=str(e))
        raise HTTPException(status_code=502, detail=f'ChatGPT 图片生成失败: {str(e)}')


@app.post('/api/chatgpt/image/batch', summary='ChatGPT 并发批量生图 (gpt-image-2)', tags=['ChatGPT 逆向与号池'])
def chatgpt_image_batch_generation(body: ChatGPTConcurrentImageRequest):
    require_service_enabled('chatgpt')
    start_t = time.time()
    target_model = body.model or 'gpt-image-2'
    fmt = body.response_format or 'b64_json'
    prompt_log = body.prompts if body.prompts else (f'{body.prompt} (x{body.count or 1})' if body.prompt else '')
    chat_id = chat_history_manager.start_chat(endpoint='/api/chatgpt/image/batch', model=target_model, messages=prompt_log, is_stream=False, actual_model=target_model, meta={'type': 'image_generation', 'batch': True, 'response_format': fmt})
    try:
        res = chatgpt_client.generate_images_concurrent(prompts=body.prompts, prompt=body.prompt, count=body.count or 1, model=target_model, n=body.n or 1, response_format=fmt, max_concurrency=body.max_concurrency or 3, timeout=body.timeout or 240)
        latency = int((time.time() - start_t) * 1000)
        summary_text, meta = _format_image_history_summary(res, response_format=fmt)
        meta.update({'batch': True, 'total_tasks': res.get('total_tasks', 0), 'succeeded': res.get('succeeded', 0), 'failed': res.get('failed', 0), 'max_concurrency': res.get('max_concurrency', 1)})
        errs = [f'#{r.get('index', 0)+1}: {r.get('error')}' for r in res.get('results', []) if not r.get('success')]
        ok_cnt, tot_cnt, mc = res.get('succeeded', 0), res.get('total_tasks', 0), res.get('max_concurrency', 1)
        chat_history_manager.finish_chat(chat_id, response_text=f'并发出图完成: 成功 {ok_cnt}/{tot_cnt} (并发度 {mc})\n{summary_text}', status=200 if res.get('success') else 502, latency_ms=latency, actual_model=target_model, error_message='; '.join(errs[:5]), meta=meta)
        if not res.get('success'):
            raise HTTPException(status_code=502, detail='ChatGPT 并发图片生成全部失败: ' + '; '.join(errs[:3]))
        return res
    except (ServiceDisabledError, HTTPException):
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        latency = int((time.time() - start_t) * 1000)
        chat_history_manager.finish_chat(chat_id, response_text='', status=502, latency_ms=latency, actual_model=target_model, error_message=str(e))
        raise HTTPException(status_code=502, detail=f'ChatGPT 并发图片生成失败: {str(e)}')


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
    require_service_enabled("aistudio")
    try:
        ok = aistudio_client.start()
        return {
            "success": ok,
            "message": "AI Studio 逆向服务已成功启动并就绪" if ok else "启动失败，请检查控制台日志",
            "status": aistudio_client.get_status(),
        }
    except ServiceDisabledError:
        raise
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
    require_service_enabled("aistudio")
    try:
        ok = aistudio_client.restart()
        return {
            "success": ok,
            "message": "AI Studio 逆向服务已重启并重新就绪" if ok else "重启失败",
            "status": aistudio_client.get_status(),
        }
    except ServiceDisabledError:
        raise
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
    require_service_enabled("aistudio")
    try:
        res = aistudio_client.sync_cookies_from_hub()
        return res
    except ServiceDisabledError:
        raise
    except Exception as e:
        _service_error(500, f"同步 AI Studio 凭证失败: {str(e)}", "aistudio")


@app.post("/api/aistudio/chat", summary="向 Google AI Studio 发起原生智能对话", tags=["Google AI Studio 逆向"])
def aistudio_chat(req: AIStudioChatRequest):
    """
    通过 Google AI Studio Playground 逆向原生通道调用 Gemini 大模型，
    支持 gemini-4-argon, gemini-3.8-flash 等全系列模型，支持流式 SSE 打字机输出。
    """
    require_service_enabled("aistudio")
    start_t = time.time()
    target_model = req.model or "gemini-4-argon"
    try:
        if req.stream:
            stream_gen = aistudio_client.chat(
                prompt=req.prompt,
                model=target_model,
                stream=True,
                timeout=req.timeout or 120,
            )
            wrapped_gen = wrap_chat_stream(
                stream_gen,
                endpoint="/api/aistudio/chat",
                model=target_model,
                messages=req.prompt,
                actual_model=target_model,
                start_time=start_t,
            )
            return StreamingResponse(
                wrapped_gen,
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
                model=target_model,
                stream=False,
                timeout=req.timeout or 120,
            )
            latency = int((time.time() - start_t) * 1000)
            chat_history_manager.record_chat(
                endpoint="/api/aistudio/chat",
                model=target_model,
                messages=req.prompt,
                response_text=str(result) if not isinstance(result, dict) else json.dumps(result, ensure_ascii=False),
                status=200,
                latency_ms=latency,
                is_stream=False,
                actual_model=target_model
            )
            return {"success": True, "result": result}
    except Exception as e:
        _service_error(502, f"AI Studio 对话请求失败: {str(e)}", "aistudio")


# ==========================================
# 4. Bilibili 业务接口
# ==========================================
@app.get("/api/bilibili/user", summary="获取 B 站登录用户信息与大会员资产", tags=["Bilibili 视频特权"])
def get_bilibili_user():
    require_service_enabled("bilibili")
    try:
        return bili_service.get_user_info()
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 B 站用户失败: {str(e)}")


@app.get("/api/bilibili/video", summary="查询 B 站视频信息与最高画质流", tags=["Bilibili 视频特权"])
def get_bilibili_video(bvid: str = Query(..., description="视频 BV 号，如 BV1GJ411x7h7")):
    require_service_enabled("bilibili")
    try:
        return bili_service.get_video_info(bvid)
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析视频失败: {str(e)}")


# ==========================================
# 5. 百度网盘业务接口
# ==========================================
@app.get("/api/baidupan/quota", summary="获取百度网盘存储容量与配额信息", tags=["百度网盘服务"])
def get_baidupan_quota():
    require_service_enabled("baidupan")
    try:
        return baidu_service.get_quota()
    except ServiceDisabledError:
        raise
    except Exception as e:
        _service_error(500, f"查询网盘配额失败: {str(e)}", "baidu")


@app.get("/api/baidupan/user", summary="获取百度网盘账号资料与 VIP 等级", tags=["百度网盘服务"])
def get_baidupan_user():
    require_service_enabled("baidupan")
    try:
        return baidu_service.get_user_info()
    except ServiceDisabledError:
        raise
    except Exception as e:
        _service_error(500, f"查询网盘用户失败: {str(e)}", "baidu")


@app.get("/api/baidupan/files", summary="遍历百度网盘指定目录下的文件", tags=["百度网盘服务"])
def list_baidupan_files(dir_path: str = Query("/", description="网盘目录路径，默认根目录 /")):
    require_service_enabled("baidupan")
    try:
        return baidu_service.list_files(dir_path=dir_path)
    except ServiceDisabledError:
        raise
    except Exception as e:
        _service_error(500, f"遍历网盘文件失败: {str(e)}", "baidu")


@app.post("/api/baidupan/refresh", summary="强制从浏览器刷新百度网盘凭证", tags=["百度网盘服务"])
def refresh_baidupan_auth():
    require_service_enabled("baidupan")
    try:
        return baidu_service.refresh_auth()
    except ServiceDisabledError:
        raise
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
    allowed, disabled_ids = is_domain_cookie_allowed(domain)
    if not allowed:
        raise HTTPException(
            status_code=503,
            detail={
                "message": f"域名 {domain} 对应的网页 API ({', '.join(disabled_ids)}) 已在管理控制台关闭，已禁止获取 Cookie。",
                "type": "service_disabled",
                "disabled_services": disabled_ids,
            },
        )
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
    require_service_enabled("suno")
    try:
        return suno_client.get_credits()
    except ServiceDisabledError:
        raise
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
    require_service_enabled("suno")
    try:
        clips = suno_client.get_feed(page=page)
        return _enrich_suno_clips(clips)
    except ServiceDisabledError:
        raise
    except Exception as e:
        _service_error(500, f"获取 Suno 历史曲库失败: {str(e)}", "suno")


@app.post("/api/suno/generate", summary="提交 Suno 音乐创作任务", tags=["Suno 音乐生成"])
def generate_suno_music(req: SunoGenerateRequest):
    require_service_enabled("suno")
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
    require_service_enabled("suno")
    try:
        id_list = [i.strip() for i in clip_ids.split(",") if i.strip()]
        clips = suno_client.fetch_clips_status(id_list)
        return _enrich_suno_clips(clips)
    except ServiceDisabledError:
        raise
    except Exception as e:
        _service_error(500, f"查询任务状态失败: {str(e)}", "suno")


@app.post("/api/suno/lyrics", summary="使用 Suno AI 单独创作歌词", tags=["Suno 音乐生成"])
def generate_suno_lyrics(req: SunoLyricsRequest):
    require_service_enabled("suno")
    try:
        return suno_client.generate_lyrics(prompt=req.prompt)
    except ServiceDisabledError:
        raise
    except Exception as e:
        _service_error(500, f"创作歌词失败: {str(e)}", "suno")


@app.post("/api/suno/refresh", summary="强制刷新 Suno 凭证与 Clerk JWT 令牌", tags=["Suno 音乐生成"])
def refresh_suno_auth():
    require_service_enabled("suno")
    try:
        return suno_client.refresh_auth()
    except ServiceDisabledError:
        raise
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
    require_service_enabled("minimax")
    return minimax_client.get_quota()


@app.post("/api/minimax/speech", summary="MiniMax 高级语音合成", tags=["MiniMax 语音合成"])
def post_minimax_speech(req: MinimaxSpeechRequest):
    import io
    require_service_enabled("minimax")
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
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MiniMax 语音合成失败: {str(e)}")


@app.post("/api/minimax/auto_fetch", summary="通知浏览器扩展唤醒并自动拉取 MiniMax 登录态", tags=["MiniMax 语音合成"])
def post_minimax_auto_fetch(force: bool = Query(True, description="是否强制后台打开页面以唤醒会话")):
    require_service_enabled("minimax")
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
    start_t = time.time()
    last_user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    if not last_user_msg:
        raise HTTPException(status_code=400, detail="未包含有效的 user 消息")

    model_name = (req.model or "gemini-4-hydrogen").lower().strip()

    # 0. Google AI Studio 逆向分流。网页选择器里的 4 Hydrogen / 4 Argon 留在号池。
    if not _is_gemini_web_pool_model(model_name) and (
        model_name.startswith("aistudio") or model_name.startswith("gemini-4") or "argon" in model_name
    ):
        require_service_enabled("aistudio")
        actual_model = req.model.replace("aistudio/", "").replace("aistudio-", "") if req.model else "gemini-4-argon"
        messages_payload = [m.model_dump(exclude_none=True) for m in req.messages]
        req_timeout = getattr(req, "timeout", None) or 120
        if req.stream:
            stream_gen = aistudio_client.chat(
                prompt=last_user_msg,
                model=actual_model,
                stream=True,
                messages=messages_payload,
                timeout=req_timeout,
                tools=req.tools,
                tool_choice=req.tool_choice,
            )
            wrapped_gen = wrap_chat_stream(
                stream_gen,
                endpoint="/v1/chat/completions",
                model=req.model or "gemini-4-argon",
                messages=messages_payload,
                actual_model=actual_model,
                start_time=start_t,
            )
            return StreamingResponse(
                wrapped_gen,
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
                    tools=req.tools,
                    tool_choice=req.tool_choice,
                )
                latency = int((time.time() - start_t) * 1000)
                reply_text = ""
                if isinstance(res, dict):
                    choices = res.get("choices", [])
                    if choices and isinstance(choices[0], dict):
                        reply_text = choices[0].get("message", {}).get("content", "")
                chat_history_manager.record_chat(
                    endpoint="/v1/chat/completions",
                    model=req.model or "gemini-4-argon",
                    messages=messages_payload,
                    response_text=reply_text,
                    status=200,
                    latency_ms=latency,
                    is_stream=False,
                    actual_model=actual_model
                )
                return res
            except Exception as e:
                _service_error(502, f"AI Studio 兼容接口调用失败: {str(e)}", "aistudio")

    # 1. Gemini 分流
    if model_name.startswith("gemini"):
        require_service_enabled("gemini")

        target_model = req.model if req.model and "gemini" in req.model else "gemini-4-hydrogen"
        reasoning = req.reasoning_effort or req.reasoning_level or "off"
        effective_timeout = _resolve_gemini_timeout(
            target_model, reasoning, getattr(req, "timeout", None)
        )
        messages_payload = [m.model_dump(exclude_none=True) for m in req.messages]
        extra = req.model_extra or {}
        tools = req.tools if req.tools is not None else extra.get("tools")
        tool_choice = req.tool_choice if req.tool_choice is not None else extra.get("tool_choice")
        gemini_tools_active = (
            has_tool_protocol(messages_payload, tools)
            and str(tool_choice or "").lower() != "none"
            and not (isinstance(tool_choice, dict) and str(tool_choice.get("type") or "").lower() == "none")
        )

        if req.stream:
            def _gemini_retry_stream():
                attempt_messages = sanitize_tool_limit_history(
                    messages_payload, tools_active=gemini_tools_active
                )
                sent_role = False

                for attempt in range(MAX_TOOL_LIMIT_RETRIES + 1):
                    if target_model.endswith("-task") or not gemini_pool.is_running():
                        raw_gen = gemini_conv_manager.stream_openai_task_chat(
                            messages=attempt_messages,
                            model=target_model,
                            tools=tools,
                            tool_choice=tool_choice,
                            timeout=effective_timeout,
                        )
                    else:
                        raw_gen = gemini_pool.stream_chat_messages(
                            messages=attempt_messages,
                            model=target_model,
                            reasoning_level=reasoning,
                            timeout=effective_timeout,
                            tools=tools,
                            tool_choice=tool_choice,
                        )
                    stream_iter = intercept_openai_sse_tool_limit(
                        raw_gen, tools_active=gemini_tools_active
                    )
                    try:
                        skip_next_blank = False
                        for item in stream_iter:
                            stripped = item.strip()
                            if skip_next_blank:
                                skip_next_blank = False
                                if not stripped:
                                    continue
                            if stripped.startswith("data:") and stripped[5:].strip() not in ("", "[DONE]"):
                                try:
                                    obj = json.loads(stripped[5:].strip())
                                    choices = obj.get("choices") or []
                                    if choices and isinstance(choices[0], dict):
                                        delta = choices[0].get("delta") or {}
                                        if isinstance(delta, dict) and "role" in delta:
                                            if sent_role and set(delta.keys()) == {"role"} and choices[0].get("finish_reason") is None:
                                                if not (item.endswith("\n\n") or item.endswith("\r\n\r\n")):
                                                    skip_next_blank = True
                                                continue
                                            sent_role = True
                                except Exception:
                                    pass
                            yield item
                        return
                    except ToolLimitReachedError as limit_err:
                        preview = (
                            limit_err.reply_text.strip().splitlines()[0][:80]
                            if limit_err.reply_text.strip()
                            else ""
                        )
                        print(
                            f"⚠️ [Gemini Tool-Limit] 拦截到伪造次数上限提示 "
                            f"(第 {attempt + 1}/{MAX_TOOL_LIMIT_RETRIES} 次自动续轮): "
                            f"{preview!r}",
                            flush=True,
                        )
                        if attempt >= MAX_TOOL_LIMIT_RETRIES:
                            cid = f"chatcmpl-gemini-{int(time.time() * 1000)}"
                            created_ts = int(time.time())
                            delta_payload = {"content": limit_err.reply_text}
                            if not sent_role:
                                delta_payload["role"] = "assistant"
                                sent_role = True
                            c1 = {
                                "id": cid,
                                "object": "chat.completion.chunk",
                                "created": created_ts,
                                "model": target_model,
                                "choices": [{"index": 0, "delta": delta_payload, "finish_reason": None}],
                            }
                            c2 = {
                                "id": cid,
                                "object": "chat.completion.chunk",
                                "created": created_ts,
                                "model": target_model,
                                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                            }
                            yield f"data: {json.dumps(c1, ensure_ascii=False)}\n\n"
                            yield f"data: {json.dumps(c2, ensure_ascii=False)}\n\n"
                            yield "data: [DONE]\n\n"
                            return
                        attempt_messages = append_tool_limit_override(
                            attempt_messages,
                            limit_err.reply_text,
                            attempt=attempt + 1,
                        )

            wrapped_gen = wrap_chat_stream(
                _gemini_retry_stream(),
                endpoint="/v1/chat/completions",
                model=req.model or target_model,
                messages=messages_payload,
                actual_model=target_model,
                meta={"reasoning_level": reasoning},
                start_time=start_t,
            )
            return StreamingResponse(
                wrapped_gen,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )

        if target_model.endswith("-task") or not gemini_pool.is_running():
            attempt_messages = sanitize_tool_limit_history(messages_payload, tools_active=gemini_tools_active)
            txt_parts, tc_map, fin_reason = [], {}, "stop"
            for sse_line in gemini_conv_manager.stream_openai_task_chat(
                messages=attempt_messages, model=target_model, tools=tools, tool_choice=tool_choice, timeout=effective_timeout
            ):
                st = sse_line.strip()
                if not st.startswith("data:") or st == "data: [DONE]": continue
                try: obj = json.loads(st[5:].strip())
                except Exception: continue
                ch0 = (obj.get("choices") or [{}])[0]
                if ch0.get("finish_reason"): fin_reason = ch0["finish_reason"]
                dl = ch0.get("delta") or {}
                if dl.get("content"): txt_parts.append(dl["content"])
                for tc in dl.get("tool_calls") or []:
                    idx = tc.get("index", 0)
                    tc_map.setdefault(idx, {"id": tc.get("id", ""), "type": "function", "function": {"name": "", "arguments": ""}})
                    if tc.get("id"): tc_map[idx]["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    tc_map[idx]["function"]["name"] += fn.get("name", "")
                    tc_map[idx]["function"]["arguments"] += fn.get("arguments", "")
            msg_out = {"role": "assistant", "content": "".join(txt_parts) or None}
            if tc_map: msg_out["tool_calls"] = [tc_map[k] for k in sorted(tc_map)]
            return {
                "id": f"chatcmpl-gemini-task-{int(time.time()*1000)}",
                "object": "chat.completion", "created": int(time.time()), "model": target_model,
                "choices": [{"index": 0, "message": msg_out, "finish_reason": fin_reason}],
                "usage": {"prompt_tokens": len(last_user_msg), "completion_tokens": len(msg_out.get("content") or ""), "total_tokens": len(last_user_msg) + len(msg_out.get("content") or "")},
            }

        try:
            res = gemini_pool.ask_with_details(
                prompt=last_user_msg,
                model=target_model,
                reasoning_level=reasoning,
                timeout=effective_timeout,
            )
        except Exception as first_err:
            failure_kind = gemini_failure_kind(str(first_err))
            if failure_kind in {"login", "unbound"}:
                print(f"[Gemini OpenAI] 检测到上游异常 ({failure_kind})，正在从 Cookie Hub 自动刷新凭证...", flush=True)
            elif not gemini_failure_should_retry(str(first_err)):
                _gemini_stop(str(first_err))
            try:
                if failure_kind in {"login", "unbound"}:
                    refreshed = gemini_pool.recover_from_failure(failure_kind)
                    if failure_kind == "unbound" and not refreshed:
                        _gemini_stop(str(first_err))
                else:
                    gemini_pool.reset_proxies()
                res = gemini_pool.ask_with_details(
                    prompt=last_user_msg,
                    model=target_model,
                    reasoning_level=reasoning,
                    timeout=effective_timeout,
                )
            except HTTPException:
                raise
            except Exception as retry_err:
                _service_error(
                    502,
                    f"Gemini 兼容接口调用失败: {first_err} (自愈重试亦未成功: {retry_err})",
                    "gemini",
                )

        cid = f"chatcmpl-gemini-{int(time.time()*1000)}"
        chat_history_manager.record_chat(
            endpoint="/v1/chat/completions",
            model=req.model or target_model,
            messages=messages_payload,
            response_text=res.get("reply", ""),
            status=200,
            latency_ms=res.get("took_ms", 0),
            is_stream=False,
            actual_model=target_model,
            meta={
                "account_id": res.get("account_id"),
                "account_label": res.get("account_label"),
                "authuser": res.get("authuser"),
            }
        )
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
    require_service_enabled("chatgpt")
    req_model_lower = (req.model or "").lower().strip()
    if "moni" in req_model_lower or req_model_lower in ("chatgpt-web", "chatgpt-web-moni"):
        target_gpt_model = "chatgpt-web-moni"
    elif req_model_lower in ("gpt-4o", "gpt-3.5-turbo"):
        target_gpt_model = "auto"  # 已下线模型平滑过渡至 auto
    elif req.model:
        target_gpt_model = req.model
    else:
        target_gpt_model = "auto"

    audit_messages = [m.model_dump(exclude_none=True) for m in req.messages]
    _, _, is_member_plan = _chatgpt_plan_context()
    target_gpt_model, effort = _resolve_chatgpt_model_and_effort(
        target_gpt_model,
        req.reasoning_effort or req.reasoning_level or "",
        is_member_plan,
    )
    extra = req.model_extra or {}
    tools = req.tools if req.tools is not None else extra.get("tools")
    tool_choice = req.tool_choice if req.tool_choice is not None else extra.get("tool_choice")

    use_tool_bridge = (
        target_gpt_model != "chatgpt-web-moni"
        and has_tool_protocol(audit_messages, tools)
    )
    allowed_tool_names = None
    tool_mode = "auto"
    upstream_messages = audit_messages
    upstream_tools = tools
    upstream_tool_choice = tool_choice
    if use_tool_bridge:
        upstream_messages, allowed_tool_names, tool_mode = prepare_tool_messages(
            audit_messages,
            tools=tools,
            tool_choice=tool_choice,
        )
        # Prompt-level tool bridge handles tool schemas directly; do not pass raw
        # `tools` to chatgpt2api, which would otherwise inject TOOL_UNAVAILABLE_SYSTEM_MESSAGE.
        upstream_tools = None
        upstream_tool_choice = None

    tool_audit_meta = {
        "tools_declared": len(tools or []),
        "tool_names": [item["name"] for item in normalize_tool_definitions(tools)],
        "tool_bridge": use_tool_bridge,
        "tool_mode": tool_mode,
        "tool_choice": tool_choice,
    }

    if req.stream:
        attempt_messages = upstream_messages
        stream_iter = None
        first_chunk = None

        for attempt in range(MAX_TOOL_LIMIT_RETRIES + 1):
            def _request_upstream(stream_messages):
                return chatgpt_client.chat(
                    stream_messages,
                    model=target_gpt_model,
                    stream=True,
                    thinking_effort=effort,
                    tools=upstream_tools,
                    tool_choice=upstream_tool_choice,
                )
            if use_tool_bridge:
                stream_iter = iter(
                    stream_tool_bridge(
                        _request_upstream,
                        attempt_messages,
                        model=req.model or target_gpt_model,
                        allowed_names=allowed_tool_names,
                        mode=tool_mode,
                        audit_state=tool_audit_meta,
                    )
                )
            else:
                stream_iter = iter(_request_upstream(attempt_messages))
            try:
                first_chunk = next(stream_iter)
                break
            except ToolLimitReachedError as limit_err:
                if attempt >= MAX_TOOL_LIMIT_RETRIES:
                    cid = f"chatcmpl-{int(time.time() * 1000)}"
                    created_ts = int(time.time())
                    m_name = req.model or target_gpt_model
                    first_chunk = {
                        "id": cid,
                        "object": "chat.completion.chunk",
                        "created": created_ts,
                        "model": m_name,
                        "choices": [{"index": 0, "delta": {"role": "assistant", "content": limit_err.reply_text}, "finish_reason": None}],
                    }
                    stream_iter = iter([
                        {
                            "id": cid,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": m_name,
                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                        }
                    ])
                    break
                attempt_messages = append_tool_limit_override(
                    attempt_messages,
                    limit_err.reply_text,
                    attempt=attempt + 1,
                )
                continue
            except StopIteration:
                latency = int((time.time() - start_t) * 1000)
                err_msg = "ChatGPT 上游流式返回为空，未产生任何输出"
                chat_history_manager.record_chat(
                    endpoint="/v1/chat/completions",
                    model=req.model or target_gpt_model,
                    messages=audit_messages,
                    response_text="",
                    status=502,
                    latency_ms=latency,
                    is_stream=True,
                    actual_model=target_gpt_model,
                    error_message=err_msg,
                )
                return JSONResponse(
                    status_code=502,
                    content={"error": {"message": err_msg, "type": "upstream_error", "code": "empty_stream"}},
                )
            except Exception as e:
                latency = int((time.time() - start_t) * 1000)
                err_msg = str(e)
                low = err_msg.lower()
                is_too_large = ("status=413" in low) or ("payload too large" in low) or ("request entity too large" in low)
                is_timeout = ("timed out" in low or "timeout" in low or "超时" in err_msg)
                err_status = 400 if is_too_large else (504 if is_timeout else 502)
                chat_history_manager.record_chat(
                    endpoint="/v1/chat/completions",
                    model=req.model or target_gpt_model,
                    messages=audit_messages,
                    response_text="",
                    status=err_status,
                    latency_ms=latency,
                    is_stream=True,
                    actual_model=target_gpt_model,
                    error_message=err_msg,
                )
                return JSONResponse(
                    status_code=err_status,
                    content={
                        "error": {
                            "message": err_msg,
                            "type": "invalid_request_error" if is_too_large else ("timeout_error" if err_status == 504 else "upstream_error"),
                            "code": "context_length_exceeded" if is_too_large else str(err_status),
                        }
                    },
                )

        def _sse_generator():
            try:
                yield f"data: {json.dumps(first_chunk, ensure_ascii=False)}\n\n"
                for chunk in stream_iter:
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                err_data = {"error": {"message": str(e), "type": "chatgpt_error"}}
                yield f"data: {json.dumps(err_data, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

        wrapped_gen = wrap_chat_stream(
            _sse_generator(),
            endpoint="/v1/chat/completions",
            model=req.model or target_gpt_model,
            messages=audit_messages,
            actual_model=target_gpt_model,
            start_time=start_t,
            meta=tool_audit_meta,
        )
        return StreamingResponse(
            wrapped_gen,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        attempt_messages = upstream_messages
        res = None
        for attempt in range(MAX_TOOL_LIMIT_RETRIES + 1):
            res = chatgpt_client.chat(
                attempt_messages,
                model=target_gpt_model,
                stream=False,
                thinking_effort=effort,
                tools=upstream_tools,
                tool_choice=upstream_tool_choice,
            )
            if use_tool_bridge:
                try:
                    res = adapt_completion_response(res, allowed_names=allowed_tool_names, mode=tool_mode)
                except ToolLimitReachedError as limit_err:
                    if attempt >= MAX_TOOL_LIMIT_RETRIES:
                        break
                    attempt_messages = append_tool_limit_override(
                        attempt_messages,
                        limit_err.reply_text,
                        attempt=attempt + 1,
                    )
                    continue
            break
        latency = int((time.time() - start_t) * 1000)
        reply_content = ""
        if isinstance(res, dict):
            choices = res.get("choices", [])
            if choices and isinstance(choices[0], dict):
                msg_obj = choices[0].get("message", {})
                reply_content = msg_obj.get("content") or ""
                if not reply_content and isinstance(msg_obj.get("tool_calls"), list):
                    reply_content = " ".join(
                        f"[tool_call: {tc.get('function', {}).get('name')}({tc.get('function', {}).get('arguments', '{}')})]"
                        for tc in msg_obj["tool_calls"]
                        if isinstance(tc, dict)
                    )
        chat_history_manager.record_chat(
            endpoint="/v1/chat/completions",
            model=req.model or target_gpt_model,
            messages=audit_messages,
            response_text=reply_content,
            status=200,
            latency_ms=latency,
            is_stream=False,
            actual_model=target_gpt_model,
            meta=tool_audit_meta,
        )
        return res
    except Exception as e:
        if use_tool_bridge:
            latency = int((time.time() - start_t) * 1000)
            err_msg = str(e)
            low = err_msg.lower()
            is_too_large = ("status=413" in low) or ("payload too large" in low) or ("request entity too large" in low)
            err_status = 400 if is_too_large else 502
            chat_history_manager.record_chat(
                endpoint="/v1/chat/completions",
                model=req.model or target_gpt_model,
                messages=audit_messages,
                response_text="",
                status=err_status,
                latency_ms=latency,
                is_stream=False,
                actual_model=target_gpt_model,
                error_message=err_msg,
            )
            if is_too_large:
                return JSONResponse(
                    status_code=400,
                    content={"error": {"message": err_msg, "type": "invalid_request_error", "code": "context_length_exceeded"}},
                )
            _service_error(502, f"ChatGPT 工具调用桥接失败: {err_msg}", "chatgpt")
        # 降级尝试单句提问
        try:
            reply = chatgpt_client.ask(last_user_msg, model=target_gpt_model)
            latency = int((time.time() - start_t) * 1000)
            cid = f"chatcmpl-gpt-{int(time.time()*1000)}"
            chat_history_manager.record_chat(
                endpoint="/v1/chat/completions",
                model=req.model or target_gpt_model,
                messages=audit_messages,
                response_text=reply,
                status=200,
                latency_ms=latency,
                is_stream=False,
                actual_model=target_gpt_model
            )
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
            latency = int((time.time() - start_t) * 1000)
            chat_history_manager.record_chat(
                endpoint="/v1/chat/completions",
                model=req.model or target_gpt_model,
                messages=audit_messages,
                response_text="",
                status=502,
                latency_ms=latency,
                is_stream=False,
                actual_model=target_gpt_model,
                error_message=str(fallback_err),
            )
            _service_error(502, f"ChatGPT 兼容调用失败: {str(fallback_err)}", "chatgpt")


@app.post("/v1/images/generations", summary="OpenAI 兼容图片生成接口", tags=["OpenAI 兼容接口"])
def openai_image_generations(body: OpenAIImageGenerationRequest):
    """
    提供标准 OpenAI POST /v1/images/generations 接口，
    底层自动路由到 chatgpt2api 官方逆向的 gpt-image-2 / DALL-E 3 生成能力。
    """
    require_service_enabled('chatgpt')
    start_t = time.time()
    target_model = body.model or 'gpt-image-2'
    fmt = body.response_format or 'b64_json'
    n_val = body.n or 1
    chat_id = chat_history_manager.start_chat(endpoint='/v1/images/generations', model=target_model, messages=body.prompt, is_stream=False, actual_model=target_model, meta={'type': 'image_generation', 'n': n_val, 'response_format': fmt})
    try:
        res = chatgpt_client.generate_image(prompt=body.prompt, model=target_model, n=n_val, response_format=fmt)
        latency = int((time.time() - start_t) * 1000)
        summary_text, meta = _format_image_history_summary(res, response_format=fmt)
        meta['n'] = n_val
        chat_history_manager.finish_chat(chat_id, response_text=summary_text, status=200, latency_ms=latency, actual_model=target_model, meta=meta)
        return res
    except ServiceDisabledError:
        raise
    except Exception as e:
        latency = int((time.time() - start_t) * 1000)
        chat_history_manager.finish_chat(chat_id, response_text='', status=502, latency_ms=latency, actual_model=target_model, error_message=str(e))
        raise HTTPException(status_code=502, detail=f'ChatGPT 图片生成失败: {str(e)}')


@app.post("/v1/audio/speech", summary="OpenAI 兼容语音合成接口", tags=["OpenAI 兼容接口"])
def openai_audio_speech(body: OpenAISpeechRequest):
    """
    提供标准 OpenAI POST /v1/audio/speech 接口，
    底层自动路由到 MiniMax / 海螺语音平台原生 WebSocket 与模型进行超自然高保真语音渲染。
    返回标准 audio/mpeg 二进制音频流。
    """
    import io
    require_service_enabled("minimax")
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
    except ServiceDisabledError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


# 模型元数据中文描述字典 (保留全部官方模型及 Plus/Work 专有模型，底层不剥夺)
REVERSE_MODEL_DESCRIPTIONS = {
    # --- 语音合成模型 (MiniMax TTS: OpenAI 兼容) ---
    "speech-01-hd": "[超自然语音/TTS] MiniMax 海螺语音 HD 高保真自然拟真模型",
    "speech-02-hd": "[超自然语音/TTS] MiniMax 旗舰超自然语音合成模型",
    "tts-1": "[语音合成/TTS] OpenAI 兼容快速语音合成 (由 MiniMax 驱动)",
    "tts-1-hd": "[语音合成/TTS] OpenAI 兼容高保真语音合成 (由 MiniMax 驱动)",

    # --- 日常聊天模型 (免费账号正式露出与高频主选) ---
    "auto": "[日常聊天/Auto] Auto 智能自动优选模型",
    "gpt-6": "[日常聊天/Instant] 6 Instant 官方日常聊天模型 (自动决定思考时长)",
    "gpt-6-t-mini": "[深度思考/Thinking] 6 Thinking 快速深度思考模型",
    "gpt-6-instant": "[极速响应/Chat] GPT-6 极速即时响应模型",
    "gpt-6-thinking": "[深度思考/Chat] GPT-6 深度思考模型",
    "gpt-6-mini": "[轻量不思考/Mini] GPT-6 纯轻量不思考模型",
    "gpt-6-t-mini-mini": "[微缩思考/Mini] GPT-6 微缩思考模型",

    # --- Plus / 高阶 / 深度推理模型 (保留支持，Plus 账号可见) ---
    "gpt-5-6": "[深度推理/Luna] GPT-5.6 Luna 深度推理模型",
    "gpt-5-6-thinking": "[深度思考/旧标识] GPT-5.6 思考模型",
    "gpt-5-6-instant": "[极速响应/Chat] GPT-5.6 极速即时响应模型",
    "gpt-5-6-mini": "[轻量不思考/Mini] GPT-5.6 纯轻量不思考模型",
    "gpt-5-6-t-mini": "[轻量思考/Mini] GPT-5.6 轻量思考模型",
    "gpt-5-6-t-mini-mini": "[微缩思考/Mini] GPT-5.6 微缩思考模型",
    "research": "[学术研报/Plus专享] Deep Research 全网深度学术与研报挖掘模型",
    "gpt-image-2": "[文生图/Image] ChatGPT 官方逆向绘图专用 (DALL-E 3)",
    "codex-gpt-image-2": "[高清绘图/Codex] ChatGPT Codex 高清画图专用",

    # --- Work 协同工作台专有模型 (Work Mode: is_work_mode_model = true, 官方带 -wm 后缀，Plus专享) ---
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


def _resolve_chatgpt_model_and_effort(
    requested_model: str,
    reasoning_level: Optional[str],
    is_member: bool,
) -> tuple[str, str]:
    """将网页端主模型 (6 / 6 Plus / 5.6 / 6 Sol / 5.6 Sol / Auto) + 三档推理深度映射为上游真实模型与 thinking_effort。"""
    mid = str(requested_model or "auto").strip()
    raw_effort = str(reasoning_level or "").strip().lower()

    if mid == "gpt-6":
        if raw_effort in ("", "off", "none"):
            return "gpt-6-instant", ""
        if raw_effort in ("low", "medium", "standard"):
            return ("gpt-6-thinking" if is_member else "gpt-6-t-mini"), "standard"
        if raw_effort in ("high", "xhigh", "extended", "max"):
            return ("gpt-6-thinking" if is_member else "gpt-6-t-mini"), "extended"
        return "gpt-6", ""

    if mid == "gpt-6-plus":
        if raw_effort in ("", "off", "none"):
            return "gpt-6-thinking", ""
        if raw_effort in ("low", "medium", "standard"):
            return "gpt-6-thinking", "standard"
        if raw_effort == "max":
            return "gpt-6-thinking", "max"
        return "gpt-6-thinking", "extended"

    if mid == "gpt-5-6":
        if raw_effort in ("", "off", "none"):
            return "gpt-5-6-instant", ""
        if raw_effort in ("low", "medium", "standard"):
            return "gpt-5-6-thinking", "standard"
        if raw_effort in ("high", "xhigh", "extended", "max"):
            return "gpt-5-6-thinking", "extended"
        return "gpt-5-6", ""

    return mid, _normalize_chatgpt_thinking_effort(raw_effort, mid)


def _normalize_chatgpt_thinking_effort(effort: Optional[str], model: str = "") -> str:
    """将 OpenAI/控制台推理级别 (off/low/medium/high) 映射为 ChatGPT 网页端协议支持的 thinking_effort (standard/extended/max)。"""
    raw = str(effort or "").strip().lower()
    if raw in ("", "off", "none", "auto"):
        return ""
    mid = str(model or "").strip().lower()
    if mid in ("gpt-6-instant", "gpt-5-6-instant", "gpt-6-mini", "gpt-5-6-mini", "research", "chatgpt-web", "chatgpt-web-moni"):
        return ""
    mapping = {
        "low": "standard",
        "medium": "standard",
        "standard": "standard",
        "high": "extended",
        "xhigh": "extended",
        "extended": "extended",
        "max": "max",
    }
    return mapping.get(raw, "")


_GEMINI_MODEL_NOTES = {
    "gemini-3.5-flash-lite": "极速响应",
    "gemini-3.6-flash": "多模态高通量",
    "gemini-3.8-flash": "新一代 Flash",
    "gemini-3.7-flash": "3.8 Flash 的旧别名",
    "gemini-3.1-pro": "强推理",
    "gemini-4-argon": "复杂推理",
    "gemini-image": "网页生图",
    "gemini-video": "网页生视频",
    "gemini-music": "网页生音乐",
    "gemini-canvas": "Canvas",
}

_GEMINI_MODEL_FALLBACK = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-3.1-pro",
    "gemini-4-argon",
    "gemini-canvas",
    "gemini-image",
    "gemini-music",
    "gemini-video",
]


def _is_gemini_web_pool_model(name: str) -> bool:
    """网页选择器上的模型走 Gemini 号池，不进 AI Studio。"""
    base = (name or "").lower().strip()
    for suffix in ("-thinking-medium", "-thinking", "-thinking-lite", "-task"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base in {
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.8-flash",
        "gemini-3.1-pro",
        "gemini-4-hydrogen",
        "gemini-4-argon",
        "gemini-4-carbon",
        "gemini-image",
        "gemini-video",
        "gemini-music",
        "gemini-canvas",
    }


def _chatgpt_plan_context():
    """解析当前生效 ChatGPT 账号的订阅方案 (free / plus / pro / team / enterprise)。"""
    plan = "free"
    plan_label = "免费版"
    try:
        hint = chatgpt_client.public_account() or {}
        if hint.get("plan"):
            plan = str(hint.get("plan")).strip().lower() or "free"
        if hint.get("plan_label"):
            plan_label = str(hint.get("plan_label")).strip() or plan_label
    except Exception:
        pass
    if plan == "free":
        try:
            accts = chatgpt_client.get_dashboard_accounts() or []
            active = [a for a in accts if a.get("status") in ("enabled", "ready") and a.get("is_member")]
            if active:
                plan = str(active[0].get("membership") or active[0].get("plan_tier") or "plus").strip().lower()
                plan_label = chatgpt_client.plan_label(plan)
        except Exception:
            pass
    is_member = plan not in ("", "free", "none", "unknown")
    return plan, plan_label, is_member


def _build_chatgpt_model_catalog(raw_res: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """构建区分免费版与 Plus 会员的 ChatGPT 模型目录，过滤内部 gate 占位符。"""
    plan, plan_label, is_member = _chatgpt_plan_context()
    raw_items = (raw_res or {}).get("data") if isinstance(raw_res, dict) else []
    clean_data = []
    seen_ids = set()
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        mid = str(item.get("id") or "").strip()
        if not mid or mid in seen_ids or "reserved_gate" in mid:
            continue
        seen_ids.add(mid)
        clean_data.append(item)

    if not clean_data:
        for mid in REVERSE_MODEL_DESCRIPTIONS:
            clean_data.append({
                "id": mid,
                "object": "model",
                "created": 0,
                "owned_by": "chatgpt",
            })
            seen_ids.add(mid)

    # 对齐 ChatGPT 网页选择器：仅保留主线模型，推理深度通过 Reasoning 下拉框三档映射
    webpage_specs = [
        ("auto", f"Auto（{plan_label} · 智能优选）" if is_member else "Auto（免费 · 智能优选）", False, "chat"),
        ("gpt-6", "GPT-6（Instant / Thinking）", False, "chat"),
        ("gpt-6-plus", f"GPT-6 Plus（{plan_label} 专享）" if is_member else "GPT-6 Plus（Plus 专享/未开通）", True, "chat"),
        ("gpt-5-6", "GPT-5.6（Instant / Thinking）" if is_member else "GPT-5.6（Plus 专享/未开通）", True, "chat"),
        ("gpt-6-sol-wm", "GPT-6 Sol（协同工作区）" if is_member else "GPT-6 Sol（Plus 专享/未开通）", True, "work"),
        ("gpt-5.6-sol-wm", "GPT-5.6 Sol（协同工作区）" if is_member else "GPT-5.6 Sol（Plus 专享/未开通）", True, "work"),
        ("research", "Deep Research（全网深度研究）" if is_member else "Deep Research（Plus 专享/未开通）", True, "chat"),
        ("gpt-image-2", "GPT Image 2（绘图/动图）", False, "image"),
        ("chatgpt-web", "ChatGPT Web（网页原生）", False, "chat"),
    ]

    ui_models = []
    for mid, label, is_plus_only, scene in webpage_specs:
        # 若上游列表非空，过滤掉上游完全不存在且非合成入口的模型（gpt-6 / gpt-6-plus / chatgpt-web 始终保留）
        if mid not in ("auto", "gpt-6", "gpt-6-plus", "gpt-image-2", "chatgpt-web"):
            has_upstream = (
                mid in seen_ids
                or (mid == "gpt-5-6" and any(k in seen_ids for k in ("gpt-5-6", "gpt-5-6-instant", "gpt-5-6-thinking")))
            )
            if not has_upstream:
                continue
        tier = "plus" if is_plus_only else "free"
        locked = bool(is_plus_only and not is_member)
        ui_models.append({
            "id": mid,
            "label": label,
            "tier": tier,
            "locked": locked,
            "scene": scene,
            "description": REVERSE_MODEL_DESCRIPTIONS.get(mid, MODEL_DISPLAY_NAMES.get(mid, label)),
        })

    return {
        "object": "list",
        "plan": plan,
        "plan_label": plan_label,
        "is_member": is_member,
        "models": ui_models,
        "data": clean_data,
    }


def _gemini_catalog_rows():
    """对外目录用网页上的型号名。3.8 已下线，日常模型是 4 Hydrogen。"""
    rows = []
    seen = set()
    for item in gemini_pool.list_web_models():
        mid = item.get("id") or ""
        if not mid or mid in seen or item.get("locked"):
            continue
        seen.add(mid)
        note = item.get("label") or mid
        rows.append({
            "id": mid, "object": "model", "owned_by": "google-cookie-suite",
            "tag": "pool", "type": "gemini_pool", "mode": "chat",
            "description": f"[Gemini 聊天] {note}",
        })
    for item in gemini_pool.list_task_models():
        mid = item.get("id") or ""
        if not mid or mid in seen:
            continue
        seen.add(mid)
        note = item.get("label") or mid
        rows.append({
            "id": mid, "object": "model", "owned_by": "google-cookie-suite",
            "tag": "pool_task", "type": "gemini_task", "mode": "task",
            "description": f"[Gemini 任务/Agent] {note}",
        })
    for mid, note in (
        ("gemini-image", "网页生图"),
        ("gemini-video", "网页生视频"),
        ("gemini-music", "网页生音乐"),
        ("gemini-canvas", "Canvas"),
    ):
        if mid in seen:
            continue
        rows.append({
            "id": mid,
            "object": "model",
            "owned_by": "google-cookie-suite",
            "tag": "pool",
            "type": "gemini_pool",
            "description": f"[号池协议直连] {mid} · {note}",
        })
    return rows


@app.post("/api/export/opencode", summary="把当前对话模型写入 OpenCode 配置", tags=["系统管理"])
def export_opencode(set_default: bool = Query(False, description="是否把默认模型改成 cookie-suite/gemini-3.5-flash-lite")):
    """按本机 OpenCode 1.18 的 provider 格式合并写入 ~/.config/opencode/opencode.json。
    区分免费版与 Plus 版展示：免费版仅展示官方前台主力模型，Plus 账号额外展示高阶专享模型。
    """
    catalog = openai_models()
    raw = catalog.get("data") if isinstance(catalog, dict) else []
    plan = "free"
    try:
        hint = chatgpt_client.public_account()
        if hint and hint.get("plan"):
            plan = str(hint.get("plan")).lower()
    except Exception:
        pass
    try:
        result = export_to_file(raw or [], set_default=set_default, plan=plan, api_key=token_store.get_token())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"写入 OpenCode 配置失败: {exc}")
    return {
        "success": True,
        "message": f"已写入 OpenCode，共 {result['count']} 个对话模型（当前方案: {plan}）。",
        **result,
    }


@app.get("/v1/models", summary="OpenAI 兼容模型列表", tags=["OpenAI 兼容接口"])
def openai_models():
    """返回 OpenAI 兼容模型列表，动态同步逆向引擎真实可用模型并打标：
    - moni (网页模拟输入): 基于浏览器 DOM 模拟键盘输入与发送 (chatgpt-web, chatgpt-web-moni)
    - reverse (协议逆向直连): 包含 GPT-6 / GPT-5.6 的 thinking、instant、mini 系列及深度研究模型
    - pool (谷歌号池直连): Google Gemini 多账号自动轮询直连
    - 已彻底移除官方下线的过时 gpt-4o 模型
    """
    plan, plan_label, is_member = _chatgpt_plan_context()
    reverse_models = []
    seen_ids = set()

    def _make_reverse_row(mid: str, desc: str) -> Dict[str, Any]:
        is_wm = "-wm" in mid.lower()
        is_plus_only = (mid in PLUS_EXCLUSIVE_MODELS) or is_wm
        row: Dict[str, Any] = {
            "id": mid,
            "object": "model",
            "owned_by": "openai-reverse",
            "tag": "reverse",
            "type": "api_reverse",
            "scene": "work" if is_wm else "chat",
            "tier": "plus" if is_plus_only else "free",
            "locked": bool(is_plus_only and not is_member),
            "description": desc,
        }
        reasoning = _chatgpt_reasoning(mid)
        if reasoning:
            row["reasoning"] = reasoning
        return row

    # 1. 优先从运行中的逆向引擎动态提取实时模型
    chatgpt_enabled = is_service_enabled("chatgpt")
    if chatgpt_enabled and chatgpt_client.reverse.is_running():
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
                reverse_models.append(_make_reverse_row(mid, desc))
        except Exception:
            pass

    # 兜底回退：若逆向引擎暂时未拉取到，使用内建全量逆向清单 (包含 thinking，无 4o)
    if chatgpt_enabled and not reverse_models:
        for mid, desc in REVERSE_MODEL_DESCRIPTIONS.items():
            reverse_models.append(_make_reverse_row(mid, desc))

    # 2. 网页模拟输入模型 (专属 moni 标签)
    moni_models = [
        {"id": "chatgpt-web-moni", "object": "model", "owned_by": "moni", "tag": "moni", "type": "dom_simulated", "description": "[网页模拟输入/moni] 浏览器扩展 DOM 按键与点击输入模拟"},
        {"id": "chatgpt-web", "object": "model", "owned_by": "moni", "tag": "moni", "type": "dom_simulated", "description": "[网页模拟输入/moni] ChatGPT 浏览器同源页面输入桥接"},
    ] if chatgpt_enabled else []

    # 3. Google 多账号池直连模型（跟号池 /v1/models 走，不再写死一份旧名单）
    gemini_models = _gemini_catalog_rows() if is_service_enabled("gemini") else []

    # 4. Google AI Studio 逆向原生模型
    aistudio_models = []
    if is_service_enabled("aistudio"):
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
        "chatgpt_plan": plan,
        "chatgpt_plan_label": plan_label,
        "data": reverse_models + moni_models + gemini_models + aistudio_models,
    }


# ==========================================
# 8. 对话历史与审计接口 (/api/history/*)
# ==========================================
@app.get("/api/history/chats", summary="获取历史对话列表 (分页/筛选/大小统计)", tags=["对话历史审计"])
def get_chat_history(
    page: int = Query(1, ge=1, description="当前页码"),
    page_size: int = Query(15, ge=1, le=100, description="每页条数"),
    model: Optional[str] = Query(None, description="模型名称筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索 (提示词/回复内容/ID)"),
    status: Optional[int] = Query(None, description="状态码筛选")
):
    return chat_history_manager.list_chats(
        page=page, page_size=page_size, model=model, keyword=keyword, status=status
    )


@app.get("/api/history/chats/{chat_id}", summary="获取单条对话完整上下文与回复详情", tags=["对话历史审计"])
def get_chat_history_detail(chat_id: int):
    detail = chat_history_manager.get_chat_detail(chat_id)
    if not detail:
        raise HTTPException(status_code=404, detail="未找到该对话历史记录")
    return detail


@app.delete("/api/history/chats/{chat_id}", summary="删除单条对话历史记录", tags=["对话历史审计"])
def delete_chat_history_item(chat_id: int):
    ok = chat_history_manager.delete_chat(chat_id)
    if not ok:
        raise HTTPException(status_code=500, detail="删除记录失败")
    return {"success": True, "message": "记录已删除"}


@app.post("/api/history/clear", summary="清空所有对话历史并释放磁盘空间", tags=["对话历史审计"])
def clear_all_chat_history():
    ok = chat_history_manager.clear_all()
    if not ok:
        raise HTTPException(status_code=500, detail="清空对话历史失败")
    return {"success": True, "message": "已清空所有对话历史并整理磁盘空间", "stats": chat_history_manager.get_stats_dict()}


@app.get("/api/history/stats", summary="获取对话历史存储占用与总量统计", tags=["对话历史审计"])
def get_chat_history_stats():
    return chat_history_manager.get_stats_dict()


# ==========================================
# 9. 现代化 Web 控制台 (Management Dashboard)
# ==========================================
import importlib
import dashboard_template

_DASHBOARD_PATH = os.path.abspath(dashboard_template.__file__)
_DASHBOARD_MTIME = os.path.getmtime(_DASHBOARD_PATH) if os.path.exists(_DASHBOARD_PATH) else 0


@app.get("/", response_class=HTMLResponse, summary="Web 管理控制台", tags=["系统管理"])
def dashboard():
    """返回可视化管理面板 HTML 页面（支持模板热更新）。"""
    global _DASHBOARD_MTIME
    try:
        mtime = os.path.getmtime(_DASHBOARD_PATH)
        if mtime != _DASHBOARD_MTIME:
            importlib.reload(dashboard_template)
            _DASHBOARD_MTIME = mtime
    except Exception:
        pass
    return HTMLResponse(content=dashboard_template.DASHBOARD_HTML)


def generate_responses_text(model, messages):
    require_service_enabled("chatgpt")
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
    uvicorn.run("app_service:app", host=COOKIE_SUITE_HOST, port=COOKIE_SUITE_PORT, reload=False)
