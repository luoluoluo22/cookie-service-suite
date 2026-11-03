// Presets for recognized web services and their key authentication cookies
const SERVICE_PRESETS = [
  {
    pattern: /bilibili\.com/i,
    service: '哔哩哔哩 (Bilibili)',
    keys: ['SESSDATA', 'bili_jct', 'DedeUserID', 'DedeUserID__ckMd5'],
    tip: '调用 4K 视频流、投币点赞与 API 需 SESSDATA 和 bili_jct (CSRF)'
  },
  {
    pattern: /(music\.163\.com|163\.com)/i,
    service: '网易云音乐 (NetEase Cloud Music)',
    keys: ['MUSIC_U', '__csrf'],
    tip: '获取黑胶 VIP 无损音乐播放直链与打卡核心凭据为 MUSIC_U'
  },
  {
    pattern: /(baidu\.com|tieba\.baidu\.com)/i,
    service: '百度网盘 / 百度贴吧',
    keys: ['BDUSS', 'STOKEN', 'BAIDUID'],
    tip: 'BaiduPCS-Go 命令行高速下载与贴吧自动签到核心为 BDUSS'
  },
  {
    pattern: /(twitter\.com|x\.com)/i,
    service: 'Twitter / X',
    keys: ['auth_token', 'ct0'],
    tip: 'twscrape 爬虫与 Web 接口免官方 API 费用的关键凭据为 auth_token, ct0'
  },
  {
    pattern: /(gemini\.google\.com|google\.com)/i,
    service: 'Google / Gemini',
    keys: ['__Secure-1PSID', '__Secure-1PSIDTS', 'SAPISID', 'SID'],
    tip: 'Gemini-Web2API 逆向接口核心为 __Secure-1PSID 与 __Secure-1PSIDTS'
  },
  {
    pattern: /(chatgpt\.com|openai\.com)/i,
    service: 'OpenAI / ChatGPT',
    keys: ['__Secure-next-auth.session-token', '_cfuvid'],
    tip: 'ChatGPT 网页转 API 核心会话凭据为 session-token'
  },
  {
    pattern: /claude\.ai/i,
    service: 'Anthropic Claude',
    keys: ['sessionKey'],
    tip: 'Claude 网页端逆向调用核心认证字段为 sessionKey'
  },
  {
    pattern: /notion\.so/i,
    service: 'Notion',
    keys: ['token_v2'],
    tip: 'Notion 私有内部 API 完整读写凭证为 token_v2'
  },
  {
    pattern: /jd\.com/i,
    service: '京东 (JD)',
    keys: ['pt_key', 'pt_pin'],
    tip: '京东资产管理、自动签到与京豆任务核心为 pt_key 和 pt_pin'
  },
  {
    pattern: /weibo\.(com|cn)/i,
    service: '新浪微博',
    keys: ['SUB', 'SUBP', 'SSOLoginState'],
    tip: '微博爬虫与 API 采集核心为 SUB'
  },
  {
    pattern: /zhihu\.com/i,
    service: '知乎',
    keys: ['z_c0', '_xsrf'],
    tip: '知乎免登录风控抓取核心为 z_c0'
  },
  {
    pattern: /xiaohongshu\.com/i,
    service: '小红书 (Xiaohongshu)',
    keys: ['web_session', 'a1', 'webId'],
    tip: '小红书图文笔记与无水印原图采集核心为 web_session'
  }
];

// Global state
let currentCookies = [];
let activeTabUrl = '';
let activeDomain = '';
let revealAll = false;

// DOM Elements
const elDomain = document.getElementById('current-domain');
const elCountBadge = document.getElementById('cookie-count-badge');
const elSystemTip = document.getElementById('system-page-tip');
const elPresetCard = document.getElementById('preset-card');
const elPresetServiceName = document.getElementById('preset-service-name');
const elPresetServiceTip = document.getElementById('preset-service-tip');
const elPresetTokens = document.getElementById('preset-tokens-container');
const elCookieList = document.getElementById('cookie-list');
const elEmptyState = document.getElementById('empty-state');
const elSearchInput = document.getElementById('input-search');
const elCheckReveal = document.getElementById('check-reveal-all');
const elToast = document.getElementById('toast');

// Bridge Status Elements
const elBridgePill = document.getElementById('bridge-status-pill');
const elBridgeText = document.getElementById('bridge-status-text');

// Buttons
const btnRefresh = document.getElementById('btn-refresh');
const btnCopyHeader = document.getElementById('btn-copy-header');
const btnCopyJson = document.getElementById('btn-copy-json');
const btnCopyPuppeteer = document.getElementById('btn-copy-puppeteer');
const btnCopyNetscape = document.getElementById('btn-copy-netscape');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  loadCookies();
  checkBridgeStatus();
  setupEventListeners();
});

function setupEventListeners() {
  btnRefresh.addEventListener('click', () => {
    loadCookies();
    checkBridgeStatus();
  });

  elBridgePill.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'RECONNECT_BRIDGE' }, (res) => {
      checkBridgeStatus();
      showToast('正在尝试连接本地服务 (127.0.0.1:18888)...');
    });
  });

  btnCopyHeader.addEventListener('click', () => {
    if (!currentCookies.length) return showToast('暂无 Cookie 可导出', true);
    const headerStr = currentCookies.map(c => `${c.name}=${c.value}`).join('; ');
    copyToClipboard(headerStr, '已复制 Cookie Header 字符串！');
  });

  btnCopyJson.addEventListener('click', () => {
    if (!currentCookies.length) return showToast('暂无 Cookie 可导出', true);
    const kvObj = {};
    currentCookies.forEach(c => { kvObj[c.name] = c.value; });
    copyToClipboard(JSON.stringify(kvObj, null, 2), '已复制 Key-Value JSON！');
  });

  btnCopyPuppeteer.addEventListener('click', () => {
    if (!currentCookies.length) return showToast('暂无 Cookie 可导出', true);
    const formatted = currentCookies.map(c => ({
      name: c.name,
      value: c.value,
      domain: c.domain,
      path: c.path,
      expires: c.expirationDate || -1,
      httpOnly: c.httpOnly,
      secure: c.secure,
      sameSite: c.sameSite || 'Lax'
    }));
    copyToClipboard(JSON.stringify(formatted, null, 2), '已复制 Playwright/Puppeteer 数组！');
  });

  btnCopyNetscape.addEventListener('click', () => {
    if (!currentCookies.length) return showToast('暂无 Cookie 可导出', true);
    const netscapeLines = [
      '# Netscape HTTP Cookie File',
      '# https://curl.se/docs/http-cookies.html',
      '# Generated by Cookie Hub',
      ''
    ];
    currentCookies.forEach(c => {
      const domain = c.domain.startsWith('.') ? c.domain : '.' + c.domain;
      const tailmatch = c.domain.startsWith('.') ? 'TRUE' : 'FALSE';
      const path = c.path || '/';
      const secure = c.secure ? 'TRUE' : 'FALSE';
      const expires = c.expirationDate ? Math.round(c.expirationDate) : 0;
      netscapeLines.push(`${domain}\t${tailmatch}\t${path}\t${secure}\t${expires}\t${c.name}\t${c.value}`);
    });
    copyToClipboard(netscapeLines.join('\n'), '已复制 Netscape (yt-dlp) 格式！');
  });

  elSearchInput.addEventListener('input', renderCookieList);

  elCheckReveal.addEventListener('change', (e) => {
    revealAll = e.target.checked;
    renderCookieList();
  });
}

// Check local bridge connection status via background worker
function checkBridgeStatus() {
  chrome.runtime.sendMessage({ type: 'GET_BRIDGE_STATUS' }, (res) => {
    if (chrome.runtime.lastError || !res) {
      updateBridgeUI(false);
      return;
    }
    updateBridgeUI(!!res.isConnected);
  });
}

function updateBridgeUI(connected) {
  if (connected) {
    elBridgePill.className = 'bridge-status-pill connected';
    elBridgeText.textContent = '本地通信已连接';
    elBridgePill.title = '本地通信服务在线 (127.0.0.1:18888)';
  } else {
    elBridgePill.className = 'bridge-status-pill disconnected';
    elBridgeText.textContent = '本地服务离线';
    elBridgePill.title = '未连接到 127.0.0.1:18888。点击可重试连接。';
  }
}

// Fetch cookies for the active browser tab
async function loadCookies() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs || !tabs.length) {
      elDomain.textContent = '无法获取当前标签页';
      return;
    }

    const tab = tabs[0];
    activeTabUrl = tab.url || '';

    // Check if system page
    if (!activeTabUrl || activeTabUrl.startsWith('chrome://') || activeTabUrl.startsWith('edge://') || activeTabUrl.startsWith('about:')) {
      elDomain.textContent = '系统内置页面';
      elCountBadge.textContent = '0 个';
      elSystemTip.style.display = 'block';
      elPresetCard.style.display = 'none';
      elCookieList.innerHTML = '';
      elEmptyState.style.display = 'none';
      currentCookies = [];
      return;
    }

    elSystemTip.style.display = 'none';
    const parsedUrl = new URL(activeTabUrl);
    activeDomain = parsedUrl.hostname;
    elDomain.textContent = activeDomain;
    elDomain.title = activeTabUrl;

    // Fetch cookies for this specific URL & root domain
    const urlCookies = await chrome.cookies.getAll({ url: activeTabUrl });
    const domainCookies = await chrome.cookies.getAll({ domain: activeDomain });

    // Deduplicate by name + domain + path
    const map = new Map();
    [...urlCookies, ...domainCookies].forEach(c => {
      const key = `${c.name}@${c.domain}${c.path}`;
      if (!map.has(key)) {
        map.set(key, c);
      }
    });

    currentCookies = Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
    elCountBadge.textContent = `${currentCookies.length} 个`;

    checkServicePresets();
    renderCookieList();
  } catch (err) {
    console.error('加载 Cookie 失败:', err);
    elDomain.textContent = '读取失败';
    showToast('读取 Cookie 出现异常: ' + err.message, true);
  }
}

// Check if current site matches any known service preset
function checkServicePresets() {
  const matched = SERVICE_PRESETS.find(p => p.pattern.test(activeDomain) || p.pattern.test(activeTabUrl));
  if (!matched) {
    elPresetCard.style.display = 'none';
    return;
  }

  elPresetServiceName.textContent = matched.service;
  elPresetServiceTip.textContent = matched.tip;
  elPresetTokens.innerHTML = '';

  let hasFoundToken = false;
  matched.keys.forEach(keyName => {
    const found = currentCookies.find(c => c.name.toLowerCase() === keyName.toLowerCase());
    if (found) {
      hasFoundToken = true;
      const row = document.createElement('div');
      row.className = 'preset-token-row';
      row.innerHTML = `
        <div class="preset-token-info">
          <span class="preset-token-name">${found.name}</span>
          <span class="preset-token-val" title="${escapeHtml(found.value)}">${maskValue(found.value)}</span>
        </div>
        <button class="btn-mini-copy" data-val="${escapeHtml(found.value)}" data-name="${escapeHtml(found.name)}">
          复制
        </button>
      `;
      row.querySelector('.btn-mini-copy').addEventListener('click', (e) => {
        const val = e.currentTarget.getAttribute('data-val');
        const name = e.currentTarget.getAttribute('data-name');
        copyToClipboard(val, `已复制 ${name} 凭据！`);
      });
      elPresetTokens.appendChild(row);
    }
  });

  if (hasFoundToken) {
    elPresetCard.style.display = 'flex';
  } else {
    elPresetTokens.innerHTML = `
      <div style="font-size: 11px; color: #f59e0b; padding: 4px 0;">
        ⚠️ 检测到为 ${matched.service} 站点，但未在此页面找到登录鉴权 Cookie，请确保已在该站点登录。
      </div>
    `;
    elPresetCard.style.display = 'flex';
  }
}

// Render filtered cookie list
function renderCookieList() {
  const query = elSearchInput.value.trim().toLowerCase();
  const filtered = currentCookies.filter(c => {
    if (!query) return true;
    return c.name.toLowerCase().includes(query) || c.value.toLowerCase().includes(query);
  });

  if (!filtered.length) {
    elCookieList.innerHTML = '';
    elEmptyState.style.display = 'block';
    return;
  }

  elEmptyState.style.display = 'none';
  elCookieList.innerHTML = '';

  filtered.forEach(c => {
    const row = document.createElement('div');
    row.className = 'cookie-row';

    const tagsHtml = [
      c.httpOnly ? '<span class="tag tag-httponly">HttpOnly</span>' : '',
      c.secure ? '<span class="tag tag-secure">Secure</span>' : ''
    ].filter(Boolean).join('');

    const displayVal = revealAll ? escapeHtml(c.value) : maskValue(c.value);

    row.innerHTML = `
      <div class="cookie-row-top">
        <div class="cookie-name-wrap">
          <span class="cookie-name" title="${escapeHtml(c.name)}">${escapeHtml(c.name)}</span>
          ${tagsHtml}
        </div>
        <div class="row-actions">
          <button class="copy-mini-btn" title="复制此 Cookie 值" data-val="${escapeHtml(c.value)}" data-name="${escapeHtml(c.name)}">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          </button>
        </div>
      </div>
      <div class="cookie-val" title="点击可快速复制">${displayVal}</div>
    `;

    const copyBtn = row.querySelector('.copy-mini-btn');
    copyBtn.addEventListener('click', () => {
      copyToClipboard(c.value, `已复制 ${c.name}！`);
    });

    const valEl = row.querySelector('.cookie-val');
    valEl.style.cursor = 'pointer';
    valEl.addEventListener('click', () => {
      copyToClipboard(c.value, `已复制 ${c.name}！`);
    });

    elCookieList.appendChild(row);
  });
}

// Utility: Copy text to clipboard
async function copyToClipboard(text, successMsg) {
  try {
    await navigator.clipboard.writeText(text);
    showToast(successMsg);
  } catch (err) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      showToast(successMsg);
    } catch (e) {
      showToast('复制失败，请手动选择', true);
    }
    document.body.removeChild(textArea);
  }
}

// Utility: Mask value for privacy
function maskValue(val) {
  if (!val) return '';
  if (val.length <= 8) return '••••••••';
  return val.slice(0, 4) + '••••••••' + val.slice(-4);
}

// Utility: HTML Escaping
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Utility: Show floating toast
let toastTimer = null;
function showToast(msg, isError = false) {
  clearTimeout(toastTimer);
  elToast.textContent = msg;
  elToast.style.background = isError ? '#ef4444' : '#10b981';
  elToast.classList.add('show');
  toastTimer = setTimeout(() => {
    elToast.classList.remove('show');
  }, 2000);
}
