#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 现代化 Web 控制台前端模板
特性：
- 左侧固定导航栏切换独立工作视图：调试台、运行概览、账号看板、对话历史、接口清单、文档规范
- 极简低噪的暗色开发者控制台美学，消除堆叠冗余与视觉干扰
- 调试台采用主流请求工具布局（平台切换 -> 统一请求栏 -> 参数配置与实时响应双栏）
- 动态计算全量 52 个标准化 API 端点分类数量，支持一键填入/测试与流式/图文/音频渲染
"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cookie Service Suite | 本地服务与 API 控制台</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    :root {
      --bg-canvas: #090d16;
      --bg-surface: #0f1623;
      --bg-elevated: #141d2e;
      --border-subtle: rgba(148, 163, 184, 0.14);
    }
    body {
      background-color: var(--bg-canvas);
      color: #f1f5f9;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
    }
    code, pre, .font-mono {
      font-family: "JetBrains Mono", "Cascadia Code", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    .panel {
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
    }
    .panel-soft {
      background-color: rgba(15, 22, 35, 0.65);
      border: 1px solid var(--border-subtle);
    }
    *::-webkit-scrollbar { width: 6px; height: 6px; }
    *::-webkit-scrollbar-track { background: transparent; }
    *::-webkit-scrollbar-thumb { background: rgba(100, 116, 139, 0.35); border-radius: 9999px; }
    *::-webkit-scrollbar-thumb:hover { background: rgba(148, 163, 184, 0.55); }

    .nav-item {
      cursor: pointer;
      transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
    }
    .nav-item-active {
      background: rgba(56, 189, 248, 0.12);
      color: #38bdf8;
      border-color: rgba(56, 189, 248, 0.32);
      font-weight: 600;
    }
    .plat-pill {
      cursor: pointer;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(148, 163, 184, 0.14);
      transition: all 0.15s ease;
    }
    .plat-pill:hover {
      background: rgba(30, 41, 59, 0.85);
      border-color: rgba(56, 189, 248, 0.35);
      color: #e2e8f0;
    }
    .plat-pill-active {
      background: rgba(56, 189, 248, 0.14);
      border-color: rgba(56, 189, 248, 0.55);
      color: #38bdf8;
      font-weight: 600;
    }
    .tab-active {
      background: rgba(56, 189, 248, 0.14);
      color: #38bdf8;
      border-color: rgba(56, 189, 248, 0.45);
    }
    .view-section {
      display: none;
    }
    .view-section.active {
      display: block;
      animation: fadeSlideIn 0.16s ease-out;
    }
    @keyframes fadeSlideIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @media (prefers-reduced-motion: reduce) {
      .view-section.active { animation: none; }
      * { transition-duration: 0.01ms !important; }
    }
  </style>
</head>
<body class="min-h-screen flex bg-[#090d16] text-slate-100 antialiased selection:bg-sky-500/30 selection:text-sky-200">

  <!-- 移动端遮罩 -->
  <div id="mobile-backdrop" onclick="toggleMobileSidebar(false)" class="fixed inset-0 bg-black/60 z-40 hidden lg:hidden"></div>

  <!-- ======================================================== -->
  <!-- 1. 左侧固定导航栏 (Left Sidebar)                         -->
  <!-- ======================================================== -->
  <aside id="app-sidebar" class="fixed lg:sticky top-0 left-0 z-50 h-screen w-60 bg-[#0d131f] border-r border-slate-800/80 flex flex-col justify-between shrink-0 transform -translate-x-full lg:translate-x-0 transition-transform duration-200">
    <div class="p-4 space-y-6 overflow-y-auto">
      <!-- 品牌标识 -->
      <div class="flex items-center justify-between px-1 pb-3 border-b border-slate-800/80">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-sky-500/15 border border-sky-400/30 flex items-center justify-center shrink-0">
            <i class="fa-solid fa-cookie-bite text-sky-400 text-sm"></i>
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-1.5">
              <span class="font-semibold text-sm text-slate-100 tracking-tight truncate">Cookie Suite</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">v2.0</span>
            </div>
            <p class="text-[11px] text-slate-500 truncate">本地服务调度中心</p>
          </div>
        </div>
        <button onclick="toggleMobileSidebar(false)" class="lg:hidden text-slate-400 hover:text-slate-200 p-1 cursor-pointer" aria-label="关闭侧边栏">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- 主导航 (切换视图) -->
      <div class="space-y-1">
        <div class="text-[11px] font-medium text-slate-500 px-2.5 pb-1.5">控制台视图</div>
        <nav class="space-y-1 text-[13px]" id="sidebar-nav">
          <button type="button" onclick="switchView('playground')" data-view="playground" class="nav-item w-full flex items-center justify-between px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent nav-item-active">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-terminal w-4 text-center text-sky-400"></i>
              <span>调试台</span>
            </span>
          </button>

          <button type="button" onclick="switchView('overview')" data-view="overview" class="nav-item w-full flex items-center justify-between px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-gauge-high w-4 text-center text-slate-400"></i>
              <span>运行概览</span>
            </span>
            <span id="nav-overview-dot" class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          </button>

          <button type="button" onclick="switchView('accounts')" data-view="accounts" class="nav-item w-full flex items-center justify-between px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-users w-4 text-center text-slate-400"></i>
              <span>账号看板</span>
            </span>
            <span id="nav-account-count" class="text-[11px] text-slate-500 font-mono">--</span>
          </button>

          <button type="button" onclick="switchView('history')" data-view="history" class="nav-item w-full flex items-center justify-between px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-clock-rotate-left w-4 text-center text-slate-400"></i>
              <span>对话历史</span>
            </span>
            <span id="nav-history-count" class="text-[11px] text-slate-500 font-mono">0</span>
          </button>

          <button type="button" onclick="switchView('endpoints')" data-view="endpoints" class="nav-item w-full flex items-center justify-between px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-code w-4 text-center text-slate-400"></i>
              <span>接口清单</span>
            </span>
            <span id="nav-endpoints-count" class="text-[11px] text-slate-500 font-mono">52</span>
          </button>

          <button type="button" onclick="switchView('docs')" data-view="docs" class="nav-item w-full flex items-center justify-between px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-book-open w-4 text-center text-slate-400"></i>
              <span>文档规范</span>
            </span>
          </button>
        </nav>
      </div>

      <!-- 系统工具 -->
      <div class="space-y-1.5 pt-3 border-t border-slate-800/80">
        <div class="text-[11px] font-medium text-slate-500 px-2.5 pb-1">本地工具</div>

        <button type="button" onclick="toggleAutostart()" id="sidebar-btn-autostart" class="w-full px-3 py-2 rounded-lg bg-slate-900/80 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs flex items-center justify-between transition cursor-pointer" title="切换 Windows 开机自启">
          <span class="flex items-center gap-2">
            <i class="fa-solid fa-power-off text-slate-400 w-3.5 text-center"></i>
            <span id="sidebar-autostart-text">自启: 检测中</span>
          </span>
          <span class="w-2 h-2 rounded-full bg-slate-500" id="sidebar-autostart-dot"></span>
        </button>

        <button type="button" onclick="openProjectFolder()" class="w-full px-3 py-2 rounded-lg bg-slate-900/80 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs flex items-center justify-between transition cursor-pointer" title="在 Windows 资源管理器中打开项目根目录">
          <span class="flex items-center gap-2">
            <i class="fa-solid fa-folder-open text-amber-400/90 w-3.5 text-center"></i>
            <span>打开项目目录</span>
          </span>
          <i class="fa-solid fa-arrow-up-right-from-square text-[10px] text-slate-500"></i>
        </button>

        <button type="button" onclick="refreshDashboard()" class="w-full px-3 py-2 rounded-lg bg-slate-900/80 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs flex items-center justify-between transition cursor-pointer">
          <span class="flex items-center gap-2">
            <i class="fa-solid fa-arrows-rotate text-sky-400 w-3.5 text-center" id="sidebar-refresh-icon"></i>
            <span>刷新服务状态</span>
          </span>
          <span class="text-[10px] text-slate-500 font-mono">12s</span>
        </button>
      </div>
    </div>

    <!-- 侧边栏底部: 监听地址与运行状态 -->
    <div class="p-3.5 border-t border-slate-800/80 bg-[#0b101a] text-[11px] space-y-1">
      <div class="flex items-center justify-between">
        <span class="text-slate-400 flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span> 守护进程在线
        </span>
        <span id="sidebar-uptime-mini" class="text-slate-400 font-mono">0m</span>
      </div>
      <div class="text-[11px] text-slate-500 font-mono">127.0.0.1:18800</div>
    </div>
  </aside>

  <!-- ======================================================== -->
  <!-- 2. 右侧主内容区域 (Main Workspace)                       -->
  <!-- ======================================================== -->
  <div class="flex-1 min-w-0 flex flex-col min-h-screen">

    <!-- 精简顶栏 -->
    <header class="h-14 bg-[#0d131f]/90 backdrop-blur border-b border-slate-800/80 px-4 sm:px-6 flex items-center justify-between gap-4 sticky top-0 z-30">
      <div class="flex items-center gap-3 min-w-0">
        <button onclick="toggleMobileSidebar(true)" class="lg:hidden p-2 -ml-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 cursor-pointer" aria-label="打开菜单">
          <i class="fa-solid fa-bars"></i>
        </button>
        <div class="min-w-0">
          <h1 id="topbar-title" class="text-sm font-semibold text-slate-100 truncate">调试台</h1>
          <p id="topbar-subtitle" class="text-[11px] text-slate-500 truncate hidden sm:block">多平台 API 在线调试与实时流式响应预览</p>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <button type="button" onclick="switchView('overview')" id="topbar-health-pill" class="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs text-slate-300 transition cursor-pointer">
          <span id="topbar-health-dot" class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span id="topbar-health-text">服务就绪</span>
        </button>
        <button type="button" onclick="exportToOpenCode()" class="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-1.5 cursor-pointer" title="将当前对话模型写入 OpenCode 配置">
          <i class="fa-solid fa-file-export text-sky-400"></i>
          <span class="hidden md:inline">导入 OpenCode</span>
        </button>
        <a href="/docs" target="_blank" class="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-1.5">
          <i class="fa-solid fa-bolt text-sky-400"></i>
          <span>Swagger</span>
        </a>
        <a href="/redoc" target="_blank" class="hidden sm:flex px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition items-center gap-1.5">
          <i class="fa-solid fa-book text-slate-400"></i>
          <span>ReDoc</span>
        </a>
      </div>
    </header>

    <!-- 主体工作区容器 -->
    <main class="flex-1 max-w-[1440px] w-full mx-auto px-4 sm:px-6 py-5 space-y-4">

      <!-- 登录提醒条 (仅在存在未登录服务时显示) -->
      <div id="login-guide" class="hidden rounded-xl border border-amber-500/35 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-100 flex items-center justify-between gap-3"></div>

      <!-- ==================================================== -->
      <!-- 视图 1: 调试台 (Playground)                          -->
      <!-- ==================================================== -->
      <section id="view-playground" class="view-section active space-y-4">

        <!-- 平台分类精简条 -->
        <div class="flex flex-wrap items-center gap-1.5" id="playground-category-nav">
          <!-- JS 动态渲染紧凑平台胶囊 -->
        </div>

        <!-- 统一请求控制栏 -->
        <div class="panel rounded-xl p-3 space-y-2.5">
          <div class="flex flex-col md:flex-row gap-2.5 items-stretch md:items-center">
            <!-- 预设模板选择 -->
            <div class="md:w-72 shrink-0">
              <select id="api-selector" onchange="switchApiTemplate()" aria-label="选择预设 API 模板" class="w-full h-9 bg-[#090d16] border border-slate-800 hover:border-slate-700 rounded-lg px-3 text-xs text-slate-200 focus:outline-none focus:border-sky-500 transition cursor-pointer">
              </select>
            </div>

            <!-- 方法 + 路径 + 发送按钮 -->
            <div class="flex-1 flex items-center gap-2 min-w-0">
              <span id="req-method-badge" class="h-9 px-3 rounded-lg text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono flex items-center shrink-0">POST</span>
              <input type="text" id="req-endpoint" aria-label="请求路径" class="flex-1 min-w-0 h-9 bg-[#090d16] border border-slate-800 rounded-lg px-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-sky-500 transition" value="/api/gemini/chat">
              <button type="button" onclick="executeApiCall()" id="btn-send" class="h-9 px-4 rounded-lg text-xs font-semibold bg-sky-500 hover:bg-sky-400 text-slate-950 transition flex items-center gap-2 shrink-0 cursor-pointer">
                <i class="fa-solid fa-paper-plane"></i>
                <span>发送请求</span>
              </button>
            </div>
          </div>

          <!-- 紧凑参数条 (仅对话/特定 POST 接口显示) -->
          <div id="playground-params-bar" class="pt-2.5 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 items-end">
            <div id="model-select-container">
              <label for="model-selector" class="text-[11px] text-slate-400 block mb-1">模型 (Model)</label>
              <select id="model-selector" onchange="onModelOrReasoningChange()" class="w-full h-8 bg-[#090d16] border border-slate-800 rounded-lg px-2.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500 cursor-pointer">
                <option value="gemini-4-hydrogen" selected>4 Hydrogen（日常帮助）</option>
              </select>
            </div>

            <div id="reasoning-level-container">
              <label for="reasoning-selector" class="text-[11px] text-slate-400 block mb-1">推理深度 (Reasoning)</label>
              <select id="reasoning-selector" onchange="onModelOrReasoningChange()" class="w-full h-8 bg-[#090d16] border border-slate-800 rounded-lg px-2.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500 cursor-pointer">
                <option value="off">低 · Fast and efficient</option>
                <option value="medium">中 · 深度适中</option>
                <option value="high">高 · 超级详尽</option>
              </select>
            </div>

            <div id="ai-preset-container">
              <label for="ai-preset-selector" class="text-[11px] text-slate-400 block mb-1">快捷提示词预设</label>
              <select id="ai-preset-selector" onchange="applyAiPreset()" class="w-full h-8 bg-[#090d16] border border-slate-800 rounded-lg px-2.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500 cursor-pointer">
                <option value="quantum" selected>物理科普 · 量子纠缠</option>
                <option value="python_async">编程开发 · Python 异步下载器</option>
                <option value="translation">专业翻译 · 学术中英互译</option>
                <option value="raft_paxos">深度思考 · Raft vs Paxos</option>
                <option value="marketing">产品文案 · 开发者工具推介</option>
                <option value="cyberpunk_cat">图像提示词 · 赛博朋克机械猫</option>
                <option value="suno_music">音乐创作 · 夏日流行海滩曲</option>
              </select>
            </div>

            <div id="stream-toggle-container" class="flex items-center justify-between h-8 px-3 rounded-lg bg-[#090d16] border border-slate-800 text-xs">
              <span class="text-slate-400 flex items-center gap-1.5">
                <i class="fa-solid fa-bolt text-amber-400 text-[11px]"></i>
                <span>流式 (SSE)</span>
              </span>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" id="stream-toggle" onchange="onStreamToggleChange()" class="sr-only peer" checked>
                <div class="w-8 h-4 bg-slate-700 rounded-full peer peer-checked:after:translate-x-4 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-sky-500"></div>
                <span id="stream-toggle-text" class="ml-2 text-[11px] font-mono text-sky-400">开启</span>
              </label>
            </div>
          </div>
        </div>

        <!-- 双栏工作区: 左请求体 / 右响应区 -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <!-- 左栏: 请求体编辑器 -->
          <div class="lg:col-span-5 panel rounded-xl flex flex-col overflow-hidden">
            <div class="px-4 py-2.5 border-b border-slate-800/80 flex items-center justify-between bg-[#0d131f]">
              <span class="text-xs font-medium text-slate-300 flex items-center gap-2">
                <i class="fa-solid fa-brackets-curly text-slate-400"></i> 请求体 (JSON Body)
              </span>
              <div class="flex items-center gap-1.5">
                <button type="button" onclick="formatRequestJson()" id="btn-format-json" class="px-2 py-1 rounded text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition cursor-pointer">
                  格式化
                </button>
                <button type="button" onclick="switchApiTemplate()" id="btn-reset-json" class="px-2 py-1 rounded text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition cursor-pointer">
                  重置
                </button>
              </div>
            </div>

            <div id="req-body-container" class="flex-1 flex flex-col p-3">
              <textarea id="req-body" rows="16" spellcheck="false" class="flex-1 w-full min-h-[360px] bg-[#090d16] font-mono text-xs leading-relaxed border border-slate-800/90 rounded-lg p-3.5 text-sky-300 focus:outline-none focus:border-sky-500 resize-y"></textarea>
            </div>

            <div id="get-body-empty" class="hidden flex-1 min-h-[360px] flex flex-col items-center justify-center p-6 text-center text-slate-500 text-xs space-y-2">
              <i class="fa-solid fa-arrow-right-arrow-left text-2xl text-slate-700"></i>
              <p class="text-slate-400 font-medium">当前为 GET 请求</p>
              <p class="max-w-xs text-[11px] text-slate-500">无需 JSON 请求体参数。您可以直接在上方修改 Query 参数后点击「发送请求」。</p>
            </div>
          </div>

          <!-- 右栏: 响应输出区 -->
          <div class="lg:col-span-7 panel rounded-xl flex flex-col overflow-hidden">
            <div class="px-4 py-2.5 border-b border-slate-800/80 flex items-center justify-between bg-[#0d131f] gap-2">
              <div class="flex items-center gap-2.5 min-w-0">
                <span class="text-xs font-medium text-slate-300">响应结果</span>
                <span id="resp-status" class="text-[11px] px-2 py-0.5 rounded font-mono hidden">200 OK</span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span id="resp-time" class="text-[11px] text-slate-400 font-mono">耗时: 0s</span>
                <button type="button" onclick="copyResponseOutput()" class="px-2 py-1 rounded text-[11px] bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition flex items-center gap-1 cursor-pointer">
                  <i class="fa-regular fa-copy"></i> 复制
                </button>
                <button type="button" onclick="clearResponseOutput()" class="px-2 py-1 rounded text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition cursor-pointer">
                  清空
                </button>
              </div>
            </div>

            <div class="p-3 flex-1 flex flex-col gap-3">
              <!-- 图片/GIF 预览 -->
              <div id="image-preview-card" class="hidden bg-[#090d16] border border-sky-500/30 rounded-lg p-3 flex flex-col items-center gap-2">
                <div class="w-full flex items-center justify-between text-xs text-sky-300">
                  <span class="font-medium flex items-center gap-1.5"><i class="fa-solid fa-image"></i> 生成图片预览</span>
                  <a id="btn-download-img" href="#" download="generated_image.png" class="px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 hover:bg-sky-500/25 text-[11px] font-mono flex items-center gap-1">
                    <i class="fa-solid fa-download"></i> 保存
                  </a>
                </div>
                <img id="rendered-image" src="" alt="生成的图片预览" class="max-h-64 max-w-full rounded border border-slate-800 object-contain">
              </div>

              <!-- 音频试听卡片 -->
              <div id="audio-preview-card" class="hidden bg-[#090d16] border border-indigo-500/30 rounded-lg p-3 flex flex-col gap-2">
                <div class="w-full flex items-center justify-between text-xs text-indigo-300">
                  <span class="font-medium flex items-center gap-1.5"><i class="fa-solid fa-music"></i> <span id="audio-preview-title">在线音频试听</span></span>
                  <a id="btn-download-audio" href="#" download="suno_music.m4a" class="px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 hover:bg-indigo-500/25 text-[11px] font-mono flex items-center gap-1">
                    <i class="fa-solid fa-download"></i> 下载音频
                  </a>
                </div>
                <audio id="rendered-audio" controls class="w-full h-9 rounded outline-none"></audio>
              </div>

              <pre id="resp-output" class="flex-1 bg-[#090d16] border border-slate-800/90 rounded-lg p-4 text-xs font-mono leading-relaxed text-emerald-400/95 overflow-auto min-h-[360px] max-h-[540px] whitespace-pre-wrap break-words">点击右上角「发送请求」，实时响应或流式输出将展示在此处...</pre>
            </div>
          </div>
        </div>
      </section>

      <!-- ==================================================== -->
      <!-- 视图 2: 运行概览 (Overview)                          -->
      <!-- ==================================================== -->
      <section id="view-overview" class="view-section space-y-5">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-base font-semibold text-slate-100">系统运行概览</h2>
            <p class="text-xs text-slate-400 mt-0.5">实时监控各本地子服务、扩展桥接与端口运行状态</p>
          </div>
          <button type="button" onclick="refreshDashboard()" class="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs flex items-center gap-1.5 transition cursor-pointer">
            <i class="fa-solid fa-arrows-rotate text-sky-400"></i> 立即刷新
          </button>
        </div>

        <!-- 3 列宽敞服务卡片 -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <div class="panel rounded-xl p-5 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-400">Cookie Hub 扩展桥</span>
              <span class="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center">
                <i class="fa-solid fa-puzzle-piece text-sm"></i>
              </span>
            </div>
            <div class="text-lg font-semibold text-slate-100 flex items-center gap-2" id="hub-status-text">
              <span class="inline-block w-2 h-2 rounded-full bg-emerald-400"></span> 正在连接
            </div>
            <div class="pt-2 border-t border-slate-800/70 text-xs text-slate-500 flex justify-between font-mono">
              <span>Port 18888</span>
              <span id="hub-clients">客户端: 0</span>
            </div>
          </div>

          <div class="panel rounded-xl p-5 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-400">Gemini 多账号统一池</span>
              <span class="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
                <i class="fa-solid fa-brain text-sm"></i>
              </span>
            </div>
            <div class="text-lg font-semibold text-slate-100" id="gemini-status-text">同步中</div>
            <div class="pt-2 border-t border-slate-800/70 text-xs text-slate-500 flex justify-between font-mono">
              <span>Port 18083</span>
              <span>LRU 自动均衡</span>
            </div>
          </div>

          <div class="panel rounded-xl p-5 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-400">AI Studio 逆向通道</span>
              <span class="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                <i class="fa-solid fa-wand-magic-sparkles text-sm"></i>
              </span>
            </div>
            <div class="text-lg font-semibold text-slate-100 flex items-center gap-2" id="aistudio-status-text">
              <span class="inline-block w-2 h-2 rounded-full bg-slate-500"></span> 检测中
            </div>
            <div class="pt-2 border-t border-slate-800/70 text-xs text-slate-500 flex justify-between font-mono">
              <span>Port 2048</span>
              <span id="aistudio-models-count">78+ 原生模型</span>
            </div>
          </div>

          <div class="panel rounded-xl p-5 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-400">ChatGPT 逆向工程</span>
              <span class="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                <i class="fa-solid fa-robot text-sm"></i>
              </span>
            </div>
            <div class="text-lg font-semibold text-slate-100" id="chatgpt-status-text">就绪</div>
            <div class="pt-2 border-t border-slate-800/70 text-xs text-slate-500 flex justify-between font-mono">
              <span>Port 18084</span>
              <span>支持 gpt-image-2</span>
            </div>
          </div>

          <div class="panel rounded-xl p-5 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-400">OpenAI 标准兼容接口</span>
              <span class="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
                <i class="fa-solid fa-network-wired text-sm"></i>
              </span>
            </div>
            <div class="text-lg font-semibold text-emerald-300 font-mono">/v1 开放中</div>
            <div class="pt-2 border-t border-slate-800/70 text-xs text-slate-500 flex justify-between font-mono">
              <span>Port 18800</span>
              <span>NextChat / Cursor</span>
            </div>
          </div>

          <div class="panel rounded-xl p-5 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-400">运行时长与开机自启</span>
              <span class="w-8 h-8 rounded-lg bg-slate-800 text-slate-300 flex items-center justify-center">
                <i class="fa-solid fa-clock text-sm"></i>
              </span>
            </div>
            <div class="text-lg font-semibold text-slate-100 font-mono" id="uptime-text">0m</div>
            <div class="pt-2 border-t border-slate-800/70 text-xs flex justify-between items-center">
              <span id="autostart-status-badge" class="text-slate-400 font-medium">自启: 检测中</span>
              <span class="text-slate-500 font-mono">双模守护</span>
            </div>
          </div>
        </div>

        <!-- 浏览器登录态检查详情 -->
        <div class="panel rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold text-slate-200">站点浏览器登录状态</h3>
            <span class="text-[11px] text-slate-500">依赖 Cookie Hub 自动同步</span>
          </div>
          <div id="overview-login-list" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 text-xs">
            <div class="text-slate-500 py-2">正在检测各平台浏览器登录状态...</div>
          </div>
        </div>
      </section>

      <!-- ==================================================== -->
      <!-- 视图 3: 账号看板 (Accounts)                          -->
      <!-- ==================================================== -->
      <section id="view-accounts" class="view-section space-y-4">
        <div class="panel rounded-xl p-5 space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
            <div>
              <h2 class="text-base font-semibold text-slate-100">Google 账号池看板</h2>
              <p class="text-xs text-slate-400 mt-0.5" id="accounts-summary">正在从浏览器同步 Google 账号...</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button type="button" onclick="syncProfiles()" id="btn-sync-profiles" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5 cursor-pointer">
                <i class="fa-solid fa-id-card text-sky-400"></i> 同步真实名称与邮箱
              </button>
              <button type="button" onclick="refreshAllCookies()" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 transition flex items-center gap-1.5 cursor-pointer">
                <i class="fa-solid fa-arrows-rotate"></i> 刷新全部凭证
              </button>
            </div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-300">
              <thead class="bg-[#090d16] text-[11px] uppercase text-slate-400 border-b border-slate-800 whitespace-nowrap">
                <tr>
                  <th class="py-3 px-3 font-medium">Google 账号</th>
                  <th class="py-3 px-3 font-medium">5小时滚动额度</th>
                  <th class="py-3 px-3 font-medium">周累计额度</th>
                  <th class="py-3 px-3 font-medium">会话状态</th>
                  <th class="py-3 px-3 font-medium text-right">操作</th>
                </tr>
              </thead>
              <tbody id="accounts-tbody" class="divide-y divide-slate-800/60">
                <tr><td colspan="5" class="py-8 text-center text-slate-500">正在获取账号数据...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- ==================================================== -->
      <!-- 视图 4: 对话历史与调用审计 (History)                 -->
      <!-- ==================================================== -->
      <section id="view-history" class="view-section space-y-4">
        <div class="panel rounded-xl p-5 space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
            <div>
              <h2 class="text-base font-semibold text-slate-100">对话历史与调用审计</h2>
              <p class="text-xs text-slate-400 mt-0.5">记录模型请求与完整返回（上限 100MB，超出自动 FIFO 清理）</p>
            </div>
            <div class="flex flex-wrap items-center gap-2.5">
              <div class="bg-[#090d16] border border-slate-800 rounded-lg px-3 py-1.5 flex items-center gap-2.5">
                <div class="space-y-1">
                  <div class="flex items-center justify-between text-[11px] gap-3 font-mono">
                    <span class="text-slate-500">存储</span>
                    <span id="history-size-badge" class="text-slate-300">0.00 MB / 100 MB</span>
                  </div>
                  <div class="w-28 h-1 bg-slate-800 rounded-full overflow-hidden">
                    <div id="history-size-bar" class="h-full bg-sky-400 rounded-full transition-all duration-300" style="width: 0%"></div>
                  </div>
                </div>
              </div>
              <button type="button" onclick="loadChatHistory(1, true)" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs flex items-center gap-1.5 transition cursor-pointer">
                <i class="fa-solid fa-rotate text-sky-400" id="history-refresh-icon"></i> 刷新
              </button>
              <button type="button" onclick="confirmClearHistory()" class="px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs flex items-center gap-1.5 transition cursor-pointer">
                <i class="fa-solid fa-trash-can"></i> 清空
              </button>
            </div>
          </div>

          <!-- 筛选栏 -->
          <div class="flex flex-wrap items-center justify-between gap-2.5 bg-[#090d16] p-2.5 rounded-lg border border-slate-800/80">
            <div class="flex flex-wrap items-center gap-2">
              <select id="history-filter-model" onchange="loadChatHistory(1, false)" aria-label="按模型筛选" class="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-sky-500 cursor-pointer">
                <option value="">全部模型</option>
                <option value="gemini">Gemini 系列</option>
                <option value="gpt">ChatGPT 系列</option>
                <option value="aistudio">AI Studio 系列</option>
                <option value="minimax">MiniMax 语音</option>
              </select>

              <select id="history-filter-status" onchange="loadChatHistory(1, false)" aria-label="按状态筛选" class="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-sky-500 cursor-pointer">
                <option value="">全部状态</option>
                <option value="200">仅成功 (200)</option>
                <option value="error">仅异常报错</option>
              </select>

              <div class="relative">
                <input type="text" id="history-search-input" onkeydown="if(event.key==='Enter')loadChatHistory(1, false)" placeholder="搜索 Prompt 或回复..." class="bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 w-48 sm:w-64" />
                <i class="fa-solid fa-magnifying-glass absolute left-2.5 top-2.5 text-slate-500 text-[11px]"></i>
              </div>
              <button type="button" onclick="loadChatHistory(1, false)" class="px-3 py-1.5 bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 rounded-lg text-xs transition cursor-pointer">
                搜索
              </button>
            </div>
            <div class="text-[11px] text-slate-500 font-mono px-1" id="history-pagination-summary">载入中...</div>
          </div>

          <!-- 列表 -->
          <div id="history-list-container" class="space-y-2.5 min-h-[160px]"></div>

          <!-- 分页 -->
          <div class="flex items-center justify-between border-t border-slate-800/80 pt-3 text-xs">
            <div class="text-slate-500" id="history-total-info">共 0 条记录</div>
            <div class="flex items-center gap-2">
              <button type="button" id="history-btn-prev" onclick="historyPageChange(-1)" disabled class="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer">
                上一页
              </button>
              <span id="history-page-indicator" class="font-mono text-slate-300 px-2">1 / 1</span>
              <button type="button" id="history-btn-next" onclick="historyPageChange(1)" disabled class="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer">
                下一页
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- ==================================================== -->
      <!-- 视图 5: 接口清单 (Endpoints)                         -->
      <!-- ==================================================== -->
      <section id="view-endpoints" class="view-section space-y-4">
        <div class="panel rounded-xl p-5 space-y-4">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h2 class="text-base font-semibold text-slate-100">标准化 API 接口清单</h2>
              <p class="text-xs text-slate-400 mt-0.5">点击「填入调试」或「立即测试」将自动跳转至调试台执行</p>
            </div>
            <div class="flex items-center gap-2.5">
              <div class="relative">
                <i class="fa-solid fa-magnifying-glass absolute left-3 top-2.5 text-[11px] text-slate-500"></i>
                <input type="text" id="api-search-input" oninput="filterEndpoints()" placeholder="搜索路径、名称或方法..." class="bg-[#090d16] border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 w-56 sm:w-64">
              </div>
              <span class="text-xs px-2.5 py-1.5 rounded-lg bg-[#090d16] text-slate-400 border border-slate-800 font-mono" id="endpoints-count-badge">共 52 个</span>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 border-b border-slate-800/80 pb-3" id="category-tabs">
            <!-- JS 动态渲染精确计数的分类按钮 -->
          </div>

          <div id="endpoints-grid" class="grid grid-cols-1 md:grid-cols-2 gap-3"></div>
        </div>
      </section>

      <!-- ==================================================== -->
      <!-- 视图 6: 文档与集成规范 (Docs)                        -->
      <!-- ==================================================== -->
      <section id="view-docs" class="view-section space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <a href="/docs" target="_blank" class="panel rounded-xl p-5 hover:border-sky-500/40 transition flex flex-col justify-between group">
            <div class="space-y-2">
              <div class="w-9 h-9 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center">
                <i class="fa-solid fa-bolt"></i>
              </div>
              <div class="text-sm font-semibold text-slate-100">Swagger UI 在线交互文档</div>
              <p class="text-slate-400 leading-relaxed">基于 FastAPI 自动生成的 OpenAPI 交互调试页面，支持查看所有字段 Schema 并直接发起请求。</p>
            </div>
            <div class="mt-5 pt-3 border-t border-slate-800/70 flex items-center justify-between text-sky-400 font-mono">
              <span>GET /docs</span>
              <i class="fa-solid fa-arrow-up-right-from-square group-hover:translate-x-0.5 transition"></i>
            </div>
          </a>

          <a href="/redoc" target="_blank" class="panel rounded-xl p-5 hover:border-indigo-500/40 transition flex flex-col justify-between group">
            <div class="space-y-2">
              <div class="w-9 h-9 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                <i class="fa-solid fa-book-bookmark"></i>
              </div>
              <div class="text-sm font-semibold text-slate-100">ReDoc 接口规格手册</div>
              <p class="text-slate-400 leading-relaxed">清晰的三栏式标准接口参考文档，适合排查数据结构、错误码与模型参数定义。</p>
            </div>
            <div class="mt-5 pt-3 border-t border-slate-800/70 flex items-center justify-between text-indigo-400 font-mono">
              <span>GET /redoc</span>
              <i class="fa-solid fa-arrow-up-right-from-square group-hover:translate-x-0.5 transition"></i>
            </div>
          </a>

          <div class="panel rounded-xl p-5 flex flex-col justify-between">
            <div class="space-y-2.5">
              <div class="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                <i class="fa-solid fa-plug"></i>
              </div>
              <div class="text-sm font-semibold text-slate-100">OpenAI 兼容接入</div>
              <p class="text-slate-400 leading-relaxed">可直接接入 NextChat、Chatbox、Cursor 或 OpenCode 等第三方客户端。</p>
              <div class="bg-[#090d16] border border-slate-800 rounded-lg px-3 py-2 font-mono text-[11px] text-slate-300 flex items-center justify-between gap-2">
                <span class="truncate">http://127.0.0.1:18800/v1</span>
                <button type="button" onclick="copyText('http://127.0.0.1:18800/v1')" class="text-slate-400 hover:text-sky-400 shrink-0 cursor-pointer" title="复制 Base URL">
                  <i class="fa-regular fa-copy"></i>
                </button>
              </div>
            </div>
            <div class="mt-4 pt-3 border-t border-slate-800/70 flex items-center justify-between gap-2">
              <span class="text-slate-500 font-mono text-[11px] whitespace-nowrap">API Key: 任意非空值</span>
              <button type="button" onclick="exportToOpenCode()" class="px-2.5 py-1 rounded-md bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 transition cursor-pointer whitespace-nowrap shrink-0">
                写入 OpenCode
              </button>
            </div>
          </div>
        </div>
      </section>

    </main>
  </div>

  <!-- 全局 Toast -->
  <div id="live-toast" class="hidden fixed bottom-5 right-5 z-50 bg-[#131c2e] border border-sky-500/40 text-sky-200 text-xs px-4 py-2.5 rounded-xl shadow-xl items-center gap-2"></div>

  <!-- ======================================================== -->
  <!-- 3. 全局脚本 (JavaScript)                                 -->
  <!-- ======================================================== -->
  <script>
    const VIEW_META = {
      playground: { title: "调试台", subtitle: "多平台 API 在线调试与实时流式响应预览" },
      overview:   { title: "运行概览", subtitle: "实时子服务健康状态、扩展桥接与站点登录态" },
      accounts:   { title: "账号看板", subtitle: "Google 4 账号池配额统计、健康检测与保活续期" },
      history:    { title: "对话历史", subtitle: "请求审计记录、耗时统计与完整上下文检索" },
      endpoints:  { title: "接口清单", subtitle: "Cookie Service Suite 全部 RESTful API 索引" },
      docs:       { title: "文档规范", subtitle: "OpenAPI 交互文档与 OpenAI 兼容客户端配置" },
    };

    const PLATFORM_CATEGORIES = [
      { key: "all",      name: "全部平台",           shortName: "全部",       icon: "/assets/icons/all.svg",      fallbackIcon: "fa-solid fa-shapes text-sky-400" },
      { key: "gemini",   name: "Google Gemini",      shortName: "Gemini",     icon: "/assets/icons/gemini.svg",   fallbackIcon: "fa-solid fa-sparkles text-purple-400" },
      { key: "aistudio", name: "Google AI Studio",   shortName: "AI Studio",  icon: "/assets/icons/gemini.svg",   fallbackIcon: "fa-solid fa-wand-magic-sparkles text-cyan-400" },
      { key: "gpt",      name: "ChatGPT / OpenAI",   shortName: "GPT/OpenAI", icon: "/assets/icons/chatgpt.png",  fallbackIcon: "fa-solid fa-robot text-emerald-400" },
      { key: "minimax",  name: "MiniMax 语音",       shortName: "MiniMax",    icon: null,                         fallbackIcon: "fa-solid fa-microphone-lines text-rose-400" },
      { key: "suno",     name: "Suno AI 音乐",       shortName: "Suno AI",    icon: "/assets/icons/suno.png",     fallbackIcon: "fa-solid fa-music text-amber-400" },
      { key: "baidu",    name: "百度网盘",           shortName: "百度网盘",   icon: "/assets/icons/baidupan.png", fallbackIcon: "fa-solid fa-cloud text-blue-400" },
      { key: "bilibili", name: "哔哩哔哩",           shortName: "哔哩哔哩",   icon: "/assets/icons/bilibili.png", fallbackIcon: "fa-solid fa-tv text-pink-400" },
      { key: "system",   name: "Cookie Hub & 系统",  shortName: "系统服务",   icon: "/assets/icons/system.svg",   fallbackIcon: "fa-solid fa-terminal text-sky-400" },
    ];

    let currentView = "playground";
    let currentPlaygroundCategory = "gemini";
    let currentCategory = "all";

    const MODELS_BY_PLATFORM = {
      gemini: [
        ["gemini-3.5-flash-lite", "3.5 Flash-Lite（快速解答）", false],
        ["gemini-4-hydrogen", "4 Hydrogen（日常帮助）", false],
        ["gemini-3.1-pro", "3.1 Pro（深度研究）", false],
        ["gemini-4-argon", "4 Argon（代码与分析）", false],
        ["gemini-4-carbon", "4 Carbon（高难任务 · 未开通）", true],
      ],
      aistudio: [
        ["gemini-4-argon", "gemini-4-argon (AI Studio 原生)"],
        ["gemini-3.8-flash", "gemini-3.8-flash"],
        ["gemini-3.5-flash-lite", "gemini-3.5-flash-lite"],
        ["gemini-3.1-pro-preview", "gemini-3.1-pro-preview"],
      ],
      gpt: [
        ["auto", "auto（免费 · 自动选模型）"],
        ["gpt-6", "gpt-6（免费 · Instant）"],
        ["gpt-6-t-mini", "gpt-6-t-mini（免费 · Thinking mini）"],
        ["gpt-5-6", "gpt-5-6"],
        ["gpt-image-2", "gpt-image-2 (绘图/动图)"],
        ["chatgpt-web", "chatgpt-web (网页原生)"],
      ],
    };

    const GEMINI_ID_ALIAS = {
      "gemini-3.8-flash": "gemini-4-hydrogen",
      "gemini-3.7-flash": "gemini-4-hydrogen",
      "gemini-3.6-flash": "gemini-4-hydrogen",
    };

    const REASONING_LABELS = {
      gemini: ["低 · Fast and efficient", "中 · 深度适中", "高 · 超级详尽"],
      other:  ["关闭思考 (Off · 直出)", "中等推理 (Medium · 均衡)", "深度思考 (High · 长思维链)"],
    };

    // 全量 52 个 API 端点定义
    const ALL_ENDPOINTS = [
      // Google Gemini (7)
      { id: "gemini_chat", category: "gemini", method: "POST", url: "/api/gemini/chat", name: "Gemini 智能对话", desc: "4账号 LRU 自动轮换，模型与网页选择器一致", body: { prompt: "请用一句话告诉我：量子纠缠是什么？", model: "gemini-4-hydrogen", reasoning_level: "off", stream: true, timeout: 300 } },
      { id: "gemini_accounts", category: "gemini", method: "GET", url: "/api/gemini/accounts", name: "Gemini 4账号状态与额度", desc: "查看 4 个 Google 账号状态、5小时与每周计算配额、健康度", body: null },
      { id: "gemini_sync_profiles", category: "gemini", method: "POST", url: "/api/gemini/accounts/sync-profiles", name: "同步 Google 真实昵称邮箱", desc: "向 Google 上游拉取各 authuser 对应的真实用户显示昵称与 Gmail 邮箱", body: {} },
      { id: "gemini_check", category: "gemini", method: "POST", url: "/api/gemini/accounts/1/check", name: "检测账号凭证健康度", desc: "向 Google 上游验证指定账号 (如 #1) 会话有效性并更新健康状态", body: {} },
      { id: "gemini_rotate", category: "gemini", method: "POST", url: "/api/gemini/accounts/1/rotate", name: "触发账号令牌保活续期", desc: "向 Google 申请换发最新短命会话票据，防止 Cookie 失效", body: {} },
      { id: "gemini_refresh", category: "gemini", method: "POST", url: "/api/gemini/refresh", name: "从 Cookie Hub 刷新凭证", desc: "从浏览器提取最新鉴权 Cookie 并批量写入 SQLite 数据库", body: {} },
      { id: "gemini_requests", category: "gemini", method: "GET", url: "/api/gemini/requests?limit=10", name: "请求调度轨迹历史", desc: "查看最近请求调度轨迹与各账号响应延迟历史", body: null },

      // Google AI Studio (8)
      { id: "aistudio_chat", category: "aistudio", method: "POST", url: "/api/aistudio/chat", name: "AI Studio 原生智能对话", desc: "走 Google 官方 Playground 原生通道，支持 78+ 模型与 SSE 流式输出", body: { prompt: "请用一句话告诉我：量子纠缠是什么？", model: "gemini-4-argon", stream: true, timeout: 120 } },
      { id: "aistudio_status", category: "aistudio", method: "GET", url: "/api/aistudio/status", name: "AI Studio 逆向服务状态", desc: "检测 aistudio2api 本地核心引擎 (2048)、数据面与 BotGuard 状态", body: null },
      { id: "aistudio_models", category: "aistudio", method: "GET", url: "/api/aistudio/models", name: "AI Studio 可用原生模型列表", desc: "获取原生暴露的 Google 最新大模型清单 (gemini-4-argon, gemini-3.8-flash 等)", body: null },
      { id: "aistudio_accounts", category: "aistudio", method: "GET", url: "/api/aistudio/accounts", name: "AI Studio 号池账号清单", desc: "查看当前绑定的 Google AI Studio 账号列表及健康度", body: null },
      { id: "aistudio_sync", category: "aistudio", method: "POST", url: "/api/aistudio/sync-cookies", name: "从 Cookie Hub 一键同步入池", desc: "从浏览器 Cookie Hub 自动提取 google.com Cookie 并载入 AI Studio 号池", body: {} },
      { id: "aistudio_start", category: "aistudio", method: "POST", url: "/api/aistudio/start", name: "启动 AI Studio 独立逆向", desc: "启动本地 aistudio2api 无头服务并激活数据面", body: {} },
      { id: "aistudio_stop", category: "aistudio", method: "POST", url: "/api/aistudio/stop", name: "停止 AI Studio 逆向服务", desc: "优雅停止本地 aistudio2api 进程与数据面", body: {} },
      { id: "aistudio_restart", category: "aistudio", method: "POST", url: "/api/aistudio/restart", name: "重启 AI Studio 逆向服务", desc: "重启核心进程并重载 BotGuard 与账号池", body: {} },

      // OpenAI 兼容 (3)
      { id: "openai_chat", category: "openai", method: "POST", url: "/v1/chat/completions", name: "OpenAI 兼容聊天接口", desc: "无缝对接 NextChat、Chatbox、Cursor，底层分流 Gemini 与 ChatGPT", body: { model: "gemini-3.5-flash-lite", messages: [{ role: "user", content: "请用一句话告诉我：量子纠缠是什么？" }], reasoning_level: "off", stream: true } },
      { id: "openai_image", category: "openai", method: "POST", url: "/v1/images/generations", name: "OpenAI 兼容生图接口", desc: "标准 POST /v1/images/generations，底层路由至 gpt-image-2 / DALL-E 3", body: { prompt: "一只可爱的赛博朋克发光小猫，超高清，8k壁纸", model: "gpt-image-2", n: 1, response_format: "b64_json" } },
      { id: "openai_models", category: "openai", method: "GET", url: "/v1/models", name: "OpenAI 兼容模型列表", desc: "动态聚合逆向模型、页面模拟与谷歌号池所有可用模型", body: null },

      // ChatGPT 逆向 (9)
      { id: "chatgpt_chat", category: "chatgpt", method: "POST", url: "/api/chatgpt/chat", name: "ChatGPT 智能问答", desc: "支持逆向引擎直连与浏览器同源扩展双通道", body: { prompt: "请用幽默风趣的一句话自我介绍！", model: "auto", stream: true } },
      { id: "chatgpt_image", category: "chatgpt", method: "POST", url: "/api/chatgpt/image", name: "ChatGPT 逆向图片/GIF生成", desc: "基于官方逆向生成高质量图片或代码解释器生成的动图", body: { prompt: "一只戴着宇航头盔的橙色猫咪在火星漫步，水彩插画", model: "gpt-image-2", n: 1, response_format: "b64_json" } },
      { id: "chatgpt_status", category: "chatgpt", method: "GET", url: "/api/chatgpt/status", name: "ChatGPT 服务状态", desc: "检测逆向端口 (18084)、健康度与浏览器桥接状态", body: null },
      { id: "chatgpt_models", category: "chatgpt", method: "GET", url: "/api/chatgpt/models", name: "ChatGPT 可用模型列表", desc: "拉取逆向暴露或支持的模型 (auto, gpt-6, gpt-image-2 等)", body: null },
      { id: "chatgpt_accounts", category: "chatgpt", method: "GET", url: "/api/chatgpt/accounts", name: "ChatGPT 号池账号列表", desc: "查看已导入逆向引擎的账号列表、额度与健康状态", body: null },
      { id: "chatgpt_sync", category: "chatgpt", method: "POST", url: "/api/chatgpt/accounts/sync-browser", name: "浏览器 Token 一键同步入池", desc: "从浏览器提取 chatgpt.com 当前会话 Access Token 并载入逆向号池", body: {} },
      { id: "chatgpt_session", category: "chatgpt", method: "GET", url: "/api/chatgpt/session", name: "提取当前登录会话", desc: "提取当前 ChatGPT 标签页登录用户与 Access Token", body: null },
      { id: "chatgpt_start", category: "chatgpt", method: "POST", url: "/api/chatgpt/start", name: "启动独立逆向后台", desc: "手动按需启动基于 chatgpt2api 的独立无头逆向进程 (18084)", body: {} },
      { id: "chatgpt_stop", category: "chatgpt", method: "POST", url: "/api/chatgpt/stop", name: "停止独立逆向后台", desc: "停止 ChatGPT 独立无头逆向进程", body: {} },

      // Suno AI (7)
      { id: "suno_quota", category: "suno", method: "GET", url: "/api/suno/quota", name: "Suno AI 积分与可用曲目", desc: "查询 Suno 账号剩余积分及本月可用生成曲目数", body: null },
      { id: "suno_feed", category: "suno", method: "GET", url: "/api/suno/feed?page=1", name: "Suno AI 历史创作作品库", desc: "拉取已生成的音乐曲目、封面、歌词与音频直链", body: null },
      { id: "suno_gen", category: "suno", method: "POST", url: "/api/suno/generate", name: "Suno AI 提交音乐生成任务", desc: "根据描述词生成两首完整人声/器乐歌曲 (支持自定义模式)", body: { prompt: "一段欢快阳光的夏日流行海滩音乐，带有原声吉他和轻快的鼓点", is_custom: false, model: "chirp-goose", wait: false } },
      { id: "suno_audio", category: "suno", method: "GET", url: "/api/suno/audio/f42ad222-213f-4e8b-a7b1-dbc23455d1eb", name: "Suno AI 解密流式试听", desc: "自动解密 Suno 渐进流并直接在浏览器在线播放无损 M4A", body: null },
      { id: "suno_status", category: "suno", method: "GET", url: "/api/suno/status?clip_ids=f42ad222-213f-4e8b-a7b1-dbc23455d1eb", name: "Suno AI 任务状态轮询", desc: "查询任务渲染进度与本地解密流式播放直链", body: null },
      { id: "suno_lyrics", category: "suno", method: "POST", url: "/api/suno/lyrics", name: "Suno AI 独立歌词创作", desc: "输入主题生成结构完整的双节押韵歌词", body: { prompt: "写一首关于秋天落叶与思念的流行歌词" } },
      { id: "suno_refresh", category: "suno", method: "POST", url: "/api/suno/refresh", name: "Suno AI 刷新鉴权凭证", desc: "强制刷新 Suno 会话凭证与 Clerk JWT 令牌", body: {} },

      // MiniMax 语音 (6)
      { id: "minimax_speech", category: "minimax", method: "POST", url: "/api/minimax/speech", name: "MiniMax 语音合成", desc: "高保真拟真声音合成，支持语速/音量/音高调节并直出音频试听", body: { text: "你好！这是来自 MiniMax 海螺语音超自然 TTS 的实时合成试听。", voice_id: "226869000163456", speed: 1.0, vol: 1.0, pitch: 0.0, format: "mp3" } },
      { id: "openai_speech", category: "minimax", method: "POST", url: "/v1/audio/speech", name: "OpenAI 兼容语音合成接口", desc: "标准 POST /v1/audio/speech，支持 alloy, nova, onyx, shimmer, fable, echo 音色", body: { model: "speech-01-hd", input: "Today is a beautiful day to build something remarkable.", voice: "alloy", speed: 1.0, response_format: "mp3" } },
      { id: "minimax_voices", category: "minimax", method: "GET", url: "/api/minimax/voices", name: "MiniMax 可选音色列表", desc: "获取预置与可选音色列表", body: null },
      { id: "minimax_quota", category: "minimax", method: "GET", url: "/api/minimax/quota", name: "MiniMax 配额与字符余量", desc: "查询 MiniMax / 海螺语音平台当前账户剩余可用字符与积分", body: null },
      { id: "minimax_status", category: "minimax", method: "GET", url: "/api/minimax/status", name: "MiniMax 会话状态与Token", desc: "检查本地缓存 Token、设备指纹与扩展桥接就绪状态", body: null },
      { id: "minimax_auto_fetch", category: "minimax", method: "POST", url: "/api/minimax/auto_fetch?force=true", name: "从浏览器刷新 MiniMax 凭证", desc: "通知 Cookie Hub 扩展后台访问并自动提取最新 Token", body: {} },

      // 百度网盘 (4)
      { id: "baidu_quota", category: "baidu", method: "GET", url: "/api/baidupan/quota", name: "百度网盘 存储容量与配额", desc: "获取已用空间、总空间与 VIP 配额详情", body: null },
      { id: "baidu_user", category: "baidu", method: "GET", url: "/api/baidupan/user", name: "百度网盘 用户账号资料", desc: "获取百度网盘用户名、头像与 VIP 等级", body: null },
      { id: "baidu_files", category: "baidu", method: "GET", url: "/api/baidupan/files?dir_path=/", name: "百度网盘 目录文件遍历", desc: "遍历网盘根目录 / 或指定子目录下的文件清单", body: null },
      { id: "baidu_refresh", category: "baidu", method: "POST", url: "/api/baidupan/refresh", name: "百度网盘 刷新鉴权凭证", desc: "从浏览器 Cookie Hub 强制同步最新百度网盘登录凭证", body: {} },

      // 哔哩哔哩 (2)
      { id: "bili_user", category: "bilibili", method: "GET", url: "/api/bilibili/user", name: "B站 登录用户信息与资产", desc: "查看当前 B 站登录用户资料、硬币、B币与大会员有效期", body: null },
      { id: "bili_video", category: "bilibili", method: "GET", url: "/api/bilibili/video?bvid=BV1GJ411x7h7", name: "B站 视频信息与特权流", desc: "查询视频元数据与大会员专属 4K/1080P60 播放直链", body: null },

      // Cookie Hub & 系统管理 (6)
      { id: "system_overview", category: "system", method: "GET", url: "/api/system/overview", name: "系统全局运行总览", desc: "查看 Cookie Hub、Gemini 池、ChatGPT 与开机自启动全景状态", body: null },
      { id: "system_open_dir", category: "system", method: "POST", url: "/api/system/open-directory", name: "打开项目本地目录", desc: "在 Windows 资源管理器中弹出打开套件根目录文件夹", body: {} },
      { id: "system_autostart_get", category: "system", method: "GET", url: "/api/system/autostart", name: "查询 Windows 开机自启状态", desc: "检查注册表 Run 与开始菜单 Startup 双重持久化配置", body: null },
      { id: "system_autostart_toggle", category: "system", method: "POST", url: "/api/system/autostart/toggle", name: "一键切换开机自启动", desc: "在开启与关闭之间一键切换", body: {} },
      { id: "hub_status", category: "system", method: "GET", url: "/api/hub/status", name: "Cookie Hub 扩展桥状态", desc: "检测 Chrome/Edge 扩展与本地 Node 服务长连接", body: null },
      { id: "hub_cookies", category: "system", method: "GET", url: "/api/hub/cookies?domain=google.com", name: "按域名动态提取 Cookie", desc: "从浏览器实时提取指定域名 (如 google.com) 的 Cookie 字典与 Header", body: null },
    ];

    // ==========================================
    // 视图切换与响应式侧边栏
    // ==========================================
    function toggleMobileSidebar(open) {
      const sidebar = document.getElementById("app-sidebar");
      const backdrop = document.getElementById("mobile-backdrop");
      if (!sidebar || !backdrop) return;
      if (open) {
        sidebar.classList.remove("-translate-x-full");
        backdrop.classList.remove("hidden");
      } else {
        sidebar.classList.add("-translate-x-full");
        backdrop.classList.add("hidden");
      }
    }

    function switchView(viewKey, updateHash = true) {
      if (!VIEW_META[viewKey]) viewKey = "playground";
      currentView = viewKey;

      document.querySelectorAll(".view-section").forEach(sec => {
        sec.classList.toggle("active", sec.id === `view-${viewKey}`);
      });

      document.querySelectorAll("#sidebar-nav .nav-item").forEach(btn => {
        const isActive = btn.getAttribute("data-view") === viewKey;
        btn.classList.toggle("nav-item-active", isActive);
        const icon = btn.querySelector("i");
        if (icon) {
          icon.classList.toggle("text-sky-400", isActive);
          icon.classList.toggle("text-slate-400", !isActive);
        }
      });

      const meta = VIEW_META[viewKey];
      const titleEl = document.getElementById("topbar-title");
      const subEl = document.getElementById("topbar-subtitle");
      if (titleEl) titleEl.innerText = meta.title;
      if (subEl) subEl.innerText = meta.subtitle;

      if (updateHash && window.location.hash !== `#${viewKey}`) {
        history.replaceState(null, "", `#${viewKey}`);
      }

      if (window.innerWidth < 1024) {
        toggleMobileSidebar(false);
      }
    }

    // ==========================================
    // 平台与模型联动逻辑
    // ==========================================
    function endpointMatchesPlatform(ep, platformKey) {
      if (platformKey === "all") return true;
      if (platformKey === "gpt") return ep.category === "chatgpt" || ep.category === "openai";
      if (platformKey === "ecosystem") return ["bilibili", "baidu", "suno"].includes(ep.category);
      return ep.category === platformKey;
    }

    function getPlatformKeyForEndpoint(ep) {
      if (ep.category === "chatgpt" || ep.category === "openai") return "gpt";
      return ep.category || "all";
    }

    function geminiBaseId(id) {
      const raw = String(id || "").replace(/-thinking-medium$/, "").replace(/-thinking$/, "");
      return GEMINI_ID_ALIAS[raw] || raw;
    }

    function applyGeminiModelCatalog(models) {
      const rows = [];
      models.forEach(item => {
        if (!item) return;
        if (typeof item === "string") {
          rows.push([item, item, false]);
          return;
        }
        if (!item.id || /-thinking/.test(item.id)) return;
        rows.push([item.id, item.label || item.id, !!item.locked]);
      });
      if (!rows.length) return;
      MODELS_BY_PLATFORM.gemini = rows;
    }

    function syncReasoningLabels(platformKey) {
      const el = document.getElementById("reasoning-selector");
      if (!el) return;
      const texts = platformKey === "gemini" ? REASONING_LABELS.gemini : REASONING_LABELS.other;
      ["off", "medium", "high"].forEach((value, index) => {
        const opt = el.querySelector(`option[value="${value}"]`);
        if (opt) opt.textContent = texts[index];
      });
    }

    async function refreshGeminiModelCatalog() {
      try {
        const res = await fetch("/api/gemini/models");
        const data = await res.json();
        const models = data.models || [];
        if (!models.length) return;
        const current = document.getElementById("model-selector");
        const before = current ? current.value : "";
        applyGeminiModelCatalog(models);
        if (currentPlaygroundCategory === "gemini") {
          populateModelSelector("gemini", before || "gemini-4-hydrogen");
          const after = document.getElementById("model-selector");
          if (after && before && after.value !== geminiBaseId(before)) onModelOrReasoningChange();
        }
      } catch (e) {}
    }

    function resolveGeminiModel(baseModel, reasoning) {
      const raw = geminiBaseId(baseModel);
      if (raw === "gemini-4-carbon") return raw;
      if (reasoning === "high") return raw + "-thinking";
      if (reasoning === "medium" && raw === "gemini-4-argon") return raw + "-thinking-medium";
      return raw;
    }

    function populateModelSelector(platformKey, preferred) {
      const select = document.getElementById("model-selector");
      const models = MODELS_BY_PLATFORM[platformKey];
      if (!select || !models) return;
      select.innerHTML = models.map(([value, label, locked]) => {
        const disabled = locked ? " disabled" : "";
        return `<option value="${value}"${disabled}>${label}</option>`;
      }).join("");
      let want = preferred || "";
      if (platformKey === "gemini") want = geminiBaseId(want);
      const enabled = models.filter(([, , locked]) => !locked);
      const matched = enabled.some(([value]) => value === want);
      const fallback = (enabled[0] && enabled[0][0]) || models[0][0];
      const hydrogen = enabled.some(([value]) => value === "gemini-4-hydrogen");
      select.value = matched ? want : (platformKey === "gemini" && hydrogen && !preferred ? "gemini-4-hydrogen" : fallback);
      syncReasoningLabels(platformKey);
    }

    function handlePlatformIconError(imgEl, fallbackClass) {
      if (!imgEl || !imgEl.parentNode) return;
      const icon = document.createElement("i");
      icon.className = fallbackClass + " text-xs";
      imgEl.replaceWith(icon);
    }

    function renderPlaygroundCategoryNav() {
      const nav = document.getElementById("playground-category-nav");
      if (!nav) return;

      nav.innerHTML = PLATFORM_CATEGORIES.map(cat => {
        const isActive = cat.key === currentPlaygroundCategory;
        const count = ALL_ENDPOINTS.filter(ep => endpointMatchesPlatform(ep, cat.key)).length;
        const iconHtml = cat.icon
          ? `<img src="${cat.icon}" alt="${cat.shortName}" class="w-4 h-4 object-contain shrink-0" data-fallback="${cat.fallbackIcon}" onerror="handlePlatformIconError(this, this.dataset.fallback)">`
          : `<i class="${cat.fallbackIcon} text-xs"></i>`;
        return `
          <button type="button" onclick="setPlaygroundCategory('${cat.key}', true)"
                  id="plat-tab-${cat.key}"
                  class="plat-pill shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs ${isActive ? "plat-pill-active" : "text-slate-300"}">
            ${iconHtml}
            <span>${cat.shortName}</span>
            <span class="text-[10px] font-mono ${isActive ? "text-sky-300" : "text-slate-500"}">${count}</span>
          </button>
        `;
      }).join("");
    }

    function setPlaygroundCategory(catKey, autoSelect = true) {
      currentPlaygroundCategory = catKey;
      renderPlaygroundCategoryNav();
      populateModelSelector(catKey);
      if (catKey === "gemini") refreshGeminiModelCatalog();
      const filtered = populateApiSelector(catKey);
      if (autoSelect && filtered && filtered.length > 0) {
        loadEndpoint(filtered[0].id, false, false);
      }
    }

    function populateApiSelector(catKey) {
      const selector = document.getElementById("api-selector");
      if (!selector) return [];

      const filtered = ALL_ENDPOINTS.filter(ep => endpointMatchesPlatform(ep, catKey));
      if (catKey === "all") {
        let html = "";
        const groups = [
          { label: "Google Gemini", key: "gemini" },
          { label: "Google AI Studio", key: "aistudio" },
          { label: "OpenAI 兼容", key: "openai" },
          { label: "ChatGPT 逆向", key: "chatgpt" },
          { label: "MiniMax 语音", key: "minimax" },
          { label: "Suno AI 音乐", key: "suno" },
          { label: "百度网盘", key: "baidu" },
          { label: "哔哩哔哩", key: "bilibili" },
          { label: "Cookie Hub & 系统", key: "system" },
        ];
        groups.forEach(g => {
          const gEps = ALL_ENDPOINTS.filter(e => e.category === g.key);
          if (gEps.length > 0) {
            html += `<optgroup label="${g.label}">`;
            gEps.forEach(e => {
              html += `<option value="${e.id}">[${e.method}] ${e.name} (${e.url})</option>`;
            });
            html += `</optgroup>`;
          }
        });
        selector.innerHTML = html;
      } else {
        selector.innerHTML = filtered.map(e => {
          return `<option value="${e.id}">[${e.method}] ${e.name} (${e.url})</option>`;
        }).join("");
      }
      return filtered;
    }

    // ==========================================
    // 接口清单渲染与搜索
    // ==========================================
    function renderEndpointCategoryTabs() {
      const container = document.getElementById("category-tabs");
      if (!container) return;
      const tabs = [
        { key: "all",      label: "全部" },
        { key: "gemini",   label: "Google Gemini" },
        { key: "aistudio", label: "Google AI Studio" },
        { key: "openai",   label: "OpenAI 兼容" },
        { key: "chatgpt",  label: "ChatGPT 逆向" },
        { key: "minimax",  label: "MiniMax 语音" },
        { key: "suno",     label: "Suno AI" },
        { key: "baidu",    label: "百度网盘" },
        { key: "bilibili", label: "哔哩哔哩" },
        { key: "system",   label: "系统 & Cookie Hub" },
      ];

      container.innerHTML = tabs.map(t => {
        const cnt = t.key === "all"
          ? ALL_ENDPOINTS.length
          : ALL_ENDPOINTS.filter(ep => ep.category === t.key).length;
        const active = currentCategory === t.key;
        return `
          <button type="button" onclick="setCategoryFilter('${t.key}')" data-cat="${t.key}"
                  class="category-tab px-2.5 py-1 rounded-lg text-xs font-medium border transition cursor-pointer ${active ? "tab-active" : "border-slate-800 bg-[#090d16] text-slate-400 hover:text-slate-200 hover:border-slate-700"}">
            ${t.label} <span class="font-mono text-[10px] opacity-75 ml-0.5">${cnt}</span>
          </button>
        `;
      }).join("");
    }

    function renderEndpointsList() {
      const grid = document.getElementById("endpoints-grid");
      if (!grid) return;
      const searchKeyword = (document.getElementById("api-search-input")?.value || "").trim().toLowerCase();

      const filtered = ALL_ENDPOINTS.filter(ep => {
        const matchesCat = currentCategory === "all" || ep.category === currentCategory;
        if (!matchesCat) return false;
        if (!searchKeyword) return true;
        return ep.url.toLowerCase().includes(searchKeyword) ||
               ep.name.toLowerCase().includes(searchKeyword) ||
               ep.desc.toLowerCase().includes(searchKeyword) ||
               ep.method.toLowerCase().includes(searchKeyword);
      });

      const badge = document.getElementById("endpoints-count-badge");
      if (badge) badge.innerText = `${filtered.length} / ${ALL_ENDPOINTS.length}`;
      const navCount = document.getElementById("nav-endpoints-count");
      if (navCount) navCount.innerText = String(ALL_ENDPOINTS.length);

      if (filtered.length === 0) {
        grid.innerHTML = `<div class="col-span-full py-10 text-center text-slate-500 text-xs">未找到匹配的 API 端点</div>`;
        return;
      }

      grid.innerHTML = filtered.map(ep => {
        const isPost = ep.method === "POST";
        const methodBadgeClass = isPost
          ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
          : "bg-sky-500/15 text-sky-300 border-sky-500/30";

        return `
          <div class="bg-[#090d16] p-3.5 rounded-xl border border-slate-800/90 hover:border-slate-700 transition flex flex-col justify-between gap-2.5">
            <div>
              <div class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-2 min-w-0">
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-bold border font-mono shrink-0 ${methodBadgeClass}">${ep.method}</span>
                  <span class="font-medium text-xs text-slate-200 truncate">${ep.name}</span>
                </div>
                <button type="button" onclick="copyText('${ep.url}')" class="text-slate-500 hover:text-slate-200 text-xs p-1 cursor-pointer shrink-0" title="复制路径">
                  <i class="fa-regular fa-copy"></i>
                </button>
              </div>
              <div class="mt-1.5 font-mono text-[11px] text-sky-300/90 break-all select-all">${ep.url}</div>
              <div class="mt-1 text-[11px] text-slate-400 line-clamp-2">${ep.desc}</div>
            </div>
            <div class="flex items-center justify-end gap-2 pt-2 border-t border-slate-800/60">
              <button type="button" onclick="loadEndpoint('${ep.id}', false, true)" class="px-2.5 py-1 rounded-md text-[11px] bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-1 cursor-pointer">
                <i class="fa-solid fa-code text-sky-400"></i> 填入调试
              </button>
              <button type="button" onclick="loadEndpoint('${ep.id}', true, true)" class="px-2.5 py-1 rounded-md text-[11px] bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 transition flex items-center gap-1 font-medium cursor-pointer">
                <i class="fa-solid fa-play text-[10px]"></i> 立即测试
              </button>
            </div>
          </div>
        `;
      }).join("");
    }

    function setCategoryFilter(cat) {
      currentCategory = cat;
      renderEndpointCategoryTabs();
      renderEndpointsList();
    }

    function filterEndpoints() {
      renderEndpointsList();
    }

    // ==========================================
    // 剪贴板与通知工具 (分离避免冲突)
    // ==========================================
    function copyText(text, btn) {
      navigator.clipboard.writeText(text).then(() => {
        if (btn) {
          const oldHtml = btn.innerHTML;
          btn.innerHTML = "已复制";
          setTimeout(() => { btn.innerHTML = oldHtml; }, 1400);
        }
        showToast("已复制: " + (text.length > 48 ? text.slice(0, 48) + "..." : text));
      }).catch(() => {});
    }

    function copyElementText(targetKey, btn) {
      const targetEl = document.getElementById(`copy-target-${targetKey}`);
      if (!targetEl) return;
      copyText(targetEl.innerText, btn);
    }

    let toastTimerId = null;
    function showToast(msg) {
      const toast = document.getElementById("live-toast");
      if (!toast) return;
      toast.innerHTML = `<i class="fa-solid fa-circle-check text-sky-400"></i> <span>${escapeHtml(msg)}</span>`;
      toast.classList.remove("hidden");
      toast.classList.add("flex");
      if (toastTimerId) clearTimeout(toastTimerId);
      toastTimerId = setTimeout(() => {
        toast.classList.add("hidden");
        toast.classList.remove("flex");
      }, 2600);
    }

    // ==========================================
    // 调试台逻辑
    // ==========================================
    function loadEndpoint(endpointId, autoRun = false, switchToPlayground = false) {
      const ep = ALL_ENDPOINTS.find(e => e.id === endpointId);
      if (!ep) return;

      if (switchToPlayground && currentView !== "playground") {
        switchView("playground");
      }

      const epPlat = getPlatformKeyForEndpoint(ep);
      if (currentPlaygroundCategory !== "all" && currentPlaygroundCategory !== epPlat) {
        setPlaygroundCategory(epPlat, false);
      } else if (!document.getElementById("api-selector").options.length) {
        populateApiSelector(currentPlaygroundCategory);
      }

      const selector = document.getElementById("api-selector");
      if (selector) selector.value = ep.id;

      const methodBadge = document.getElementById("req-method-badge");
      methodBadge.innerText = ep.method;
      methodBadge.className = ep.method === "POST"
        ? "h-9 px-3 rounded-lg text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono flex items-center shrink-0"
        : "h-9 px-3 rounded-lg text-xs font-bold bg-sky-500/15 text-sky-300 border border-sky-500/30 font-mono flex items-center shrink-0";

      document.getElementById("req-endpoint").value = ep.url;

      const bodyContainer = document.getElementById("req-body-container");
      const getEmpty = document.getElementById("get-body-empty");
      const paramsBar = document.getElementById("playground-params-bar");
      const modelContainer = document.getElementById("model-select-container");
      const reasoningContainer = document.getElementById("reasoning-level-container");
      const presetContainer = document.getElementById("ai-preset-container");
      const streamContainer = document.getElementById("stream-toggle-container");
      const btnFormat = document.getElementById("btn-format-json");
      const btnReset = document.getElementById("btn-reset-json");

      if (ep.method === "GET") {
        bodyContainer.classList.add("hidden");
        getEmpty.classList.remove("hidden");
        paramsBar.classList.add("hidden");
        if (btnFormat) btnFormat.classList.add("hidden");
        if (btnReset) btnReset.classList.add("hidden");
      } else {
        bodyContainer.classList.remove("hidden");
        getEmpty.classList.add("hidden");
        if (btnFormat) btnFormat.classList.remove("hidden");
        if (btnReset) btnReset.classList.remove("hidden");

        const bodyStr = ep.body ? JSON.stringify(ep.body, null, 2) : "{}";
        document.getElementById("req-body").value = bodyStr;

        const isChatEndpoint = ["gemini_chat", "aistudio_chat", "openai_chat", "chatgpt_chat"].includes(ep.id);
        const hasPrompt = ep.body && (ep.body.prompt !== undefined || ep.body.messages !== undefined);

        if (isChatEndpoint || hasPrompt) {
          paramsBar.classList.remove("hidden");
        } else {
          paramsBar.classList.add("hidden");
        }

        if (presetContainer) presetContainer.classList.toggle("hidden", !hasPrompt);

        if (isChatEndpoint) {
          if (modelContainer) modelContainer.classList.remove("hidden");
          if (reasoningContainer) reasoningContainer.classList.toggle("hidden", epPlat === "aistudio");
          if (streamContainer) streamContainer.classList.remove("hidden");

          let preferredModel = "";
          try { preferredModel = JSON.parse(bodyStr).model || ""; } catch (e) {}
          if (epPlat === "gemini" && preferredModel) {
            const reasoningEl = document.getElementById("reasoning-selector");
            if (reasoningEl) {
              if (/-thinking-medium$/.test(preferredModel)) reasoningEl.value = "medium";
              else if (/-thinking$/.test(preferredModel)) reasoningEl.value = "high";
              else reasoningEl.value = "off";
            }
          }
          populateModelSelector(epPlat, preferredModel);
          if (preferredModel && document.getElementById("model-selector").value !== preferredModel) {
            onModelOrReasoningChange();
          }
          const streamToggle = document.getElementById("stream-toggle");
          if (streamToggle) {
            try {
              const parsed = JSON.parse(bodyStr);
              if (parsed && typeof parsed.stream === "boolean") {
                streamToggle.checked = parsed.stream;
                updateStreamToggleLabel(parsed.stream);
              }
            } catch (e) {}
          }
        } else {
          if (modelContainer) modelContainer.classList.add("hidden");
          if (reasoningContainer) reasoningContainer.classList.add("hidden");
          if (streamContainer) streamContainer.classList.add("hidden");
        }
      }

      if (autoRun) {
        setTimeout(() => { executeApiCall(); }, 120);
      }
    }

    function updateStreamToggleLabel(isStream) {
      const toggleText = document.getElementById("stream-toggle-text");
      if (!toggleText) return;
      toggleText.innerText = isStream ? "开启" : "关闭";
      toggleText.className = isStream ? "ml-2 text-[11px] font-mono text-sky-400" : "ml-2 text-[11px] font-mono text-slate-500";
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
          targetModel = resolveGeminiModel(baseModel, reasoning);
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
      updateStreamToggleLabel(isStream);
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
      loadEndpoint(key, false, false);
    }

    function formatRequestJson() {
      const bodyEl = document.getElementById("req-body");
      if (!bodyEl || !bodyEl.value.trim()) return;
      try {
        const obj = JSON.parse(bodyEl.value);
        bodyEl.value = JSON.stringify(obj, null, 2);
        showToast("JSON 已格式化");
      } catch (e) {
        showToast("JSON 格式有误: " + e.message);
      }
    }

    const AI_PRESETS_MAP = {
      quantum: "请用一句话告诉我：量子纠缠是什么？",
      python_async: "用 Python 编写一个高性能并发异步下载器，带连接池、超时自愈重试与流式进度展示",
      translation: "请将以下技术段落进行中英专业学术级双向互译，保持术语严谨准确并给出语法对照解析：\n\n'Modern distributed consensus systems rely on replicated state machines to guarantee safety under network partitions.'",
      raft_paxos: "详细对比分布式架构下 Raft 与 Paxos 一致性算法的优缺点、工程选型考量与极端网络分区脑裂下的自愈恢复机制",
      marketing: "为一款主打轻量敏捷与 Google 多账号智能 LRU 自动分流的 Cookie Service Suite 开发者工具撰写一段极具吸引力的小红书/推特爆款推介文案，突出秒出首字与稳定自愈特性",
      cyberpunk_cat: "一只可爱的赛博朋克霓虹发光机械猫咪在雨夜未来街道漫步，8K超高清，虚幻5电影级光影质感",
      suno_music: "一段欢快阳光的夏日流行海滩音乐，带有原声吉他和轻快的鼓点",
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
        showToast("已应用预设提示词");
      } catch (e) {
        console.error("更新预设提示词失败:", e);
      }
    }

    function formatHumanDuration(ms) {
      if (ms === null || ms === undefined || isNaN(ms)) return "0s";
      const sec = ms / 1000;
      if (sec < 60) {
        return sec < 1 ? (sec.toFixed(2) + "s") : (sec.toFixed(1) + "s");
      }
      return (sec / 60).toFixed(1) + "min";
    }

    let cooldownTimerId = null;

    async function forceResetCooldown() {
      if (cooldownTimerId) {
        clearInterval(cooldownTimerId);
        cooldownTimerId = null;
      }
      try {
        const res = await fetch("/api/gemini/reset-pace", { method: "POST" });
        const d = await res.json();
        showToast(d.message || "已强制解除 Gemini 频率与并发保护锁");
      } catch (e) {
        showToast("解除请求发送失败: " + e.message);
      }
      const btn = document.getElementById("btn-send");
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> <span>发送请求</span>`;
      const statusSpan = document.getElementById("resp-status");
      statusSpan.innerText = "已解锁";
      statusSpan.className = "text-[11px] px-2 py-0.5 rounded font-mono bg-emerald-500/15 text-emerald-400";
    }

    function startCooldownTimer(seconds) {
      if (cooldownTimerId) clearInterval(cooldownTimerId);
      const btn = document.getElementById("btn-send");
      const statusSpan = document.getElementById("resp-status");
      let remain = Math.max(1, parseInt(seconds) || 12);

      btn.disabled = false;

      function tick() {
        if (remain <= 0) {
          clearInterval(cooldownTimerId);
          cooldownTimerId = null;
          btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> <span>发送请求</span>`;
          statusSpan.innerText = "可重新调用";
          statusSpan.className = "text-[11px] px-2 py-0.5 rounded font-mono bg-emerald-500/15 text-emerald-400";
          return;
        }
        btn.innerHTML = `<i class="fa-solid fa-hourglass-half fa-spin"></i> <span>冷却 ${remain}s (点击解锁)</span>`;
        statusSpan.innerText = `等待 ${remain}s`;
        statusSpan.className = "text-[11px] px-2 py-0.5 rounded font-mono bg-amber-500/15 text-amber-300";
        remain--;
      }

      tick();
      cooldownTimerId = setInterval(tick, 1000);
    }

    function clearResponseOutput() {
      document.getElementById("resp-output").innerText = "输出已清空，等待下一次请求...";
      document.getElementById("resp-status").classList.add("hidden");
      document.getElementById("resp-time").innerText = "耗时: 0s";
      document.getElementById("image-preview-card").classList.add("hidden");
      document.getElementById("audio-preview-card").classList.add("hidden");
    }

    async function executeApiCall() {
      if (cooldownTimerId) {
        await forceResetCooldown();
        return;
      }
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

      let detectedCooldownSeconds = 0;

      imgCard.classList.add("hidden");
      if (audioCard) audioCard.classList.add("hidden");
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>调用中...</span>`;
      out.innerText = "请求发送中，等待响应...";

      const t0 = performance.now();
      try {
        const opts = { method: method, headers: { "Content-Type": "application/json" } };
        if (method === "POST") {
          opts.body = document.getElementById("req-body").value;
        }
        const resp = await fetch(endpoint, opts);
        const took = Math.round(performance.now() - t0);
        timeSpan.innerText = `耗时: ${formatHumanDuration(took)}`;
        statusSpan.classList.remove("hidden");
        statusSpan.innerText = `${resp.status} ${resp.statusText}`;
        statusSpan.className = resp.ok
          ? "text-[11px] px-2 py-0.5 rounded font-mono bg-emerald-500/15 text-emerald-400"
          : "text-[11px] px-2 py-0.5 rounded font-mono bg-rose-500/15 text-rose-400";

        const contentType = resp.headers.get("content-type") || "";

        if (contentType.includes("text/event-stream") && resp.body) {
          statusSpan.innerText = `${resp.status} Streaming`;
          statusSpan.className = "text-[11px] px-2 py-0.5 rounded font-mono bg-sky-500/15 text-sky-400";
          out.innerText = "";

          const reader = resp.body.getReader();
          const decoder = new TextDecoder("utf-8");
          let streamDone = false;
          let streamFailed = false;
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
                timeSpan.innerText = `首字: ${formatHumanDuration(firstTokenTime)} · 流式输出中`;
              }
              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split("\n");
              buffer = lines.pop();

              for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || trimmed.startsWith("event:")) continue;
                if (trimmed.startsWith("data:")) {
                  const payload = trimmed.substring(5).trim();
                  if (payload === "[DONE]") {
                    streamDone = true;
                    try { await reader.cancel(); } catch (e) {}
                    break;
                  }
                  try {
                    const parsed = JSON.parse(payload);
                    if (parsed.error) {
                      const errObj = typeof parsed.error === "string" ? null : parsed.error;
                      const errMsg = typeof parsed.error === "string" ? parsed.error : (parsed.error.message || JSON.stringify(parsed.error));
                      const needs = ((errObj && errObj.needs_login) || []).map(item => item && item.name).filter(Boolean);
                      let retryAfter = errObj && errObj.retry_after;
                      let lastFailReason = errObj && errObj.last_failure_reason;
                      if (!retryAfter) {
                        const m = errMsg.match(/(?:倒计时|等待|还剩)\s*(\d+)\s*秒/);
                        if (m) retryAfter = parseInt(m[1]);
                      }
                      if (!lastFailReason) {
                        const mFail = errMsg.match(/【上次失败原因:\s*(.+?)】/);
                        if (mFail) lastFailReason = mFail[1];
                      }
                      if (retryAfter) detectedCooldownSeconds = retryAfter;
                      streamError = errMsg;
                      streamFailed = true;
                      fullText += "\n[流式异常] " + errMsg;
                      if (lastFailReason && !errMsg.includes(lastFailReason)) {
                        fullText += "\n[上次失败原因] " + lastFailReason;
                      }
                      if (retryAfter) {
                        fullText += `\n[保护倒计时] 需等待 ${retryAfter} 秒，可点击发送按钮立即强制解锁。`;
                      }
                      if (needs.length) fullText += " 请登录：" + needs.join("、") + "。";
                      fullText += "\n";
                      out.innerText = fullText;
                      out.scrollTop = out.scrollHeight;
                      statusSpan.innerText = retryAfter ? `等待 ${retryAfter}s` : "失败";
                      statusSpan.className = "text-[11px] px-2 py-0.5 rounded font-mono bg-rose-500/15 text-rose-400";
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
                      // 正常结束块
                    } else if (!parsed.choices) {
                      fullText += payload + "\n";
                      out.innerText = fullText;
                      out.scrollTop = out.scrollHeight;
                    }
                  } catch (e) {
                    fullText += payload + "\n";
                    out.innerText = fullText;
                    out.scrollTop = out.scrollHeight;
                  }
                } else if (trimmed) {
                  fullText += trimmed + "\n";
                  out.innerText = fullText;
                  out.scrollTop = out.scrollHeight;
                }
              }
            }
          }

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
                    fullText += "\n[流式异常] " + errMsg + "\n";
                  } else {
                    const delta = parsed.choices?.[0]?.delta?.content ||
                                  parsed.choices?.[0]?.delta?.reasoning_content ||
                                  parsed.delta || parsed.text || parsed.reply || "";
                    if (delta) fullText += delta;
                    else if (!parsed.choices) fullText += payload;
                  }
                } catch (e) {
                  fullText += payload;
                }
              }
            }
          }

          const totalTook = Math.round(performance.now() - t0);
          timeSpan.innerText = `首字: ${formatHumanDuration(firstTokenTime || 0)} · 总耗时: ${formatHumanDuration(totalTook)}`;

          if (streamError || streamFailed) {
            statusSpan.innerText = "流式异常";
            statusSpan.className = "text-[11px] px-2 py-0.5 rounded font-mono bg-rose-500/15 text-rose-400";
            out.innerText = fullText || ("[流式异常]: " + (streamError || "请求失败"));
          } else if (!fullText.trim()) {
            out.innerText = "上游流式已结束，但未解析出文本内容。\n建议检查模型与入参配置，或前往账号看板刷新凭证。";
            statusSpan.innerText = "200 (空响应)";
            statusSpan.className = "text-[11px] px-2 py-0.5 rounded font-mono bg-amber-500/15 text-amber-300";
          } else {
            out.innerText = fullText;
            statusSpan.innerText = "200 OK";
            statusSpan.className = "text-[11px] px-2 py-0.5 rounded font-mono bg-emerald-500/15 text-emerald-400";
          }
          return;
        }

        if (contentType.includes("audio") || contentType.includes("video")) {
          if (audioCard && renderedAudio) {
            let audioSrc = endpoint;
            if (method.toUpperCase() === "POST") {
              const blob = await resp.blob();
              audioSrc = URL.createObjectURL(blob);
            }
            renderedAudio.src = audioSrc;
            const isMiniMax = endpoint.includes("minimax") || endpoint.includes("speech");
            const ext = isMiniMax ? "mp3" : "m4a";
            if (btnDownloadAudio) {
              btnDownloadAudio.href = audioSrc;
              btnDownloadAudio.download = isMiniMax ? `minimax_${Date.now()}.${ext}` : (endpoint.split("/").pop() || `suno_audio.${ext}`);
            }
            if (audioTitle) {
              audioTitle.innerText = isMiniMax ? "MiniMax 在线语音试听" : "Suno 在线流式播放 (" + (endpoint.split("/").pop() || "Clip") + ")";
            }
            audioCard.classList.remove("hidden");
            try { renderedAudio.play(); } catch (e) {}
          }
          out.innerText = `[200 OK 音频流已就绪]\nContent-Type: ${contentType}\nURL: ${window.location.origin}${endpoint}`;
          return;
        }

        const data = await resp.json();
        const detail = data && data.detail && typeof data.detail === "object" ? data.detail : null;
        let retryAfter = detail && detail.retry_after;
        let lastFailReason = detail && detail.last_failure_reason;
        const rawMsg = (detail && detail.message) || (typeof data.detail === "string" ? data.detail : (data && data.error && data.error.message) || "");
        if (!retryAfter && rawMsg) {
          const m = rawMsg.match(/(?:倒计时|等待|还剩)\s*(\d+)\s*秒/);
          if (m) retryAfter = parseInt(m[1]);
        }
        if (!lastFailReason && rawMsg) {
          const mFail = rawMsg.match(/【上次失败原因:\s*(.+?)】/);
          if (mFail) lastFailReason = mFail[1];
        }
        if (retryAfter) detectedCooldownSeconds = retryAfter;

        if (detail && (detail.message || (detail.needs_login || []).length)) {
          const needs = (detail.needs_login || []).map(item => item.name).filter(Boolean);
          const head = [detail.message || "", needs.length ? ("请登录：" + needs.join("、") + "。") : ""].filter(Boolean).join(" ");
          let showText = head;
          if (lastFailReason && !head.includes(lastFailReason)) showText += "\n[上次失败原因] " + lastFailReason;
          if (retryAfter) showText += `\n[保护倒计时] 需等待 ${retryAfter} 秒（可点击按钮立即强制解锁）。`;
          out.innerText = showText + "\n\n" + JSON.stringify(data, null, 2);
        } else {
          out.innerText = JSON.stringify(data, null, 2);
        }

        // 图片检测
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

        // Suno 音频链接检测
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
              btnDownloadAudio.download = songTitle ? songTitle + ".m4a" : "suno_audio.m4a";
            }
            if (audioTitle) {
              audioTitle.innerText = songTitle ? `Suno 试听: ${songTitle}` : "Suno 在线音乐试听";
            }
            audioCard.classList.remove("hidden");
          }
        } catch (audioErr) {}

      } catch (err) {
        timeSpan.innerText = "失败";
        statusSpan.classList.remove("hidden");
        statusSpan.innerText = "Error";
        statusSpan.className = "text-[11px] px-2 py-0.5 rounded font-mono bg-rose-500/15 text-rose-400";
        out.innerText = "调用异常: " + err.message;
      } finally {
        if (detectedCooldownSeconds > 0) {
          startCooldownTimer(detectedCooldownSeconds);
        } else if (!cooldownTimerId) {
          btn.disabled = false;
          btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> <span>发送请求</span>`;
        }
      }
    }

    function copyResponseOutput() {
      const text = document.getElementById("resp-output").innerText;
      copyText(text);
    }

    // ==========================================
    // 系统工具与状态刷新
    // ==========================================
    async function openProjectFolder() {
      showToast("正在打开项目目录...");
      try {
        const res = await fetch("/api/system/open-directory", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          showToast("已在资源管理器中打开项目目录");
        } else {
          showToast("打开失败: " + (data.detail || "未知错误"));
        }
      } catch (err) {
        showToast("打开目录异常: " + err.message);
      }
    }

    async function toggleAutostart() {
      const btn = document.getElementById("sidebar-btn-autostart");
      btn.disabled = true;
      try {
        const res = await fetch("/api/system/autostart/toggle", { method: "POST" });
        const data = await res.json();
        showToast(data.message || (data.enabled ? "已开启开机自启" : "已关闭开机自启"));
        await refreshDashboard();
      } catch (err) {
        showToast("操作异常: " + err.message);
      } finally {
        btn.disabled = false;
      }
    }

    async function exportToOpenCode() {
      if (!confirm("把当前 API 的对话模型写入 OpenCode 配置？已有的其他供应商会保留。")) return;
      try {
        const res = await fetch("/api/export/opencode", { method: "POST" });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.detail || "导入失败");
          return;
        }
        showToast(data.message || "已写入 OpenCode");
      } catch (err) {
        showToast("导入异常: " + err.message);
      }
    }

    function renderLoginGuide(data) {
      const box = document.getElementById("login-guide");
      const overviewList = document.getElementById("overview-login-list");
      const services = (data && data.services) || [];
      const needs = (data && data.needs_login) || [];

      const chatgpt = services.find(item => item.id === "chatgpt");
      const gemini = services.find(item => item.id === "gemini");
      const aistudio = services.find(item => item.id === "aistudio");

      const gptText = document.getElementById("chatgpt-status-text");
      if (gptText && chatgpt) {
        if (chatgpt.logged_in === false) gptText.innerText = "未登录 chatgpt.com";
        else if (chatgpt.plan_label) gptText.innerText = "已登录 · " + chatgpt.plan_label;
        else if (chatgpt.logged_in) gptText.innerText = "浏览器已登录";
      }
      const geminiText = document.getElementById("gemini-status-text");
      if (geminiText && gemini && gemini.logged_in === false) geminiText.innerText = "未登录 Gemini";
      const aisText = document.getElementById("aistudio-status-text");
      if (aisText && aistudio && aistudio.logged_in === false) {
        aisText.innerHTML = `<span class="inline-block w-2 h-2 rounded-full bg-amber-400"></span> 未登录 AI Studio`;
      }

      if (overviewList && services.length) {
        overviewList.innerHTML = services.map(s => {
          const ok = s.logged_in !== false;
          const badge = ok
            ? `<span class="text-emerald-400 font-mono">已登录</span>`
            : `<a href="${s.login_url}" target="_blank" rel="noopener" class="text-amber-300 hover:text-amber-200 underline">去登录</a>`;
          return `
            <div class="bg-[#090d16] border border-slate-800/80 rounded-lg px-3 py-2.5 flex items-center justify-between gap-2">
              <div class="flex items-center gap-2 min-w-0">
                <span class="w-2 h-2 rounded-full shrink-0 ${ok ? "bg-emerald-400" : "bg-amber-400"}"></span>
                <span class="text-slate-200 font-medium truncate">${escapeHtml(s.name || s.id)}</span>
              </div>
              <div class="shrink-0">${badge}</div>
            </div>
          `;
        }).join("");
      }

      const healthDot = document.getElementById("topbar-health-dot");
      const healthText = document.getElementById("topbar-health-text");
      const navOverviewDot = document.getElementById("nav-overview-dot");
      if (needs.length) {
        if (healthDot) healthDot.className = "w-1.5 h-1.5 rounded-full bg-amber-400";
        if (healthText) healthText.innerText = `${needs.length} 项待登录`;
        if (navOverviewDot) navOverviewDot.className = "w-1.5 h-1.5 rounded-full bg-amber-400";
      } else {
        if (healthDot) healthDot.className = "w-1.5 h-1.5 rounded-full bg-emerald-400";
        if (healthText) healthText.innerText = "服务全部就绪";
        if (navOverviewDot) navOverviewDot.className = "w-1.5 h-1.5 rounded-full bg-emerald-400";
      }

      if (!box) return;
      if (!needs.length || window.__loginBannerDismissed) {
        box.classList.add("hidden");
        box.innerHTML = "";
        return;
      }
      const links = needs.map(item => `<a class="underline decoration-amber-300/70 hover:text-white font-medium" href="${item.login_url}" target="_blank" rel="noopener">${escapeHtml(item.name)}</a>`).join("、");
      box.classList.remove("hidden");
      box.innerHTML = `
        <div class="flex items-center gap-2 min-w-0">
          <i class="fa-solid fa-triangle-exclamation text-amber-400 shrink-0"></i>
          <span>以下服务尚未检测到浏览器登录态，请在已安装 Cookie Hub 的浏览器中登录：${links}</span>
        </div>
        <div class="flex items-center gap-1.5 shrink-0">
          <button type="button" onclick="refreshLoginGuide()" class="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 cursor-pointer">重新检测</button>
          <button type="button" onclick="window.__loginBannerDismissed=true; document.getElementById('login-guide').classList.add('hidden');" class="p-1 text-amber-300/70 hover:text-amber-100 cursor-pointer" title="暂时收起">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
      `;
    }

    async function refreshLoginGuide() {
      try {
        const res = await fetch("/api/system/logins");
        if (!res.ok) return;
        renderLoginGuide(await res.json());
      } catch (e) {}
    }

    async function refreshDashboard() {
      const icon = document.getElementById("sidebar-refresh-icon");
      if (icon) icon.classList.add("fa-spin");

      try {
        const sysRes = await fetch("/api/system/overview");
        if (sysRes.ok) {
          const sys = await sysRes.json();
          const mins = Math.round((sys.uptime_seconds || 0) / 60);
          const uptimeStr = mins >= 60 ? `${(mins / 60).toFixed(1)}h` : `${mins}m`;
          document.getElementById("uptime-text").innerText = uptimeStr;
          const miniUp = document.getElementById("sidebar-uptime-mini");
          if (miniUp) miniUp.innerText = uptimeStr;

          const hubOk = sys.services?.cookie_hub?.extension_connected;
          document.getElementById("hub-status-text").innerHTML = hubOk
            ? `<span class="inline-block w-2 h-2 rounded-full bg-emerald-400"></span> 扩展已连接`
            : `<span class="inline-block w-2 h-2 rounded-full bg-rose-400"></span> 扩展未连接`;
          document.getElementById("hub-clients").innerText = `客户端: ${sys.services?.cookie_hub?.clients || 0}`;

          const readyCount = sys.services?.gemini_pool?.active_accounts;
          document.getElementById("gemini-status-text").innerText = readyCount ? `${readyCount} 账号就绪` : "正在同步账号";

          const ais = sys.services?.aistudio;
          const aisText = document.getElementById("aistudio-status-text");
          const aisModels = document.getElementById("aistudio-models-count");
          if (aisText && ais) {
            if (ais.running && ais.data_plane_ready) {
              aisText.innerHTML = `<span class="inline-block w-2 h-2 rounded-full bg-emerald-400"></span> 运行中`;
            } else if (ais.running) {
              aisText.innerHTML = `<span class="inline-block w-2 h-2 rounded-full bg-sky-400"></span> 待命`;
            } else {
              aisText.innerHTML = `<span class="inline-block w-2 h-2 rounded-full bg-slate-500"></span> 待启动`;
            }
          }
          if (aisModels && ais && ais.models_count) {
            aisModels.innerText = `${ais.models_count} 个原生模型`;
          }

          const gptRunning = sys.services?.chatgpt?.reverse_running;
          document.getElementById("chatgpt-status-text").innerText = gptRunning ? "逆向运行中" : "就绪 (按需启动)";

          const autoOk = sys.autostart && sys.autostart.enabled;
          const autoSideText = document.getElementById("sidebar-autostart-text");
          const autoSideDot = document.getElementById("sidebar-autostart-dot");
          const autoBadge = document.getElementById("autostart-status-badge");
          if (autoOk) {
            if (autoSideText) autoSideText.innerText = "自启: 已开启";
            if (autoSideDot) autoSideDot.className = "w-2 h-2 rounded-full bg-emerald-400";
            if (autoBadge) {
              autoBadge.innerText = "自启: 已开启";
              autoBadge.className = "text-emerald-400 font-medium";
            }
          } else {
            if (autoSideText) autoSideText.innerText = "自启: 已关闭";
            if (autoSideDot) autoSideDot.className = "w-2 h-2 rounded-full bg-slate-600";
            if (autoBadge) {
              autoBadge.innerText = "自启: 已关闭";
              autoBadge.className = "text-slate-400 font-medium";
            }
          }
        }

        // 账号列表
        const acctRes = await fetch("/api/gemini/accounts");
        if (acctRes.ok) {
          const data = await acctRes.json();
          const tbody = document.getElementById("accounts-tbody");
          tbody.innerHTML = "";
          const accounts = (data.accounts || []).filter(a => a.visible);
          const named = [];
          accounts.forEach(a => {
            if (a.email && !named.includes(a.email)) named.push(a.email);
          });
          const summary = document.getElementById("accounts-summary");
          if (summary) {
            summary.innerText = named.length
              ? `当前浏览器共 ${named.length} 个 Google 账号：${named.join("、")}`
              : "正在按当前浏览器的登录账号同步，没有独立登录的槽位不会显示";
          }
          const navCount = document.getElementById("nav-account-count");
          if (navCount) navCount.innerText = named.length ? String(named.length) : "--";

          if (!accounts.length) {
            tbody.innerHTML = `<tr><td colspan="5" class="py-8 text-center text-slate-500">暂无可见账号槽位，请先在浏览器登录 Google 并确保 Cookie Hub 已连接</td></tr>`;
          }

          accounts.forEach(a => {
            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-900/40 transition";

            const displayName = a.name ? a.name : (a.label || `账号槽位 u/${a.auth_user}`);
            const displayEmail = a.email ? a.email : "未解析邮箱";
            const initialChar = (displayName || displayEmail || "G").trim().charAt(0).toUpperCase();

            const q5hUsed = a.quota_5h_used !== undefined ? a.quota_5h_used : 0;
            const q5hLimit = a.quota_5h_limit || 50;
            const q5hRemaining = a.quota_5h_remaining !== undefined ? a.quota_5h_remaining : (q5hLimit - q5hUsed);
            const q5hPct = Math.min(100, Math.round((q5hUsed / q5hLimit) * 100));
            const q5hReset = a.quota_5h_reset_str || "滚动重置就绪";

            const qWeekUsed = a.quota_weekly_used !== undefined ? a.quota_weekly_used : 0;
            const qWeekLimit = a.quota_weekly_limit || 500;
            const qWeekPct = Math.min(100, Math.round((qWeekUsed / qWeekLimit) * 100));
            const qStatus = (a.quota_status || "充裕").replace(/[\u{1F300}-\u{1FAFF}]/gu, "").trim() || "充裕";

            const enabled = a.status === "enabled";

            tr.innerHTML = `
              <td class="py-3 px-3">
                <div class="flex items-center gap-2.5">
                  <div class="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-semibold text-sky-300 shrink-0">
                    ${escapeHtml(initialChar)}
                  </div>
                  <div class="min-w-0">
                    <div class="font-medium text-slate-100 flex items-center gap-1.5">
                      <span class="truncate">${escapeHtml(displayName)}</span>
                      <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono shrink-0">#${a.id} · u/${a.auth_user}</span>
                    </div>
                    <div class="text-[11px] text-slate-400 font-mono mt-0.5 truncate">
                      ${escapeHtml(displayEmail)}${(a.note || "").includes("同一登录") ? ` <span class="text-amber-300/80">· 重复登录</span>` : ""}
                    </div>
                  </div>
                </div>
              </td>
              <td class="py-3 px-3">
                <div class="w-32 space-y-1">
                  <div class="flex items-center justify-between text-[11px] font-mono">
                    <span class="text-slate-200">${q5hUsed}/${q5hLimit}</span>
                    <span class="text-slate-500">余 ${q5hRemaining}</span>
                  </div>
                  <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div class="h-full bg-amber-400/80 rounded-full" style="width: ${q5hPct}%"></div>
                  </div>
                  <div class="text-[10px] text-slate-500 whitespace-nowrap">${escapeHtml(q5hReset)}</div>
                </div>
              </td>
              <td class="py-3 px-3">
                <div class="w-28 space-y-1">
                  <div class="flex items-center justify-between text-[11px] font-mono">
                    <span class="text-slate-200">${qWeekUsed}/${qWeekLimit}</span>
                    <span class="text-emerald-400 font-sans">${escapeHtml(qStatus)}</span>
                  </div>
                  <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div class="h-full bg-sky-400/80 rounded-full" style="width: ${qWeekPct}%"></div>
                  </div>
                </div>
              </td>
              <td class="py-3 px-3 whitespace-nowrap">
                <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border whitespace-nowrap ${enabled ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" : "bg-slate-800 text-slate-400 border-slate-700"}">
                  <span class="w-1.5 h-1.5 rounded-full ${enabled ? "bg-emerald-400" : "bg-slate-500"}"></span>
                  ${enabled ? "已启用" : escapeHtml(a.status || "未知")}
                </span>
              </td>
              <td class="py-3 px-3 text-right space-x-1 whitespace-nowrap">
                <button type="button" onclick="checkAccount(${a.id})" class="px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-[11px] text-slate-300 border border-slate-800 transition cursor-pointer">检测</button>
                <button type="button" onclick="rotateAccount(${a.id})" class="px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-[11px] text-amber-300 border border-slate-800 transition cursor-pointer">保活</button>
              </td>
            `;
            tbody.appendChild(tr);
          });
        }

        await refreshLoginGuide();
        await loadChatHistory(currentHistoryPage, false);
      } catch (e) {
        console.error("刷新失败:", e);
      } finally {
        if (icon) icon.classList.remove("fa-spin");
      }
    }

    async function syncProfiles() {
      const btn = document.getElementById("btn-sync-profiles");
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>正在提取...</span>`;
      try {
        const res = await fetch("/api/gemini/accounts/sync-profiles", { method: "POST" });
        const data = await res.json();
        showToast(data.message || "账号真实用户名与邮箱已同步");
        await refreshDashboard();
      } catch (err) {
        showToast("同步异常: " + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-id-card text-sky-400"></i> 同步真实名称与邮箱`;
      }
    }

    async function checkAccount(id) {
      showToast("正在验证账号 #" + id + " 凭证...");
      try {
        const res = await fetch(`/api/gemini/accounts/${id}/check`, { method: "POST" });
        const data = await res.json();
        showToast("检测完成: " + (data.status || "OK"));
        refreshDashboard();
      } catch (err) {
        showToast("检测失败: " + err.message);
      }
    }

    async function rotateAccount(id) {
      showToast("正在为账号 #" + id + " 申请保活...");
      try {
        const res = await fetch(`/api/gemini/accounts/${id}/rotate`, { method: "POST" });
        const data = await res.json();
        showToast("保活完成: " + (data.status || "OK"));
        refreshDashboard();
      } catch (err) {
        showToast("保活失败: " + err.message);
      }
    }

    async function refreshAllCookies() {
      if (!confirm("确认从当前浏览器 Cookie Hub 重新提取 Google 全量会话凭证？")) return;
      try {
        const res = await fetch("/api/gemini/refresh", { method: "POST" });
        const data = await res.json();
        showToast(data.message || "凭证刷新成功");
        refreshDashboard();
      } catch (err) {
        showToast("刷新失败: " + err.message);
      }
    }

    // ==========================================
    // 对话历史与审计模块
    // ==========================================
    let currentHistoryPage = 1;
    let totalHistoryPages = 1;
    const historyDetailCache = {};

    function escapeHtml(str) {
      if (str === null || str === undefined) return "";
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    async function loadChatHistory(page = 1, showToastMsg = false) {
      currentHistoryPage = page;
      const icon = document.getElementById("history-refresh-icon");
      if (icon) icon.classList.add("fa-spin");

      const modelFilter = document.getElementById("history-filter-model")?.value || "";
      const statusFilter = document.getElementById("history-filter-status")?.value || "";
      const keyword = document.getElementById("history-search-input")?.value?.trim() || "";

      let url = `/api/history/chats?page=${page}&page_size=10`;
      if (modelFilter) url += `&model=${encodeURIComponent(modelFilter)}`;
      if (statusFilter) url += `&status=${statusFilter === "error" ? 500 : statusFilter}`;
      if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;

      try {
        const res = await fetch(url);
        const data = await res.json();

        const navCount = document.getElementById("nav-history-count");
        if (navCount && data.stats) {
          navCount.innerText = String(data.stats.total_count || 0);
        }

        const sizeBadge = document.getElementById("history-size-badge");
        const sizeBar = document.getElementById("history-size-bar");
        if (sizeBadge && sizeBar && data.stats) {
          const usedMb = data.stats.db_size_mb || 0;
          const pct = Math.min(100, data.stats.used_percent || 0);
          sizeBadge.innerText = `${usedMb.toFixed(2)} MB / 100 MB`;
          sizeBar.style.width = `${Math.max(2, pct)}%`;
          sizeBar.className = pct > 80
            ? "h-full bg-rose-500 rounded-full transition-all duration-300"
            : "h-full bg-sky-400 rounded-full transition-all duration-300";
        }

        renderHistoryList(data);

        totalHistoryPages = Math.max(1, Math.ceil((data.total || 0) / 10));
        const indicator = document.getElementById("history-page-indicator");
        if (indicator) indicator.innerText = `${data.page} / ${totalHistoryPages}`;
        const totalInfo = document.getElementById("history-total-info");
        if (totalInfo) {
          const start = data.total === 0 ? 0 : (page - 1) * 10 + 1;
          const end = Math.min(data.total, page * 10);
          totalInfo.innerText = `第 ${start} - ${end} 条 · 共 ${data.total} 条`;
        }
        const prevBtn = document.getElementById("history-btn-prev");
        const nextBtn = document.getElementById("history-btn-next");
        if (prevBtn) prevBtn.disabled = (page <= 1);
        if (nextBtn) nextBtn.disabled = (page >= totalHistoryPages);

        const summaryEl = document.getElementById("history-pagination-summary");
        if (summaryEl) summaryEl.innerText = `共 ${data.total} 条记录`;

        if (showToastMsg) showToast("对话历史已更新");
      } catch (err) {
        console.error("加载对话历史异常:", err);
      } finally {
        if (icon) icon.classList.remove("fa-spin");
      }
    }

    function renderHistoryList(data) {
      const container = document.getElementById("history-list-container");
      if (!container) return;

      if (!data.items || data.items.length === 0) {
        container.innerHTML = `
          <div class="text-center py-12 text-slate-500 text-xs bg-[#090d16] rounded-xl border border-slate-800/80">
            <i class="fa-solid fa-inbox text-2xl text-slate-700 mb-2 block"></i>
            暂无匹配的对话记录
          </div>
        `;
        return;
      }

      container.innerHTML = data.items.map(item => {
        const isSuccess = item.status >= 200 && item.status < 300;
        const statusDot = isSuccess ? "bg-emerald-400" : "bg-rose-400";
        const statusText = isSuccess ? `${item.status} OK` : `${item.status} ERR`;

        return `
          <div class="bg-[#090d16] border border-slate-800/90 hover:border-slate-700 rounded-xl p-3.5 transition space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800/70">
              <div class="flex flex-wrap items-center gap-2 text-[11px] font-mono">
                <span class="w-1.5 h-1.5 rounded-full ${statusDot}"></span>
                <span class="px-2 py-0.5 rounded bg-slate-900 text-sky-300 border border-slate-800 font-semibold">${escapeHtml(item.model)}</span>
                <span class="text-slate-400">${escapeHtml(item.endpoint || "/v1/chat/completions")}</span>
                <span class="${isSuccess ? "text-emerald-400" : "text-rose-400"}">${statusText}</span>
                <span class="text-slate-500">· ${item.is_stream ? "流式" : "非流式"}</span>
                <span class="text-slate-500">· ${item.latency_ms}ms</span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <span class="text-[11px] font-mono text-slate-500">${escapeHtml(item.created_at)}</span>
                <button type="button" id="detail-btn-${item.id}" onclick="toggleChatDetail(${item.id})" class="px-2 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-[11px] flex items-center gap-1 transition cursor-pointer">
                  <span>详情</span>
                  <i class="fa-solid fa-chevron-down text-[9px]"></i>
                </button>
                <button type="button" onclick="deleteHistoryItem(${item.id})" class="p-1 text-slate-500 hover:text-rose-400 transition cursor-pointer" title="删除此条记录">
                  <i class="fa-regular fa-trash-can text-xs"></i>
                </button>
              </div>
            </div>

            <div class="text-xs space-y-1 font-mono">
              <div class="text-slate-300 line-clamp-1"><span class="text-sky-400 select-none">Q: </span>${escapeHtml(item.prompt_summary || "（无文本）")}</div>
              <div class="${item.error_message ? "text-rose-400" : "text-slate-400"} line-clamp-2"><span class="text-slate-500 select-none">A: </span>${escapeHtml(item.response_summary || (item.error_message ? `[错误] ${item.error_message}` : "（未捕获回答或仍在流中）"))}</div>
            </div>

            <div id="detail-panel-${item.id}" class="hidden pt-3 border-t border-slate-800/70 space-y-3"></div>
          </div>
        `;
      }).join("");
    }

    async function toggleChatDetail(chatId) {
      const panel = document.getElementById(`detail-panel-${chatId}`);
      const btn = document.getElementById(`detail-btn-${chatId}`);
      if (!panel) return;

      if (!panel.classList.contains("hidden")) {
        panel.classList.add("hidden");
        if (btn) btn.innerHTML = `<span>详情</span> <i class="fa-solid fa-chevron-down text-[9px]"></i>`;
        return;
      }

      panel.classList.remove("hidden");
      if (btn) btn.innerHTML = `<span>收起</span> <i class="fa-solid fa-chevron-up text-[9px]"></i>`;

      if (historyDetailCache[chatId]) {
        renderDetailContent(chatId, historyDetailCache[chatId]);
        return;
      }

      panel.innerHTML = `<div class="p-3 text-center text-slate-500 text-xs"><i class="fa-solid fa-spinner fa-spin mr-1.5"></i> 加载完整上下文...</div>`;

      try {
        const res = await fetch(`/api/history/chats/${chatId}`);
        const detail = await res.json();
        historyDetailCache[chatId] = detail;
        renderDetailContent(chatId, detail);
      } catch (err) {
        panel.innerHTML = `<div class="p-3 text-rose-400 text-xs">加载详情失败: ${err.message}</div>`;
      }
    }

    function renderDetailContent(chatId, detail) {
      const panel = document.getElementById(`detail-panel-${chatId}`);
      if (!panel) return;

      let messagesHtml = "";
      if (Array.isArray(detail.messages)) {
        messagesHtml = detail.messages.map(m => {
          const role = (m.role || "user").toLowerCase();
          return `
            <div class="rounded-lg p-2.5 border border-slate-800 bg-slate-900/60 text-xs font-mono space-y-1">
              <span class="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-sky-300 border border-slate-700">${escapeHtml(role)}</span>
              <div class="text-slate-200 whitespace-pre-wrap break-words">${escapeHtml(typeof m.content === "string" ? m.content : JSON.stringify(m.content || ""))}</div>
            </div>
          `;
        }).join("");
      } else {
        messagesHtml = `<div class="text-xs font-mono text-slate-300 whitespace-pre-wrap">${escapeHtml(String(detail.messages || ""))}</div>`;
      }

      panel.innerHTML = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div class="space-y-2 bg-[#0b101b] p-3 rounded-lg border border-slate-800">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-medium text-sky-400">Request 内容</span>
              <button type="button" onclick="copyElementText('${chatId}-req', this)" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono transition cursor-pointer">复制</button>
            </div>
            <div id="copy-target-${chatId}-req" class="space-y-2 max-h-[280px] overflow-y-auto pr-1">${messagesHtml}</div>
          </div>

          <div class="space-y-2 bg-[#0b101b] p-3 rounded-lg border border-slate-800">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-medium text-emerald-400">Response 返回</span>
              <button type="button" onclick="copyElementText('${chatId}-resp', this)" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono transition cursor-pointer">复制</button>
            </div>
            <div id="copy-target-${chatId}-resp" class="max-h-[280px] overflow-y-auto pr-1">
              <pre class="text-xs font-mono ${detail.error_message && !detail.response_text ? "text-rose-300" : "text-slate-200"} whitespace-pre-wrap break-words leading-relaxed">${escapeHtml(detail.response_text || (detail.error_message ? `[错误] ${detail.error_message}` : "（无文本内容或发生异常）"))}</pre>
            </div>
          </div>
        </div>

        <div class="text-[11px] font-mono text-slate-500 flex flex-wrap items-center justify-between gap-2 pt-1">
          <span>Trace: <span class="text-slate-400">${escapeHtml(detail.trace_id)}</span></span>
          <span>映射模型: <span class="text-slate-400">${escapeHtml(detail.actual_model)}</span></span>
          <span>耗时: <span class="text-slate-300">${detail.latency_ms}ms</span></span>
          <span>字数: <span class="text-slate-300">${(detail.response_text || "").length}</span></span>
        </div>
      `;
    }

    function historyPageChange(delta) {
      const target = currentHistoryPage + delta;
      if (target >= 1 && target <= totalHistoryPages) {
        loadChatHistory(target, false);
      }
    }

    async function confirmClearHistory() {
      if (!confirm("确定要清空全部对话历史吗？\n该操作将从 SQLite 数据库中物理清除所有会话记录并释放磁盘空间。")) return;
      try {
        const res = await fetch("/api/history/clear", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          showToast("全部对话历史已清空");
          for (const k in historyDetailCache) delete historyDetailCache[k];
          loadChatHistory(1, false);
        } else {
          showToast("清空失败: " + (data.detail || "未知错误"));
        }
      } catch (e) {
        showToast("清空异常: " + e.message);
      }
    }

    async function deleteHistoryItem(chatId) {
      if (!confirm("确认删除此条对话记录？")) return;
      try {
        const res = await fetch(`/api/history/chats/${chatId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.success) {
          showToast("记录已删除");
          delete historyDetailCache[chatId];
          loadChatHistory(currentHistoryPage, false);
        }
      } catch (e) {
        showToast("删除失败: " + e.message);
      }
    }

    // ==========================================
    // 初始化
    // ==========================================
    (function init() {
      const initialHash = (window.location.hash || "").replace(/^#/, "");
      if (VIEW_META[initialHash]) {
        switchView(initialHash, false);
      } else {
        switchView("playground", false);
      }

      renderEndpointCategoryTabs();
      renderEndpointsList();
      renderPlaygroundCategoryNav();
      setPlaygroundCategory("gemini", true);
      refreshDashboard();
      setInterval(refreshDashboard, 12000);
    })();
  </script>
</body>
</html>"""
