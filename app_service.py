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
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# 保证本地通信不被外部代理拦截
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"

from cookie_bridge import CookieBridge
from gemini_service import MultiAccountGeminiPool, GeminiService
from chatgpt_service import ChatGPTBridgeClient
from bilibili_service import BilibiliService
from baidu_pan_service import BaiduPanService

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
chatgpt_client = ChatGPTBridgeClient()
bili_service = BilibiliService()
baidu_service = BaiduPanService()

START_TIME = datetime.datetime.now()


# ==========================================
# Pydantic 请求与响应模型
# ==========================================
class ChatRequest(BaseModel):
    prompt: str = Field(..., description="提问正文或指令内容", example="量子纠缠的基本原理是什么？")
    model: Optional[str] = Field("gemini-3.5-flash-lite", description="模型名称 (gemini-3.5-flash-lite, gemini-3.1-pro 等)", example="gemini-3.5-flash-lite")
    timeout: Optional[int] = Field(60, description="请求超时时间 (秒)", example=60)


class OpenAIMessage(BaseModel):
    role: str = Field(..., example="user")
    content: str = Field(..., example="Hello!")


class OpenAIChatRequest(BaseModel):
    model: Optional[str] = Field("gemini-3.5-flash-lite", example="gemini-3.5-flash-lite")
    messages: List[OpenAIMessage] = Field(..., description="对话历史消息列表")
    stream: Optional[bool] = Field(False, description="是否启用流式输出")
    temperature: Optional[float] = Field(0.7, example=0.7)


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


@app.post("/api/gemini/chat", summary="向 Gemini 发起提问 (自动 LRU 负载均衡轮换)", tags=["Gemini 多账号调度"])
def gemini_chat(req: ChatRequest):
    """
    底层通过最久未用 (LRU) 算法自动在已接入的 4 个账号之间分发请求，
    遇凭证过期或网络异常自动触发 Cookie Hub 热刷新与重试自愈。
    """
    if not gemini_pool.is_running():
        gemini_pool.start()

    try:
        res = gemini_pool.ask_with_details(prompt=req.prompt, model=req.model, timeout=req.timeout)
    except Exception as first_err:
        # 自动故障自愈：从 Cookie Hub 刷新凭证后重试一次
        try:
            gemini_pool.refresh_pool_cookies()
            res = gemini_pool.ask_with_details(prompt=req.prompt, model=req.model, timeout=req.timeout)
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
# 3. ChatGPT Web 原生桥接服务
# ==========================================
@app.get("/api/chatgpt/session", summary="获取当前 ChatGPT 登录会话与邮箱", tags=["ChatGPT Web 桥接"])
def get_chatgpt_session():
    """提取当前浏览器 ChatGPT 标签页的已登录用户与 Access Token。"""
    try:
        return chatgpt_client.get_session()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"无法获取 ChatGPT 会话: {str(e)}")


@app.get("/api/chatgpt/models", summary="获取 ChatGPT 账号可用模型列表", tags=["ChatGPT Web 桥接"])
def get_chatgpt_models():
    try:
        return chatgpt_client.get_models()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"无法获取模型列表: {str(e)}")


@app.post("/api/chatgpt/chat", summary="向 ChatGPT 发起网页端同源对话", tags=["ChatGPT Web 桥接"])
def chatgpt_ask(req: ChatRequest):
    """突破 Cloudflare Turnstile 验证码拦截，通过同源 SSE 拦截器获取模型回复。"""
    try:
        reply = chatgpt_client.ask(req.prompt)
        return {"success": True, "reply": reply}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ChatGPT 提问失败: {str(e)}")


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
# 7. 标准 OpenAI 兼容 API 路由 (/v1/*)
# ==========================================
@app.post("/v1/chat/completions", summary="OpenAI 兼容聊天接口", tags=["OpenAI 兼容接口"])
def openai_chat_completions(req: OpenAIChatRequest):
    """
    提供标准 OpenAI 规范接口，可无缝对接 NextChat、Chatbox、OpenCat、Cursor 等第三方大模型客户端。
    底层自动路由到 4 个 Google 账号池进行均衡轮询。
    """
    last_user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    if not last_user_msg:
        raise HTTPException(status_code=400, detail="未包含有效的 user 消息")

    if not gemini_pool.is_running():
        gemini_pool.start()

    target_model = req.model if req.model and "gemini" in req.model else "gemini-3.5-flash-lite"
    try:
        res = gemini_pool.ask_with_details(prompt=last_user_msg, model=target_model)
    except Exception as first_err:
        try:
            gemini_pool.refresh_pool_cookies()
            res = gemini_pool.ask_with_details(prompt=last_user_msg, model=target_model)
        except Exception as retry_err:
            raise HTTPException(status_code=502, detail=f"OpenAI 兼容接口调用失败: {str(retry_err)}")

    cid = f"chatcmpl-suite-{int(time.time()*1000)}"
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


@app.get("/v1/models", summary="OpenAI 兼容模型列表", tags=["OpenAI 兼容接口"])
def openai_models():
    return {
        "object": "list",
        "data": [
            {"id": "gemini-3.5-flash-lite", "object": "model", "owned_by": "google-cookie-suite"},
            {"id": "gemini-3.1-pro", "object": "model", "owned_by": "google-cookie-suite"},
            {"id": "gemini-3.6-flash", "object": "model", "owned_by": "google-cookie-suite"},
            {"id": "chatgpt-web", "object": "model", "owned_by": "openai-cookie-suite"},
        ],
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
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
            <i class="fa-solid fa-users-gear text-amber-400"></i> Google Gemini 4 账号槽位看板
          </h2>
          <p class="text-xs text-slate-400">基于浏览器 /u/0 ~ /u/3 多登录体系，自动分发、保活与熔断切换</p>
        </div>
        <div class="flex items-center gap-2">
          <button onclick="refreshAllCookies()" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20 transition flex items-center gap-1.5">
            <i class="fa-solid fa-arrows-rotate"></i> 从 Cookie Hub 刷新全部凭证
          </button>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-900/60 text-xs uppercase text-slate-400 border-b border-slate-800">
            <tr>
              <th class="py-3 px-4">序号</th>
              <th class="py-3 px-4">账号标签</th>
              <th class="py-3 px-4">URL 路由前缀</th>
              <th class="py-3 px-4">会话状态</th>
              <th class="py-3 px-4">连续失败数</th>
              <th class="py-3 px-4">最近调用时间</th>
              <th class="py-3 px-4 text-right">操作</th>
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
          <p class="text-xs text-slate-400">快速发起真实接口请求，查看响应数据与详细元信息</p>
        </div>

        <div>
          <label class="text-xs font-semibold text-slate-300 uppercase block mb-1.5">选择预设 API 模板</label>
          <select id="api-selector" onchange="switchApiTemplate()" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-400">
            <option value="gemini_chat">[POST] /api/gemini/chat (Gemini 4账号轮询对话)</option>
            <option value="openai_chat">[POST] /v1/chat/completions (OpenAI 兼容对话)</option>
            <option value="gemini_accounts">[GET] /api/gemini/accounts (查看4账号状态)</option>
            <option value="hub_status">[GET] /api/hub/status (Cookie Hub 状态)</option>
            <option value="hub_cookies">[GET] /api/hub/cookies?domain=google.com (提取实时Cookie)</option>
            <option value="bili_user">[GET] /api/bilibili/user (B站个人资料与大会员)</option>
            <option value="baidu_quota">[GET] /api/baidupan/quota (百度网盘总配额)</option>
            <option value="chatgpt_session">[GET] /api/chatgpt/session (ChatGPT 会话提取)</option>
          </select>
        </div>

        <div class="flex gap-2 items-center">
          <span id="req-method-badge" class="px-2.5 py-1 rounded-lg text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">POST</span>
          <input type="text" id="req-endpoint" class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-400" value="/api/gemini/chat" readonly>
        </div>

        <div id="req-body-container">
          <label class="text-xs font-semibold text-slate-300 uppercase block mb-1.5">请求 Body (JSON)</label>
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
            <i class="fa-solid fa-globe"></i> ChatGPT Web / Bilibili / 百度网盘
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-2 font-mono">
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
        body: JSON.stringify({ prompt: "请用一句话告诉我：量子纠缠是什么？", model: "gemini-3.5-flash-lite", timeout: 60 }, null, 2)
      },
      openai_chat: {
        method: "POST",
        url: "/v1/chat/completions",
        body: JSON.stringify({ model: "gemini-3.5-flash-lite", messages: [{ role: "user", content: "请只回复两个字母：OK。" }] }, null, 2)
      },
      gemini_accounts: {
        method: "GET",
        url: "/api/gemini/accounts",
        body: ""
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
      chatgpt_session: {
        method: "GET",
        url: "/api/chatgpt/session",
        body: ""
      }
    };

    function switchApiTemplate() {
      const key = document.getElementById("api-selector").value;
      const t = TEMPLATES[key];
      if (!t) return;
      document.getElementById("req-method-badge").innerText = t.method;
      document.getElementById("req-endpoint").value = t.url;
      const container = document.getElementById("req-body-container");
      if (t.method === "GET") {
        container.style.display = "none";
      } else {
        container.style.display = "block";
        document.getElementById("req-body").value = t.body;
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

        // 2. 账号列表
        const acctRes = await fetch("/api/gemini/accounts");
        if (acctRes.ok) {
          const data = await acctRes.json();
          const tbody = document.getElementById("accounts-tbody");
          tbody.innerHTML = "";
          (data.accounts || []).forEach(a => {
            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-900/40 transition";
            const lastUsed = a.last_used_at > 0 ? new Date(a.last_used_at * 1000).toLocaleTimeString() : "从未调用";
            tr.innerHTML = `
              <td class="py-3 px-4 font-mono text-cyan-400">u/${a.auth_user}</td>
              <td class="py-3 px-4 font-medium text-slate-200">${a.label}</td>
              <td class="py-3 px-4 text-xs font-mono text-slate-400">${a.url_prefix}</td>
              <td class="py-3 px-4"><span class="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">可用 (LRU)</span></td>
              <td class="py-3 px-4 font-mono ${a.fail_count > 0 ? 'text-rose-400 font-bold' : 'text-slate-400'}">${a.fail_count}</td>
              <td class="py-3 px-4 text-xs text-slate-400 font-mono">${lastUsed}</td>
              <td class="py-3 px-4 text-right space-x-1.5">
                <button onclick="checkAccount(${a.id})" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300">检测</button>
                <button onclick="rotateAccount(${a.id})" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-amber-400">保活</button>
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
