#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cookie Service Suite - 现代化 Web 控制台前端模板
特性：
- 左侧固定导航栏切换独立工作视图：调试台、运行概览、账号看板、对话历史、接口清单、文档规范
- 极简低噪的暗色开发者控制台美学，消除堆叠冗余与视觉干扰
- 调试台采用主流请求工具布局（平台切换 -> 统一请求栏 -> 参数配置与实时响应双栏）
- 动态计算全量 54 个标准化 API 端点分类数量，支持一键填入/测试与流式/图文/音频渲染
"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cookie Service Suite | 本地服务与 API 控制台</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script>
    (function applyEarlyTheme() {
      try {
        const saved = localStorage.getItem("css_dashboard_theme");
        const prefersLight = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
        const theme = saved === "light" || saved === "dark" ? saved : (prefersLight ? "light" : "dark");
        if (theme === "light") document.documentElement.classList.add("theme-light");
      } catch (e) {}
    })();
  </script>
  <style>
    :root {
      --bg-canvas: #090d16;
      --bg-surface: #0f1623;
      --bg-elevated: #141d2e;
      --border-subtle: rgba(148, 163, 184, 0.14);
      color-scheme: dark;
    }
    html.theme-light {
      --bg-canvas: #f8fafc;
      --bg-surface: #ffffff;
      --bg-elevated: #f1f5f9;
      --border-subtle: rgba(15, 23, 42, 0.10);
      color-scheme: light;
    }
    html.theme-light body { color: #0f172a; }
    html.theme-light .panel { box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }
    html.theme-light .panel-soft { background-color: rgba(248, 250, 252, 0.85); }
    html.theme-light .nav-item-active { background: rgba(2, 132, 199, 0.10); color: #0284c7; border-color: rgba(2, 132, 199, 0.28); }
    html.theme-light .plat-pill { background: #ffffff; border-color: rgba(15, 23, 42, 0.12); color: #334155; }
    html.theme-light .plat-pill:hover { background: #f1f5f9; border-color: rgba(2, 132, 199, 0.38); color: #0f172a; }
    html.theme-light .plat-pill-active { background: rgba(2, 132, 199, 0.10); border-color: rgba(2, 132, 199, 0.45); color: #0284c7; }
    html.theme-light .tab-active { background: rgba(2, 132, 199, 0.10); color: #0284c7; border-color: rgba(2, 132, 199, 0.40); }
    /* 浅色模式全局语义色彩映射 */
    html.theme-light .bg-\[\#090d16\] { background-color: #f8fafc !important; }
    html.theme-light .bg-\[\#0b101a\] { background-color: #f1f5f9 !important; }
    html.theme-light .bg-\[\#0b101b\] { background-color: #f8fafc !important; }
    html.theme-light .bg-\[\#0d131f\] { background-color: #ffffff !important; }
    html.theme-light .bg-\[\#0d131f\]\/90 { background-color: rgba(255, 255, 255, 0.92) !important; }
    html.theme-light .bg-\[\#131c2e\] { background-color: #ffffff !important; }
    html.theme-light .bg-slate-950\/30 { background-color: rgba(241, 245, 249, 0.7) !important; }
    html.theme-light .bg-slate-900, html.theme-light .bg-slate-900\/90, html.theme-light .bg-slate-900\/80, html.theme-light .bg-slate-900\/60 { background-color: #f1f5f9 !important; }
    html.theme-light .bg-slate-800, html.theme-light .bg-slate-800\/90, html.theme-light .bg-slate-800\/80 { background-color: #e2e8f0 !important; }
    html.theme-light .bg-slate-700 { background-color: #cbd5e1 !important; }
    html.theme-light .bg-slate-600, html.theme-light .bg-slate-500 { background-color: #94a3b8 !important; }
    html.theme-light .hover\:bg-slate-900\/40:hover, html.theme-light .hover\:bg-slate-900\/30:hover { background-color: rgba(226, 232, 240, 0.55) !important; }
    html.theme-light .hover\:bg-slate-800:hover, html.theme-light .hover\:bg-slate-800\/60:hover { background-color: #e2e8f0 !important; }
    html.theme-light .hover\:bg-slate-700:hover { background-color: #cbd5e1 !important; }
    html.theme-light .text-slate-100 { color: #0f172a !important; }
    html.theme-light .text-slate-200 { color: #1e293b !important; }
    html.theme-light .text-slate-300 { color: #334155 !important; }
    html.theme-light .text-slate-400, html.theme-light .text-slate-500 { color: #64748b !important; }
    html.theme-light .text-slate-700 { color: #cbd5e1 !important; }
    html.theme-light .hover\:text-slate-100:hover { color: #0f172a !important; }
    html.theme-light .hover\:text-slate-200:hover { color: #1e293b !important; }
    html.theme-light .placeholder-slate-500::placeholder { color: #94a3b8 !important; }
    html.theme-light .border-slate-800, html.theme-light .border-slate-800\/90, html.theme-light .border-slate-800\/80, html.theme-light .border-slate-800\/70, html.theme-light .border-slate-800\/60 { border-color: rgba(15, 23, 42, 0.11) !important; }
    html.theme-light .border-slate-700, html.theme-light .border-slate-700\/80 { border-color: rgba(15, 23, 42, 0.16) !important; }
    html.theme-light .hover\:border-slate-700:hover { border-color: rgba(15, 23, 42, 0.25) !important; }
    html.theme-light .divide-slate-800\/60 > :not([hidden]) ~ :not([hidden]) { border-color: rgba(15, 23, 42, 0.08) !important; }
    html.theme-light .text-sky-200, html.theme-light .text-sky-300, html.theme-light .text-sky-300\/90 { color: #0369a1 !important; }
    html.theme-light .text-sky-400 { color: #0284c7 !important; }
    html.theme-light .hover\:text-sky-300:hover, html.theme-light .hover\:text-sky-400:hover { color: #0369a1 !important; }
    html.theme-light .text-amber-100, html.theme-light .text-amber-200, html.theme-light .text-amber-300, html.theme-light .text-amber-300\/80, html.theme-light .text-amber-300\/70 { color: #b45309 !important; }
    html.theme-light .text-amber-400, html.theme-light .text-amber-400\/90 { color: #d97706 !important; }
    html.theme-light .hover\:text-amber-100:hover, html.theme-light .hover\:text-amber-200:hover { color: #92400e !important; }
    html.theme-light .text-emerald-300, html.theme-light .text-emerald-400, html.theme-light .text-emerald-400\/95, html.theme-light .text-emerald-400\/90 { color: #047857 !important; }
    html.theme-light .text-rose-300, html.theme-light .text-rose-400 { color: #be123c !important; }
    html.theme-light .hover\:text-rose-400:hover { color: #9f1239 !important; }
    html.theme-light .text-indigo-300, html.theme-light .text-indigo-400 { color: #4338ca !important; }
    html.theme-light .text-purple-300, html.theme-light .text-purple-400 { color: #7e22ce !important; }
    html.theme-light .text-pink-300, html.theme-light .text-pink-400 { color: #be185d !important; }
    html.theme-light .text-violet-300, html.theme-light .text-violet-400 { color: #6d28d9 !important; }
    html.theme-light .text-blue-300, html.theme-light .text-blue-400 { color: #1d4ed8 !important; }
    html.theme-light .text-cyan-400 { color: #0e7490 !important; }
    html.theme-light #req-body { background-color: #f8fafc !important; color: #0369a1 !important; }
    html.theme-light #resp-output { background-color: #f8fafc !important; color: #065f46 !important; }
    html.theme-light #live-toast { background-color: #ffffff !important; color: #0369a1 !important; border-color: rgba(2, 132, 199, 0.35) !important; box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.12) !important; }
    html.theme-light .bg-black\/60 { background-color: rgba(15, 23, 42, 0.35) !important; }
    html.theme-light .bg-black\/75 { background-color: rgba(15, 23, 42, 0.45) !important; }
    html.theme-light ::selection { background-color: rgba(2, 132, 199, 0.18); color: #0c4a6e; }
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
    .api-switch {
      position: relative;
      display: inline-flex;
      align-items: center;
      width: 40px;
      height: 22px;
      border-radius: 9999px;
      background-color: #334155;
      transition: background-color 0.18s ease, opacity 0.18s ease;
      cursor: pointer;
      flex-shrink: 0;
      border: 1px solid rgba(148, 163, 184, 0.22);
    }
    .api-switch[aria-checked="true"] {
      background-color: #10b981;
      border-color: rgba(16, 185, 129, 0.5);
    }
    .api-switch:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
    .api-switch-thumb {
      width: 16px;
      height: 16px;
      border-radius: 9999px;
      background-color: #ffffff;
      transform: translateX(2px);
      transition: transform 0.18s ease;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
    }
    .api-switch[aria-checked="true"] .api-switch-thumb {
      transform: translateX(20px);
    }
    html.theme-light .api-switch {
      background-color: #cbd5e1;
      border-color: rgba(15, 23, 42, 0.14);
    }
    html.theme-light .api-switch[aria-checked="true"] {
      background-color: #059669;
      border-color: rgba(5, 150, 105, 0.5);
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

          <button type="button" onclick="switchView('conversations')" data-view="conversations" class="nav-item w-full flex items-center justify-between px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-comments w-4 text-center text-slate-400"></i>
              <span>Gemini 对话</span>
            </span>
            <span id="nav-conv-count" class="text-[11px] text-slate-500 font-mono">0</span>
          </button>

          <button type="button" onclick="switchView('endpoints')" data-view="endpoints" class="nav-item w-full flex items-center justify-between px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent">
            <span class="flex items-center gap-2.5">
              <i class="fa-solid fa-code w-4 text-center text-slate-400"></i>
              <span>接口清单</span>
            </span>
            <span id="nav-endpoints-count" class="text-[11px] text-slate-500 font-mono">54</span>
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

      <!-- API 访问令牌 (Token) 快捷管理 -->
      <div class="space-y-2 pt-3 border-t border-slate-800/80">
        <div class="flex items-center justify-between px-1">
          <span class="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
            <i class="fa-solid fa-key text-amber-400 text-[10px]"></i>
            <span>API Token</span>
          </span>
          <button type="button" onclick="toggleTokenVisibility()" id="sidebar-token-eye" class="text-[11px] text-slate-500 hover:text-slate-200 transition cursor-pointer" title="显示或隐藏完整 Token">
            <i class="fa-regular fa-eye"></i>
          </button>
        </div>
        <div id="sidebar-token-preview" class="bg-[#090d16] border border-slate-800 rounded-lg px-2.5 py-1.5 font-mono text-[11px] text-slate-300 truncate select-all" title="API 访问令牌">加载中...</div>
        <div class="grid grid-cols-2 gap-1.5">
          <button type="button" onclick="copyApiToken(this)" id="btn-copy-token-sidebar" class="px-2 py-1.5 rounded-lg bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-800 text-[11px] flex items-center justify-center gap-1 transition cursor-pointer" title="复制当前 Token">
            <i class="fa-regular fa-copy text-sky-400"></i>
            <span>复制</span>
          </button>
          <button type="button" onclick="generateApiToken(this)" id="btn-gen-token-sidebar" class="px-2 py-1.5 rounded-lg bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 text-[11px] flex items-center justify-center gap-1 transition cursor-pointer" title="生成新 Token 并自动复制">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
            <span>生成</span>
          </button>
        </div>
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
      <div id="sidebar-listen-addr" class="text-[11px] text-slate-500 font-mono">0.0.0.0:18800</div>
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
        <button type="button" onclick="toggleTheme()" id="btn-theme-toggle" class="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-1.5 cursor-pointer" title="切换浅色 / 暗色外观主题">
          <i id="theme-toggle-icon" class="fa-solid fa-sun text-amber-400"></i>
          <span id="theme-toggle-text" class="hidden sm:inline">浅色模式</span>
        </button>
        <button type="button" onclick="switchView('overview')" id="topbar-health-pill" class="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs text-slate-300 transition cursor-pointer">
          <span id="topbar-health-dot" class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span id="topbar-health-text">服务就绪</span>
        </button>
        <button type="button" onclick="exportToOpenCode()" class="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-1.5 cursor-pointer" title="将当前对话模型写入 OpenCode 配置">
          <i class="fa-solid fa-file-export text-sky-400"></i>
          <span class="hidden md:inline">导入 OpenCode</span>
        </button>
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
              <input type="text" id="req-endpoint" aria-label="请求路径" class="flex-1 min-w-0 h-9 bg-[#090d16] border border-slate-800 rounded-lg px-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-sky-500 transition" value="/api/pool/chat">
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
            <p class="text-xs text-slate-400 mt-0.5">实时监控各本地子服务、网页 API 启停开关与端口运行状态</p>
          </div>
          <button type="button" onclick="refreshDashboard()" class="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs flex items-center gap-1.5 transition cursor-pointer">
            <i class="fa-solid fa-arrows-rotate text-sky-400"></i> 立即刷新
          </button>
        </div>

        <!-- 网页 API 精细化启停控制面板 -->
        <div class="panel rounded-xl p-5 space-y-3" id="web-api-switches-panel">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-800/80">
            <div>
              <h3 class="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <i class="fa-solid fa-sliders text-sky-400 text-xs"></i>
                <span>网页 API 精细化启停开关</span>
              </h3>
              <p class="text-[11px] text-slate-400 mt-0.5">关闭后将停止获取或刷新对应网页的 Cookie，并同步停止所依赖的后台转换程序（如 Gemini 转 API、AI Studio、ChatGPT 逆向等）</p>
            </div>
            <span id="web-api-switches-summary" class="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-[#090d16] border border-slate-800 text-slate-300 shrink-0">加载中...</span>
          </div>
          <div id="web-api-switches-grid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <div class="col-span-full py-6 text-center text-xs text-slate-500">正在加载网页 API 开关配置...</div>
          </div>
        </div>

        <!-- Google 防风控与同步频率控制面板 -->
        <div class="panel rounded-xl p-5 space-y-3" id="google-sync-panel">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-800/80">
            <div>
              <h3 class="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <i class="fa-solid fa-shield-halved text-amber-400 text-xs"></i>
                <span>Google 防风控与同步频率控制</span>
              </h3>
              <p class="text-[11px] text-slate-400 mt-0.5">控制后台自动监听 Google Cookie、刷新 Gemini 官网额度的频率；开启一键静默后，后台将停止所有主动轮询（不影响手动对话）</p>
            </div>
            <button type="button" id="btn-google-sync-master" onclick="toggleGoogleAutoSyncMaster()" class="px-3 py-1.5 rounded-lg text-xs font-medium border transition cursor-pointer shrink-0 bg-emerald-500/15 text-emerald-300 border-emerald-500/40">
              <i class="fa-solid fa-power-off mr-1"></i> <span id="google-sync-master-text">自动监听中（点击一键全关）</span>
            </button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1.5">
              <label for="gs-usage-interval" class="text-slate-300 font-medium block">Gemini 额度自动刷新间隔</label>
              <select id="gs-usage-interval" onchange="saveGoogleSyncSettings()" class="w-full bg-slate-950/60 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500">
                <option value="0">关闭自动刷新（仅手动，最安全）</option>
                <option value="900">每 15 分钟</option>
                <option value="1800">每 30 分钟（推荐）</option>
                <option value="3600">每 1 小时</option>
                <option value="7200">每 2 小时</option>
              </select>
            </div>
            <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1.5">
              <label for="gs-cookie-interval" class="text-slate-300 font-medium block">Google Cookie 监听/同步间隔</label>
              <select id="gs-cookie-interval" onchange="saveGoogleSyncSettings()" class="w-full bg-slate-950/60 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500">
                <option value="0">关闭自动同步（仅手动）</option>
                <option value="900">每 15 分钟</option>
                <option value="1800">每 30 分钟（推荐）</option>
                <option value="3600">每 1 小时</option>
              </select>
            </div>
            <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 flex items-center justify-between gap-2">
              <div>
                <div class="text-slate-300 font-medium">自动唤醒浏览器标签页</div>
                <div class="text-[11px] text-slate-500 mt-0.5">关闭可避免频繁弹页触发风控</div>
              </div>
              <input type="checkbox" id="gs-allow-tab" onchange="saveGoogleSyncSettings()" class="w-4 h-4 accent-sky-500 cursor-pointer" />
            </div>
          </div>
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
          <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
            <div>
              <h2 class="text-base font-semibold text-slate-100">全平台账号看板</h2>
              <p class="text-xs text-slate-400 mt-0.5" id="accounts-summary">正在从浏览器与服务池同步各平台账号...</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <div class="flex items-center gap-2.5 text-[11px] font-mono bg-[#090d16] border border-slate-800/90 rounded-lg px-3 py-1.5">
                <span class="text-slate-400">账号 <strong id="accounts-stat-total" class="text-slate-100">0</strong></span>
                <span class="text-slate-700">|</span>
                <span class="text-slate-400">会员 <strong id="accounts-stat-members" class="text-amber-300">0</strong></span>
                <span class="text-slate-700">|</span>
                <span class="text-slate-400">平台 <strong id="accounts-stat-platforms" class="text-emerald-400">0</strong></span>
              </div>
              <button type="button" onclick="refreshAccountsAll()" id="btn-refresh-accounts" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 transition flex items-center gap-1.5 cursor-pointer">
                <i class="fa-solid fa-arrows-rotate"></i> 刷新
              </button>
            </div>
          </div>

          <!-- 平台过滤胶囊 -->
          <div id="accounts-platform-filters" class="flex flex-wrap items-center gap-1.5"></div>
        </div>

        <!-- Google 账号池明细 -->
        <div id="google-accounts-panel" class="panel rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <img src="/assets/icons/gemini.svg" alt="Google" class="w-4 h-4 object-contain shrink-0" onerror="handlePlatformIconError(this, 'fa-solid fa-sparkles text-purple-400')">
              <h3 class="text-sm font-semibold text-slate-200">Google 账号池</h3>
              <span id="google-accounts-count" class="text-[11px] px-1.5 py-0.5 rounded bg-slate-800/90 text-slate-400 font-mono">0</span>
            </div>
            <div class="flex items-center gap-2.5">
              <span class="text-[11px] text-slate-500 font-mono cursor-help" title="消耗预估指示点：绿点 ≤90% · 黄点 90%~100% · 红点 ≥100%">LRU 自动均衡 · 5h/周配额</span>
              <button type="button" id="btn-refresh-google-quota" onclick="refreshPlatformAccounts('gemini', this)" title="刷新额度" aria-label="刷新额度" class="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-[11px] text-amber-300 border border-slate-800 transition flex items-center gap-1 cursor-pointer">
                <i class="fa-solid fa-arrows-rotate"></i>
                <span>刷新</span>
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

        <!-- 其他平台账号明细 (ChatGPT / Suno / MiniMax / 百度网盘 / 哔哩哔哩 等) -->
        <div id="other-accounts-panel" class="panel rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <i class="fa-solid fa-layer-group text-sky-400 text-xs"></i>
              <h3 class="text-sm font-semibold text-slate-200">多平台服务账号</h3>
              <span id="other-accounts-count" class="text-[11px] px-1.5 py-0.5 rounded bg-slate-800/90 text-slate-400 font-mono">0</span>
            </div>
            <span class="text-[11px] text-slate-500">自动识别昵称、邮箱、会员等级与实时资产</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-300">
              <thead class="bg-[#090d16] text-[11px] uppercase text-slate-400 border-b border-slate-800 whitespace-nowrap">
                <tr>
                  <th class="py-3 px-3 font-medium">平台</th>
                  <th class="py-3 px-3 font-medium">账号信息</th>
                  <th class="py-3 px-3 font-medium">会员等级</th>
                  <th class="py-3 px-3 font-medium">配额 / 资产</th>
                  <th class="py-3 px-3 font-medium">会话状态</th>
                  <th class="py-3 px-3 font-medium text-right">操作</th>
                </tr>
              </thead>
              <tbody id="other-accounts-tbody" class="divide-y divide-slate-800/60">
                <tr><td colspan="6" class="py-8 text-center text-slate-500">正在获取多平台账号数据...</td></tr>
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
      <!-- 视图 4.5: Gemini 原生对话托管与控制 (Conversations)    -->
      <!-- ==================================================== -->
      <section id="view-conversations" class="view-section space-y-4">
        <div class="panel rounded-xl p-5 space-y-4">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h2 class="text-base font-semibold text-slate-100 flex items-center gap-2">
                <i class="fa-solid fa-comments text-purple-400"></i>
                <span>Gemini 原生对话托管台</span>
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">无需打开网页端，直接监控本地/官网对话实时输出、完成提醒、随时停止并向原对话续发消息（已落盘持久化）</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <span id="gconv-sse-badge" class="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-slate-500" id="gconv-sse-dot"></span>
                <span id="gconv-sse-text">实时监听中</span>
              </span>
              <button type="button" onclick="syncGeminiConversations(this)" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs flex items-center gap-1.5 transition cursor-pointer">
                <i class="fa-solid fa-cloud-arrow-down text-sky-400"></i> 从官网同步列表
              </button>
              <button type="button" onclick="prepareNewGeminiConversation()" class="px-3 py-1.5 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/40 text-xs flex items-center gap-1.5 transition cursor-pointer">
                <i class="fa-solid fa-plus"></i> 新建对话
              </button>
            </div>
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <!-- 左侧对话列表 -->
            <div class="lg:col-span-4 border border-slate-800/80 rounded-xl bg-slate-950/30 p-3 flex flex-col gap-2 max-h-[620px] overflow-y-auto" id="gconv-list">
              <div class="text-xs text-slate-500 text-center py-8">点击「从官网同步列表」或「新建对话」开始</div>
            </div>

            <!-- 右侧对话详情与控制 -->
            <div class="lg:col-span-8 border border-slate-800/80 rounded-xl bg-slate-950/30 p-4 flex flex-col justify-between min-h-[520px] max-h-[620px]">
              <div class="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
                <div class="min-w-0">
                  <div class="text-sm font-semibold text-slate-100 truncate" id="gconv-active-title">未选择对话（可直接输入发起新对话）</div>
                  <div class="text-[11px] font-mono text-slate-400 flex flex-wrap items-center gap-2 mt-0.5" id="gconv-active-meta">
                    <span>cid: --</span>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span id="gconv-active-status" class="px-2 py-0.5 rounded-md text-[11px] font-mono bg-slate-800 text-slate-400 border border-slate-700">idle</span>
                  <button type="button" id="gconv-btn-refresh" onclick="refreshActiveGeminiConversation()" class="hidden px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs transition cursor-pointer" title="从官网 hNvQHb 拉取最新轮次">
                    <i class="fa-solid fa-rotate text-sky-400"></i> 同步消息
                  </button>
                  <button type="button" id="gconv-btn-stop" onclick="stopActiveGeminiConversation()" class="hidden px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-xs flex items-center gap-1 transition cursor-pointer">
                    <i class="fa-solid fa-stop"></i> 停止输出
                  </button>
                  <button type="button" id="gconv-btn-delete" onclick="deleteActiveGeminiConversation()" class="hidden px-2 py-1 rounded-lg bg-slate-900 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-slate-800 text-xs transition cursor-pointer" title="删除本地记录">
                    <i class="fa-regular fa-trash-can"></i>
                  </button>
                </div>
              </div>

              <!-- 消息流容器 -->
              <div id="gconv-messages" class="flex-1 overflow-y-auto py-3 space-y-3 pr-1">
                <div class="text-xs text-slate-500 text-center py-12">在下方输入消息即可发起新对话，或从左侧选择一条历史对话继续。</div>
              </div>

              <!-- 底部发送/续聊栏 -->
              <div class="pt-3 border-t border-slate-800/80 space-y-2">
                <div class="flex flex-wrap items-center gap-2">
                  <select id="gconv-model-select" aria-label="选择 Gemini 模型" class="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-sky-500">
                    <option value="gemini-3.6-flash">gemini-3.6-flash</option>
                    <option value="gemini-3.5-flash-lite">gemini-3.5-flash-lite</option>
                    <option value="gemini-3.1-pro">gemini-3.1-pro</option>
                    <option value="gemini-3.8-flash">gemini-3.8-flash</option>
                    <option value="gemini-4-argon">gemini-4-argon</option>
                    <option value="gemini-3.6-flash-thinking">gemini-3.6-flash-thinking</option>
                    <option value="gemini-3.1-pro-thinking">gemini-3.1-pro-thinking</option>
                    <option value="gemini-4-argon-thinking">gemini-4-argon-thinking</option>
                  </select>
                  <span class="text-[11px] text-slate-500" id="gconv-send-hint">发送后自动落盘并实时监听完成</span>
                </div>
                <div class="flex gap-2">
                  <textarea id="gconv-input" rows="2" onkeydown="if(event.key==='Enter' && !event.shiftKey){event.preventDefault(); sendGeminiConvMessage();}" placeholder="输入消息内容（Enter 发送，Shift+Enter 换行）..." class="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 resize-none"></textarea>
                  <button type="button" id="gconv-btn-send" onclick="sendGeminiConvMessage()" class="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium flex items-center gap-1.5 transition cursor-pointer shrink-0">
                    <i class="fa-solid fa-paper-plane"></i> 发送
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
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
                <span id="docs-openai-base-url" class="truncate">http://127.0.0.1:18800/v1</span>
                <button type="button" onclick="copyOpenAIBaseUrl(this)" class="text-slate-400 hover:text-sky-400 shrink-0 cursor-pointer" title="复制 Base URL">
                  <i class="fa-regular fa-copy"></i>
                </button>
              </div>
              <div class="bg-[#090d16] border border-slate-800 rounded-lg px-3 py-2 font-mono text-[11px] text-amber-200 flex items-center justify-between gap-2">
                <span id="docs-api-token-preview" class="truncate">Token 加载中...</span>
                <div class="flex items-center gap-1.5 shrink-0">
                  <button type="button" onclick="copyApiToken(this)" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[10px] transition cursor-pointer" title="复制 API Token">复制</button>
                  <button type="button" onclick="generateApiToken(this)" class="px-2 py-0.5 rounded bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 text-[10px] transition cursor-pointer" title="生成新 Token">生成</button>
                </div>
              </div>
            </div>
            <div class="mt-4 pt-3 border-t border-slate-800/70 flex items-center justify-between gap-2">
              <span class="text-slate-500 font-mono text-[11px] whitespace-nowrap">外网需 Bearer Token</span>
              <button type="button" onclick="exportToOpenCode()" class="px-2.5 py-1 rounded-md bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 transition cursor-pointer whitespace-nowrap shrink-0">
                写入 OpenCode
              </button>
            </div>
          </div>
        </div>
      </section>

    </main>
  </div>

  <!-- 远程访问鉴权弹窗 -->
  <div id="auth-unlock-modal" class="hidden fixed inset-0 z-50 bg-black/75 backdrop-blur-sm items-center justify-center p-4">
    <div class="panel rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl border-slate-700/80">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400 flex items-center justify-center shrink-0">
          <i class="fa-solid fa-shield-halved"></i>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-slate-100">需要访问令牌 (Token)</h3>
          <p class="text-xs text-slate-400 mt-0.5">当前通过远程地址访问控制面板，请输入 API Token 解锁操作权限</p>
        </div>
      </div>
      <div class="space-y-2">
        <input type="password" id="auth-token-input" onkeydown="if(event.key==='Enter')submitAuthToken()" placeholder="粘贴 sk-css-... 访问令牌" class="w-full h-10 bg-[#090d16] border border-slate-700 rounded-lg px-3 text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500">
        <div id="auth-token-error" class="hidden text-xs text-rose-400"></div>
      </div>
      <div class="flex items-center justify-end gap-2">
        <button type="button" onclick="submitAuthToken()" id="btn-auth-unlock" class="w-full h-9 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold text-xs transition cursor-pointer">
          验证并解锁控制台
        </button>
      </div>
    </div>
  </div>

  <!-- 全局 Toast -->
  <div id="platform-context-menu" class="hidden fixed z-50 min-w-[184px] bg-[#131c2e] border border-slate-700/80 rounded-xl shadow-2xl p-1.5 text-xs text-slate-200 backdrop-blur-md select-none"></div>\r\n  <div id="live-toast" class="hidden fixed bottom-5 right-5 z-50 bg-[#131c2e] border border-sky-500/40 text-sky-200 text-xs px-4 py-2.5 rounded-xl shadow-xl items-center gap-2"></div>

  <!-- ======================================================== -->
  <!-- 3. 全局脚本 (JavaScript)                                 -->
  <!-- ======================================================== -->
  <script>
    const VIEW_META = {
      playground: { title: "调试台", subtitle: "多平台 API 在线调试与实时流式响应预览" },
      overview:   { title: "运行概览", subtitle: "实时子服务健康状态、扩展桥接与站点登录态" },
      accounts:      { title: "账号看板", subtitle: "全平台账号状态、会员等级、配额额度与健康度统一看板" },
      history:       { title: "对话历史", subtitle: "请求审计记录、耗时统计与完整上下文检索" },
      conversations: { title: "Gemini 对话", subtitle: "原生对话落盘托管、实时输出监控、停止与续聊控制" },
      endpoints:     { title: "接口清单", subtitle: "Cookie Service Suite 全部 RESTful API 索引" },
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
      gemini: [],
      aistudio: [
        ["gemini-4-argon", "gemini-4-argon (AI Studio 原生)"],
        ["gemini-3.8-flash", "gemini-3.8-flash"],
        ["gemini-3.5-flash-lite", "gemini-3.5-flash-lite"],
        ["gemini-3.1-pro-preview", "gemini-3.1-pro-preview"],
      ],
      gpt: [
        ["auto", "Auto（智能优选）"],
        ["gpt-6", "GPT-6（Instant / Thinking）"],
        ["gpt-6-plus", "GPT-6 Plus（Plus 专享）"],
        ["gpt-5-6", "GPT-5.6（Instant / Thinking）"],
        ["gpt-6-sol-wm", "GPT-6 Sol（协同工作区）"],
        ["gpt-5.6-sol-wm", "GPT-5.6 Sol（协同工作区）"],
        ["research", "Deep Research（全网深度研究）"],
        ["gpt-image-2", "GPT Image 2（绘图/动图）"],
        ["chatgpt-web", "ChatGPT Web（网页原生）"],
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

    // 全量 54 个 API 端点定义
    const ALL_ENDPOINTS = [
      // Google Gemini (7)
      { id: "gemini_chat", category: "gemini", method: "POST", url: "/api/pool/chat", name: "Gemini 智能对话", desc: "4账号 LRU 自动轮换，模型与网页选择器一致", body: { prompt: "请用一句话告诉我：量子纠缠是什么？", model: "gemini-4-hydrogen", reasoning_level: "off", stream: true, timeout: 300 } },
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
      { id: "chatgpt_image_batch", category: "chatgpt", method: "POST", url: "/api/chatgpt/image/batch", name: "ChatGPT 并发批量出图", desc: "支持多提示词或单提示词多张并发生成图片（可配置并发度 max_concurrency）", body: { prompts: ["一只在太空漂浮的橘猫，赛博朋克风格", "一座漂浮在云海上的玻璃图书馆，宫崎骏风格"], model: "gpt-image-2", n: 1, max_concurrency: 2, response_format: "b64_json" } },
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

      // Cookie Hub & 系统管理 (8)
      { id: "accounts_all", category: "system", method: "GET", url: "/api/accounts", name: "全平台账号看板汇总", desc: "聚合 Google、ChatGPT、Suno、MiniMax、百度网盘、B站 等平台账号、会员等级与配额", body: null },
      { id: "accounts_refresh", category: "system", method: "POST", url: "/api/accounts/refresh", name: "全平台账号刷新同步", desc: "刷新所有平台（或指定 ?platform=）账号信息、会员等级与配额状态", body: {} },
      { id: "system_overview", category: "system", method: "GET", url: "/api/system/overview", name: "系统全局运行总览", desc: "查看 Cookie Hub、Gemini 池、ChatGPT 与开机自启动全景状态", body: null },
      { id: "system_open_dir", category: "system", method: "POST", url: "/api/system/open-directory", name: "打开项目本地目录", desc: "在 Windows 资源管理器中弹出打开套件根目录文件夹", body: {} },
      { id: "system_autostart_get", category: "system", method: "GET", url: "/api/system/autostart", name: "查询 Windows 开机自启状态", desc: "检查注册表 Run 与开始菜单 Startup 双重持久化配置", body: null },
      { id: "system_autostart_toggle", category: "system", method: "POST", url: "/api/system/autostart/toggle", name: "一键切换开机自启动", desc: "在开启与关闭之间一键切换", body: {} },
      { id: "system_web_apis", category: "system", method: "GET", url: "/api/system/web-apis", name: "查看网页 API 启停开关", desc: "获取各个网页 API 的启停状态、关联域名与后台依赖进程状态", body: null },
      { id: "system_web_apis_toggle", category: "system", method: "POST", url: "/api/system/web-apis/gemini/toggle", name: "切换指定网页 API 启停", desc: "开启或关闭指定网页 API（关闭后停止获取/刷新 Cookie 并停止依赖后台程序）", body: { enabled: false } },
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

      if (viewKey === "conversations" && typeof loadGeminiConversations === "function") {
        loadGeminiConversations();
        if (typeof ensureGeminiConvSSE === "function") ensureGeminiConvSSE();
      }
      if (viewKey === "overview" && typeof loadGoogleSyncSettings === "function") {
        loadGoogleSyncSettings();
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
        const chatModels = data.chat_models || [];
        const taskModels = data.task_models || [];
        const models = (chatModels.length || taskModels.length) ? [...chatModels, ...taskModels] : (data.models || []);
        if (!models.length) return;
        const current = document.getElementById("model-selector");
        const before = current ? current.value : "";
        applyGeminiModelCatalog(models);
        if (currentPlaygroundCategory === "gemini") {
          populateModelSelector("gemini", before || "gemini-4-hydrogen");
          const after = document.getElementById("model-selector");
          if (after && after.value && after.value !== geminiBaseId(before)) onModelOrReasoningChange();
        }
      } catch (e) {}
    }

    function applyChatGPTModelCatalog(models) {
      const rows = [];
      (models || []).forEach(item => {
        if (!item) return;
        if (typeof item === "string") {
          rows.push([item, item, false]);
          return;
        }
        if (!item.id) return;
        rows.push([item.id, item.label || item.id, !!item.locked]);
      });
      if (!rows.length) return;
      MODELS_BY_PLATFORM.gpt = rows;
    }

    async function refreshChatGPTModelCatalog() {
      try {
        const res = await fetch("/api/chatgpt/models");
        const data = await res.json();
        const models = data.models || [];
        if (!models.length) return;
        const current = document.getElementById("model-selector");
        const before = current ? current.value : "";
        applyChatGPTModelCatalog(models);
        if (currentPlaygroundCategory === "gpt") {
          populateModelSelector("gpt", before || "auto");
          const after = document.getElementById("model-selector");
          if (after && before && after.value !== before) onModelOrReasoningChange();
        }
      } catch (e) {}
    }

    function resolveGeminiModel(baseModel, reasoning) {
      const raw = geminiBaseId(baseModel);
      if (raw === "gemini-4-carbon" || raw.endsWith("-task")) return raw;
      if (reasoning === "high") return raw + "-thinking";
      if (reasoning === "medium" && raw === "gemini-4-argon") return raw + "-thinking-medium";
      return raw;
    }

    function populateModelSelector(platformKey, preferred) {
      const select = document.getElementById("model-selector");
      const models = MODELS_BY_PLATFORM[platformKey];
      if (!select || !models || !models.length) {
        if (select) select.innerHTML = '<option value="">加载中...</option>';
        return;
      }
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
      if (catKey === "gpt") refreshChatGPTModelCatalog();
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
    // 剪贴板与通知工具 (支持 HTTP 环境降级复制)
    // ==========================================
    function fallbackCopyText(text) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.top = "-9999px";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      let ok = false;
      try {
        ok = document.execCommand("copy");
      } catch (e) {
        ok = false;
      }
      document.body.removeChild(ta);
      return ok;
    }

    function copyText(text, btn) {
      const onSuccess = () => {
        if (btn) {
          const oldHtml = btn.innerHTML;
          btn.innerHTML = "已复制";
          setTimeout(() => { btn.innerHTML = oldHtml; }, 1400);
        }
        showToast("已复制: " + (text.length > 48 ? text.slice(0, 48) + "..." : text));
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(onSuccess).catch(() => {
          if (fallbackCopyText(text)) onSuccess();
          else showToast("复制失败，请手动选中复制");
        });
      } else if (fallbackCopyText(text)) {
        onSuccess();
      } else {
        showToast("当前环境不支持自动剪贴板写入，请手动复制");
      }
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

        const rawText = await resp.text();
        let data = {};
        if (rawText && rawText.trim()) {
          try {
            data = JSON.parse(rawText);
          } catch (parseErr) {
            out.innerText = `[HTTP ${resp.status} ${resp.statusText || ""}] 非 JSON 响应：\n${rawText}`;
            return;
          }
        } else {
          out.innerText = `[HTTP ${resp.status} ${resp.statusText || ""}] 响应体为空（请检查网络连接、代理或服务是否正在重启）`;
          return;
        }
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
        if (chatgpt.enabled === false) gptText.innerText = "已关闭 (不获取 Cookie)";
        else if (chatgpt.logged_in === false) gptText.innerText = "未登录 chatgpt.com";
        else if (chatgpt.plan_label) gptText.innerText = "已登录 · " + chatgpt.plan_label;
        else if (chatgpt.logged_in) gptText.innerText = "浏览器已登录";
      }
      const geminiText = document.getElementById("gemini-status-text");
      if (geminiText && gemini) {
        if (gemini.enabled === false) geminiText.innerText = "已关闭 (后台已停)";
        else if (gemini.logged_in === false) geminiText.innerText = "未登录 Gemini";
      }
      const aisText = document.getElementById("aistudio-status-text");
      if (aisText && aistudio) {
        if (aistudio.enabled === false) {
          aisText.innerHTML = `<span class="inline-block w-2 h-2 rounded-full bg-slate-500"></span> 已关闭 (后台已停)`;
        } else if (aistudio.logged_in === false) {
          aisText.innerHTML = `<span class="inline-block w-2 h-2 rounded-full bg-amber-400"></span> 未登录 AI Studio`;
        }
      }

      if (overviewList && services.length) {
        overviewList.innerHTML = services.map(s => {
          if (s.enabled === false) {
            return `
              <div class="bg-[#090d16] border border-slate-800/60 rounded-lg px-3 py-2.5 flex items-center justify-between gap-2 opacity-75">
                <div class="flex items-center gap-2 min-w-0">
                  <span class="w-2 h-2 rounded-full shrink-0 bg-slate-500"></span>
                  <span class="text-slate-400 font-medium truncate">${escapeHtml(s.name || s.id)}</span>
                </div>
                <div class="shrink-0"><span class="text-slate-500 font-mono text-[11px]">已关闭 · 不获取 Cookie</span></div>
              </div>
            `;
          }
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

    let dashboardRefreshing = false;
    let lastAccountsRefreshAt = 0;

    async function fetchWithTimeout(url, opts = {}, timeoutMs = 15000) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        return await fetch(url, Object.assign({}, opts, { signal: controller.signal }));
      } finally {
        clearTimeout(timer);
      }
    }

    async function refreshLoginGuide() {
      try {
        const res = await fetchWithTimeout("/api/system/logins", {}, 10000);
        if (!res.ok) return;
        renderLoginGuide(await res.json());
      } catch (e) {}
    }

    async function refreshDashboard(forceAccounts = true) {
      if (dashboardRefreshing && !forceAccounts) return;
      dashboardRefreshing = true;
      const icon = document.getElementById("sidebar-refresh-icon");
      if (icon) icon.classList.add("fa-spin");

      try {
        const refreshOverviewTask = async () => {
          const sysRes = await fetchWithTimeout("/api/system/overview", {}, 12000);
          if (!sysRes.ok) return;
          const sys = await sysRes.json();
          const mins = Math.round((sys.uptime_seconds || 0) / 60);
          const uptimeStr = mins >= 60 ? `${(mins / 60).toFixed(1)}h` : `${mins}m`;
          document.getElementById("uptime-text").innerText = uptimeStr;
          const miniUp = document.getElementById("sidebar-uptime-mini");
          if (miniUp) miniUp.innerText = uptimeStr;
          const listenEl = document.getElementById("sidebar-listen-addr");
          if (listenEl && sys.listen_host && sys.listen_port) {
            listenEl.innerText = `${sys.listen_host}:${sys.listen_port}`;
          }

          const hubOk = sys.services?.cookie_hub?.extension_connected;
          document.getElementById("hub-status-text").innerHTML = hubOk
            ? `<span class="inline-block w-2 h-2 rounded-full bg-emerald-400"></span> 扩展已连接`
            : `<span class="inline-block w-2 h-2 rounded-full bg-rose-400"></span> 扩展未连接`;
          document.getElementById("hub-clients").innerText = `客户端: ${sys.services?.cookie_hub?.clients || 0}`;

          const gemInfo = sys.services?.gemini_pool;
          const readyCount = gemInfo?.active_accounts;
          if (gemInfo && gemInfo.enabled === false) {
            document.getElementById("gemini-status-text").innerText = "已关闭 (后台已停)";
          } else {
            document.getElementById("gemini-status-text").innerText = readyCount ? `${readyCount} 账号就绪` : "正在同步账号";
          }

          const ais = sys.services?.aistudio;
          const aisText = document.getElementById("aistudio-status-text");
          const aisModels = document.getElementById("aistudio-models-count");
          if (aisText && ais) {
            if (ais.enabled === false) {
              aisText.innerHTML = `<span class="inline-block w-2 h-2 rounded-full bg-slate-500"></span> 已关闭 (后台已停)`;
            } else if (ais.running && ais.data_plane_ready) {
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

          const gptInfo = sys.services?.chatgpt;
          const gptRunning = gptInfo?.reverse_running;
          if (gptInfo && gptInfo.enabled === false) {
            document.getElementById("chatgpt-status-text").innerText = "已关闭 (后台已停)";
          } else {
            document.getElementById("chatgpt-status-text").innerText = gptRunning ? "逆向运行中" : "就绪 (按需启动)";
          }

          if (Array.isArray(sys.web_apis)) {
            renderWebApiSwitches(sys.web_apis);
          } else {
            await loadWebApiSwitches();
          }

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
        };

        const refreshAccountsTask = async () => {
          const shouldRefreshAccounts = forceAccounts || currentView === "accounts" || (Date.now() - lastAccountsRefreshAt >= 30000);
          if (!shouldRefreshAccounts) return;
          let acctData = null;
          try {
            const acctRes = await fetchWithTimeout("/api/accounts", {}, 18000);
            if (acctRes.ok) {
              acctData = await acctRes.json();
            }
          } catch (acctErr) {}

          if (!acctData) {
            const gemRes = await fetchWithTimeout("/api/gemini/accounts", {}, 10000);
            if (gemRes.ok) {
              const gemJson = await gemRes.json();
              const gemList = (gemJson.accounts || []).map(a => Object.assign({}, a, {
                platform: "gemini",
                platform_name: "Google Gemini",
                raw_id: a.id,
                id: `gemini:${a.id}`,
                is_member: ["PRO", "ULTRA", "PLUS"].includes(String(a.plan_tier || "").toUpperCase()),
                membership_label: a.plan_tier ? `Google ${String(a.plan_tier).toUpperCase()}` : "免费版",
              }));
              acctData = {
                total: gemList.length,
                visible_total: gemList.filter(a => a.visible).length,
                member_total: gemList.filter(a => a.visible && a.is_member).length,
                platforms_order: ["gemini", "chatgpt", "suno", "minimax", "baidupan", "bilibili"],
                platforms: {
                  gemini: { platform: "gemini", platform_name: "Google", login_url: "https://gemini.google.com/", logged_in: gemList.some(a => a.visible), account_count: gemList.filter(a => a.visible).length, member_count: gemList.filter(a => a.visible && a.is_member).length, error: null },
                },
                accounts: gemList,
              };
            }
          }

          if (acctData) {
            lastAccountsRefreshAt = Date.now();
            latestAccountsPayload = acctData;
            renderAccountsDashboard(acctData);
          }
        };

        await Promise.allSettled([
          refreshOverviewTask(),
          refreshAccountsTask(),
          refreshLoginGuide(),
          loadChatHistory(currentHistoryPage, false),
        ]);
      } catch (e) {
        console.error("刷新失败:", e);
      } finally {
        dashboardRefreshing = false;
        if (icon) icon.classList.remove("fa-spin");
      }
    }

    const WEB_API_ICON_META = {
      gemini:   { icon: "/assets/icons/gemini.svg",   fallbackIcon: "fa-solid fa-sparkles text-purple-400" },
      aistudio: { icon: "/assets/icons/gemini.svg",   fallbackIcon: "fa-solid fa-wand-magic-sparkles text-cyan-400" },
      chatgpt:  { icon: "/assets/icons/chatgpt.png",  fallbackIcon: "fa-solid fa-robot text-emerald-400" },
      suno:     { icon: "/assets/icons/suno.png",     fallbackIcon: "fa-solid fa-music text-amber-400" },
      minimax:  { icon: null,                         fallbackIcon: "fa-solid fa-microphone-lines text-rose-400" },
      baidupan: { icon: "/assets/icons/baidupan.png", fallbackIcon: "fa-solid fa-cloud text-blue-400" },
      bilibili: { icon: "/assets/icons/bilibili.png", fallbackIcon: "fa-solid fa-tv text-pink-400" },
      udio:     { icon: null,                         fallbackIcon: "fa-solid fa-headphones text-violet-400" },
    };

    let latestWebApiItems = [];

    function renderWebApiSwitches(items) {
      latestWebApiItems = Array.isArray(items) ? items : [];
      const grid = document.getElementById("web-api-switches-grid");
      const summaryEl = document.getElementById("web-api-switches-summary");
      if (!grid) return;

      const enabledCount = latestWebApiItems.filter(item => item.enabled !== false).length;
      if (summaryEl) {
        summaryEl.innerText = `已开启 ${enabledCount} / ${latestWebApiItems.length}`;
      }

      if (!latestWebApiItems.length) {
        grid.innerHTML = `<div class="col-span-full py-6 text-center text-xs text-slate-500">暂无网页 API 配置</div>`;
        return;
      }

      grid.innerHTML = latestWebApiItems.map(item => {
        const sid = item.id;
        const enabled = item.enabled !== false;
        const iconMeta = WEB_API_ICON_META[sid] || { icon: null, fallbackIcon: "fa-solid fa-plug text-sky-400" };
        const iconHtml = iconMeta.icon
          ? `<img src="${iconMeta.icon}" alt="${escapeHtml(item.name)}" class="w-4 h-4 object-contain shrink-0" data-fallback="${iconMeta.fallbackIcon}" onerror="handlePlatformIconError(this, this.dataset.fallback)">`
          : `<i class="${iconMeta.fallbackIcon} text-xs"></i>`;

        const daemonText = item.has_daemon
          ? (item.daemon_running
              ? `<span class="text-emerald-400 font-mono">后台运行中</span>`
              : `<span class="text-slate-500 font-mono">后台已停止</span>`)
          : `<span class="text-slate-500 font-mono">无独立后台程序</span>`;

        const cookieBadge = enabled
          ? `<span class="inline-flex items-center gap-1 text-[10px] text-emerald-400"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>允许获取/刷新 Cookie</span>`
          : `<span class="inline-flex items-center gap-1 text-[10px] text-rose-400"><span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>已停止获取/刷新 Cookie</span>`;

        const cardBorder = enabled ? "border-slate-800/90" : "border-slate-800/50 opacity-80";

        return `
          <div class="bg-[#090d16] border ${cardBorder} rounded-xl p-3.5 flex flex-col justify-between gap-2.5 transition" data-web-api-card="${escapeHtml(sid)}">
            <div class="flex items-start justify-between gap-2">
              <div class="flex items-center gap-2 min-w-0">
                <div class="w-7 h-7 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center shrink-0">
                  ${iconHtml}
                </div>
                <div class="min-w-0">
                  <div class="text-xs font-semibold text-slate-100 truncate">${escapeHtml(item.name)}</div>
                  <div class="text-[10px] text-slate-500 truncate">${escapeHtml(item.category || "")}</div>
                </div>
              </div>
              <button type="button"
                      role="switch"
                      aria-checked="${enabled ? "true" : "false"}"
                      aria-label="切换 ${escapeHtml(item.name)} 网页 API"
                      id="switch-web-api-${escapeHtml(sid)}"
                      onclick="toggleWebApiService('${escapeHtml(sid)}', ${enabled ? "false" : "true"}, this)"
                      class="api-switch"
                      title="${enabled ? "点击关闭（停止获取/刷新 Cookie 与依赖后台）" : "点击开启"}">
                <span class="api-switch-thumb"></span>
              </button>
            </div>
            <div class="text-[11px] text-slate-400 line-clamp-2">${escapeHtml(item.description || "")}</div>
            <div class="pt-2 border-t border-slate-800/70 flex items-center justify-between gap-2 text-[10px]">
              ${cookieBadge}
              ${daemonText}
            </div>
            ${item.daemon_label ? `<div class="text-[10px] text-slate-500 font-mono truncate" title="${escapeHtml(item.daemon_label)}">依赖: ${escapeHtml(item.daemon_label)}</div>` : ""}
          </div>
        `;
      }).join("");
    }

    async function loadWebApiSwitches() {
      try {
        const res = await fetch("/api/system/web-apis");
        if (!res.ok) return;
        const data = await res.json();
        if (Array.isArray(data.items)) {
          renderWebApiSwitches(data.items);
        }
      } catch (e) {}
    }

    async function toggleWebApiService(serviceId, targetEnabled, btnEl) {
      if (btnEl) btnEl.disabled = true;
      try {
        const payload = (typeof targetEnabled === "boolean") ? { enabled: targetEnabled } : {};
        const res = await fetch(`/api/system/web-apis/${encodeURIComponent(serviceId)}/toggle`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.detail || "切换网页 API 状态失败");
        }
        if (Array.isArray(data.items)) {
          renderWebApiSwitches(data.items);
        }
        showToast(data.message || `${data.name || serviceId} 已${data.enabled ? "开启" : "关闭"}`);
        await refreshDashboard();
      } catch (err) {
        showToast("操作失败: " + err.message);
      } finally {
        if (btnEl) btnEl.disabled = false;
      }
    }

    const ACCOUNT_PLATFORM_META = {
      all:      { label: "全部",     icon: "/assets/icons/all.svg",      fallbackIcon: "fa-solid fa-shapes text-sky-400",          badgeClass: "bg-sky-500/15 text-sky-300 border-sky-500/30",          avatarClass: "text-sky-300" },
      gemini:   { label: "Google",   icon: "/assets/icons/gemini.svg",   fallbackIcon: "fa-solid fa-sparkles text-purple-400",     badgeClass: "bg-purple-500/15 text-purple-300 border-purple-500/30", avatarClass: "text-purple-300" },
      chatgpt:  { label: "ChatGPT",  icon: "/assets/icons/chatgpt.png",  fallbackIcon: "fa-solid fa-robot text-emerald-400",       badgeClass: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", avatarClass: "text-emerald-300" },
      suno:     { label: "Suno",     icon: "/assets/icons/suno.png",     fallbackIcon: "fa-solid fa-music text-amber-400",         badgeClass: "bg-amber-500/15 text-amber-300 border-amber-500/30",    avatarClass: "text-amber-300" },
      minimax:  { label: "MiniMax",  icon: null,                         fallbackIcon: "fa-solid fa-microphone-lines text-rose-400", badgeClass: "bg-rose-500/15 text-rose-300 border-rose-500/30",     avatarClass: "text-rose-300" },
      baidupan: { label: "百度网盘", icon: "/assets/icons/baidupan.png", fallbackIcon: "fa-solid fa-cloud text-blue-400",          badgeClass: "bg-blue-500/15 text-blue-300 border-blue-500/30",       avatarClass: "text-blue-300" },
      bilibili: { label: "哔哩哔哩", icon: "/assets/icons/bilibili.png", fallbackIcon: "fa-solid fa-tv text-pink-400",             badgeClass: "bg-pink-500/15 text-pink-300 border-pink-500/30",       avatarClass: "text-pink-300" },
      udio:     { label: "Udio",     icon: null,                         fallbackIcon: "fa-solid fa-headphones text-violet-400",   badgeClass: "bg-violet-500/15 text-violet-300 border-violet-500/30", avatarClass: "text-violet-300" },
    };

    let currentAccountsFilter = "all";
    let latestAccountsPayload = null;

    function normalizeAccountPlatform(plat) {
      const key = String(plat || "").trim().toLowerCase();
      if (key === "baidu") return "baidupan";
      return key || "other";
    }

    function getAccountPlatformMeta(plat) {
      const key = normalizeAccountPlatform(plat);
      return ACCOUNT_PLATFORM_META[key] || {
        label: plat || "其他",
        icon: null,
        fallbackIcon: "fa-solid fa-circle-user text-slate-400",
        badgeClass: "bg-slate-800 text-slate-300 border-slate-700",
        avatarClass: "text-slate-300",
      };
    }

    function closeAccountPlatformContextMenu() {
      const menu = document.getElementById("platform-context-menu");
      if (menu) {
        menu.classList.add("hidden");
        menu.innerHTML = "";
      }
    }

    function openAccountPlatformContextMenu(event, plat) {
      if (!plat || plat === "all") return;
      event.preventDefault();
      event.stopPropagation();

      const menu = document.getElementById("platform-context-menu");
      if (!menu) return;

      const meta = getAccountPlatformMeta(plat);
      const platformsMap = (latestAccountsPayload && latestAccountsPayload.platforms) ? latestAccountsPayload.platforms : {};
      const pInfo = platformsMap[plat] || {};
      const isEnabled = pInfo.enabled !== false;

      const iconHtml = meta.icon
        ? `<img src="${meta.icon}" alt="${escapeHtml(meta.label)}" class="w-3.5 h-3.5 object-contain shrink-0" data-fallback="${meta.fallbackIcon}" onerror="handlePlatformIconError(this, this.dataset.fallback)">`
        : `<i class="${meta.fallbackIcon} text-xs"></i>`;

      menu.innerHTML = `
        <div class="px-2.5 py-1.5 mb-1 border-b border-slate-800/80 flex items-center justify-between gap-2">
          <div class="flex items-center gap-1.5 font-semibold text-slate-100 truncate">
            ${iconHtml}
            <span class="truncate">${escapeHtml(meta.label)}</span>
          </div>
          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono shrink-0 ${isEnabled ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400"}">${isEnabled ? "已启用" : "已禁用"}</span>
        </div>
        <button type="button" id="ctx-plat-toggle" class="w-full text-left px-2.5 py-1.5 rounded-lg flex items-center gap-2 transition cursor-pointer ${isEnabled ? "text-rose-300 hover:bg-rose-500/15" : "text-emerald-300 hover:bg-emerald-500/15"}">
          <i class="fa-solid ${isEnabled ? "fa-ban" : "fa-power-off"} w-3.5 text-center"></i>
          <span>${isEnabled ? `禁用 ${escapeHtml(meta.label)}` : `启用 ${escapeHtml(meta.label)}`}</span>
        </button>
        <button type="button" id="ctx-plat-filter" class="w-full text-left px-2.5 py-1.5 rounded-lg flex items-center gap-2 text-slate-300 hover:bg-slate-800/80 transition cursor-pointer">
          <i class="fa-solid fa-filter w-3.5 text-center text-sky-400"></i>
          <span>仅看 ${escapeHtml(meta.label)}</span>
        </button>
        ${isEnabled ? `
        <button type="button" id="ctx-plat-refresh" class="w-full text-left px-2.5 py-1.5 rounded-lg flex items-center gap-2 text-slate-300 hover:bg-slate-800/80 transition cursor-pointer">
          <i class="fa-solid fa-arrows-rotate w-3.5 text-center text-amber-400"></i>
          <span>刷新 ${escapeHtml(meta.label)}</span>
        </button>` : ""}
      `;

      menu.classList.remove("hidden");
      const rect = menu.getBoundingClientRect();
      const vw = window.innerWidth || document.documentElement.clientWidth;
      const vh = window.innerHeight || document.documentElement.clientHeight;
      const left = Math.min(Math.max(8, event.clientX), Math.max(8, vw - rect.width - 8));
      const top = Math.min(Math.max(8, event.clientY), Math.max(8, vh - rect.height - 8));
      menu.style.left = `${left}px`;
      menu.style.top = `${top}px`;

      const toggleBtn = document.getElementById("ctx-plat-toggle");
      if (toggleBtn) {
        toggleBtn.onclick = () => {
          closeAccountPlatformContextMenu();
          toggleWebApiService(plat, !isEnabled);
        };
      }
      const filterBtn = document.getElementById("ctx-plat-filter");
      if (filterBtn) {
        filterBtn.onclick = () => {
          closeAccountPlatformContextMenu();
          setAccountsPlatformFilter(plat);
        };
      }
      const refreshBtn = document.getElementById("ctx-plat-refresh");
      if (refreshBtn) {
        refreshBtn.onclick = () => {
          closeAccountPlatformContextMenu();
          refreshPlatformAccounts(plat);
        };
      }
    }

    document.addEventListener("click", (e) => {
      const menu = document.getElementById("platform-context-menu");
      if (menu && !menu.classList.contains("hidden") && !menu.contains(e.target)) {
        closeAccountPlatformContextMenu();
      }
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeAccountPlatformContextMenu();
    });
    window.addEventListener("scroll", closeAccountPlatformContextMenu, true);

    function setAccountsPlatformFilter(plat) {
      currentAccountsFilter = plat || "all";
      if (latestAccountsPayload) {
        renderAccountsDashboard(latestAccountsPayload);
      }
    }

    function isAccountVisibleActive(a) {
      if (!a) return false;
      if (a.visible === false) return false;
      const st = String(a.status || "").toLowerCase();
      return st !== "not_logged_in" && st !== "deleted";
    }

    function renderAccountSourceLabel(source) {
      const map = {
        reverse_pool: "逆向池",
        browser_session: "浏览器",
        browser: "浏览器",
        cookie_hub: "Cookie Hub",
        local_cache: "本地缓存",
        official: "官网同步",
      };
      const key = String(source || "").trim().toLowerCase();
      return map[key] || (source ? String(source) : "");
    }

    function renderMembershipBadge(account) {
      const isMember = !!account.is_member;
      const tier = String(account.plan_tier || "").trim().toUpperCase();
      const label = String(account.membership_label || "").trim() || (isMember ? (tier || "付费会员") : "免费版");

      if (!isMember) {
        return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-800/80 text-slate-400 border border-slate-700/80 whitespace-nowrap">${escapeHtml(label)}</span>`;
      }

      let styleClass = "bg-sky-500/15 text-sky-300 border-sky-500/35";
      if (["ULTRA", "PREMIER", "SVIP"].includes(tier) || /超级会员|SVIP|Premier|Ultra/i.test(label)) {
        styleClass = "bg-amber-500/15 text-amber-300 border-amber-500/35";
      } else if (["PRO", "TEAM", "ENTERPRISE"].includes(tier) || /\bPro\b|Team|Enterprise/i.test(label)) {
        styleClass = "bg-indigo-500/15 text-indigo-300 border-indigo-500/35";
      } else if (/大会员/.test(label)) {
        styleClass = "bg-pink-500/15 text-pink-300 border-pink-500/35";
      } else if (tier === "PLUS" || /Plus/i.test(label)) {
        styleClass = "bg-emerald-500/15 text-emerald-300 border-emerald-500/35";
      }

      return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border whitespace-nowrap ${styleClass}"><i class="fa-solid fa-crown text-[9px]"></i><span>${escapeHtml(label)}</span></span>`;
    }

    function renderAccountStatusBadge(status, isGoogle = false) {
      const st = String(status || "").toLowerCase();
      if (st === "enabled" || st === "ready" || st === "active" || st === "online") {
        const text = isGoogle ? "已启用" : (st === "enabled" ? "已启用" : "已连接");
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border whitespace-nowrap bg-emerald-500/10 text-emerald-400 border-emerald-500/30"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>${text}</span>`;
      }
      if (st === "disabled") {
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border whitespace-nowrap bg-slate-800 text-slate-400 border-slate-700"><span class="w-1.5 h-1.5 rounded-full bg-slate-500"></span>已停用</span>`;
      }
      if (st === "not_logged_in") {
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border whitespace-nowrap bg-amber-500/10 text-amber-300 border-amber-500/30"><span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>未登录</span>`;
      }
      if (st === "offline" || st === "expired") {
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border whitespace-nowrap bg-amber-500/10 text-amber-300 border-amber-500/30"><span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>${st === "expired" ? "凭证过期" : "离线"}</span>`;
      }
      if (st === "error") {
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border whitespace-nowrap bg-rose-500/10 text-rose-300 border-rose-500/30"><span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>异常</span>`;
      }
      return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border whitespace-nowrap bg-slate-800 text-slate-400 border-slate-700"><span class="w-1.5 h-1.5 rounded-full bg-slate-500"></span>${escapeHtml(status || "未知")}</span>`;
    }

    function safeExternalUrl(url) {
      const s = String(url || "").trim();
      return /^https?:\/\//i.test(s) ? s : "";
    }

    function renderAccountsDashboard(data) {
      const platformsMap = data.platforms || {};
      const defaultOrder = ["gemini", "chatgpt", "suno", "minimax", "baidupan", "bilibili"];
      const orderRaw = Array.isArray(data.platforms_order) && data.platforms_order.length ? data.platforms_order : defaultOrder;
      const platformsOrder = [];
      orderRaw.forEach(p => {
        const norm = normalizeAccountPlatform(p);
        if (!platformsOrder.includes(norm)) platformsOrder.push(norm);
      });

      const allAccounts = Array.isArray(data.accounts) ? data.accounts : [];
      const activeAccounts = allAccounts.filter(isAccountVisibleActive);
      const googleAccounts = activeAccounts.filter(a => normalizeAccountPlatform(a.platform) === "gemini");
      const otherAccounts = activeAccounts.filter(a => normalizeAccountPlatform(a.platform) !== "gemini");

      const totalCount = activeAccounts.length;
      const memberCount = activeAccounts.filter(a => !!a.is_member).length;
      const activePlatformKeys = new Set(activeAccounts.map(a => normalizeAccountPlatform(a.platform)));
      Object.entries(platformsMap).forEach(([k, info]) => {
        if (info && (info.logged_in === true || (info.account_count || 0) > 0)) {
          activePlatformKeys.add(normalizeAccountPlatform(k));
        }
      });

      const navCount = document.getElementById("nav-account-count");
      if (navCount) navCount.innerText = totalCount > 0 ? String(totalCount) : "0";

      const statTotal = document.getElementById("accounts-stat-total");
      const statMembers = document.getElementById("accounts-stat-members");
      const statPlatforms = document.getElementById("accounts-stat-platforms");
      if (statTotal) statTotal.innerText = String(totalCount);
      if (statMembers) statMembers.innerText = String(memberCount);
      if (statPlatforms) statPlatforms.innerText = `${activePlatformKeys.size}/${platformsOrder.length}`;

      const summary = document.getElementById("accounts-summary");
      if (summary) {
        if (totalCount > 0) {
          const activeNames = platformsOrder
            .filter(p => activeAccounts.some(a => normalizeAccountPlatform(a.platform) === p))
            .map(p => getAccountPlatformMeta(p).label);
          summary.innerText = `已同步 ${totalCount} 个账号（含 ${memberCount} 个付费会员），已覆盖：${activeNames.join("、")}`;
        } else {
          summary.innerText = "暂未检测到已登录账号，请在浏览器登录对应平台并确保 Cookie Hub 已连接";
        }
      }

      // 渲染平台过滤胶囊
      const filtersEl = document.getElementById("accounts-platform-filters");
      if (filtersEl) {
        const filterKeys = ["all", ...platformsOrder];
        if (!filterKeys.includes(currentAccountsFilter)) currentAccountsFilter = "all";

        filtersEl.innerHTML = filterKeys.map(key => {
          const meta = getAccountPlatformMeta(key);
          const isActive = currentAccountsFilter === key;
          const cnt = key === "all"
            ? totalCount
            : activeAccounts.filter(a => normalizeAccountPlatform(a.platform) === key).length;
          const pInfo = platformsMap[key];
          const isPlatEnabled = key === "all" ? true : !(pInfo && pInfo.enabled === false);
          const hasLogin = key === "all" ? totalCount > 0 : (cnt > 0 || (pInfo && pInfo.logged_in === true));
          const iconHtml = meta.icon
            ? `<img src="${meta.icon}" alt="${escapeHtml(meta.label)}" class="w-3.5 h-3.5 object-contain shrink-0" data-fallback="${meta.fallbackIcon}" onerror="handlePlatformIconError(this, this.dataset.fallback)">`
            : `<i class="${meta.fallbackIcon} text-xs"></i>`;
          const countBadgeClass = !isPlatEnabled
            ? "bg-rose-500/15 text-rose-400"
            : (isActive ? "bg-sky-500/20 text-sky-300" : (hasLogin ? "bg-emerald-500/15 text-emerald-300" : "bg-slate-800 text-slate-500"));
          return `
            <button type="button" onclick="setAccountsPlatformFilter('${escapeHtml(key)}')"${key !== "all" ? ` oncontextmenu="openAccountPlatformContextMenu(event, '${escapeHtml(key)}')"` : ""}
                    title="${key !== "all" ? `左键筛选 ${escapeHtml(meta.label)} · 右键${isPlatEnabled ? "禁用" : "启用"}` : "显示全部平台"}"
                    class="plat-pill shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs ${isActive ? "plat-pill-active" : "text-slate-300"} ${!isPlatEnabled ? "opacity-60" : ""}">
              ${iconHtml}
              <span class="${!isPlatEnabled ? "line-through opacity-80" : ""}">${escapeHtml(meta.label)}</span>
              <span class="text-[10px] font-mono px-1 rounded ${countBadgeClass}">${!isPlatEnabled ? "已禁用" : cnt}</span>
            </button>
          `;
        }).join("");
      }

      const refreshBtn = document.getElementById("btn-refresh-accounts");
      if (refreshBtn && !refreshBtn.disabled) {
        const filterLabel = currentAccountsFilter === "all" ? "刷新全部" : `刷新 ${getAccountPlatformMeta(currentAccountsFilter).label}`;
        refreshBtn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> ${escapeHtml(filterLabel)}`;
      }

      // 控制 Google / 其他平台面板显隐
      const googlePanel = document.getElementById("google-accounts-panel");
      const otherPanel = document.getElementById("other-accounts-panel");
      const showGoogle = currentAccountsFilter === "all" || currentAccountsFilter === "gemini";
      const showOther = currentAccountsFilter !== "gemini";
      if (googlePanel) googlePanel.classList.toggle("hidden", !showGoogle);
      if (otherPanel) otherPanel.classList.toggle("hidden", !showOther);

      if (showGoogle) {
        renderGoogleAccountsTable(googleAccounts, platformsMap.gemini || null);
      }
      if (showOther) {
        renderOtherAccountsTable(otherAccounts, platformsMap, platformsOrder, currentAccountsFilter);
      }
    }

    function formatPaceEta(secs) {
      if (secs === null || secs === undefined) return "";
      const n = Math.max(0, Math.round(Number(secs) || 0));
      if (n <= 0) return "已触及上限";
      const d = Math.floor(n / 86400);
      const h = Math.floor((n % 86400) / 3600);
      const m = Math.floor((n % 3600) / 60);
      if (d > 0) return `${d}天 ${h}h`;
      if (h > 0) return `${h}h ${m}m`;
      return `${Math.max(1, m)}m`;
    }

    function resolveQuotaPace(paceObj, fallbackUsedPct, resetEpoch, windowSec, fetchedAt, minElapsedSec) {
      if (paceObj && typeof paceObj === "object" && typeof paceObj.projected_pct === "number") {
        return paceObj;
      }
      const pct = Math.max(0, Number(fallbackUsedPct) || 0);
      const winSec = Math.max(1, Number(windowSec) || 18000);
      const minEl = Math.max(1, Number(minElapsedSec) || 300);
      let elapsed = 0;
      let remaining = winSec;
      const rEpoch = Number(resetEpoch) || 0;
      if (rEpoch > 0) {
        const fAt = Number(fetchedAt) || 0;
        const nowSec = Math.floor(Date.now() / 1000);
        const refTs = nowSec >= rEpoch ? nowSec : (fAt > 0 && fAt < rEpoch ? fAt : nowSec);
        remaining = Math.max(0, rEpoch - refTs);
        elapsed = remaining === 0 ? winSec : Math.min(winSec, Math.max(minEl, winSec - remaining));
      }
      let ratePerHour = 0;
      let projected = 0;
      if (pct > 0) {
        if (elapsed > 0) {
          ratePerHour = pct / (elapsed / 3600);
          projected = pct * (winSec / elapsed);
          if (pct >= 100) projected = Math.max(100, projected);
        } else {
          projected = pct;
        }
      }
      const projectedRound = Math.round(Math.min(projected, 999.9) * 10) / 10;
      const rateHourRound = Math.round(ratePerHour * 100) / 100;
      const rateDayRound = Math.round(ratePerHour * 24 * 100) / 100;
      let level = "green";
      let color = "emerald";
      let label = "充裕";
      if (pct >= 100 || projectedRound >= 100) {
        level = "red";
        color = "rose";
        label = "预计超限";
      } else if (projectedRound > 90) {
        level = "yellow";
        color = "amber";
        label = "接近上限";
      }
      let eta = null;
      if (pct >= 100) eta = 0;
      else if (ratePerHour > 0 && projectedRound >= 100) eta = Math.round(((100 - pct) / ratePerHour) * 3600);
      return {
        projected_pct: projectedRound,
        level,
        color,
        label,
        rate_per_hour: rateHourRound,
        rate_per_day: rateDayRound,
        elapsed_sec: Math.round(elapsed),
        remaining_sec: remaining,
        eta_to_limit_sec: eta,
      };
    }

    function renderQuotaPaceDot(pace, isWeekly) {
      const level = pace && pace.level ? String(pace.level) : "green";
      const dotCls = level === "red"
        ? "bg-rose-500 shadow-[0_0_6px_rgba(244,63,94,0.75)]"
        : (level === "yellow"
            ? "bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.7)]"
            : "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.65)]");
      const winName = isWeekly ? "周" : "5小时";
      const statusRule = level === "red"
        ? "预计超限 ≥100%"
        : (level === "yellow" ? "接近上限 90%~100%" : "充裕 ≤90%");
      const rateTxt = isWeekly
        ? `${Number(pace.rate_per_day || 0).toFixed(1)}%/天`
        : `${Number(pace.rate_per_hour || 0).toFixed(1)}%/h`;
      const parts = [
        `${winName}消耗预估：${statusRule}`,
        `当前速率 ${rateTxt}`,
        `预计本周期消耗 ${Number(pace.projected_pct || 0).toFixed(1)}%`,
      ];
      if (pace.eta_to_limit_sec !== null && pace.eta_to_limit_sec !== undefined) {
        parts.push(pace.eta_to_limit_sec === 0 ? "已达上限" : `约 ${formatPaceEta(pace.eta_to_limit_sec)} 触及上限`);
      }
      const tip = parts.join(" · ");
      return `<span class="inline-block w-2 h-2 rounded-full ${dotCls} shrink-0 cursor-help" data-quota-pace="${isWeekly ? "weekly" : "5h"}" data-pace-level="${escapeHtml(level)}" data-projected-pct="${escapeHtml(String(pace.projected_pct ?? 0))}" title="${escapeHtml(tip)}" aria-label="${escapeHtml(tip)}"></span>`;
    }

    function renderGoogleAccountsTable(accounts, geminiInfo) {
      const tbody = document.getElementById("accounts-tbody");
      const countEl = document.getElementById("google-accounts-count");
      if (countEl) countEl.innerText = String(accounts.length);
      if (!tbody) return;
      tbody.innerHTML = "";

      if (!accounts.length) {
        if (geminiInfo && geminiInfo.enabled === false) {
          tbody.innerHTML = `
            <tr>
              <td colspan="5" class="py-7 text-center text-slate-500">
                <span>Google Gemini 网页 API 已在管理控制台关闭，已停止获取/刷新 Cookie 与后台号池</span>
                <button type="button" onclick="toggleWebApiService('gemini', true, this)" class="ml-2 px-2.5 py-1 rounded-md bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 text-[11px] cursor-pointer">开启 Gemini</button>
              </td>
            </tr>`;
          return;
        }
        const loginUrl = safeExternalUrl(geminiInfo && geminiInfo.login_url) || "https://gemini.google.com/";
        tbody.innerHTML = `
          <tr>
            <td colspan="5" class="py-7 text-center text-slate-500">
              <span>暂无可见 Google 账号槽位，请先在浏览器登录 Google 并确保 Cookie Hub 已连接</span>
              <a href="${escapeHtml(loginUrl)}" target="_blank" rel="noopener" class="ml-2 text-sky-400 hover:text-sky-300 underline">前往登录</a>
            </td>
          </tr>`;
        return;
      }

      accounts.forEach(a => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-900/40 transition";

        const rawId = (a.raw_id !== undefined && a.raw_id !== null)
          ? a.raw_id
          : (String(a.id || "").includes(":") ? String(a.id).split(":")[1] : a.id);
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

        const isOfficial = a.usage_source === "official";
        const tier = (a.plan_tier || "").toUpperCase();
        const tierBadge = tier ? (
          tier === "ULTRA" ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold shrink-0">ULTRA</span>` :
          tier === "PRO" ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-semibold shrink-0">PRO</span>` :
          tier === "PLUS" ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30 font-semibold shrink-0">PLUS</span>` :
          `<span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-medium shrink-0">FREE</span>`
        ) : "";

        const real5hPct = (isOfficial && a.real_5h_pct !== null && a.real_5h_pct !== undefined) ? a.real_5h_pct : q5hPct;
        const real5hLeftPct = Math.max(0, 100 - real5hPct);
        const real5hReset = (isOfficial && a.real_5h_reset_str) ? a.real_5h_reset_str : q5hReset;
        const real5hBarColor = real5hPct >= 85 ? "bg-rose-400/90" : (real5hPct >= 50 ? "bg-amber-400/85" : "bg-emerald-400/80");

        const realWeekPct = (isOfficial && a.real_weekly_pct !== null && a.real_weekly_pct !== undefined) ? a.real_weekly_pct : qWeekPct;
        const realWeekLeftPct = Math.max(0, 100 - realWeekPct);
        const realWeekReset = (isOfficial && a.real_weekly_reset_str) ? a.real_weekly_reset_str : "";

        const pace5h = resolveQuotaPace(
          a.quota_5h_pace,
          isOfficial ? (a.real_5h_pct_exact ?? real5hPct) : q5hPct,
          isOfficial ? a.real_5h_reset_epoch : 0,
          5 * 3600,
          a.usage_fetched_at,
          300
        );
        const paceWeekly = resolveQuotaPace(
          a.quota_weekly_pace,
          isOfficial ? (a.real_weekly_pct_exact ?? realWeekPct) : qWeekPct,
          isOfficial ? a.real_weekly_reset_epoch : 0,
          7 * 86400,
          a.usage_fetched_at,
          3600
        );

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
                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono shrink-0">#${escapeHtml(rawId)} · u/${escapeHtml(a.auth_user)}</span>
                  ${tierBadge}
                </div>
                <div class="text-[11px] text-slate-400 font-mono mt-0.5 truncate">
                  ${escapeHtml(displayEmail)}${(a.note || "").includes("同一登录") ? ` <span class="text-amber-300/80">· 重复登录</span>` : ""}
                </div>
              </div>
            </div>
          </td>
          <td class="py-3 px-3">
            <div class="w-44 space-y-1" title="${escapeHtml((isOfficial ? `官网实时用量 ${a.real_5h_pct_exact ?? real5hPct}% | 本地统计 ${q5hUsed} 次` : "本地滑动窗口估算") + ` | 预计本周期 ${pace5h.projected_pct}% (${pace5h.label})`)}">
              <div class="flex items-center justify-end text-[11px] font-mono">
                <span class="text-slate-200">${isOfficial ? `余 ${real5hLeftPct}%` : `余 ${q5hRemaining}`}</span>
              </div>
              <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div class="h-full ${isOfficial ? real5hBarColor : "bg-amber-400/80"} rounded-full" style="width: ${real5hPct}%"></div>
              </div>
              <div class="flex items-center justify-between gap-1.5 text-[10px] text-slate-400">
                <span class="whitespace-nowrap truncate">${escapeHtml(real5hReset)}</span>
                ${renderQuotaPaceDot(pace5h, false)}
              </div>
            </div>
          </td>
          <td class="py-3 px-3">
            <div class="w-40 space-y-1" title="${escapeHtml((isOfficial ? `官网周用量 ${a.real_weekly_pct_exact ?? realWeekPct}% | 本地本周 ${qWeekUsed} 次` : "本地周累计估算") + ` | 预计本周 ${paceWeekly.projected_pct}% (${paceWeekly.label})`)}">
              <div class="flex items-center justify-end text-[11px] font-mono">
                <span class="text-slate-200">${isOfficial ? `余 ${realWeekLeftPct}%` : `余 ${Math.max(0, qWeekLimit - qWeekUsed)}`}</span>
              </div>
              <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div class="h-full bg-sky-400/80 rounded-full" style="width: ${realWeekPct}%"></div>
              </div>
              <div class="flex items-center justify-between gap-1.5 text-[10px] text-slate-500">
                <span class="whitespace-nowrap truncate">${escapeHtml(realWeekReset || "本周窗口")}</span>
                ${renderQuotaPaceDot(paceWeekly, true)}
              </div>
            </div>
          </td>
          <td class="py-3 px-3 whitespace-nowrap">
            ${renderAccountStatusBadge(a.status, true)}
          </td>
          <td class="py-3 px-3 text-right whitespace-nowrap">
            <div class="inline-flex items-center justify-end gap-1.5">
              <button type="button" role="switch" aria-checked="${enabled ? "true" : "false"}" aria-label="${enabled ? "停用" : "启用"}账号" title="${enabled ? "已启用，点击停用该账号" : "已停用，点击启用该账号"}" onclick="setAccountStatus(${Number(rawId)}, '${enabled ? "disabled" : "enabled"}')" class="api-switch">
                <span class="api-switch-thumb"></span>
              </button>
              <button type="button" onclick="setAccountStatus(${Number(rawId)}, 'deleted')" title="移除该账号的本地凭证记录" class="px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-[11px] text-rose-300 border border-slate-800 cursor-pointer">删除</button>
              ${enabled ? `<button type="button" onclick="checkAccount(${Number(rawId)})" title="向 Google 发送轻量探测请求，检查该账号 Cookie 与对话通道是否可用" class="px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-[11px] text-slate-300 border border-slate-800 cursor-pointer">检测</button><button type="button" onclick="rotateAccount(${Number(rawId)})" title="主动轮转并刷新该账号会话状态，防止长时间闲置导致凭证失效" class="px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-[11px] text-amber-300 border border-slate-800 cursor-pointer">保活</button>` : ""}
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    function renderOtherAccountsTable(otherAccounts, platformsMap, platformsOrder, filter) {
      const tbody = document.getElementById("other-accounts-tbody");
      const countEl = document.getElementById("other-accounts-count");
      if (!tbody) return;

      const filteredAccounts = otherAccounts.filter(a => {
        if (filter === "all") return true;
        return normalizeAccountPlatform(a.platform) === filter;
      });
      if (countEl) countEl.innerText = String(filteredAccounts.length);

      const targetPlatforms = (filter === "all"
        ? platformsOrder.filter(p => p !== "gemini")
        : [filter].filter(p => p !== "gemini"));

      const missingPlatforms = targetPlatforms.filter(plat => {
        const hasAccount = filteredAccounts.some(a => normalizeAccountPlatform(a.platform) === plat);
        if (hasAccount) return false;
        return Boolean(platformsMap[plat]) || filter !== "all";
      });

      tbody.innerHTML = "";
      if (!filteredAccounts.length && !missingPlatforms.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-slate-500">暂无多平台账号数据</td></tr>`;
        return;
      }

      const renderPlatformBadge = (plat, nameOverride) => {
        const meta = getAccountPlatformMeta(plat);
        const label = nameOverride || meta.label;
        const iconHtml = meta.icon
          ? `<img src="${meta.icon}" alt="${escapeHtml(meta.label)}" class="w-3.5 h-3.5 object-contain shrink-0" data-fallback="${meta.fallbackIcon}" onerror="handlePlatformIconError(this, this.dataset.fallback)">`
          : `<i class="${meta.fallbackIcon} text-xs"></i>`;
        return `
          <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-medium border whitespace-nowrap ${meta.badgeClass}">
            ${iconHtml}
            <span>${escapeHtml(label)}</span>
          </span>
        `;
      };

      filteredAccounts.forEach(a => {
        const plat = normalizeAccountPlatform(a.platform);
        const meta = getAccountPlatformMeta(plat);
        const displayName = a.name || a.email || a.raw_id || a.id || meta.label;
        const displaySub = a.email || (a.note ? a.note : (a.raw_id ? `ID: ${a.raw_id}` : "未提供邮箱"));
        const initialChar = String(displayName).trim().charAt(0).toUpperCase() || "?";
        const sourceText = renderAccountSourceLabel(a.source);
        const quotaText = a.quota_summary || "已连接";
        const loginUrl = safeExternalUrl(a.login_url || (platformsMap[plat] && platformsMap[plat].login_url));
        const st = String(a.status || "").toLowerCase();
        const needsLogin = ["offline", "expired", "error", "not_logged_in"].includes(st);

        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-900/40 transition";
        tr.innerHTML = `
          <td class="py-3 px-3 whitespace-nowrap">
            ${renderPlatformBadge(plat, a.platform_name || meta.label)}
          </td>
          <td class="py-3 px-3">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-semibold ${meta.avatarClass} shrink-0">
                ${escapeHtml(initialChar)}
              </div>
              <div class="min-w-0">
                <div class="font-medium text-slate-100 flex items-center gap-1.5">
                  <span class="truncate max-w-[180px]">${escapeHtml(displayName)}</span>
                  ${sourceText ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/80 shrink-0">${escapeHtml(sourceText)}</span>` : ""}
                </div>
                <div class="text-[11px] text-slate-400 font-mono mt-0.5 truncate max-w-[240px]">
                  ${escapeHtml(displaySub)}${a.email && a.note ? ` <span class="text-slate-500">· ${escapeHtml(a.note)}</span>` : ""}
                </div>
              </div>
            </div>
          </td>
          <td class="py-3 px-3 whitespace-nowrap">
            ${renderMembershipBadge(a)}
          </td>
          <td class="py-3 px-3">
            <div class="text-xs text-slate-200 max-w-[260px] break-words">${escapeHtml(quotaText)}</div>
          </td>
          <td class="py-3 px-3 whitespace-nowrap">
            ${renderAccountStatusBadge(a.status, false)}
          </td>
          <td class="py-3 px-3 text-right space-x-1 whitespace-nowrap">
            ${needsLogin && loginUrl ? `<a href="${escapeHtml(loginUrl)}" target="_blank" rel="noopener" class="inline-block px-2.5 py-1 rounded-md bg-amber-500/15 hover:bg-amber-500/25 text-[11px] text-amber-300 border border-amber-500/30">去登录</a>` : ""}
            <button type="button" onclick="refreshPlatformAccounts('${escapeHtml(plat)}', this)" class="px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-[11px] text-sky-300 border border-slate-800 cursor-pointer">刷新</button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      missingPlatforms.forEach(plat => {
        const meta = getAccountPlatformMeta(plat);
        const pInfo = platformsMap[plat] || {};
        if (pInfo.enabled === false) {
          const tr = document.createElement("tr");
          tr.className = "bg-slate-950/30 hover:bg-slate-900/30 transition opacity-75";
          tr.innerHTML = `
            <td class="py-3 px-3 whitespace-nowrap">
              ${renderPlatformBadge(plat, pInfo.platform_name || meta.label)}
            </td>
            <td class="py-3 px-3">
              <div class="flex items-center gap-2.5 opacity-80">
                <div class="w-8 h-8 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-xs text-slate-500 shrink-0">
                  <i class="${meta.fallbackIcon}"></i>
                </div>
                <div class="min-w-0">
                  <div class="font-medium text-slate-400">网页 API 已关闭</div>
                  <div class="text-[11px] text-slate-500 mt-0.5 truncate max-w-[260px]">已停止获取或刷新该平台 Cookie 及关联后台服务</div>
                </div>
              </div>
            </td>
            <td class="py-3 px-3 whitespace-nowrap"><span class="text-[11px] text-slate-500">--</span></td>
            <td class="py-3 px-3"><span class="text-[11px] text-slate-500">--</span></td>
            <td class="py-3 px-3 whitespace-nowrap">${renderAccountStatusBadge("disabled", false)}</td>
            <td class="py-3 px-3 text-right space-x-1 whitespace-nowrap">
              <button type="button" onclick="toggleWebApiService('${escapeHtml(plat)}', true, this)" class="px-2.5 py-1 rounded-md bg-emerald-500/15 hover:bg-emerald-500/25 text-[11px] text-emerald-300 border border-emerald-500/30 cursor-pointer">开启</button>
            </td>
          `;
          tbody.appendChild(tr);
          return;
        }
        const loginUrl = safeExternalUrl(pInfo.login_url);
        const errText = pInfo.error ? String(pInfo.error) : "";
        const statusKey = errText ? "error" : (pInfo.logged_in === false ? "not_logged_in" : "offline");
        const hint = errText
          ? errText
          : (pInfo.logged_in === false ? "浏览器未检测到登录态，请先登录并保持 Cookie Hub 连接" : "暂未同步到账号信息，可点击刷新重试");

        const tr = document.createElement("tr");
        tr.className = "bg-slate-950/30 hover:bg-slate-900/30 transition";
        tr.innerHTML = `
          <td class="py-3 px-3 whitespace-nowrap">
            ${renderPlatformBadge(plat, pInfo.platform_name || meta.label)}
          </td>
          <td class="py-3 px-3">
            <div class="flex items-center gap-2.5 opacity-80">
              <div class="w-8 h-8 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-xs text-slate-500 shrink-0">
                <i class="${meta.fallbackIcon}"></i>
              </div>
              <div class="min-w-0">
                <div class="font-medium text-slate-400">未检测到已登录账号</div>
                <div class="text-[11px] text-slate-500 mt-0.5 truncate max-w-[260px]" title="${escapeHtml(hint)}">${escapeHtml(hint)}</div>
              </div>
            </div>
          </td>
          <td class="py-3 px-3 whitespace-nowrap">
            <span class="text-[11px] text-slate-500">--</span>
          </td>
          <td class="py-3 px-3">
            <span class="text-[11px] text-slate-500">--</span>
          </td>
          <td class="py-3 px-3 whitespace-nowrap">
            ${renderAccountStatusBadge(statusKey, false)}
          </td>
          <td class="py-3 px-3 text-right space-x-1 whitespace-nowrap">
            ${loginUrl ? `<a href="${escapeHtml(loginUrl)}" target="_blank" rel="noopener" class="inline-block px-2.5 py-1 rounded-md bg-amber-500/15 hover:bg-amber-500/25 text-[11px] text-amber-300 border border-amber-500/30">去登录</a>` : ""}
            <button type="button" onclick="refreshPlatformAccounts('${escapeHtml(plat)}', this)" class="px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-[11px] text-slate-300 border border-slate-800 cursor-pointer">检测</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function setAccountStatus(id, status) {
      if (status === 'deleted' && !confirm('删除此账号的本地 Gemini 凭证并停止向远端同步？浏览器和其他 AI Studio 号池中的账号不会删除。')) return;
      try {
        const res = await fetch(`/api/gemini/accounts/${id}/status?status=${status}`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || '操作失败');
        showToast(status === 'deleted' ? '账号已从 Gemini 池移除' : (status === 'enabled' ? '账号已启用' : '账号已停用'));
        await refreshDashboard();
      } catch (err) { showToast('账号操作失败: ' + err.message); }
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

    async function refreshPlatformAccounts(platform, btn) {
      const meta = getAccountPlatformMeta(platform);
      const oldHtml = btn ? btn.innerHTML : "";
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
      }
      try {
        const res = await fetch(`/api/accounts/refresh?platform=${encodeURIComponent(platform)}`, { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.message || "刷新失败");
        showToast(data.message || `${meta.label} 账号已刷新`);
        if (data && Array.isArray(data.accounts)) {
          latestAccountsPayload = data;
          renderAccountsDashboard(data);
        }
        await refreshDashboard();
      } catch (err) {
        showToast(`${meta.label} 刷新失败: ` + err.message);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = oldHtml;
        }
      }
    }

    async function refreshAccountsAll() {
      const btn = document.getElementById("btn-refresh-accounts");
      const targetPlat = currentAccountsFilter && currentAccountsFilter !== "all" ? currentAccountsFilter : "";
      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>正在刷新...</span>`;
      try {
        const url = targetPlat
          ? `/api/accounts/refresh?platform=${encodeURIComponent(targetPlat)}`
          : "/api/accounts/refresh";
        let res = await fetch(url, { method: "POST" });
        if (res.status === 404 && (!targetPlat || targetPlat === "gemini")) {
          res = await fetch("/api/gemini/accounts/refresh-all", { method: "POST" });
        }
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.message || "刷新失败");
        showToast(data.message || "凭证、账号与额度已全部刷新");
        await refreshDashboard();
      } catch (err) {
        showToast("刷新失败: " + err.message);
      } finally {
        btn.disabled = false;
        const filterLabel = currentAccountsFilter === "all" ? "刷新全部" : `刷新 ${getAccountPlatformMeta(currentAccountsFilter).label}`;
        btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> ${escapeHtml(filterLabel)}`;
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
        const res = await fetchWithTimeout(url, {}, 10000);
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

      if (window._historyPollTimer) { clearTimeout(window._historyPollTimer); window._historyPollTimer = null; }

      if (!data.items || data.items.length === 0) {
        container.innerHTML = `
          <div class="text-center py-12 text-slate-500 text-xs bg-[#090d16] rounded-xl border border-slate-800/80">
            <i class="fa-solid fa-inbox text-2xl text-slate-700 mb-2 block"></i>
            暂无匹配的对话记录
          </div>
        `;
        return;
      }

      let hasRunning = false;
      const fmtLat = (ms) => { const s = Math.max(0, Number(ms) || 0) / 1000; if (s < 60) return `${s.toFixed(1)}s`; const m = Math.floor(s / 60); return `${m}min ${(s - m * 60).toFixed(1)}s`; };
      container.innerHTML = data.items.map(item => {
        const isRunning = item.status === 0 || item.status === 102;
        const isRecentRunning = isRunning && (!item.timestamp || (Date.now() - item.timestamp * 1000) < 30 * 60 * 1000);
        if (isRecentRunning) hasRunning = true;
        const isSuccess = item.status >= 200 && item.status < 300;
        const statusDot = isRunning ? '<span class="relative flex h-2 w-2"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-amber-400"></span></span>' : `<span class="w-1.5 h-1.5 rounded-full ${isSuccess ? 'bg-emerald-400' : 'bg-rose-400'}"></span>`;
        const statusText = isRunning ? '运行中...' : (isSuccess ? `${item.status} OK` : `${item.status} ERR`);
        const statusCls = isRunning ? 'text-amber-400 animate-pulse' : (isSuccess ? 'text-emerald-400' : 'text-rose-400');
        const borderCls = isRunning ? 'border-amber-500/40 hover:border-amber-400/60' : 'border-slate-800/90 hover:border-slate-700';
        const msVal = isRunning && item.timestamp ? Math.max(0, Date.now() - item.timestamp * 1000) : item.latency_ms;
        const latTxt = fmtLat(msVal);

        return `
          <div class="bg-[#090d16] border ${borderCls} rounded-xl p-3.5 transition space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800/70">
              <div class="flex flex-wrap items-center gap-2 text-[11px] font-mono">
                ${statusDot}
                <span class="px-2 py-0.5 rounded bg-slate-900 text-sky-300 border border-slate-800 font-semibold">${escapeHtml(item.model)}</span>
                <span class="text-slate-400">${escapeHtml(item.endpoint || "/v1/chat/completions")}</span>
                <span class="${statusCls}">${statusText}</span>
                <span class="text-slate-500">· ${item.is_stream ? "流式" : "非流式"}</span>
                <span class="${isRunning ? 'text-amber-300/90' : 'text-slate-500'}">· ${latTxt}</span>
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
              <div class="${item.error_message ? "text-rose-400" : "text-slate-400"} line-clamp-2"><span class="text-slate-500 select-none">A: </span>${isRunning ? "正在运行中，等待返回结果..." : escapeHtml(item.response_summary || (item.error_message ? `[错误] ${item.error_message}` : "（未捕获回答）"))}</div>
            </div>

            <div id="detail-panel-${item.id}" class="hidden pt-3 border-t border-slate-800/70 space-y-3"></div>
          </div>
        `;
      }).join("");
      if (hasRunning) { window._historyPollTimer = setTimeout(() => loadChatHistory(currentHistoryPage, false), 2500); }
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
          <span>耗时: <span class="text-slate-300">${((detail.latency_ms||0)/1000)<60 ? ((detail.latency_ms||0)/1000).toFixed(1)+'s' : Math.floor((detail.latency_ms||0)/60000)+'min '+(((detail.latency_ms||0)/1000)%60).toFixed(1)+'s'}</span></span>
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
    // 访问令牌 (Token) 管理与远程鉴权
    // ==========================================
    const TOKEN_STORAGE_KEY = "css_api_token";
    let currentApiToken = "";
    let currentApiTokenMasked = "";
    let tokenVisible = false;

    function getStoredToken() {
      try {
        return (localStorage.getItem(TOKEN_STORAGE_KEY) || "").trim();
      } catch (e) {
        return "";
      }
    }

    function setStoredToken(tok) {
      try {
        if (tok) localStorage.setItem(TOKEN_STORAGE_KEY, tok);
        else localStorage.removeItem(TOKEN_STORAGE_KEY);
      } catch (e) {}
    }

    function renderApiTokenUI() {
      const displayVal = tokenVisible
        ? (currentApiToken || "未加载")
        : (currentApiTokenMasked || (currentApiToken ? currentApiToken.slice(0, 10) + "..." + currentApiToken.slice(-4) : "未加载"));

      const sidePreview = document.getElementById("sidebar-token-preview");
      if (sidePreview) {
        sidePreview.innerText = displayVal;
        sidePreview.title = tokenVisible && currentApiToken ? currentApiToken : "点击右侧按钮复制完整 Token";
      }

      const docsPreview = document.getElementById("docs-api-token-preview");
      if (docsPreview) {
        docsPreview.innerText = displayVal;
      }

      const eyeBtn = document.getElementById("sidebar-token-eye");
      if (eyeBtn) {
        eyeBtn.innerHTML = tokenVisible
          ? `<i class="fa-regular fa-eye-slash"></i>`
          : `<i class="fa-regular fa-eye"></i>`;
      }
    }

    function toggleTokenVisibility() {
      tokenVisible = !tokenVisible;
      renderApiTokenUI();
    }

    async function loadApiToken() {
      try {
        const res = await fetch("/api/system/token");
        if (res.status === 401) {
          showAuthModal();
          return;
        }
        if (!res.ok) return;
        const data = await res.json();
        currentApiToken = data.token || "";
        currentApiTokenMasked = data.masked || "";
        if (currentApiToken) setStoredToken(currentApiToken);
        renderApiTokenUI();
      } catch (e) {}
    }

    async function copyApiToken(btn) {
      if (!currentApiToken) {
        await loadApiToken();
      }
      if (!currentApiToken) {
        showToast("尚未获取到 Token，请先解锁或刷新");
        return;
      }
      copyText(currentApiToken, btn);
    }

    async function generateApiToken(btn) {
      if (currentApiToken && !confirm("确认生成新的 API Token？\n生成后旧 Token 将立即失效。")) {
        return;
      }
      const oldHtml = btn ? btn.innerHTML : "";
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
      }
      try {
        const res = await fetch("/api/system/token/generate", { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "生成失败");
        currentApiToken = data.token || "";
        currentApiTokenMasked = data.masked || "";
        if (currentApiToken) {
          setStoredToken(currentApiToken);
          await fetch("/api/system/auth/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: currentApiToken }),
          }).catch(() => {});
        }
        renderApiTokenUI();
        copyText(currentApiToken);
        showToast("已生成新 Token 并复制到剪贴板");
      } catch (err) {
        showToast("生成 Token 失败: " + err.message);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = oldHtml;
        }
      }
    }

    function getOpenAIBaseUrl() {
      return `${window.location.origin}/v1`;
    }

    function copyOpenAIBaseUrl(btn) {
      copyText(getOpenAIBaseUrl(), btn);
    }

    function showAuthModal(errMsg = "") {
      const modal = document.getElementById("auth-unlock-modal");
      if (!modal) return;
      modal.classList.remove("hidden");
      modal.classList.add("flex");
      const errEl = document.getElementById("auth-token-error");
      if (errEl) {
        if (errMsg) {
          errEl.innerText = errMsg;
          errEl.classList.remove("hidden");
        } else {
          errEl.classList.add("hidden");
        }
      }
      const input = document.getElementById("auth-token-input");
      if (input) setTimeout(() => input.focus(), 50);
    }

    function hideAuthModal() {
      const modal = document.getElementById("auth-unlock-modal");
      if (!modal) return;
      modal.classList.add("hidden");
      modal.classList.remove("flex");
    }

    async function submitAuthToken() {
      const input = document.getElementById("auth-token-input");
      const errEl = document.getElementById("auth-token-error");
      const btn = document.getElementById("btn-auth-unlock");
      const token = (input?.value || "").trim();
      if (!token) {
        if (errEl) {
          errEl.innerText = "请输入访问令牌";
          errEl.classList.remove("hidden");
        }
        return;
      }
      if (btn) btn.disabled = true;
      try {
        const res = await fetch("/api/system/auth/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "访问令牌无效");
        }
        setStoredToken(token);
        hideAuthModal();
        showToast("访问令牌验证成功");
        await loadApiToken();
        await refreshDashboard();
      } catch (err) {
        if (errEl) {
          errEl.innerText = err.message || "验证失败";
          errEl.classList.remove("hidden");
        }
      } finally {
        if (btn) btn.disabled = false;
      }
    }

    (function installFetchAuthInterceptor() {
      const origFetch = window.fetch.bind(window);
      window.fetch = async function(input, init) {
        const url = typeof input === "string" ? input : (input && input.url ? input.url : "");
        const isApiCall = url.startsWith("/api/") || url.startsWith("/v1/");
        const opts = init ? Object.assign({}, init) : {};
        if (isApiCall) {
          const tok = getStoredToken();
          if (tok) {
            const headers = new Headers(opts.headers || (typeof input !== "string" && input.headers ? input.headers : undefined));
            if (!headers.has("Authorization")) {
              headers.set("Authorization", `Bearer ${tok}`);
            }
            opts.headers = headers;
          }
        }
        const resp = await origFetch(input, opts);
        if (resp.status === 401 && isApiCall && !url.startsWith("/api/system/auth/")) {
          showAuthModal();
        }
        return resp;
      };
    })();

    const THEME_STORAGE_KEY = "css_dashboard_theme";

    function getCurrentTheme() {
      return document.documentElement.classList.contains("theme-light") ? "light" : "dark";
    }

    function applyTheme(theme, persist = true) {
      const isLight = theme === "light";
      document.documentElement.classList.toggle("theme-light", isLight);
      const icon = document.getElementById("theme-toggle-icon");
      const text = document.getElementById("theme-toggle-text");
      if (icon) {
        icon.className = isLight ? "fa-solid fa-moon text-indigo-400" : "fa-solid fa-sun text-amber-400";
      }
      if (text) {
        text.innerText = isLight ? "暗色模式" : "浅色模式";
      }
      if (persist) {
        try { localStorage.setItem(THEME_STORAGE_KEY, isLight ? "light" : "dark"); } catch (e) {}
      }
    }

    function toggleTheme() {
      const next = getCurrentTheme() === "light" ? "dark" : "light";
      applyTheme(next, true);
    }

    // ==========================================
    // 初始化
    // ==========================================
    (async function init() {
      applyTheme(getCurrentTheme(), false);
      try {
        const params = new URLSearchParams(window.location.search);
        const queryToken = (params.get("token") || "").trim();
        if (queryToken) {
          setStoredToken(queryToken);
          params.delete("token");
          const cleanSearch = params.toString();
          const cleanUrl = window.location.pathname + (cleanSearch ? `?${cleanSearch}` : "") + window.location.hash;
          window.history.replaceState({}, "", cleanUrl);
        }
      } catch (e) {}

      const docsBase = document.getElementById("docs-openai-base-url");
      if (docsBase) docsBase.innerText = getOpenAIBaseUrl();

      const initialHash = (window.location.hash || "").replace(/^#/, "");
      if (VIEW_META[initialHash]) {
        switchView(initialHash, false);
      } else {
        switchView("playground", false);
      }

      try {
        renderEndpointCategoryTabs();
        renderEndpointsList();
        renderPlaygroundCategoryNav();
        setPlaygroundCategory("gemini", true);
      } catch (e) {
        console.error("初始化视图渲染异常:", e);
      }

      try {
        const authRes = await fetch("/api/system/auth/status");
        const authData = authRes.ok ? await authRes.json() : { authorized: true };
        if (authData.requires_token && !authData.authorized) {
          const stored = getStoredToken();
          if (stored) {
            const verifyRes = await fetch("/api/system/auth/verify", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ token: stored }),
            });
            if (!verifyRes.ok) {
              setStoredToken("");
              showAuthModal("本地保存的令牌已失效，请输入新令牌");
              return;
            }
          } else {
            showAuthModal();
            return;
          }
        }
      } catch (e) {}

      await loadApiToken();
      refreshChatGPTModelCatalog();
      await refreshDashboard(true);
      if (currentView === "conversations") {
        loadGeminiConversations();
      }
      if (currentView === "overview") {
        loadGoogleSyncSettings();
      }
      ensureGeminiConvSSE();
      setInterval(() => refreshDashboard(false), 12000);
    })();

    // ==========================================
    // Gemini 原生对话托管与实时控制
    // ==========================================
    let gconvItems = [];
    let gconvActiveCid = "";
    let gconvActiveData = null;
    let gconvEventSource = null;

    function gconvStatusBadge(status) {
      const s = String(status || "idle");
      if (s === "running") return { text: "生成中", cls: "bg-sky-500/20 text-sky-300 border-sky-500/40 animate-pulse" };
      if (s === "stopped") return { text: "已停止", cls: "bg-amber-500/20 text-amber-300 border-amber-500/40" };
      if (s === "completed") return { text: "已完成", cls: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" };
      if (s === "error") return { text: "异常", cls: "bg-rose-500/20 text-rose-300 border-rose-500/40" };
      return { text: "就绪", cls: "bg-slate-800 text-slate-400 border-slate-700" };
    }

    function ensureGeminiConvSSE() {
      if (gconvEventSource) return;
      try {
        gconvEventSource = new EventSource("/api/gemini/conversations/events");
        const dot = document.getElementById("gconv-sse-dot");
        const txt = document.getElementById("gconv-sse-text");
        gconvEventSource.addEventListener("connected", () => {
          if (dot) dot.className = "w-1.5 h-1.5 rounded-full bg-emerald-400";
          if (txt) txt.innerText = "实时监听已连接";
        });
        gconvEventSource.addEventListener("run_started", (ev) => {
          const d = JSON.parse(ev.data || "{}");
          loadGeminiConversations();
          if (d.cid && d.cid === gconvActiveCid) selectGeminiConversation(d.cid, false);
        });
        gconvEventSource.addEventListener("cid_assigned", (ev) => {
          const d = JSON.parse(ev.data || "{}");
          if (gconvActiveCid && gconvActiveCid.startsWith("pending_") && d.cid) {
            gconvActiveCid = d.cid;
          }
          loadGeminiConversations();
          if (d.cid && d.cid === gconvActiveCid) selectGeminiConversation(d.cid, false);
        });
        gconvEventSource.addEventListener("run_delta", (ev) => {
          const d = JSON.parse(ev.data || "{}");
          if (d.cid && d.cid === gconvActiveCid) {
            const liveReplyEl = document.getElementById("gconv-live-reply");
            if (liveReplyEl) {
              liveReplyEl.innerText = d.reply || "";
              const box = document.getElementById("gconv-messages");
              if (box) box.scrollTop = box.scrollHeight;
            } else {
              selectGeminiConversation(d.cid, false);
            }
          }
        });
        gconvEventSource.addEventListener("run_reasoning", (ev) => {
          const d = JSON.parse(ev.data || "{}");
          if (d.cid && d.cid === gconvActiveCid) {
            const liveReasonEl = document.getElementById("gconv-live-reasoning");
            if (liveReasonEl) {
              liveReasonEl.classList.remove("hidden");
              liveReasonEl.innerText = "思考过程:\n" + (d.reasoning || "");
            }
          }
        });
        gconvEventSource.addEventListener("run_finished", (ev) => {
          const d = JSON.parse(ev.data || "{}");
          loadGeminiConversations();
          if (d.cid && d.cid === gconvActiveCid) {
            selectGeminiConversation(d.cid, false);
          }
          if (d.status === "completed") {
            showToast(`Gemini 对话回复已完成 (${d.cid || ""})`);
          } else if (d.status === "stopped") {
            showToast(`Gemini 对话已停止输出 (${d.cid || ""})`);
          } else if (d.status === "error") {
            showToast(`Gemini 对话异常: ${d.error || "未知错误"}`);
          }
        });
        gconvEventSource.addEventListener("conversation_deleted", () => {
          loadGeminiConversations();
        });
        gconvEventSource.onerror = () => {
          if (dot) dot.className = "w-1.5 h-1.5 rounded-full bg-amber-400";
          if (txt) txt.innerText = "监听重连中...";
        };
      } catch (e) {
        console.error("Gemini SSE init error:", e);
      }
    }

    async function loadGeminiConversations() {
      try {
        const res = await fetch("/api/gemini/conversations?limit=50");
        if (!res.ok) return;
        const data = await res.json();
        gconvItems = data.conversations || [];
        const badge = document.getElementById("nav-conv-count");
        if (badge) badge.innerText = String(gconvItems.length);
        renderGeminiConversationList();
      } catch (e) {
        console.error("loadGeminiConversations failed:", e);
      }
    }

    function renderGeminiConversationList() {
      const container = document.getElementById("gconv-list");
      if (!container) return;
      if (!gconvItems.length) {
        container.innerHTML = `<div class="text-xs text-slate-500 text-center py-8">暂无落盘对话，点击「从官网同步列表」或「新建对话」开始</div>`;
        return;
      }
      container.innerHTML = gconvItems.map(item => {
        const active = item.cid === gconvActiveCid;
        const st = gconvStatusBadge(item.status);
        const dt = item.updated_at ? new Date(item.updated_at * 1000).toLocaleString() : "";
        return `
          <button type="button" onclick="selectGeminiConversation('${escapeHtml(item.cid)}', false)"
            class="w-full text-left p-2.5 rounded-lg border transition cursor-pointer ${active ? "bg-sky-500/15 border-sky-500/40" : "bg-slate-900/60 border-slate-800/80 hover:border-slate-700"}">
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-medium text-slate-100 truncate">${escapeHtml(item.title || item.cid)}</span>
              <span class="px-1.5 py-0.5 rounded text-[10px] font-mono border shrink-0 ${st.cls}">${st.text}</span>
            </div>
            <div class="text-[11px] text-slate-400 truncate mt-1">${escapeHtml(item.last_reply || item.last_prompt || "点击同步或续聊")}</div>
            <div class="flex items-center justify-between text-[10px] font-mono text-slate-500 mt-1.5">
              <span>u/${item.authuser ?? 0} · ${escapeHtml(item.model || "")}</span>
              <span>${escapeHtml(dt)}</span>
            </div>
          </button>
        `;
      }).join("");
    }

    async function syncGeminiConversations(btn) {
      if (btn) btn.disabled = true;
      try {
        const res = await fetch("/api/gemini/conversations/sync", { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "同步失败");
        showToast(`已从 Gemini 官网同步 ${data.synced || 0} 条对话`);
        await loadGeminiConversations();
      } catch (e) {
        showToast("同步官网列表失败: " + e.message);
      } finally {
        if (btn) btn.disabled = false;
      }
    }

    async function selectGeminiConversation(cid, refreshUpstream = false) {
      gconvActiveCid = cid;
      renderGeminiConversationList();
      try {
        const res = await fetch(`/api/gemini/conversations/${encodeURIComponent(cid)}?refresh=${refreshUpstream ? "true" : "false"}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "读取失败");
        gconvActiveData = data.conversation;
        renderActiveGeminiConversation();
      } catch (e) {
        showToast("加载对话详情失败: " + e.message);
      }
    }

    function prepareNewGeminiConversation() {
      gconvActiveCid = "";
      gconvActiveData = null;
      renderGeminiConversationList();
      renderActiveGeminiConversation();
      const input = document.getElementById("gconv-input");
      if (input) input.focus();
    }

    function renderActiveGeminiConversation() {
      const titleEl = document.getElementById("gconv-active-title");
      const metaEl = document.getElementById("gconv-active-meta");
      const statusEl = document.getElementById("gconv-active-status");
      const btnRefresh = document.getElementById("gconv-btn-refresh");
      const btnStop = document.getElementById("gconv-btn-stop");
      const btnDelete = document.getElementById("gconv-btn-delete");
      const btnSend = document.getElementById("gconv-btn-send");
      const msgBox = document.getElementById("gconv-messages");
      const modelSel = document.getElementById("gconv-model-select");

      if (!gconvActiveData) {
        if (titleEl) titleEl.innerText = "新对话（发送后自动创建并落盘）";
        if (metaEl) metaEl.innerHTML = `<span>cid: 待分配</span>`;
        if (statusEl) {
          statusEl.className = "px-2 py-0.5 rounded-md text-[11px] font-mono bg-slate-800 text-slate-400 border border-slate-700";
          statusEl.innerText = "就绪";
        }
        if (btnRefresh) btnRefresh.classList.add("hidden");
        if (btnStop) btnStop.classList.add("hidden");
        if (btnDelete) btnDelete.classList.add("hidden");
        if (btnSend) btnSend.disabled = false;
        if (msgBox) msgBox.innerHTML = `<div class="text-xs text-slate-500 text-center py-12">在下方输入首条消息即可发起新对话，全程无需打开网页端。</div>`;
        return;
      }

      const conv = gconvActiveData;
      const st = gconvStatusBadge(conv.status);
      const isRunning = conv.status === "running";
      if (titleEl) titleEl.innerText = conv.title || conv.cid;
      if (metaEl) {
        metaEl.innerHTML = `
          <span>cid: ${escapeHtml(conv.cid)}</span>
          <span>账号: ${escapeHtml(conv.account_label || ("u/" + (conv.authuser ?? 0)))}</span>
          <span>轮次: ${conv.turn ?? 0}</span>
          ${conv.rid ? `<span>rid: ${escapeHtml(conv.rid)}</span>` : ""}
        `;
      }
      if (statusEl) {
        statusEl.className = `px-2 py-0.5 rounded-md text-[11px] font-mono border ${st.cls}`;
        statusEl.innerText = st.text;
      }
      if (btnRefresh) btnRefresh.classList.toggle("hidden", !conv.cid || conv.cid.startsWith("pending_"));
      if (btnStop) btnStop.classList.toggle("hidden", !isRunning);
      if (btnDelete) btnDelete.classList.remove("hidden");
      if (btnSend) btnSend.disabled = isRunning;
      if (modelSel && conv.model) {
        const opt = Array.from(modelSel.options).find(o => o.value === conv.model);
        if (opt) modelSel.value = conv.model;
      }

      const msgs = conv.messages || [];
      if (!msgs.length) {
        msgBox.innerHTML = `<div class="text-xs text-slate-500 text-center py-10">暂无本地缓存消息，可点击右上角「同步消息」从官网拉取，或直接在下方续发消息。</div>`;
        return;
      }

      msgBox.innerHTML = msgs.map((m, idx) => {
        const isUser = m.role === "user";
        const isLive = !isUser && m.status === "running" && idx === msgs.length - 1;
        const mSt = gconvStatusBadge(m.status);
        return `
          <div class="rounded-xl p-3 border ${isUser ? "bg-sky-500/10 border-sky-500/25 ml-8" : "bg-slate-900/80 border-slate-800 mr-4"}">
            <div class="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1.5">
              <span>${isUser ? "User" : "Gemini"}</span>
              ${!isUser ? `<span class="px-1.5 py-0.5 rounded border text-[10px] ${mSt.cls}">${mSt.text}</span>` : ""}
            </div>
            ${!isUser ? `<div ${isLive ? 'id="gconv-live-reasoning"' : ""} class="${m.reasoning ? "" : "hidden"} text-[11px] text-slate-400 bg-slate-950/60 border border-slate-800/80 rounded-lg p-2 mb-2 whitespace-pre-wrap">${m.reasoning ? "思考过程:\n" + escapeHtml(m.reasoning) : ""}</div>` : ""}
            <div ${isLive ? 'id="gconv-live-reply"' : ""} class="text-xs text-slate-100 whitespace-pre-wrap leading-relaxed break-words">${escapeHtml(m.content || (isLive ? "正在等待 Gemini 响应..." : ""))}</div>
          </div>
        `;
      }).join("");
      msgBox.scrollTop = msgBox.scrollHeight;
    }

    async function refreshActiveGeminiConversation() {
      if (!gconvActiveCid) return;
      await selectGeminiConversation(gconvActiveCid, true);
      await loadGeminiConversations();
      showToast("已从官网同步最新对话轮次");
    }

    async function stopActiveGeminiConversation() {
      if (!gconvActiveCid) return;
      try {
        const res = await fetch(`/api/gemini/conversations/${encodeURIComponent(gconvActiveCid)}/stop`, { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "停止失败");
        showToast("已发送停止信号");
        await selectGeminiConversation(gconvActiveCid, false);
        await loadGeminiConversations();
      } catch (e) {
        showToast("停止失败: " + e.message);
      }
    }

    async function deleteActiveGeminiConversation() {
      if (!gconvActiveCid) return;
      try {
        const res = await fetch(`/api/gemini/conversations/${encodeURIComponent(gconvActiveCid)}`, { method: "DELETE" });
        if (!res.ok) throw new Error("删除失败");
        gconvActiveCid = "";
        gconvActiveData = null;
        renderActiveGeminiConversation();
        await loadGeminiConversations();
        showToast("已删除本地对话记录");
      } catch (e) {
        showToast("删除失败: " + e.message);
      }
    }

    async function sendGeminiConvMessage() {
      const input = document.getElementById("gconv-input");
      const modelSel = document.getElementById("gconv-model-select");
      const prompt = (input ? input.value : "").trim();
      if (!prompt) {
        showToast("请输入消息内容");
        return;
      }
      const model = modelSel ? modelSel.value : "gemini-3.6-flash";
      try {
        let url = "/api/gemini/conversations";
        let payload = { prompt, model };
        if (gconvActiveCid) {
          url = `/api/gemini/conversations/${encodeURIComponent(gconvActiveCid)}/messages`;
          payload = { prompt, model };
        }
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "发送失败");
        if (input) input.value = "";
        gconvActiveCid = data.cid;
        await loadGeminiConversations();
        await selectGeminiConversation(data.cid, false);
      } catch (e) {
        showToast("发送失败: " + e.message);
      }
    }
    // ==========================================
    // Google 防风控与同步频率控制
    // ==========================================
    let googleSyncState = {
      auto_sync_enabled: true,
      usage_sync_interval_sec: 1800,
      cookie_sync_interval_sec: 1800,
      allow_auto_fetch_tab: false,
    };

    function renderGoogleSyncSettings() {
      const btn = document.getElementById("btn-google-sync-master");
      const txt = document.getElementById("google-sync-master-text");
      const usageSel = document.getElementById("gs-usage-interval");
      const cookieSel = document.getElementById("gs-cookie-interval");
      const tabChk = document.getElementById("gs-allow-tab");
      const on = !!googleSyncState.auto_sync_enabled;
      if (btn) {
        btn.className = on
          ? "px-3 py-1.5 rounded-lg text-xs font-medium border transition cursor-pointer shrink-0 bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
          : "px-3 py-1.5 rounded-lg text-xs font-medium border transition cursor-pointer shrink-0 bg-rose-500/15 text-rose-300 border-rose-500/40";
      }
      if (txt) {
        txt.innerText = on ? "自动监听中（点击一键全关）" : "已开启静默模式（点击恢复）";
      }
      if (usageSel) {
        const val = String(googleSyncState.usage_sync_interval_sec ?? 1800);
        if (Array.from(usageSel.options).some(o => o.value === val)) usageSel.value = val;
        usageSel.disabled = !on;
      }
      if (cookieSel) {
        const val = String(googleSyncState.cookie_sync_interval_sec ?? 1800);
        if (Array.from(cookieSel.options).some(o => o.value === val)) cookieSel.value = val;
        cookieSel.disabled = !on;
      }
      if (tabChk) {
        tabChk.checked = !!googleSyncState.allow_auto_fetch_tab;
        tabChk.disabled = !on;
      }
    }

    async function loadGoogleSyncSettings() {
      try {
        const res = await fetch("/api/system/google-sync");
        if (!res.ok) return;
        const data = await res.json();
        if (data.settings) {
          googleSyncState = data.settings;
          renderGoogleSyncSettings();
        }
      } catch (e) {}
    }

    async function saveGoogleSyncSettings(overridePatch = null) {
      const usageSel = document.getElementById("gs-usage-interval");
      const cookieSel = document.getElementById("gs-cookie-interval");
      const tabChk = document.getElementById("gs-allow-tab");
      const payload = overridePatch || {
        usage_sync_interval_sec: usageSel ? Number(usageSel.value) : googleSyncState.usage_sync_interval_sec,
        cookie_sync_interval_sec: cookieSel ? Number(cookieSel.value) : googleSyncState.cookie_sync_interval_sec,
        allow_auto_fetch_tab: tabChk ? !!tabChk.checked : googleSyncState.allow_auto_fetch_tab,
      };
      try {
        const res = await fetch("/api/system/google-sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (res.ok && data.settings) {
          googleSyncState = data.settings;
          renderGoogleSyncSettings();
          showToast("Google 防风控与同步配置已保存");
        }
      } catch (e) {
        showToast("保存失败: " + e.message);
      }
    }

    async function toggleGoogleAutoSyncMaster() {
      const next = !googleSyncState.auto_sync_enabled;
      await saveGoogleSyncSettings({ auto_sync_enabled: next });
    }
  </script>
</body>
</html>"""
