#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 现代化 Web 控制台前端模板
特性：
- 左侧沉浸式导航栏（控制导航），导航项依序为：调试台、运行概览、账号看板、接口清单、文档规范
- 包含【打开目录】按钮，点击后调用后端在 Windows 资源管理器中打开项目根目录
- 调试台置于主区域第一位，支持在线调试、多模型选择、思考链推理与图片/动图实时渲染
- 全套 36 个标准化 API 端点目录与一键在线测试
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-CN" class="scroll-smooth">
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
    .nav-item-active { background: rgba(6, 182, 212, 0.15); color: #38bdf8; border-color: rgba(56, 189, 248, 0.35); font-weight: 600; }
    .plat-tab {
      background: rgba(15, 23, 42, 0.75);
      border: 1px solid rgba(51, 65, 85, 0.55);
      transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .plat-tab:hover {
      background: rgba(30, 41, 59, 0.9);
      border-color: rgba(56, 189, 248, 0.5);
      transform: translateY(-2px);
      box-shadow: 0 6px 16px -2px rgba(6, 182, 212, 0.18);
    }
    .plat-tab-active {
      background: linear-gradient(135deg, rgba(6, 182, 212, 0.2) 0%, rgba(59, 130, 246, 0.14) 100%) !important;
      border-color: rgba(56, 189, 248, 0.85) !important;
      color: #38bdf8 !important;
      box-shadow: 0 0 20px rgba(6, 182, 212, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
      transform: translateY(-2px);
    }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col md:flex-row">

  <!-- ======================================================== -->
  <!-- 1. 左侧导航栏 (Left Sidebar Navigation)                  -->
  <!-- ======================================================== -->
  <aside class="w-full md:w-64 md:h-screen md:sticky md:top-0 bg-slate-900/90 backdrop-blur-xl border-r border-slate-800 flex flex-col justify-between shrink-0 z-40 shadow-2xl">
    
    <!-- 侧边栏顶部: 品牌与导航区 -->
    <div class="p-4 space-y-5">
      <!-- 品牌标识 -->
      <div class="flex items-center space-x-3 pb-3 border-b border-slate-800/80">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-500/20 shrink-0">
          <i class="fa-solid fa-cookie-bite text-xl text-slate-950"></i>
        </div>
        <div class="min-w-0">
          <div class="flex items-center gap-1.5">
            <h1 class="font-bold text-sm tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-sky-300 to-cyan-200 truncate">
              Cookie Suite
            </h1>
            <span class="text-[10px] px-1.5 py-0.2 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono">v2.0</span>
          </div>
          <p class="text-[11px] text-slate-400 truncate">本地服务调度中心</p>
        </div>
      </div>

      <!-- 导航名 (四字)：控制导航 -->
      <div>
        <div class="text-[11px] font-bold uppercase tracking-wider text-cyan-400/90 mb-2.5 px-2 flex items-center justify-between">
          <span class="flex items-center gap-1.5">
            <i class="fa-solid fa-compass text-cyan-400 text-xs"></i> 控制导航
          </span>
          <span class="text-[10px] font-mono text-slate-500">Menu</span>
        </div>

        <!-- 导航菜单项依次排列 (调试台放第一个) -->
        <nav class="space-y-1 text-xs" id="sidebar-nav">
          <!-- 1. 调试台 (第一位) -->
          <a href="#section-playground" onclick="setActiveNav(this)" class="nav-item flex items-center justify-between px-3 py-2.5 rounded-xl text-slate-300 hover:bg-slate-800/80 hover:text-cyan-300 border border-transparent transition nav-item-active">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-terminal text-cyan-400 w-4 text-center"></i>
              <span class="font-medium">调试台</span>
            </span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono">首位</span>
          </a>

          <!-- 2. 运行概览 (四字) -->
          <a href="#section-overview" onclick="setActiveNav(this)" class="nav-item flex items-center justify-between px-3 py-2.5 rounded-xl text-slate-300 hover:bg-slate-800/80 hover:text-sky-300 border border-transparent transition">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-chart-pie text-sky-400 w-4 text-center"></i>
              <span class="font-medium">运行概览</span>
            </span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">5指标</span>
          </a>

          <!-- 3. 账号看板 (四字) -->
          <a href="#section-accounts" onclick="setActiveNav(this)" class="nav-item flex items-center justify-between px-3 py-2.5 rounded-xl text-slate-300 hover:bg-slate-800/80 hover:text-amber-300 border border-transparent transition">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-users-gear text-amber-400 w-4 text-center"></i>
              <span class="font-medium">账号看板</span>
            </span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 font-mono">4账号</span>
          </a>

          <!-- 4. 接口清单 (四字) -->
          <a href="#section-endpoints" onclick="setActiveNav(this)" class="nav-item flex items-center justify-between px-3 py-2.5 rounded-xl text-slate-300 hover:bg-slate-800/80 hover:text-emerald-300 border border-transparent transition">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-list-check text-emerald-400 w-4 text-center"></i>
              <span class="font-medium">接口清单</span>
            </span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 font-mono">36端点</span>
          </a>

          <!-- 5. 文档规范 (四字) -->
          <a href="#section-docs" onclick="setActiveNav(this)" class="nav-item flex items-center justify-between px-3 py-2.5 rounded-xl text-slate-300 hover:bg-slate-800/80 hover:text-indigo-300 border border-transparent transition">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-book text-indigo-400 w-4 text-center"></i>
              <span class="font-medium">文档规范</span>
            </span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 font-mono">OpenAPI</span>
          </a>
        </nav>
      </div>

      <!-- 快捷操作区 -->
      <div class="space-y-2 pt-2 border-t border-slate-800/70">
        <div class="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-2 mb-1.5">快捷工具</div>

        <!-- 【打开目录】按钮 (点击后在 Windows 资源管理器中打开项目目录) -->
        <button onclick="openProjectFolder()" class="w-full px-3 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-medium flex items-center justify-between transition group shadow-sm" title="在 Windows 资源管理器中打开当前项目根目录">
          <span class="flex items-center gap-2">
            <i class="fa-solid fa-folder-open text-amber-400"></i>
            <span>打开项目目录</span>
          </span>
          <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-amber-400/70 group-hover:translate-x-0.5 transition"></i>
        </button>

        <!-- 开机自启切换按钮 -->
        <button onclick="toggleAutostart()" id="sidebar-btn-autostart" class="w-full px-3 py-2 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-medium flex items-center justify-between transition" title="一键切换 Windows 开机自启状态">
          <span class="flex items-center gap-2">
            <i class="fa-solid fa-power-off text-indigo-400"></i>
            <span id="sidebar-autostart-text">自启: 检测中...</span>
          </span>
          <span class="w-2 h-2 rounded-full bg-slate-500" id="sidebar-autostart-dot"></span>
        </button>

        <!-- 刷新数据按钮 -->
        <button onclick="refreshDashboard()" class="w-full px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium flex items-center justify-between transition">
          <span class="flex items-center gap-2">
            <i class="fa-solid fa-arrows-rotate text-cyan-400" id="sidebar-refresh-icon"></i>
            <span>刷新服务数据</span>
          </span>
          <span class="text-[10px] text-slate-500 font-mono">12s轮询</span>
        </button>
      </div>
    </div>

    <!-- 侧边栏底部: 托盘与系统状态 -->
    <div class="p-4 border-t border-slate-800/80 bg-slate-950/40 text-[11px] space-y-1.5">
      <div class="flex items-center justify-between">
        <span class="text-slate-400 flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> 系统托盘守护
        </span>
        <span class="text-emerald-400 font-mono font-bold">在线</span>
      </div>
      <div class="text-[10px] text-slate-500 font-mono truncate">端口: 127.0.0.1:18800</div>
    </div>
  </aside>

  <!-- ======================================================== -->
  <!-- 2. 右侧主内容区域 (Main Content Area)                    -->
  <!-- ======================================================== -->
  <div class="flex-1 min-w-0 flex flex-col min-h-screen">
    
    <!-- 顶部轻量浮动条 (包含 Swagger / ReDoc 与状态提示) -->
    <header class="glass border-b border-slate-800/80 px-6 py-3 flex items-center justify-between gap-4 sticky top-0 z-30 shadow-md">
      <div class="flex items-center gap-3">
        <div class="text-xs text-slate-400 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span>服务状态: <strong class="text-emerald-300 font-normal">多子系统全部就绪</strong></span>
        </div>
      </div>
      <div class="flex items-center space-x-2.5">
        <a href="/docs" target="_blank" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/20 transition flex items-center gap-1.5">
          <i class="fa-solid fa-bolt"></i> Swagger
        </a>
        <a href="/redoc" target="_blank" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition flex items-center gap-1.5">
          <i class="fa-solid fa-book"></i> ReDoc
        </a>
      </div>
    </header>

    <!-- 主体容器 (调试台排在第一位) -->
    <main class="max-w-7xl w-full mx-auto px-6 py-6 space-y-8">

      <!-- ==================================================== -->
      <!-- [第一位] 调试台 (在线 API 调试与交互工作台)         -->
      <!-- ==================================================== -->
      <section id="section-playground" class="glass-card rounded-2xl p-6 shadow-2xl border border-cyan-500/20 space-y-5 scroll-mt-20">
        
        <!-- 1. 调试台顶栏 Header: 标题 + 打开目录 -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
          <div>
            <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
              <i class="fa-solid fa-terminal text-cyan-400"></i> 调试台
              <span class="text-xs font-normal px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-mono">主调试工作台</span>
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">在线发起真实 API 请求，支持多模型、思考链与图片/动图渲染预览</p>
          </div>
          <button onclick="openProjectFolder()" class="self-start sm:self-auto text-xs px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 items-center gap-1.5 transition flex shadow-sm">
            <i class="fa-solid fa-folder-open text-amber-400"></i> 打开目录
          </button>
        </div>

        <!-- 2. 平台专属分类导航栏 (上图标 + 下名称 + 接口数徽章) -->
        <div class="space-y-2.5">
          <div class="flex items-center justify-between">
            <div class="text-[11px] font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
              <i class="fa-solid fa-layer-group text-cyan-400"></i> 平台分类导航
              <span class="text-[10px] text-slate-500 font-normal font-sans">(点击分类单独过滤下方 API 模板)</span>
            </div>
            <div id="current-playground-cat-indicator" class="text-[11px] font-mono text-slate-400">
              当前: <span class="text-cyan-300 font-semibold">Google Gemini</span> (7个模板)
            </div>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5" id="playground-category-nav">
            <!-- 由 JS 渲染 7 个分类导航按钮 (上图标 + 下名称 + 接口数徽章) -->
          </div>
        </div>

        <!-- 3. 双栏工作区 (左侧入参配置，右侧响应结果) -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-1">
          <div class="lg:col-span-6 space-y-4">
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <label class="text-xs font-semibold text-slate-300 uppercase block">选择预设 API 模板</label>
                <span id="api-template-badge" class="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-mono">Gemini · 7 个模板</span>
              </div>
              <select id="api-selector" onchange="switchApiTemplate()" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-400 shadow-sm transition">
                <option value="gemini_chat" selected>[POST] /api/gemini/chat (Gemini 智能对话)</option>
                <option value="gemini_accounts">[GET] /api/gemini/accounts (Gemini 4账号状态与额度)</option>
                <option value="gemini_sync_profiles">[POST] /api/gemini/accounts/sync-profiles (同步 Google 真实昵称邮箱)</option>
                <option value="gemini_check">[POST] /api/gemini/accounts/1/check (检测账号凭证健康度)</option>
                <option value="gemini_rotate">[POST] /api/gemini/accounts/1/rotate (触发账号令牌保活续期)</option>
                <option value="gemini_refresh">[POST] /api/gemini/refresh (从 Cookie Hub 刷新凭证)</option>
                <option value="gemini_requests">[GET] /api/gemini/requests?limit=10 (请求调度轨迹历史)</option>
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

            <!-- 流式实时输出控制开关 -->
            <div id="stream-toggle-container" class="flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-slate-900/90 border border-slate-800 text-xs shadow-inner">
              <span class="flex items-center gap-2 text-slate-300 font-medium">
                <i class="fa-solid fa-bolt text-amber-400"></i> 流式响应 (Streaming)
                <span class="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-mono">默认开启 · 秒出首字</span>
              </span>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" id="stream-toggle" onchange="onStreamToggleChange()" class="sr-only peer" checked>
                <div class="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500"></div>
                <span id="stream-toggle-text" class="ml-2 text-xs font-mono text-cyan-300">实时打字 (SSE)</span>
              </label>
            </div>

            <div class="flex gap-2 items-center">
              <span id="req-method-badge" class="px-2.5 py-1 rounded-lg text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono">POST</span>
              <input type="text" id="req-endpoint" class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-400" value="/api/gemini/chat">
            </div>

            <!-- AI 预设 / 提示词快捷预设 -->
            <div id="ai-preset-container" class="space-y-1.5">
              <div class="flex items-center justify-between">
                <label class="text-xs font-semibold text-slate-300 uppercase flex items-center gap-1.5">
                  <i class="fa-solid fa-wand-magic-sparkles text-amber-400"></i>
                  <span>选择 AI 预设 / 快捷提示词</span>
                </label>
                <span class="text-[10px] text-amber-300/80 font-mono">一键载入常用场景</span>
              </div>
              <select id="ai-preset-selector" onchange="applyAiPreset()" class="w-full bg-slate-900 border border-amber-500/40 rounded-xl px-3 py-2 text-xs text-amber-300 focus:outline-none focus:border-amber-400 shadow-inner transition">
                <option value="quantum" selected>⚡ 物理科普: 请用一句话告诉我：量子纠缠是什么？</option>
                <option value="python_async">💻 编程开发: 用 Python 编写一个高性能并发异步下载器，带连接池、超时自愈重试与流式进度展示</option>
                <option value="translation">🌐 专业翻译: 请将以下技术段落进行中英专业学术级双向互译，保持术语严谨准确并给出对照解析</option>
                <option value="raft_paxos">🧠 深度思考: 详细对比分布式架构下 Raft 与 Paxos 一致性算法的优缺点、选型考量与极端脑裂恢复</option>
                <option value="marketing">✍️ 爆款文案: 为一款主打轻量敏捷与多账号智能分流的开发者工具撰写一段小红书/推特爆款推介文案</option>
                <option value="cyberpunk_cat">🎨 赛博艺术: 一只可爱的赛博朋克霓虹发光机械猫咪在雨夜漫步，8K超高清，虚幻5电影级光影质感</option>
                <option value="suno_music">🎵 音乐创作: 一段欢快阳光的夏日流行海滩音乐，带有原声吉他和轻快的鼓点</option>
              </select>
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

            <!-- 可视化音频试听卡片 (Suno 音乐解密直出) -->
            <div id="audio-preview-card" class="hidden bg-slate-900/90 border border-indigo-500/40 rounded-xl p-3 flex flex-col gap-2">
              <div class="w-full flex items-center justify-between text-xs text-indigo-300">
                <span class="font-semibold flex items-center gap-1.5"><i class="fa-solid fa-music animate-pulse"></i> <span id="audio-preview-title">Suno 在线试听播放器</span></span>
                <a id="btn-download-audio" href="#" download="suno_music.m4a" class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 text-[11px] font-mono flex items-center gap-1">
                  <i class="fa-solid fa-download"></i> 保存音频 (M4A)
                </a>
              </div>
              <audio id="rendered-audio" controls class="w-full h-9 rounded outline-none"></audio>
            </div>

            <pre id="resp-output" class="flex-1 bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs font-mono text-emerald-400 overflow-auto min-h-[260px] max-h-[380px]">点击左侧「发送请求」或下方接口列表中「立即测试」，结果将实时展示在此处...</pre>
          </div>
        </div>
      </section>

      <!-- ==================================================== -->
      <!-- [第二位] 运行概览 (5指标服务指标卡片)                 -->
      <!-- ==================================================== -->
      <section id="section-overview" class="space-y-4 scroll-mt-20">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-bold text-slate-100 flex items-center gap-2">
            <i class="fa-solid fa-chart-pie text-sky-400"></i> 运行概览
          </h2>
          <span class="text-xs text-slate-400">实时子服务运行总线指标</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <!-- 1. Cookie Hub -->
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

          <!-- 2. Gemini 多账号池 -->
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

          <!-- 3. ChatGPT 逆向工程 -->
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

          <!-- 4. OpenAI 兼容端点 -->
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

          <!-- 5. 系统开机自启与运行时间 -->
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
              <span id="autostart-status-badge" class="text-emerald-400 font-semibold">自启: 🟢 已开启</span>
              <span class="text-slate-500 font-mono">双模守护</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ==================================================== -->
      <!-- [第三位] 账号看板 (Google Gemini 4 账号槽位看板)    -->
      <!-- ==================================================== -->
      <section id="section-accounts" class="glass-card rounded-2xl p-6 shadow-xl space-y-4 scroll-mt-20">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 class="text-base font-bold text-slate-100 flex items-center gap-2">
              <i class="fa-solid fa-users-gear text-amber-400"></i> 账号看板
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

      <!-- ==================================================== -->
      <!-- [第四位] 接口清单 (完整 API 接口清单与在线测试)      -->
      <!-- ==================================================== -->
      <section id="section-endpoints" class="glass-card rounded-2xl p-6 shadow-xl space-y-5 scroll-mt-20">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 class="text-base font-bold text-slate-100 flex items-center gap-2">
              <i class="fa-solid fa-list-check text-emerald-400"></i> 接口清单
            </h2>
            <p class="text-xs text-slate-400">Cookie Service Suite 全套标准化 RESTful API，点击任意端点可「填入调试」或「立即测试」</p>
          </div>
          <div class="flex items-center gap-2.5">
            <!-- 实时过滤搜索框 -->
            <div class="relative">
              <i class="fa-solid fa-magnifying-glass absolute left-3 top-2.5 text-xs text-slate-500"></i>
              <input type="text" id="api-search-input" oninput="filterEndpoints()" placeholder="搜索端点、方法或关键字..." class="bg-slate-900 border border-slate-700 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 w-56 sm:w-64">
            </div>
            <span class="text-xs px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 font-mono" id="endpoints-count-badge">共 36 个端点</span>
          </div>
        </div>

        <!-- 分类标签过滤器 -->
        <div class="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3" id="category-tabs">
          <button onclick="setCategoryFilter('all')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border transition tab-active" data-cat="all">全部 (37)</button>
          <button onclick="setCategoryFilter('gemini')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition" data-cat="gemini">Google Gemini (7)</button>
          <button onclick="setCategoryFilter('openai')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition" data-cat="openai">OpenAI 兼容 (3)</button>
          <button onclick="setCategoryFilter('chatgpt')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition" data-cat="chatgpt">ChatGPT 逆向 (9)</button>
          <button onclick="setCategoryFilter('system')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition" data-cat="system">Cookie Hub & 系统 (6)</button>
          <button onclick="setCategoryFilter('ecosystem')" class="category-tab px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200 transition" data-cat="ecosystem">生态扩展 (B站/网盘/Suno) (12)</button>
        </div>

        <!-- 动态端点卡片网格 -->
        <div id="endpoints-grid" class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <!-- 由 JavaScript 动态渲染 36 个端点卡片 -->
        </div>
      </section>

      <!-- ==================================================== -->
      <!-- [第五位] 文档规范 (Swagger 与 ReDoc 快捷入口)         -->
      <!-- ==================================================== -->
      <section id="section-docs" class="glass-card rounded-2xl p-6 shadow-xl space-y-4 scroll-mt-20">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-base font-bold text-slate-100 flex items-center gap-2">
              <i class="fa-solid fa-book text-indigo-400"></i> 文档规范
            </h2>
            <p class="text-xs text-slate-400">OpenAPI 标准文档与模型客户端接口对接指引</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <!-- Swagger UI -->
          <a href="/docs" target="_blank" class="p-4 rounded-xl bg-slate-900/80 border border-cyan-500/30 hover:border-cyan-400 transition flex flex-col justify-between group">
            <div>
              <div class="text-sm font-bold text-cyan-300 flex items-center gap-2">
                <i class="fa-solid fa-bolt"></i> Swagger UI 在线交互文档
              </div>
              <p class="text-slate-400 mt-1.5 text-[11px]">基于 FastAPI 官方自动生成的交互式接口调试台，支持即开即测。</p>
            </div>
            <div class="mt-4 flex items-center justify-between text-cyan-400 font-mono text-[11px]">
              <span>/docs</span>
              <i class="fa-solid fa-arrow-up-right-from-square group-hover:translate-x-0.5 transition"></i>
            </div>
          </a>

          <!-- ReDoc -->
          <a href="/redoc" target="_blank" class="p-4 rounded-xl bg-slate-900/80 border border-indigo-500/30 hover:border-indigo-400 transition flex flex-col justify-between group">
            <div>
              <div class="text-sm font-bold text-indigo-300 flex items-center gap-2">
                <i class="fa-solid fa-book-bookmark"></i> ReDoc 接口规格文档
              </div>
              <p class="text-slate-400 mt-1.5 text-[11px]">排版优美清晰的企业级标准 API 规格参考手册，适合代码生成与集成对接。</p>
            </div>
            <div class="mt-4 flex items-center justify-between text-indigo-400 font-mono text-[11px]">
              <span>/redoc</span>
              <i class="fa-solid fa-arrow-up-right-from-square group-hover:translate-x-0.5 transition"></i>
            </div>
          </a>

          <!-- 打开目录 -->
          <div onclick="openProjectFolder()" class="p-4 rounded-xl bg-slate-900/80 border border-amber-500/30 hover:border-amber-400 transition flex flex-col justify-between cursor-pointer group">
            <div>
              <div class="text-sm font-bold text-amber-300 flex items-center gap-2">
                <i class="fa-solid fa-folder-open"></i> 本地项目源码目录
              </div>
              <p class="text-slate-400 mt-1.5 text-[11px]">一键在 Windows 资源管理器中打开项目根文件夹，便捷查看源码与日志。</p>
            </div>
            <div class="mt-4 flex items-center justify-between text-amber-400 font-mono text-[11px]">
              <span>explorer.exe</span>
              <i class="fa-solid fa-arrow-up-right-from-square group-hover:translate-x-0.5 transition"></i>
            </div>
          </div>
        </div>
      </section>

      <!-- 全局浮动通知提示 (Toast) -->
      <div id="live-toast" class="hidden fixed bottom-5 right-5 z-50 bg-slate-900 border border-cyan-500/40 text-cyan-300 text-xs px-4 py-2.5 rounded-xl shadow-2xl shadow-cyan-500/20 flex items-center gap-2 transition duration-300"></div>

    </main>
  </div>

  <!-- ======================================================== -->
  <!-- 3. 全局脚本 (JavaScript)                                -->
  <!-- ======================================================== -->
  <script>
        // 平台分类导航定义 (上图标 + 下名称 + 独立分类)
    const PLATFORM_CATEGORIES = [
      { key: "all", name: "全部平台", shortName: "全部", icon: "/assets/icons/all.svg", fallbackIcon: "fa-solid fa-shapes text-sky-400", count: 37 },
      { key: "gemini", name: "Google Gemini", shortName: "Gemini", icon: "/assets/icons/gemini.svg", fallbackIcon: "fa-solid fa-sparkles text-purple-400", count: 7 },
      { key: "gpt", name: "ChatGPT / OpenAI", shortName: "GPT / 逆向", icon: "/assets/icons/chatgpt.png", fallbackIcon: "fa-solid fa-robot text-emerald-400", count: 12 },
      { key: "suno", name: "Suno AI 音乐", shortName: "Suno AI", icon: "/assets/icons/suno.png", fallbackIcon: "fa-solid fa-music text-amber-400", count: 6 },
      { key: "baidu", name: "百度网盘", shortName: "百度网盘", icon: "/assets/icons/baidupan.png", fallbackIcon: "fa-solid fa-cloud text-blue-400", count: 3 },
      { key: "bilibili", name: "哔哩哔哩", shortName: "哔哩哔哩", icon: "/assets/icons/bilibili.png", fallbackIcon: "fa-solid fa-tv text-pink-400", count: 2 },
      { key: "system", name: "Cookie Hub & 系统", shortName: "系统服务", icon: "/assets/icons/system.svg", fallbackIcon: "fa-solid fa-terminal text-cyan-400", count: 6 },
    ];

    let currentPlaygroundCategory = "gemini";

    // 36 个 API 端点完整定义 (按平台精细化归属)
    const ALL_ENDPOINTS = [
      // 1. Google Gemini (7)
      { id: "gemini_chat", category: "gemini", method: "POST", url: "/api/gemini/chat", name: "Gemini 智能对话", desc: "4账号 LRU 自动轮换，支持模型切换与思考链推理级别", body: { prompt: "请用一句话告诉我：量子纠缠是什么？", model: "gemini-3.5-flash-lite", reasoning_level: "off", stream: true, timeout: 300 } },
      { id: "gemini_accounts", category: "gemini", method: "GET", url: "/api/gemini/accounts", name: "Gemini 4账号状态与额度", desc: "查看 4 个 Google 账号状态、5小时与每周计算配额、健康度", body: null },
      { id: "gemini_sync_profiles", category: "gemini", method: "POST", url: "/api/gemini/accounts/sync-profiles", name: "同步 Google 真实昵称邮箱", desc: "向 Google 上游拉取各 authuser 对应的真实用户显示昵称与 Gmail 邮箱", body: {} },
      { id: "gemini_check", category: "gemini", method: "POST", url: "/api/gemini/accounts/1/check", name: "检测账号凭证健康度", desc: "向 Google 上游验证指定账号 (如 #1) 会话有效性并更新健康状态", body: {} },
      { id: "gemini_rotate", category: "gemini", method: "POST", url: "/api/gemini/accounts/1/rotate", name: "触发账号令牌保活续期", desc: "向 Google 申请换发最新短命会话票据，防止 Cookie 失效", body: {} },
      { id: "gemini_refresh", category: "gemini", method: "POST", url: "/api/gemini/refresh", name: "从 Cookie Hub 刷新凭证", desc: "从浏览器提取最新鉴权 Cookie 并批量写入 SQLite 数据库", body: {} },
      { id: "gemini_requests", category: "gemini", method: "GET", url: "/api/gemini/requests?limit=10", name: "请求调度轨迹历史", desc: "查看最近请求调度轨迹与各账号响应延迟历史", body: null },

      // 2. OpenAI 兼容规范 (3)
      { id: "openai_chat", category: "openai", method: "POST", url: "/v1/chat/completions", name: "OpenAI 兼容聊天接口", desc: "无缝对接 NextChat、Chatbox、Cursor，底层分流 Gemini 与 ChatGPT", body: { model: "gemini-3.5-flash-lite", messages: [{ role: "user", content: "请用一句话告诉我：量子纠缠是什么？" }], reasoning_level: "off", stream: true } },
      { id: "openai_image", category: "openai", method: "POST", url: "/v1/images/generations", name: "OpenAI 兼容生图接口", desc: "标准 POST /v1/images/generations，底层路由至 gpt-image-2 / DALL-E 3", body: { prompt: "一只可爱的赛博朋克发光小猫，超高清，8k壁纸", model: "gpt-image-2", n: 1, response_format: "b64_json" } },
      { id: "openai_models", category: "openai", method: "GET", url: "/v1/models", name: "OpenAI 兼容模型列表", desc: "动态聚合逆向模型、页面模拟与谷歌号池所有可用模型", body: null },

      // 3. ChatGPT 逆向与号池 (9)
      { id: "chatgpt_chat", category: "chatgpt", method: "POST", url: "/api/chatgpt/chat", name: "ChatGPT 智能问答", desc: "支持逆向引擎直连与浏览器同源扩展双通道", body: { prompt: "请用幽默风趣的一句话自我介绍！", model: "auto", stream: true } },
      { id: "chatgpt_image", category: "chatgpt", method: "POST", url: "/api/chatgpt/image", name: "ChatGPT 逆向图片/GIF生成", desc: "基于官方逆向生成高质量图片或代码解释器生成的动图", body: { prompt: "一只戴着宇航头盔的橙色猫咪在火星漫步，水彩插画", model: "gpt-image-2", n: 1, response_format: "b64_json" } },
      { id: "chatgpt_status", category: "chatgpt", method: "GET", url: "/api/chatgpt/status", name: "ChatGPT 服务状态", desc: "检测逆向端口 (18084)、健康度与浏览器桥接状态", body: null },
      { id: "chatgpt_models", category: "chatgpt", method: "GET", url: "/api/chatgpt/models", name: "ChatGPT 可用模型列表", desc: "拉取逆向暴露或支持的模型 (auto, gpt-6, gpt-image-2 等)", body: null },
      { id: "chatgpt_accounts", category: "chatgpt", method: "GET", url: "/api/chatgpt/accounts", name: "ChatGPT 号池账号列表", desc: "查看已导入逆向引擎的账号列表、额度与健康状态", body: null },
      { id: "chatgpt_sync", category: "chatgpt", method: "POST", url: "/api/chatgpt/accounts/sync-browser", name: "浏览器 Token 一键同步入池", desc: "从浏览器提取 chatgpt.com 当前会话 Access Token 并载入逆向号池", body: {} },
      { id: "chatgpt_session", category: "chatgpt", method: "GET", url: "/api/chatgpt/session", name: "提取当前登录会话", desc: "提取当前 ChatGPT 标签页登录用户与 Access Token", body: null },
      { id: "chatgpt_start", category: "chatgpt", method: "POST", url: "/api/chatgpt/start", name: "启动独立逆向后台", desc: "手动按需启动基于 chatgpt2api 的独立无头逆向进程 (18084)", body: {} },
      { id: "chatgpt_stop", category: "chatgpt", method: "POST", url: "/api/chatgpt/stop", name: "停止独立逆向后台", desc: "停止 ChatGPT 独立无头逆向进程", body: {} },

      // 4. Suno AI 音乐创作 (6)
      { id: "suno_quota", category: "suno", method: "GET", url: "/api/suno/quota", name: "Suno AI 积分与可用曲目", desc: "查询 Suno 账号剩余积分及本月可用生成曲目数", body: null },
      { id: "suno_feed", category: "suno", method: "GET", url: "/api/suno/feed?page=1", name: "Suno AI 历史创作作品库", desc: "拉取已生成的音乐曲目、封面、歌词与音频直链", body: null },
      { id: "suno_gen", category: "suno", method: "POST", url: "/api/suno/generate", name: "Suno AI 提交音乐生成任务", desc: "根据描述词生成两首完整人声/器乐歌曲 (支持自定义模式)", body: { prompt: "一段欢快阳光的夏日流行海滩音乐，带有原声吉他和轻快的鼓点", is_custom: false, model: "chirp-goose", wait: false } },
      { id: "suno_audio", category: "suno", method: "GET", url: "/api/suno/audio/f42ad222-213f-4e8b-a7b1-dbc23455d1eb", name: "Suno AI 解密流式试听", desc: "自动解密 Suno 渐进流并直接在浏览器在线播放无损 M4A", body: null },
      { id: "suno_status", category: "suno", method: "GET", url: "/api/suno/status?clip_ids=f42ad222-213f-4e8b-a7b1-dbc23455d1eb", name: "Suno AI 任务状态轮询", desc: "查询任务渲染进度与本地解密流式播放直链", body: null },
      { id: "suno_lyrics", category: "suno", method: "POST", url: "/api/suno/lyrics", name: "Suno AI 独立歌词创作", desc: "输入主题生成结构完整的双节押韵歌词", body: { prompt: "写一首关于秋天落叶与思念的流行歌词" } },
      { id: "suno_refresh", category: "suno", method: "POST", url: "/api/suno/refresh", name: "Suno AI 刷新鉴权凭证", desc: "强制刷新 Suno 会话凭证与 Clerk JWT 令牌", body: {} },

      // 5. 百度网盘 存储与文件 (4)
      { id: "baidu_quota", category: "baidu", method: "GET", url: "/api/baidupan/quota", name: "百度网盘 存储容量与配额", desc: "获取已用空间、总空间与 VIP 配额详情", body: null },
      { id: "baidu_user", category: "baidu", method: "GET", url: "/api/baidupan/user", name: "百度网盘 用户账号资料", desc: "获取百度网盘用户名、头像与 VIP 等级", body: null },
      { id: "baidu_files", category: "baidu", method: "GET", url: "/api/baidupan/files?dir_path=/", name: "百度网盘 目录文件遍历", desc: "遍历网盘根目录 / 或指定子目录下的文件清单", body: null },
      { id: "baidu_refresh", category: "baidu", method: "POST", url: "/api/baidupan/refresh", name: "百度网盘 刷新鉴权凭证", desc: "从浏览器 Cookie Hub 强制同步最新百度网盘登录凭证", body: {} },

      // 6. 哔哩哔哩 个人与视频 (2)
      { id: "bili_user", category: "bilibili", method: "GET", url: "/api/bilibili/user", name: "B站 登录用户信息与资产", desc: "查看当前 B 站登录用户资料、硬币、B币与大会员有效期", body: null },
      { id: "bili_video", category: "bilibili", method: "GET", url: "/api/bilibili/video?bvid=BV1GJ411x7h7", name: "B站 视频信息与特权流", desc: "查询视频元数据与大会员专属 4K/1080P60 播放直链", body: null },

      // 7. Cookie Hub 通信与系统管理 (6)
      { id: "system_overview", category: "system", method: "GET", url: "/api/system/overview", name: "系统全局运行总览", desc: "查看 Cookie Hub、Gemini 池、ChatGPT 与开机自启动全景状态", body: null },
      { id: "system_open_dir", category: "system", method: "POST", url: "/api/system/open-directory", name: "打开项目本地目录", desc: "在 Windows 资源管理器中弹出打开套件根目录文件夹", body: {} },
      { id: "system_autostart_get", category: "system", method: "GET", url: "/api/system/autostart", name: "查询 Windows 开机自启状态", desc: "检查注册表 Run 与开始菜单 Startup 双重持久化配置", body: null },
      { id: "system_autostart_toggle", category: "system", method: "POST", url: "/api/system/autostart/toggle", name: "一键切换开机自启动", desc: "在开启 (双重保障) 与关闭之间一键无缝切换", body: {} },
      { id: "hub_status", category: "system", method: "GET", url: "/api/hub/status", name: "Cookie Hub 扩展桥状态", desc: "检测 Chrome/Edge 扩展与本地 Node 服务长连接", body: null },
      { id: "hub_cookies", category: "system", method: "GET", url: "/api/hub/cookies?domain=google.com", name: "按域名动态提取 Cookie", desc: "从浏览器实时提取指定域名 (如 google.com) 的 Cookie 字典与 Header", body: null },
    ];

    let currentCategory = "all";

    // 切换左侧导航激活样式
    
    function endpointMatchesPlatform(ep, platformKey) {
      if (platformKey === "all") return true;
      if (platformKey === "gemini") return ep.category === "gemini";
      if (platformKey === "gpt") return ep.category === "chatgpt" || ep.category === "openai";
      if (platformKey === "suno") return ep.category === "suno";
      if (platformKey === "baidu") return ep.category === "baidu";
      if (platformKey === "bilibili") return ep.category === "bilibili";
      if (platformKey === "system") return ep.category === "system";
      return ep.category === platformKey;
    }

    function getPlatformKeyForEndpoint(ep) {
      if (ep.category === "gemini") return "gemini";
      if (ep.category === "chatgpt" || ep.category === "openai") return "gpt";
      if (ep.category === "suno") return "suno";
      if (ep.category === "baidu") return "baidu";
      if (ep.category === "bilibili") return "bilibili";
      if (ep.category === "system") return "system";
      return "all";
    }

    // 渲染调试台顶部分类导航栏 (上图标 + 下名称 + 接口数徽章)
    function renderPlaygroundCategoryNav() {
      const nav = document.getElementById("playground-category-nav");
      if (!nav) return;

      nav.innerHTML = PLATFORM_CATEGORIES.map(cat => {
        const isActive = cat.key === currentPlaygroundCategory;
        const activeClass = isActive ? "plat-tab-active" : "";
        const indicatorClass = isActive ? "block" : "hidden";
        const iconBgClass = isActive ? "bg-cyan-500/20 shadow-inner" : "bg-slate-800/80";
        const titleClass = isActive ? "text-cyan-300 font-bold" : "text-slate-300 group-hover:text-cyan-200";
        const countBadgeClass = isActive ? "text-cyan-300 bg-cyan-500/20 border-cyan-500/40" : "text-slate-400 bg-slate-800/80 border-slate-700/60";

        return `
          <button onclick="setPlaygroundCategory('${cat.key}', true)" 
                  id="plat-tab-${cat.key}"
                  class="plat-tab relative group flex flex-col items-center justify-between py-2.5 px-2 rounded-xl text-center focus:outline-none ${activeClass}">
            <!-- 上图标 (28x28 居中高清晰度，带降级处理) -->
            <div class="w-8 h-8 rounded-lg ${iconBgClass} p-1 flex items-center justify-center transition duration-200 group-hover:scale-110 shrink-0">
              <img src="${cat.icon}" alt="${cat.name}" class="w-6 h-6 object-contain" onerror="this.onerror=null; this.outerHTML='<i class=\'${cat.fallbackIcon}\'></i>';">
            </div>
            <!-- 下名称 -->
            <span class="text-xs font-semibold mt-1.5 text-center ${titleClass} truncate w-full">
              ${cat.shortName}
            </span>
            <!-- 接口数量徽章 -->
            <span class="text-[10px] ${countBadgeClass} px-1.5 py-0.2 rounded-full border font-mono mt-1">
              ${cat.count} 模板
            </span>
            <!-- 激活呼吸指示条 -->
            <div class="plat-indicator ${indicatorClass} w-6 h-0.5 rounded-full bg-cyan-400 mt-1 shadow-sm shadow-cyan-400"></div>
          </button>
        `;
      }).join("");
    }

    // 切换分类导航：更新选中态并按分类重构下方下拉框
    function setPlaygroundCategory(catKey, autoSelect = true) {
      currentPlaygroundCategory = catKey;
      renderPlaygroundCategoryNav();
      const filtered = populateApiSelector(catKey);
      if (autoSelect && filtered && filtered.length > 0) {
        loadEndpoint(filtered[0].id, false);
      }
    }

    // 按当前分类动态填充下方 API 模板下拉框
    function populateApiSelector(catKey) {
      const selector = document.getElementById("api-selector");
      if (!selector) return [];

      const filtered = ALL_ENDPOINTS.filter(ep => endpointMatchesPlatform(ep, catKey));
      
      const badge = document.getElementById("api-template-badge");
      const catObj = PLATFORM_CATEGORIES.find(c => c.key === catKey) || PLATFORM_CATEGORIES[0];
      if (badge) {
        badge.innerText = `${catObj.shortName} · ${filtered.length} 个模板`;
      }
      const indicator = document.getElementById("current-playground-cat-indicator");
      if (indicator) {
        indicator.innerHTML = `当前: <span class="text-cyan-300 font-bold">${catObj.name}</span> (${filtered.length}个模板)`;
      }

      if (catKey === "all") {
        let html = "";
        const groups = [
          { label: "── Google Gemini 4账号统一池 ──", key: "gemini" },
          { label: "── OpenAI 标准兼容接口 ──", key: "openai" },
          { label: "── ChatGPT 逆向工程与号池 ──", key: "chatgpt" },
          { label: "── Suno AI 音乐创作 ──", key: "suno" },
          { label: "── 百度网盘 存储与资产 ──", key: "baidu" },
          { label: "── 哔哩哔哩 视频与特权 ──", key: "bilibili" },
          { label: "── Cookie Hub 通信与系统管理 ──", key: "system" }
        ];
        groups.forEach(g => {
          const gEps = ALL_ENDPOINTS.filter(e => e.category === g.key);
          if (gEps.length > 0) {
            html += `<optgroup label="${g.label}">`;
            gEps.forEach(e => {
              html += `<option value="${e.id}">[${e.method}] ${e.url} (${e.name})</option>`;
            });
            html += `</optgroup>`;
          }
        });
        selector.innerHTML = html;
      } else {
        selector.innerHTML = filtered.map(e => {
          return `<option value="${e.id}">[${e.method}] ${e.url} (${e.name})</option>`;
        }).join("");
      }

      return filtered;
    }

    function setActiveNav(element) {
      document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.remove("nav-item-active");
      });
      if (element) element.classList.add("nav-item-active");
    }

    // 打开 Windows 本地项目目录
    async function openProjectFolder() {
      showToast("正在打开项目目录...");
      try {
        const res = await fetch("/api/system/open-directory", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          showToast("已在 Windows 资源管理器中打开项目目录！");
        } else {
          alert("打开失败: " + (data.detail || "未知错误"));
        }
      } catch (err) {
        alert("打开项目目录异常: " + err.message);
      }
    }

    // 渲染 API 端点卡片清单
    function renderEndpointsList() {
      const grid = document.getElementById("endpoints-grid");
      const searchKeyword = (document.getElementById("api-search-input").value || "").trim().toLowerCase();
      
      const filtered = ALL_ENDPOINTS.filter(ep => {
        let matchesCategory = false;
        if (currentCategory === "all") matchesCategory = true;
        else if (currentCategory === "ecosystem") matchesCategory = ["bilibili", "baidu", "suno"].includes(ep.category);
        else if (currentCategory === "chatgpt") matchesCategory = ep.category === "chatgpt";
        else if (currentCategory === "openai") matchesCategory = ep.category === "openai";
        else if (currentCategory === "gemini") matchesCategory = ep.category === "gemini";
        else if (currentCategory === "system") matchesCategory = ep.category === "system";
        else matchesCategory = (ep.category === currentCategory);
        if (!matchesCategory) return false;
        if (!searchKeyword) return true;
        return ep.url.toLowerCase().includes(searchKeyword) ||
               ep.name.toLowerCase().includes(searchKeyword) ||
               ep.desc.toLowerCase().includes(searchKeyword) ||
               ep.method.toLowerCase().includes(searchKeyword);
      });

      document.getElementById("endpoints-count-badge").innerText = `展示 ${filtered.length} / 共 37 个端点`;

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

    // 载入指定端点到调试台，autoRun 为 true 时立即发送请求
    function loadEndpoint(endpointId, autoRun = false) {
      const ep = ALL_ENDPOINTS.find(e => e.id === endpointId);
      if (!ep) return;

      // 同步调试台平台分类导航栏与下拉模板
      const epPlat = getPlatformKeyForEndpoint(ep);
      if (currentPlaygroundCategory !== "all" && currentPlaygroundCategory !== epPlat) {
        setPlaygroundCategory(epPlat, false);
      } else if (!document.getElementById("api-selector").options.length) {
        populateApiSelector(currentPlaygroundCategory);
      }

      // 同步选择器值
      const selector = document.getElementById("api-selector");
      if (selector) selector.value = ep.id;

      document.getElementById("req-method-badge").innerText = ep.method;
      if (ep.method === "POST") {
        document.getElementById("req-method-badge").className = "px-2.5 py-1 rounded-lg text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono";
      } else {
        document.getElementById("req-method-badge").className = "px-2.5 py-1 rounded-lg text-xs font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30 font-mono";
      }

      document.getElementById("req-endpoint").value = ep.url;
      const bodyContainer = document.getElementById("req-body-container");
      const controlsGrid = document.getElementById("model-controls-grid");
      const presetContainer = document.getElementById("ai-preset-container");

      if (ep.method === "GET") {
        bodyContainer.style.display = "none";
        if (controlsGrid) controlsGrid.style.display = "none";
        if (presetContainer) presetContainer.style.display = "none";
      } else {
        bodyContainer.style.display = "block";
        if (presetContainer) presetContainer.style.display = "block";
        const bodyStr = ep.body ? JSON.stringify(ep.body, null, 2) : "{}";
        document.getElementById("req-body").value = bodyStr;

        if (ep.id === "gemini_chat" || ep.id === "openai_chat" || ep.id === "chatgpt_chat") {
          if (controlsGrid) controlsGrid.style.display = "grid";
          const streamContainer = document.getElementById("stream-toggle-container");
          if (streamContainer) streamContainer.style.display = "flex";
          const streamToggle = document.getElementById("stream-toggle");
          if (streamToggle) {
            try {
              const parsed = JSON.parse(bodyStr);
              if (parsed && typeof parsed.stream === "boolean") {
                streamToggle.checked = parsed.stream;
                const toggleText = document.getElementById("stream-toggle-text");
                if (toggleText) {
                  toggleText.innerText = parsed.stream ? "实时打字 (SSE)" : "非流式聚合";
                  toggleText.className = parsed.stream ? "ml-2 text-xs font-mono text-cyan-300" : "ml-2 text-xs font-mono text-slate-400";
                }
              }
            } catch(e) {}
          }
        } else {
          if (controlsGrid) controlsGrid.style.display = "none";
          const streamContainer = document.getElementById("stream-toggle-container");
          if (streamContainer) streamContainer.style.display = "none";
        }
      }

      // 平滑滚动至调试台
      const playSection = document.getElementById("section-playground");
      if (playSection && playSection.scrollIntoView && window.__pageLoaded) {
        playSection.scrollIntoView({ behavior: "smooth" });
      }

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
        if (data.reasoning_level !== undefined) {
          data.reasoning_level = reasoning;
        }
        const streamToggle = document.getElementById("stream-toggle");
        if (streamToggle && data.stream !== undefined) {
          data.stream = streamToggle.checked;
        }
        bodyEl.value = JSON.stringify(data, null, 2);
      } catch (e) {}
    }

    function onStreamToggleChange() {
      const isStream = document.getElementById("stream-toggle").checked;
      const toggleText = document.getElementById("stream-toggle-text");
      if (toggleText) {
        toggleText.innerText = isStream ? "实时打字 (SSE)" : "非流式聚合";
        toggleText.className = isStream ? "ml-2 text-xs font-mono text-cyan-300" : "ml-2 text-xs font-mono text-slate-400";
      }
      const bodyEl = document.getElementById("req-body");
      if (bodyEl && bodyEl.value) {
        try {
          const data = JSON.parse(bodyEl.value);
          data.stream = isStream;
          bodyEl.value = JSON.stringify(data, null, 2);
        } catch (e) {}
      }
    }

    function switchApiTemplate() {
      const key = document.getElementById("api-selector").value;
      loadEndpoint(key, false);
    }

    const AI_PRESETS_MAP = {
      quantum: "请用一句话告诉我：量子纠缠是什么？",
      python_async: "用 Python 编写一个高性能并发异步下载器，带连接池、超时自愈重试与流式进度展示",
      translation: "请将以下技术段落进行中英专业学术级双向互译，保持术语严谨准确并给出语法对照解析：\\n\\n'Modern distributed consensus systems rely on replicated state machines to guarantee safety under network partitions.'",
      raft_paxos: "详细对比分布式架构下 Raft 与 Paxos 一致性算法的优缺点、工程选型考量与极端网络分区脑裂下的自愈恢复机制",
      marketing: "为一款主打轻量敏捷与 Google 多账号智能 LRU 自动分流的 Cookie Service Suite 开发者工具撰写一段极具吸引力的小红书/推特爆款推介文案，突出秒出首字与稳定自愈特性",
      cyberpunk_cat: "一只可爱的赛博朋克霓虹发光机械猫咪在雨夜未来街道漫步，8K超高清，虚幻5电影级光影质感",
      suno_music: "一段欢快阳光的夏日流行海滩音乐，带有原声吉他和轻快的鼓点"
    };

    function applyAiPreset() {
      const selector = document.getElementById("ai-preset-selector");
      if (!selector) return;
      const key = selector.value;
      const text = AI_PRESETS_MAP[key];
      if (!text) return;

      const bodyEl = document.getElementById("req-body");
      if (!bodyEl || !bodyEl.value) return;

      try {
        const data = JSON.parse(bodyEl.value);
        if (data.prompt !== undefined) {
          data.prompt = text;
        } else if (data.messages && Array.isArray(data.messages)) {
          data.messages = [{ role: "user", content: text }];
        }

        if (key === "raft_paxos") {
          const reasoningEl = document.getElementById("reasoning-selector");
          if (reasoningEl && reasoningEl.value === "off") {
            reasoningEl.value = "medium";
            if (data.reasoning_level !== undefined) data.reasoning_level = "medium";
          }
        }

        bodyEl.value = JSON.stringify(data, null, 2);
        showToast("已成功应用 AI 预设提示词！");
      } catch (e) {
        console.error("更新预设提示词失败:", e);
      }
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

      const audioCard = document.getElementById("audio-preview-card");
      const renderedAudio = document.getElementById("rendered-audio");
      const btnDownloadAudio = document.getElementById("btn-download-audio");
      const audioTitle = document.getElementById("audio-preview-title");

      imgCard.classList.add("hidden");
      if (audioCard) audioCard.classList.add("hidden");
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

        const contentType = resp.headers.get("content-type") || "";

        // 1. 支持实时流式 (SSE) 渲染，首字秒级打字机输出
        if (contentType.includes("text/event-stream") && resp.body) {
          statusSpan.classList.remove("hidden");
          statusSpan.innerText = `${resp.status} Streaming`;
          statusSpan.className = "text-xs px-2 py-0.5 rounded font-mono bg-cyan-500/20 text-cyan-400 animate-pulse";
          out.innerText = "";
          
          const reader = resp.body.getReader();
          const decoder = new TextDecoder("utf-8");
          let streamDone = false;
          let fullText = "";
          let firstTokenTime = null;
          let buffer = "";
          let streamError = null;

          while (!streamDone) {
            const { value, done } = await reader.read();
            streamDone = done;
            if (value) {
              if (firstTokenTime === null) {
                firstTokenTime = Math.round(performance.now() - t0);
                timeSpan.innerText = `首字: ${firstTokenTime}ms | 正在流式打字...`;
              }
              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split(String.fromCharCode(10));
              buffer = lines.pop(); // 保留最后一个未闭合的行
              
              for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || trimmed.startsWith("event:")) continue;
                if (trimmed.startsWith("data:")) {
                  const payload = trimmed.substring(5).trim();
                  if (payload === "[DONE]") {
                    continue;
                  }
                  try {
                    const parsed = JSON.parse(payload);
                    if (parsed.error) {
                      const errMsg = typeof parsed.error === "string" ? parsed.error : (parsed.error.message || JSON.stringify(parsed.error));
                      streamError = errMsg;
                      fullText += String.fromCharCode(10) + "❌ [流式异常 / 上游错误]: " + errMsg + String.fromCharCode(10);
                      out.innerText = fullText;
                      out.scrollTop = out.scrollHeight;
                      continue;
                    }
                    const delta = parsed.choices?.[0]?.delta?.content || 
                                  parsed.choices?.[0]?.delta?.reasoning_content ||
                                  parsed.choices?.[0]?.text ||
                                  parsed.choices?.[0]?.message?.content ||
                                  parsed.delta || parsed.text || parsed.reply || "";
                    if (delta) {
                      fullText += delta;
                      out.innerText = fullText;
                      out.scrollTop = out.scrollHeight;
                    } else if (parsed.choices?.[0]?.delta && Object.keys(parsed.choices[0].delta).length === 0) {
                      // 忽略正常的流结束块
                    } else if (!parsed.choices) {
                      fullText += payload + String.fromCharCode(10);
                      out.innerText = fullText;
                      out.scrollTop = out.scrollHeight;
                    }
                  } catch(e) {
                    fullText += payload + String.fromCharCode(10);
                    out.innerText = fullText;
                    out.scrollTop = out.scrollHeight;
                  }
                } else if (trimmed) {
                  fullText += trimmed + String.fromCharCode(10);
                  out.innerText = fullText;
                  out.scrollTop = out.scrollHeight;
                }
              }
            }
          }

          // 处理缓冲区残留的未换行行数据
          if (buffer && buffer.trim()) {
            const trimmed = buffer.trim();
            if (trimmed.startsWith("data:")) {
              const payload = trimmed.substring(5).trim();
              if (payload && payload !== "[DONE]") {
                try {
                  const parsed = JSON.parse(payload);
                  if (parsed.error) {
                    const errMsg = typeof parsed.error === "string" ? parsed.error : (parsed.error.message || JSON.stringify(parsed.error));
                    streamError = errMsg;
                    fullText += String.fromCharCode(10) + "❌ [流式异常 / 上游错误]: " + errMsg + String.fromCharCode(10);
                  } else {
                    const delta = parsed.choices?.[0]?.delta?.content || 
                                  parsed.choices?.[0]?.delta?.reasoning_content ||
                                  parsed.delta || parsed.text || parsed.reply || "";
                    if (delta) fullText += delta;
                    else if (!parsed.choices) fullText += payload;
                  }
                } catch(e) {
                  fullText += payload;
                }
              }
            }
          }
          
          const totalTook = Math.round(performance.now() - t0);
          timeSpan.innerText = `首字: ${firstTokenTime || 0}ms | 总耗时: ${totalTook}ms`;

          if (streamError) {
            statusSpan.innerText = "Error (流式异常)";
            statusSpan.className = "text-xs px-2 py-0.5 rounded font-mono bg-rose-500/20 text-rose-400";
            out.innerText = fullText || ("❌ [流式异常]: " + streamError);
          } else if (!fullText.trim()) {
            out.innerText = "⚠️ 上游流式已结束，但未解析出文本内容。\\n建议：\\n1. 请检查上方模型与入参配置；\\n2. 点击上方【从 Cookie Hub 刷新凭证】更新最新会话。";
            statusSpan.innerText = "200 (空响应)";
            statusSpan.className = "text-xs px-2 py-0.5 rounded font-mono bg-amber-500/20 text-amber-400";
          } else {
            out.innerText = fullText;
            statusSpan.innerText = "200 OK (流式完成)";
            statusSpan.className = "text-xs px-2 py-0.5 rounded font-mono bg-emerald-500/20 text-emerald-400";
          }
          return;
        }

        if (contentType.includes("audio") || contentType.includes("video")) {
          if (audioCard && renderedAudio) {
            renderedAudio.src = endpoint;
            if (btnDownloadAudio) {
              btnDownloadAudio.href = endpoint;
              btnDownloadAudio.download = endpoint.split("/").pop() || "suno_audio.m4a";
            }
            if (audioTitle) {
              audioTitle.innerText = "Suno 在线流式播放 (" + (endpoint.split("/").pop() || "Clip") + ")";
            }
            audioCard.classList.remove("hidden");
            try { renderedAudio.play(); } catch(e){}
          }
          out.innerText = `[200 OK 音频流已就绪] Content-Type: ${contentType}\n媒体直链: ${window.location.origin}${endpoint}\n已在上方播放器中自动载入，支持拖拽与直接在线试听。`;
          return;
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

        // 智能检测 Suno 音频链接并展现试听
        try {
          let foundAudio = null;
          let songTitle = "";
          if (Array.isArray(data)) {
            for (const item of data) {
              if (item && (item.local_audio_url || item.audio_url)) {
                foundAudio = item.local_audio_url || item.audio_url;
                songTitle = item.title || "";
                break;
              }
            }
          } else if (data && (data.local_audio_url || data.audio_url)) {
            foundAudio = data.local_audio_url || data.audio_url;
            songTitle = data.title || "";
          }

          if (foundAudio && audioCard && renderedAudio && !foundAudio.includes("forbidden")) {
            renderedAudio.src = foundAudio;
            if (btnDownloadAudio) {
              btnDownloadAudio.href = foundAudio;
              btnDownloadAudio.download = (songTitle ? songTitle + ".m4a" : "suno_audio.m4a");
            }
            if (audioTitle) {
              audioTitle.innerText = songTitle ? `Suno 试听: ${songTitle}` : "Suno 在线音乐试听";
            }
            audioCard.classList.remove("hidden");
          }
        } catch (audioErr) {}

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
      const btn = document.getElementById("sidebar-btn-autostart");
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
      const icon = document.getElementById("sidebar-refresh-icon");
      if (icon) icon.classList.add("fa-spin");

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

          // 自启徽章与侧边栏更新
          const autoOk = sys.autostart && sys.autostart.enabled;
          const autoSideText = document.getElementById("sidebar-autostart-text");
          const autoSideDot = document.getElementById("sidebar-autostart-dot");
          const autoBadge = document.getElementById("autostart-status-badge");
          if (autoOk) {
            if (autoSideText) autoSideText.innerText = "自启: [已开启]";
            if (autoSideDot) autoSideDot.className = "w-2 h-2 rounded-full bg-emerald-400";
            if (autoBadge) {
              autoBadge.innerText = "自启: 🟢 已开启";
              autoBadge.className = "text-emerald-400 font-semibold";
            }
          } else {
            if (autoSideText) autoSideText.innerText = "自启: [已关闭]";
            if (autoSideDot) autoSideDot.className = "w-2 h-2 rounded-full bg-slate-500";
            if (autoBadge) {
              autoBadge.innerText = "自启: ⚪ 已关闭";
              autoBadge.className = "text-slate-400 font-semibold";
            }
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
        if (icon) icon.classList.remove("fa-spin");
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
    renderPlaygroundCategoryNav();
    setPlaygroundCategory("gemini", true);
    refreshDashboard();
    setInterval(refreshDashboard, 12000); // 12秒自动更新一次
    window.__pageLoaded = true;
  </script>
</body>
</html>"""
