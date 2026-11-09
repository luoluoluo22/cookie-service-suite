#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 现代化 Web 控制台前端模板
提供：
- 完整系统服务与开机自启动双模状态监控
- Google Gemini 4 账号池额度与健康实时看板
- 在线 API 交互调试工作台 (Live Playground)，支持图片/动图渲染预览
- 完整 API 接口清单目录 (35 个标准化端点)，支持分类检索、一键填入与立即在线测试
"""

DASHBOARD_HTML = """<!DOCTYPE html>
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
    .tab-active { background: rgba(6, 182, 212, 0.15); color: #38bdf8; border-color: rgba(56, 189, 248, 0.4); }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
  
  <!-- 顶部导航栏 -->
  <header class="sticky top-0 z-50 glass border-b border-slate-800/80 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 shadow-2xl">
    <div class="flex items-center space-x-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-500/20 shrink-0">
        <i class="fa-solid fa-cookie-bite text-xl text-slate-950"></i>
      </div>
      <div>
        <div class="flex items-center gap-2">
          <h1 class="font-bold text-lg text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-sky-300 to-cyan-200">
            Cookie Service Suite
          </h1>
          <span class="text-[11px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono">v2.0.0</span>
        </div>
        <p class="text-xs text-slate-400">本地服务总线 & 系统托盘管理控制台</p>
      </div>
    </div>

    <!-- 运行状态与快捷操作区 -->
    <div class="flex flex-wrap items-center gap-2.5">
      <!-- 托盘常驻提示徽章 -->
      <div class="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" title="在 Windows 任务栏通知区域常驻，左键点击图标可随时打开本控制台">
        <span class="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>系统托盘守护中</span>
      </div>

      <!-- 开机自启快捷切换按钮 -->
      <button onclick="toggleAutostart()" id="btn-autostart" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 transition flex items-center gap-1.5" title="点击一键切换 Windows 开机自启状态">
        <i class="fa-solid fa-power-off text-indigo-400"></i>
        <span id="autostart-btn-text">开机自启: 检测中...</span>
      </button>

      <!-- Swagger 交互文档 -->
      <a href="/docs" target="_blank" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/20 transition flex items-center gap-1.5">
        <i class="fa-solid fa-bolt"></i> Swagger 交互文档
      </a>

      <!-- ReDoc 规范 -->
      <a href="/redoc" target="_blank" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1.5">
        <i class="fa-solid fa-book"></i> ReDoc 规范
      </a>

      <!-- 刷新数据 -->
      <button onclick="refreshDashboard()" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition flex items-center gap-1.5">
        <i class="fa-solid fa-arrow-rotate-right" id="refresh-icon"></i> 刷新
      </button>
    </div>
  </header>

  <!-- 主体内容容器 -->
  <main class="max-w-7xl mx-auto px-6 py-8 space-y-8">

    <!-- 1. 服务运行指标卡片 (5列网格) -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <!-- Cookie Hub -->
      <div class="glass-card rounded-2xl p-4 shadow-xl relative overflow-hidden group">
        <div class="flex justify-between items-start">
          <div>
            <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-1">Cookie Hub 扩展桥</div>
            <div class="text-xl font-bold text-slate-100 flex items-center gap-2" id="hub-status-text">
              <span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span> 正在连接
            </div>
          </div>
          <div class="w-9 h-9 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
            <i class="fa-solid fa-puzzle-piece"></i>
          </div>
        </div>
        <div class="mt-3 text-[11px] text-slate-400 flex justify-between">
          <span>端口: 18888</span>
          <span id="hub-clients">客户端: 0</span>
        </div>
      </div>

      <!-- Gemini 多账号池 -->
      <div class="glass-card rounded-2xl p-4 shadow-xl relative overflow-hidden group">
        <div class="flex justify-between items-start">
          <div>
            <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-1">Gemini 统一池</div>
            <div class="text-xl font-bold text-amber-300 flex items-center gap-2" id="gemini-status-text">
              4 账号就绪
            </div>
          </div>
          <div class="w-9 h-9 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
            <i class="fa-solid fa-brain"></i>
          </div>
        </div>
        <div class="mt-3 text-[11px] text-slate-400 flex justify-between">
          <span>LRU 自动均衡</span>
          <span>端口: 18083</span>
        </div>
      </div>

      <!-- ChatGPT 逆向工程 -->
      <div class="glass-card rounded-2xl p-4 shadow-xl relative overflow-hidden group">
        <div class="flex justify-between items-start">
          <div>
            <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-1">ChatGPT 逆向</div>
            <div class="text-xl font-bold text-sky-300 flex items-center gap-2" id="chatgpt-status-text">
              就绪
            </div>
          </div>
          <div class="w-9 h-9 rounded-xl bg-sky-500/10 text-sky-400 flex items-center justify-center">
            <i class="fa-solid fa-robot"></i>
          </div>
        </div>
        <div class="mt-3 text-[11px] text-slate-400 flex justify-between">
          <span>支持 gpt-image-2</span>
          <span>端口: 18084</span>
        </div>
      </div>

      <!-- OpenAI 兼容端点 -->
      <div class="glass-card rounded-2xl p-4 shadow-xl relative overflow-hidden group">
        <div class="flex justify-between items-start">
          <div>
            <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-1">OpenAI 兼容规范</div>
            <div class="text-xl font-bold text-emerald-300">/v1 开放中</div>
          </div>
          <div class="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
            <i class="fa-solid fa-network-wired"></i>
          </div>
        </div>
        <div class="mt-3 text-[11px] text-slate-400 flex justify-between">
          <span>端口: 18800</span>
          <span>NextChat / Cursor</span>
        </div>
      </div>

      <!-- 系统开机自启与运行时间 -->
      <div class="glass-card rounded-2xl p-4 shadow-xl relative overflow-hidden group">
        <div class="flex justify-between items-start">
          <div>
            <div class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-1">自启 & 运行时长</div>
            <div class="text-xl font-bold text-indigo-300" id="uptime-text">0m</div>
          </div>
          <div class="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
            <i class="fa-solid fa-clock"></i>
          </div>
        </div>
        <div class="mt-3 text-[11px] text-slate-400 flex justify-between items-center">
          <span id="autostart-status-badge" class="text-emerald-400 font-semibold">自启: 已开启</span>
          <span class="text-slate-500 font-mono">双模守护</span>
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
    <section id="live-playground" class="glass-card rounded-2xl p-6 shadow-xl grid grid-cols-1 lg:grid-cols-12 gap-6 scroll-mt-24">
      <div class="lg:col-span-6 space-y-4">
        <div>
          <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
            <i class="fa-solid fa-terminal text-cyan-400"></i> 在线 API 调试工作台
          </h2>
          <p class="text-xs text-slate-400">快速发起真实接口请求，支持自选模型、思考推理级别与图片预览</p>
        </div>

        <div>
          <label class="text-xs font-semibold text-slate-300 uppercase block mb-1.5">选择预设 API 模板 (或点击下方列表一键填入)</label>
          <select id="api-selector" onchange="switchApiTemplate()" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-400">
            <optgroup label="── Google Gemini 4账号统一池 ──">
              <option value="gemini_chat">[POST] /api/gemini/chat (Gemini 智能对话 · 推荐)</option>
              <option value="gemini_accounts">[GET] /api/gemini/accounts (查看 4 账号状态与额度)</option>
              <option value="gemini_sync_profiles">[POST] /api/gemini/accounts/sync-profiles (同步 Google 真实昵称邮箱)</option>
              <option value="gemini_check">[POST] /api/gemini/accounts/1/check (检测账号 #1 凭证健康度)</option>
              <option value="gemini_rotate">[POST] /api/gemini/accounts/1/rotate (触发账号 #1 令牌保活续期)</option>
              <option value="gemini_refresh">[POST] /api/gemini/refresh (从 Cookie Hub 刷新多账号凭证)</option>
              <option value="gemini_requests">[GET] /api/gemini/requests?limit=10 (查询最近调度轨迹历史)</option>
            </optgroup>
            <optgroup label="── OpenAI 标准兼容接口 ──">
              <option value="openai_chat">[POST] /v1/chat/completions (OpenAI 兼容对话 · 智能分流)</option>
              <option value="openai_image">[POST] /v1/images/generations (OpenAI 兼容生图 · DALL-E 3)</option>
              <option value="openai_models">[GET] /v1/models (OpenAI 兼容模型列表)</option>
            </optgroup>
            <optgroup label="── ChatGPT 逆向工程与号池 ──">
              <option value="chatgpt_chat">[POST] /api/chatgpt/chat (ChatGPT 逆向智能对话)</option>
              <option value="chatgpt_image">[POST] /api/chatgpt/image (ChatGPT 逆向生图/GIF gpt-image-2)</option>
              <option value="chatgpt_status">[GET] /api/chatgpt/status (ChatGPT 逆向号池运行状态)</option>
              <option value="chatgpt_models">[GET] /api/chatgpt/models (ChatGPT 逆向可用模型列表)</option>
              <option value="chatgpt_accounts">[GET] /api/chatgpt/accounts (ChatGPT 逆向号池账号总览)</option>
              <option value="chatgpt_sync">[POST] /api/chatgpt/accounts/sync-browser (从浏览器一键同步Token)</option>
              <option value="chatgpt_session">[GET] /api/chatgpt/session (ChatGPT 会话提取)</option>
              <option value="chatgpt_start">[POST] /api/chatgpt/start (启动 ChatGPT 独立逆向后台)</option>
              <option value="chatgpt_stop">[POST] /api/chatgpt/stop (停止 ChatGPT 独立逆向后台)</option>
            </optgroup>
            <optgroup label="── Cookie Hub 通信与系统管理 ──">
              <option value="system_overview">[GET] /api/system/overview (系统全局子服务总览)</option>
              <option value="system_autostart_get">[GET] /api/system/autostart (查询 Windows 开机自启状态)</option>
              <option value="system_autostart_toggle">[POST] /api/system/autostart/toggle (一键切换开机自启动)</option>
              <option value="hub_status">[GET] /api/hub/status (Cookie Hub 扩展长连接状态)</option>
              <option value="hub_cookies">[GET] /api/hub/cookies?domain=google.com (动态按域名提取Cookie)</option>
            </optgroup>
            <optgroup label="── 多平台生态服务 (B站/网盘/Suno) ──">
              <option value="bili_user">[GET] /api/bilibili/user (B站 个人资料与大会员资产)</option>
              <option value="bili_video">[GET] /api/bilibili/video?bvid=BV1GJ411x7h7 (B站 视频信息与特权流)</option>
              <option value="baidu_quota">[GET] /api/baidupan/quota (百度网盘 总配额与使用量)</option>
              <option value="baidu_user">[GET] /api/baidupan/user (百度网盘 用户资料与VIP等级)</option>
              <option value="baidu_files">[GET] /api/baidupan/files?dir_path=/ (百度网盘 目录文件遍历)</option>
              <option value="suno_quota">[GET] /api/suno/quota (Suno AI 账户积分与可用曲目)</option>
              <option value="suno_feed">[GET] /api/suno/feed?page=1 (Suno AI 历史创作作品库)</option>
              <option value="suno_gen">[POST] /api/suno/generate (Suno AI 提交音乐创作任务)</option>
              <option value="suno_status">[GET] /api/suno/status?clip_ids=test (Suno AI 任务状态轮询)</option>
              <option value="suno_lyrics">[POST] /api/suno/lyrics (Suno AI 独立歌词创作)</option>
              <option value="suno_refresh">[POST] /api/suno/refresh (Suno AI 刷新鉴权凭证)</option>
            </optgroup>
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
              <option value="gpt-6">gpt-6 (GPT-6 官方默认新架构)</option>
              <option value="gpt-6-thinking">gpt-6-thinking (GPT-6 深度思考链)</option>
              <option value="gpt-5-6">gpt-5-6 (ChatGPT Web 旗舰)</option>
              <option value="gpt-image-2">gpt-image-2 (ChatGPT 绘图/动图专用)</option>
              <option value="chatgpt-web">chatgpt-web (ChatGPT 网页原生)</option>
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
          <input type="text" id="req-endpoint" class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-400" value="/api/gemini/chat">
        </div>

        <div id="req-body-container">
          <label class="text-xs font-semibold text-slate-300 uppercase block mb-1.5 flex items-center justify-between">
            <span>请求 Body (JSON)</span>
            <span class="text-[10px] text-slate-400 font-normal">支持直接修改入参</span>
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
          <span class="text-xs font-semibold text-slate-300 uppercase flex items-center gap-1.5">
            <i class="fa-solid fa-square-poll-vertical text-cyan-400"></i> 响应结果 (Response)
          </span>
          <div class="flex items-center gap-2">
            <span id="resp-status" class="text-xs px-2 py-0.5 rounded font-mono hidden">200 OK</span>
            <span id="resp-time" class="text-xs text-slate-400 font-mono">耗时: 0ms</span>
            <button onclick="copyResponseOutput()" class="text-xs px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition" title="复制返回 JSON 结果">
              <i class="fa-regular fa-copy"></i> 复制
            </button>
          </div>
        </div>

        <!-- 图片/GIF 实时渲染卡片 (如有) -->
        <div id="image-preview-card" class="hidden bg-slate-900/90 border border-cyan-500/40 rounded-xl p-3 flex flex-col items-center gap-2">
          <div class="w-full flex items-center justify-between text-xs text-cyan-300">
            <span class="font-semibold flex items-center gap-1"><i class="fa-solid fa-image"></i> 检测到模型生成图片 / GIF</span>
            <a id="btn-download-img" href="#" download="generated_image.png" class="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 text-[11px] font-mono flex items-center gap-1">
              <i class="fa-solid fa-download"></i> 保存图片
            </a>
          </div>
          <img id="rendered-image" src="" alt="生成的图片预览" class="max-h-64 max-w-full rounded-lg border border-slate-800 shadow-lg object-contain">
        </div>

        <pre id="resp-output" class="flex-1 bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs font-mono text-emerald-400 overflow-auto min-h-[260px] max-h-[380px]">点击左侧「发送请求」或下方接口列表中「立即测试」，结果将实时展示在此处...</pre>
      </div>
    </section>

    <!-- 4. 完整 API 接口清单与在线测试 (Interactive API Directory) -->
    <section class="glass-card rounded-2xl p-6 shadow-xl space-y-5">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
            <i class="fa-solid fa-list-check text-emerald-400"></i> 完整 API 接口清单与在线测试
          </h2>
          <p class="text-xs text-slate-400">Cookie Service Suite 全套标准化 RESTful API，点击任意端点可「填入调试」或「立即测试」</p>
        </div>
        <div class="flex items-center gap-2.5">
          <!-- 实时过滤搜索框 -->
          <div class="relative">
            <i class="fa-solid fa-magnifying-glass absolute left-3 top-2.5 text-xs text-slate-500"></i>
            <input type="text" id="api-search-input" oninput="filterEndpoints()" placeholder="搜索端点、方法或关键字..." class="bg-slate-900 border border-slate-700 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 w-56 sm:w-64">
          </div>
          <span class="text-xs px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 font-mono" id="endpoints-count-badge">共 35 个端点</span>
        </div>
      </div>

      <!-- 分类标签过滤器 -->
      <div class="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3" id="category-tabs">
        <button onclick="setCategoryFilter('all')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border transition tab-active" data-cat="all">全部 (35)</button>
        <button onclick="setCategoryFilter('gemini')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition" data-cat="gemini">Google Gemini (7)</button>
        <button onclick="setCategoryFilter('openai')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition" data-cat="openai">OpenAI 兼容 (3)</button>
        <button onclick="setCategoryFilter('chatgpt')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition" data-cat="chatgpt">ChatGPT 逆向 (9)</button>
        <button onclick="setCategoryFilter('system')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition" data-cat="system">Cookie Hub & 系统 (5)</button>
        <button onclick="setCategoryFilter('ecosystem')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition" data-cat="ecosystem">生态扩展 (B站/网盘/Suno) (11)</button>
      </div>

      <!-- 动态端点卡片网格 -->
      <div id="endpoints-grid" class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        <!-- 由 JavaScript 动态渲染 35 个端点卡片 -->
      </div>
    </section>

  </main>

  <!-- 全局交互脚本 -->
  <script>
    // 35 个 API 端点完整定义
    const ALL_ENDPOINTS = [
      // 1. Google Gemini (7)
      { id: "gemini_chat", category: "gemini", method: "POST", url: "/api/gemini/chat", name: "Gemini 智能对话", desc: "4账号 LRU 自动轮换，支持模型切换与思考链推理级别", body: { prompt: "请用一句话告诉我：量子纠缠是什么？", model: "gemini-3.5-flash-lite", reasoning_level: "off", timeout: 60 } },
      { id: "gemini_accounts", category: "gemini", method: "GET", url: "/api/gemini/accounts", name: "Gemini 4账号状态与额度", desc: "查看 4 个 Google 账号状态、5小时与每周计算配额、健康度", body: null },
      { id: "gemini_sync_profiles", category: "gemini", method: "POST", url: "/api/gemini/accounts/sync-profiles", name: "同步 Google 真实昵称邮箱", desc: "向 Google 上游拉取各 authuser 对应的真实用户显示昵称与 Gmail 邮箱", body: {} },
      { id: "gemini_check", category: "gemini", method: "POST", url: "/api/gemini/accounts/1/check", name: "检测账号凭证健康度", desc: "向 Google 上游验证指定账号 (如 #1) 会话有效性并更新健康状态", body: {} },
      { id: "gemini_rotate", category: "gemini", method: "POST", url: "/api/gemini/accounts/1/rotate", name: "触发账号令牌保活续期", desc: "向 Google 申请换发最新短命会话票据，防止 Cookie 失效", body: {} },
      { id: "gemini_refresh", category: "gemini", method: "POST", url: "/api/gemini/refresh", name: "从 Cookie Hub 刷新凭证", desc: "从浏览器提取最新鉴权 Cookie 并批量写入 SQLite 数据库", body: {} },
      { id: "gemini_requests", category: "gemini", method: "GET", url: "/api/gemini/requests?limit=10", name: "请求调度轨迹历史", desc: "查看最近请求调度轨迹与各账号响应延迟历史", body: null },

      // 2. OpenAI 兼容规范 (3)
      { id: "openai_chat", category: "openai", method: "POST", url: "/v1/chat/completions", name: "OpenAI 兼容聊天接口", desc: "无缝对接 NextChat、Chatbox、Cursor，底层分流 Gemini 与 ChatGPT", body: { model: "gemini-3.5-flash-lite", messages: [{ role: "user", content: "请只回复两个字母：OK。" }], reasoning_level: "off" } },
      { id: "openai_image", category: "openai", method: "POST", url: "/v1/images/generations", name: "OpenAI 兼容生图接口", desc: "标准 POST /v1/images/generations，底层路由至 gpt-image-2 / DALL-E 3", body: { prompt: "一只可爱的赛博朋克发光小猫，超高清，8k壁纸", model: "gpt-image-2", n: 1, response_format: "b64_json" } },
      { id: "openai_models", category: "openai", method: "GET", url: "/v1/models", name: "OpenAI 兼容模型列表", desc: "动态聚合逆向模型、页面模拟与谷歌号池所有可用模型", body: null },

      // 3. ChatGPT 逆向与号池 (9)
      { id: "chatgpt_chat", category: "chatgpt", method: "POST", url: "/api/chatgpt/chat", name: "ChatGPT 智能问答", desc: "支持逆向引擎直连与浏览器同源扩展双通道", body: { prompt: "请用幽默风趣的一句话自我介绍！", model: "auto" } },
      { id: "chatgpt_image", category: "chatgpt", method: "POST", url: "/api/chatgpt/image", name: "ChatGPT 逆向图片/GIF生成", desc: "基于官方逆向生成高质量图片或代码解释器生成的动图", body: { prompt: "一只戴着宇航头盔的橙色猫咪在火星漫步，水彩插画", model: "gpt-image-2", n: 1, response_format: "b64_json" } },
      { id: "chatgpt_status", category: "chatgpt", method: "GET", url: "/api/chatgpt/status", name: "ChatGPT 服务状态", desc: "检测逆向端口 (18084)、健康度与浏览器桥接状态", body: null },
      { id: "chatgpt_models", category: "chatgpt", method: "GET", url: "/api/chatgpt/models", name: "ChatGPT 可用模型列表", desc: "拉取逆向暴露或支持的模型 (auto, gpt-6, gpt-image-2 等)", body: null },
      { id: "chatgpt_accounts", category: "chatgpt", method: "GET", url: "/api/chatgpt/accounts", name: "ChatGPT 号池账号列表", desc: "查看已导入逆向引擎的账号列表、额度与健康状态", body: null },
      { id: "chatgpt_sync", category: "chatgpt", method: "POST", url: "/api/chatgpt/accounts/sync-browser", name: "浏览器 Token 一键同步入池", desc: "从浏览器提取 chatgpt.com 当前会话 Access Token 并载入逆向号池", body: {} },
      { id: "chatgpt_session", category: "chatgpt", method: "GET", url: "/api/chatgpt/session", name: "提取当前登录会话", desc: "提取当前 ChatGPT 标签页登录用户与 Access Token", body: null },
      { id: "chatgpt_start", category: "chatgpt", method: "POST", url: "/api/chatgpt/start", name: "启动独立逆向后台", desc: "手动按需启动基于 chatgpt2api 的独立无头逆向进程 (18084)", body: {} },
      { id: "chatgpt_stop", category: "chatgpt", method: "POST", url: "/api/chatgpt/stop", name: "停止独立逆向后台", desc: "停止 ChatGPT 独立无头逆向进程", body: {} },

      // 4. Cookie Hub 通信与系统管理 (5)
      { id: "system_overview", category: "system", method: "GET", url: "/api/system/overview", name: "系统全局运行总览", desc: "查看 Cookie Hub、Gemini 池、ChatGPT 与开机自启动全景状态", body: null },
      { id: "system_autostart_get", category: "system", method: "GET", url: "/api/system/autostart", name: "查询 Windows 开机自启状态", desc: "检查注册表 Run 与开始菜单 Startup 双重持久化配置", body: null },
      { id: "system_autostart_toggle", category: "system", method: "POST", url: "/api/system/autostart/toggle", name: "一键切换开机自启动", desc: "在开启 (双重保障) 与关闭之间一键无缝切换", body: {} },
      { id: "hub_status", category: "system", method: "GET", url: "/api/hub/status", name: "Cookie Hub 扩展桥状态", desc: "检测 Chrome/Edge 扩展与本地 Node 服务长连接", body: null },
      { id: "hub_cookies", category: "system", method: "GET", url: "/api/hub/cookies?domain=google.com", name: "按域名动态提取 Cookie", desc: "从浏览器实时提取指定域名 (如 google.com) 的 Cookie 字典与 Header", body: null },

      // 5. 多平台生态 (11)
      { id: "bili_user", category: "ecosystem", method: "GET", url: "/api/bilibili/user", name: "B站 登录用户信息与资产", desc: "查看当前 B 站登录用户资料、硬币、B币与大会员有效期", body: null },
      { id: "bili_video", category: "ecosystem", method: "GET", url: "/api/bilibili/video?bvid=BV1GJ411x7h7", name: "B站 视频信息与特权流", desc: "查询视频元数据与大会员专属 4K/1080P60 播放直链", body: null },
      { id: "baidu_quota", category: "ecosystem", method: "GET", url: "/api/baidupan/quota", name: "百度网盘 存储容量与配额", desc: "获取已用空间、总空间与 VIP 配额详情", body: null },
      { id: "baidu_user", category: "ecosystem", method: "GET", url: "/api/baidupan/user", name: "百度网盘 用户账号资料", desc: "获取百度网盘用户名、头像与 VIP 等级", body: null },
      { id: "baidu_files", category: "ecosystem", method: "GET", url: "/api/baidupan/files?dir_path=/", name: "百度网盘 目录文件遍历", desc: "遍历网盘根目录 / 或指定子目录下的文件清单", body: null },
      { id: "suno_quota", category: "ecosystem", method: "GET", url: "/api/suno/quota", name: "Suno AI 积分与可用曲目", desc: "查询 Suno 账号剩余积分及本月可用生成曲目数", body: null },
      { id: "suno_feed", category: "ecosystem", method: "GET", url: "/api/suno/feed?page=1", name: "Suno AI 历史创作作品库", desc: "拉取已生成的音乐曲目、封面、歌词与音频直链", body: null },
      { id: "suno_gen", category: "ecosystem", method: "POST", url: "/api/suno/generate", name: "Suno AI 提交音乐生成任务", desc: "根据描述词生成两首完整人声/器乐歌曲 (支持自定义模式)", body: { prompt: "一段欢快阳光的夏日流行海滩音乐，带有原声吉他和轻快的鼓点", is_custom: false, model: "chirp-v3-5", wait: false } },
      { id: "suno_status", category: "ecosystem", method: "GET", url: "/api/suno/status?clip_ids=test", name: "Suno AI 任务状态轮询", desc: "查询音乐任务渲染进度与 MP3/视频播放直链", body: null },
      { id: "suno_lyrics", category: "ecosystem", method: "POST", url: "/api/suno/lyrics", name: "Suno AI 独立歌词创作", desc: "输入主题生成结构完整的双节押韵歌词", body: { prompt: "写一首关于秋天落叶与思念的流行歌词" } },
      { id: "suno_refresh", category: "ecosystem", method: "POST", url: "/api/suno/refresh", name: "Suno AI 刷新鉴权凭证", desc: "强制刷新 Suno 会话凭证与 Clerk JWT 令牌", body: {} },
    ];

    let currentCategory = "all";

    // 渲染 API 端点卡片清单
    function renderEndpointsList() {
      const grid = document.getElementById("endpoints-grid");
      const searchKeyword = (document.getElementById("api-search-input").value || "").trim().toLowerCase();
      
      const filtered = ALL_ENDPOINTS.filter(ep => {
        const matchesCategory = currentCategory === "all" || ep.category === currentCategory;
        if (!matchesCategory) return false;
        if (!searchKeyword) return true;
        return ep.url.toLowerCase().includes(searchKeyword) ||
               ep.name.toLowerCase().includes(searchKeyword) ||
               ep.desc.toLowerCase().includes(searchKeyword) ||
               ep.method.toLowerCase().includes(searchKeyword);
      });

      document.getElementById("endpoints-count-badge").innerText = `展示 ${filtered.length} / 共 35 个端点`;

      if (filtered.length === 0) {
        grid.innerHTML = `<div class="col-span-full py-8 text-center text-slate-500 text-xs">未找到匹配的 API 端点</div>`;
        return;
      }

      grid.innerHTML = filtered.map(ep => {
        const isPost = ep.method === "POST";
        const methodBadgeClass = isPost
          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
          : "bg-sky-500/20 text-sky-300 border-sky-500/30";

        return `
          <div class="bg-slate-900/70 p-3.5 rounded-xl border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between gap-2.5">
            <div>
              <div class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-[11px] font-bold border font-mono ${methodBadgeClass}">${ep.method}</span>
                  <span class="font-bold text-xs text-slate-200">${ep.name}</span>
                </div>
                <button onclick="copyToClipboard('${ep.url}')" class="text-slate-500 hover:text-slate-300 text-xs" title="复制路径">
                  <i class="fa-regular fa-copy"></i>
                </button>
              </div>
              <div class="mt-1 font-mono text-xs text-cyan-300 break-all select-all">${ep.url}</div>
              <div class="mt-1 text-[11px] text-slate-400 line-clamp-2">${ep.desc}</div>
            </div>
            <div class="flex items-center justify-end gap-2 pt-1 border-t border-slate-800/60">
              <button onclick="loadEndpoint('${ep.id}', false)" class="px-2.5 py-1 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition flex items-center gap-1">
                <i class="fa-solid fa-code text-cyan-400"></i> 填入调试
              </button>
              <button onclick="loadEndpoint('${ep.id}', true)" class="px-2.5 py-1 rounded-lg text-xs bg-gradient-to-r from-cyan-500/20 to-blue-500/20 hover:from-cyan-500/30 hover:to-blue-500/30 text-cyan-300 border border-cyan-500/30 transition flex items-center gap-1 font-semibold">
                <i class="fa-solid fa-play text-cyan-400"></i> 立即测试
              </button>
            </div>
          </div>
        `;
      }).join("");
    }

    function setCategoryFilter(cat) {
      currentCategory = cat;
      document.querySelectorAll(".category-tab").forEach(tab => {
        if (tab.getAttribute("data-cat") === cat) {
          tab.className = "category-tab px-3 py-1.5 rounded-lg text-xs font-medium border transition tab-active";
        } else {
          tab.className = "category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition";
        }
      });
      renderEndpointsList();
    }

    function filterEndpoints() {
      renderEndpointsList();
    }

    function copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        showToast("已复制到剪贴板: " + text);
      }).catch(() => {});
    }

    function showToast(msg) {
      let toast = document.getElementById("live-toast");
      if (!toast) {
        toast = document.createElement("div");
        toast.id = "live-toast";
        toast.className = "fixed bottom-5 right-5 z-50 bg-slate-900 border border-cyan-500/40 text-cyan-300 text-xs px-4 py-2.5 rounded-xl shadow-2xl shadow-cyan-500/20 flex items-center gap-2 transition duration-300";
        document.body.appendChild(toast);
      }
      toast.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${msg}`;
      toast.style.display = "flex";
      setTimeout(() => { toast.style.display = "none"; }, 2500);
    }

    // 载入指定端点到调试工作台，autoRun 为 true 时立即发送请求
    function loadEndpoint(endpointId, autoRun = false) {
      const ep = ALL_ENDPOINTS.find(e => e.id === endpointId);
      if (!ep) return;

      // 同步选择器
      const selector = document.getElementById("api-selector");
      if (selector) selector.value = ep.id;

      document.getElementById("req-method-badge").innerText = ep.method;
      if (ep.method === "POST") {
        document.getElementById("req-method-badge").className = "px-2.5 py-1 rounded-lg text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30";
      } else {
        document.getElementById("req-method-badge").className = "px-2.5 py-1 rounded-lg text-xs font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30";
      }

      document.getElementById("req-endpoint").value = ep.url;
      const bodyContainer = document.getElementById("req-body-container");
      const controlsGrid = document.getElementById("model-controls-grid");

      if (ep.method === "GET") {
        bodyContainer.style.display = "none";
        if (controlsGrid) controlsGrid.style.display = "none";
      } else {
        bodyContainer.style.display = "block";
        const bodyStr = ep.body ? JSON.stringify(ep.body, null, 2) : "{}";
        document.getElementById("req-body").value = bodyStr;

        if (ep.id === "gemini_chat" || ep.id === "openai_chat" || ep.id === "chatgpt_chat") {
          if (controlsGrid) controlsGrid.style.display = "grid";
        } else {
          if (controlsGrid) controlsGrid.style.display = "none";
        }
      }

      // 平滑滚动至调试台
      document.getElementById("live-playground").scrollIntoView({ behavior: "smooth" });

      if (autoRun) {
        setTimeout(() => { executeApiCall(); }, 200);
      }
    }

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
      loadEndpoint(key, false);
    }

    async function executeApiCall() {
      const btn = document.getElementById("btn-send");
      const method = document.getElementById("req-method-badge").innerText;
      const endpoint = document.getElementById("req-endpoint").value;
      const out = document.getElementById("resp-output");
      const statusSpan = document.getElementById("resp-status");
      const timeSpan = document.getElementById("resp-time");
      const imgCard = document.getElementById("image-preview-card");
      const renderedImg = document.getElementById("rendered-image");
      const btnDownload = document.getElementById("btn-download-img");

      imgCard.classList.add("hidden");
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

        // 智能检测图片渲染 (b64_json 或 url 或 data:image)
        try {
          let foundImg = null;
          if (data && data.data && Array.isArray(data.data) && data.data[0]) {
            const first = data.data[0];
            if (first.b64_json) {
              const mime = first.b64_json.startsWith("R0lGOD") ? "image/gif" : "image/png";
              foundImg = `data:${mime};base64,${first.b64_json}`;
            } else if (first.url) {
              foundImg = first.url;
            }
          } else if (data && data.b64_json) {
            const mime = data.b64_json.startsWith("R0lGOD") ? "image/gif" : "image/png";
            foundImg = `data:${mime};base64,${data.b64_json}`;
          }

          if (foundImg) {
            renderedImg.src = foundImg;
            btnDownload.href = foundImg;
            btnDownload.download = foundImg.includes("image/gif") ? "generated_animation.gif" : "generated_image.png";
            imgCard.classList.remove("hidden");
          }
        } catch (imgErr) {}

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

    function copyResponseOutput() {
      const text = document.getElementById("resp-output").innerText;
      copyToClipboard(text);
    }

    // 开机自启动切换
    async function toggleAutostart() {
      const btn = document.getElementById("btn-autostart");
      btn.disabled = true;
      try {
        const res = await fetch("/api/system/autostart/toggle", { method: "POST" });
        const data = await res.json();
        showToast(data.message || (data.enabled ? "已开启开机自启" : "已关闭开机自启"));
        await refreshDashboard();
      } catch (err) {
        alert("操作异常: " + err.message);
      } finally {
        btn.disabled = false;
      }
    }

    async function refreshDashboard() {
      const icon = document.getElementById("refresh-icon");
      icon.classList.add("fa-spin");

      try {
        // 1. 系统概览与自启状态
        const sysRes = await fetch("/api/system/overview");
        if (sysRes.ok) {
          const sys = await sysRes.json();
          document.getElementById("uptime-text").innerText = `${Math.round(sys.uptime_seconds / 60)}m`;
          
          const hubOk = sys.services && sys.services.cookie_hub && sys.services.cookie_hub.extension_connected;
          document.getElementById("hub-status-text").innerHTML = hubOk
            ? `<span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400"></span> 扩展已连接`
            : `<span class="inline-block w-2.5 h-2.5 rounded-full bg-rose-400"></span> 扩展未连接`;
          document.getElementById("hub-clients").innerText = `客户端: ${sys.services?.cookie_hub?.clients || 0}`;
          document.getElementById("gemini-status-text").innerText = `${sys.services?.gemini_pool?.active_accounts || 4} 账号就绪`;

          const gptRunning = sys.services?.chatgpt?.reverse_running;
          document.getElementById("chatgpt-status-text").innerText = gptRunning ? "🟢 逆向运行中" : "⚪ 就绪 (按需)";

          // 自启徽章更新
          const autoOk = sys.autostart && sys.autostart.enabled;
          const autoBtnText = document.getElementById("autostart-btn-text");
          const autoBadge = document.getElementById("autostart-status-badge");
          if (autoOk) {
            autoBtnText.innerText = "开机自启: [已开启]";
            autoBadge.innerText = "自启: 🟢 已开启";
            autoBadge.className = "text-emerald-400 font-semibold";
          } else {
            autoBtnText.innerText = "开机自启: [已关闭]";
            autoBadge.innerText = "自启: ⚪ 已关闭";
            autoBadge.className = "text-slate-400 font-semibold";
          }
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
            
            const displayName = a.name ? a.name : (a.label || `账号槽位 u/${a.auth_user}`);
            const displayEmail = a.email ? a.email : '未解析邮箱';
            const initialChar = (displayName || displayEmail || 'G').trim().charAt(0).toUpperCase();

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
        showToast(data.message || "账号真实用户名与邮箱已同步！");
        await refreshDashboard();
      } catch (err) {
        alert("同步异常: " + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-id-card"></i> 同步真实名称与邮箱`;
      }
    }

    async function checkAccount(id) {
      showToast("正在验证账号 #" + id + " 凭证...");
      const res = await fetch(`/api/gemini/accounts/${id}/check`, { method: "POST" });
      const data = await res.json();
      showToast("检测完成: " + (data.status || "OK"));
      refreshDashboard();
    }

    async function rotateAccount(id) {
      showToast("正在为账号 #" + id + " 申请保活...");
      const res = await fetch(`/api/gemini/accounts/${id}/rotate`, { method: "POST" });
      const data = await res.json();
      showToast("保活完成: " + (data.status || "OK"));
      refreshDashboard();
    }

    async function refreshAllCookies() {
      if (!confirm("确认从当前浏览器 Cookie Hub 重新提取 Google 全量会话凭证？")) return;
      const res = await fetch("/api/gemini/refresh", { method: "POST" });
      const data = await res.json();
      showToast(data.message || "凭证刷新成功！");
      refreshDashboard();
    }

    // 初始化运行
    renderEndpointsList();
    switchApiTemplate();
    refreshDashboard();
    setInterval(refreshDashboard, 12000); // 12秒自动更新一次
  </script>
</body>
</html>"""
