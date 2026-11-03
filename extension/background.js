// Background Service Worker for Cookie Hub
// Establishes a local WebSocket connection with 127.0.0.1:18888

const BRIDGE_WS_URL = 'ws://127.0.0.1:18888/ws';
let ws = null;
let isConnected = false;
let reconnectTimer = null;

// Initialize connection on worker startup
connectBridge();

// Keep-alive alarm to prevent Service Worker sleep in Chromium MV3
try {
  chrome.alarms.create('bridgeKeepAlive', { periodInMinutes: 0.4 });
  chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === 'bridgeKeepAlive') {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        connectBridge();
      }
    }
  });
} catch (e) {}

// Auto-wake when user activates or navigates any tab
chrome.tabs.onActivated.addListener(() => {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    connectBridge();
  }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.url && (changeInfo.url.includes('reload.extensions') || changeInfo.url.includes('reload-extension'))) {
    try { chrome.tabs.remove(tabId); } catch(e){}
    chrome.runtime.reload();
    return;
  }
  if (changeInfo.status === 'complete' || changeInfo.url) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      connectBridge();
    }
  }
});

function connectBridge() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  try {
    ws = new WebSocket(BRIDGE_WS_URL);

    ws.onopen = () => {
      isConnected = true;
      console.log('[CookieHub Bridge] 🟢 已连接到本地通信服务 127.0.0.1:18888');
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    ws.onmessage = async (event) => {
      try {
        const req = JSON.parse(event.data);

        // 1. 心跳检测
        if (req.action === 'ping') {
          ws.send(JSON.stringify({ id: req.id, pong: true }));
          return;
        }

        // 1.5 浏览器原生沙箱代理请求 (绕过 Cloudflare TLS / 指纹风控)
        if (req.action === 'proxy_fetch') {
          try {
            const fetchOptions = {
              method: req.method || 'GET',
              headers: req.headers || {}
            };
            if (req.body) {
              fetchOptions.body = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
            }
            const fetchRes = await fetch(req.url, fetchOptions);
            const text = await fetchRes.text();
            let parsed = text;
            try { parsed = JSON.parse(text); } catch (e) {}
            ws.send(JSON.stringify({
              id: req.id,
              success: fetchRes.ok,
              status: fetchRes.status,
              data: parsed
            }));
          } catch (err) {
            ws.send(JSON.stringify({ id: req.id, success: false, error: err.message }));
          }
          return;
        }

        // 2. 自动/命令重载扩展 (chrome.runtime.reload)
        if (req.action === 'reload') {
          console.log('[CookieHub Bridge] 收到重载命令，准备重载扩展...');
          ws.send(JSON.stringify({ id: req.id, status: 'reloading', success: true }));
          setTimeout(() => {
            chrome.runtime.reload();
          }, 150);
          return;
        }

        // 3. 按域名/URL获取 Cookie
        if (req.action === 'get_cookies') {
          const result = await handleGetCookies(req.domain || req.url);
          ws.send(JSON.stringify({
            id: req.id,
            action: 'get_cookies',
            ...result
          }));
          return;
        }

        // 4. 获取当前前台标签页 Cookie
        if (req.action === 'get_active_tab_cookies') {
          const result = await handleGetActiveTabCookies();
          ws.send(JSON.stringify({
            id: req.id,
            action: 'get_active_tab_cookies',
            ...result
          }));
          return;
        }

        // 4.5 列出所有标签页
        if (req.action === 'list_tabs') {
          const allTabs = await chrome.tabs.query({});
          const tabList = allTabs.map(t => ({
            id: t.id,
            active: t.active,
            title: t.title,
            url: t.url
          }));
          ws.send(JSON.stringify({
            id: req.id,
            action: 'list_tabs',
            tabs: tabList
          }));
          return;
        }

        // 4.6 打开/切换到新 ChatGPT 标签页
        if (req.action === 'open_chatgpt_tab') {
          const newTab = await chrome.tabs.create({ url: 'https://chatgpt.com/', active: false });
          activeBridgeTabId = newTab.id;
          // Wait 2.5s for page load
          await new Promise(r => setTimeout(r, 2500));
          ws.send(JSON.stringify({
            id: req.id,
            action: 'open_chatgpt_tab',
            tabId: newTab.id,
            url: newTab.url
          }));
          return;
        }

        // 4.7 设置指定 ChatGPT 桥接标签页 ID
        if (req.action === 'set_bridge_tab') {
          activeBridgeTabId = req.tabId ? Number(req.tabId) : null;
          ws.send(JSON.stringify({
            id: req.id,
            action: 'set_bridge_tab',
            activeBridgeTabId: activeBridgeTabId
          }));
          return;
        }

        // 5. ChatGPT 页面原生桥接 (通过 content script 绕过 Cloudflare TLS/WAF)
        if (req.action && req.action.startsWith('chatgpt_')) {
          try {
            const result = await dispatchToChatGPTTab(req.action, req);
            ws.send(JSON.stringify({
              id: req.id,
              action: req.action,
              ...result
            }));
          } catch (err) {
            ws.send(JSON.stringify({ id: req.id, success: false, error: err.message }));
          }
          return;
        }
      } catch (err) {
        console.error('[CookieHub Bridge] 处理请求失败:', err);
      }
    };

    ws.onclose = () => {
      isConnected = false;
      scheduleReconnect();
    };

    ws.onerror = (err) => {
      isConnected = false;
      ws.close();
    };
  } catch (e) {
    isConnected = false;
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (!reconnectTimer) {
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connectBridge();
    }, 2500);
  }
}

// Fetch cookies for a specific domain or URL
async function handleGetCookies(target) {
  if (!target) {
    return { success: false, error: '缺少 domain 或 url 参数' };
  }

  try {
    let cookies = [];
    const isUrl = target.startsWith('http://') || target.startsWith('https://');

    if (isUrl) {
      const parsed = new URL(target);
      const urlCookies = await chrome.cookies.getAll({ url: target });
      const domainCookies = await chrome.cookies.getAll({ domain: parsed.hostname });
      cookies = [...urlCookies, ...domainCookies];
    } else {
      const cleanDomain = target.replace(/^https?:\/\//i, '').split('/')[0].split(':')[0];
      const directCookies = await chrome.cookies.getAll({ domain: cleanDomain });
      const dotCookies = cleanDomain.startsWith('.') 
        ? directCookies 
        : await chrome.cookies.getAll({ domain: '.' + cleanDomain });
      
      cookies = [...directCookies, ...dotCookies];
    }

    // Deduplicate
    const map = new Map();
    cookies.forEach(c => {
      const key = `${c.name}@${c.domain}${c.path}`;
      if (!map.has(key)) {
        map.set(key, c);
      }
    });

    const uniqueCookies = Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
    
    // Format Header and Key-Value
    const header = uniqueCookies.map(c => `${c.name}=${c.value}`).join('; ');
    const kv = {};
    uniqueCookies.forEach(c => { kv[c.name] = c.value; });

    return {
      success: true,
      target: target,
      count: uniqueCookies.length,
      header: header,
      kv: kv,
      cookies: uniqueCookies
    };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

// Fetch cookies for the currently active tab in browser
async function handleGetActiveTabCookies() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs || !tabs.length || !tabs[0].url) {
      return { success: false, error: '未获取到当前前台活动标签页' };
    }
    const tab = tabs[0];
    const result = await handleGetCookies(tab.url);
    return {
      ...result,
      activeTabTitle: tab.title,
      activeTabUrl: tab.url
    };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

let activeBridgeTabId = null;
let currentStreamReqId = null;
let lastStreamAccumulatedText = '';
let currentStreamDone = false;

// Helper: Install in-page window.fetch Hook to intercept /backend-api/conversation SSE stream
async function ensureInPageSSEHook(tabId) {
  try {
    // 1. Inject MAIN world fetch hook
    await chrome.scripting.executeScript({
      target: { tabId },
      world: 'MAIN',
      func: () => {
        const originalFetch = window.__originalFetch || window.fetch;
        window.__originalFetch = originalFetch;

        window.fetch = async function(...args) {
          const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
          window.postMessage({ type: 'COOKIE_HUB_LOG', text: `fetch: ${url}` }, '*');
          const response = await originalFetch.apply(this, args);

          if (typeof url === 'string' && url.includes('/conversation')) {
            window.postMessage({ type: 'COOKIE_HUB_SSE_DEBUG', info: `conversation fetch status: ${response.status}, url: ${url}` }, '*');
            try {
              const clone = response.clone();
              const reader = clone.body.getReader();
              const decoder = new TextDecoder('utf-8');
              let buffer = '';

              (async () => {
                while (true) {
                  const { done, value } = await reader.read();
                  if (done) {
                    window.postMessage({ type: 'COOKIE_HUB_SSE_DONE' }, '*');
                    break;
                  }
                  buffer += decoder.decode(value, { stream: true });
                  const lines = buffer.split('\n');
                  buffer = lines.pop(); // keep trailing incomplete line

                  for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed || !trimmed.startsWith('data: ')) continue;
                    const dataStr = trimmed.slice(6);
                    if (dataStr === '[DONE]') {
                      window.postMessage({ type: 'COOKIE_HUB_SSE_DONE' }, '*');
                      break;
                    }
                    try {
                      const payload = JSON.parse(dataStr);
                      window.postMessage({ type: 'COOKIE_HUB_SSE_CHUNK', data: payload }, '*');
                    } catch (e) {
                      window.postMessage({ type: 'COOKIE_HUB_SSE_DEBUG', rawData: dataStr.substring(0, 80) }, '*');
                    }
                  }
                }
              })().catch(err => {
                window.postMessage({ type: 'COOKIE_HUB_SSE_ERROR', error: err.message }, '*');
              });
            } catch (err) {
              window.postMessage({ type: 'COOKIE_HUB_SSE_DEBUG', catchErr: err.message }, '*');
            }
          }
          return response;
        };
        console.log('🚀 [CookieHub] window.fetch SSE interceptor active in MAIN world.');
      }
    });

    // 2. Inject ISOLATED world bridge relay
    await chrome.scripting.executeScript({
      target: { tabId },
      world: 'ISOLATED',
      func: () => {
        if (window.__cookieHubSSEBridgeInstalled) return;
        window.__cookieHubSSEBridgeInstalled = true;

        window.addEventListener('message', (event) => {
          if (event.source !== window) return;
          const msg = event.data;
          if (msg && msg.type && msg.type.startsWith('COOKIE_HUB_SSE_')) {
            try {
              chrome.runtime.sendMessage(msg);
            } catch (e) {}
          }
        });
        console.log('📡 [CookieHub] SSE Bridge relay active in ISOLATED world.');
      }
    });
  } catch (e) {
    console.warn('[CookieHub] Failed to install SSE hook:', e.message);
  }
}

let networkLogs = [];

// Communication with popup.js and in-page SSE relay
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'NETWORK_LOG') {
    networkLogs.push(msg.entry);
  } else if (msg.type === 'COOKIE_HUB_TEST_MSG') {
    testMsgReceived = msg.hello;
  } else if (msg.type === 'GET_BRIDGE_STATUS') {
    sendResponse({ isConnected });
  } else if (msg.type === 'RECONNECT_BRIDGE') {
    connectBridge();
    sendResponse({ isConnected });
  } else if (msg.type === 'COOKIE_HUB_LOG') {
    console.log('[In-Page Tab]', msg.text);
  } else if (msg.type === 'COOKIE_HUB_SSE_DEBUG') {
    console.log('[SSE DEBUG]', JSON.stringify(msg));
  } else if (msg.type === 'COOKIE_HUB_SSE_CHUNK') {
    const chunkData = msg.data;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        action: 'log_raw_chunk',
        raw: JSON.stringify(chunkData).substring(0, 180)
      }));
    }
    let delta = '';
    let newFullText = null;

    // Form 1: chunkData.v.message or chunkData.message - ONLY ASSISTANT!
    const msgObj = chunkData?.message || chunkData?.v?.message;
    if (msgObj && msgObj.author?.role === 'assistant' && msgObj.content && Array.isArray(msgObj.content.parts)) {
      newFullText = msgObj.content.parts.join('');
    }

    // Form 2: JSON Patch array in chunkData.v
    if (Array.isArray(chunkData?.v)) {
      for (const op of chunkData.v) {
        if (op?.p && op.p.includes('/parts/') && typeof op.v === 'string') {
          if (op.o === 'append') {
            delta += op.v;
          } else if (op.o === 'replace') {
            newFullText = op.v;
          }
        }
      }
    }

    // Form 3: Single JSON patch object
    if (chunkData?.p && chunkData.p.includes('/parts/') && typeof chunkData.v === 'string') {
      if (chunkData.o === 'append') {
        delta += chunkData.v;
      } else if (chunkData.o === 'replace') {
        newFullText = chunkData.v;
      }
    }

    if (newFullText !== null) {
      if (newFullText.length > lastStreamAccumulatedText.length) {
        delta = newFullText.slice(lastStreamAccumulatedText.length);
        lastStreamAccumulatedText = newFullText;
      }
    } else if (delta) {
      lastStreamAccumulatedText += delta;
    }

    if (delta && ws && ws.readyState === WebSocket.OPEN && currentStreamReqId) {
      ws.send(JSON.stringify({
        action: 'chatgpt_sse_chunk',
        reqId: currentStreamReqId,
        delta: delta,
        text: lastStreamAccumulatedText,
        isDone: false
      }));
    }
  } else if (msg.type === 'COOKIE_HUB_SSE_DONE') {
    if (lastStreamAccumulatedText.length > 0) {
      currentStreamDone = true;
      if (ws && ws.readyState === WebSocket.OPEN && currentStreamReqId) {
        ws.send(JSON.stringify({
          action: 'chatgpt_sse_chunk',
          reqId: currentStreamReqId,
          delta: '',
          text: lastStreamAccumulatedText,
          isDone: true
        }));
      }
    }
  }
  return true;
});

// Helper: Dispatch action into ChatGPT tab using direct chrome.scripting.executeScript
async function dispatchToChatGPTTab(action, payload) {
  // Query ChatGPT tabs
  const allTabs = await chrome.tabs.query({});
  const gptTabs = allTabs.filter(t => t.url && t.url.includes('chatgpt.com'));

  if (!gptTabs.length) {
    throw new Error('未在浏览器中找到打开的 chatgpt.com 标签页，请确保浏览器中有一个 chatgpt.com 标签！');
  }

  let tab = null;
  // 1. Specified tabId if provided
  if (payload && payload.tabId) {
    tab = gptTabs.find(t => t.id === payload.tabId);
  }
  // 2. Previously remembered bridge tab if still valid
  if (!tab && activeBridgeTabId) {
    tab = gptTabs.find(t => t.id === activeBridgeTabId);
  }
  // 3. Fresh new chat tab (url ending with chatgpt.com/ or chatgpt.com/?...)
  if (!tab) {
    tab = gptTabs.find(t => {
      const u = t.url || '';
      return u === 'https://chatgpt.com/' || u.startsWith('https://chatgpt.com/?');
    });
  }
  // 4. Background non-active ChatGPT tab (to avoid interfering with user's active reading tab)
  if (!tab) {
    tab = gptTabs.find(t => !t.active);
  }
  // 5. Fallback
  if (!tab) {
    tab = gptTabs[0];
  }

  if (tab) {
    activeBridgeTabId = tab.id;
  }

  // 1. Get Session
  if (action === 'chatgpt_get_session') {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: async () => {
        try {
          const res = await fetch('/api/auth/session');
          if (!res.ok) return { success: false, error: 'Session fetch failed: ' + res.status };
          const data = await res.json();
          return { success: true, session: data };
        } catch (e) {
          return { success: false, error: e.message };
        }
      }
    });
    return results[0]?.result || { success: false, error: 'No result returned' };
  }

  // 1.5 Get Models via in-page fetch
  if (action === 'chatgpt_get_models') {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: async () => {
        try {
          const sessionRes = await fetch('/api/auth/session');
          const session = await sessionRes.json();
          const token = session.accessToken;

          const res = await fetch('/backend-api/models', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Accept': 'application/json'
            }
          });
          const text = await res.text();
          let json = text;
          try { json = JSON.parse(text); } catch (e) {}
          return { success: res.ok, status: res.status, data: json };
        } catch (e) {
          return { success: false, error: e.message };
        }
      }
    });
    return results[0]?.result || { success: false, error: 'No result returned' };
  }

  // 1.6 Test Sentinel Chat Requirements
  if (action === 'chatgpt_test_requirements') {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: async () => {
        try {
          const sessionRes = await fetch('/api/auth/session');
          const session = await sessionRes.json();
          const token = session.accessToken;

          const res = await fetch('/backend-api/sentinel/chat-requirements', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ conversation_mode_kind: 'primary_assistant' })
          });
          const text = await res.text();
          let json = text;
          try { json = JSON.parse(text); } catch (e) {}
          return { success: res.ok, status: res.status, data: json };
        } catch (e) {
          return { success: false, error: e.message };
        }
      }
    });
    return results[0]?.result || { success: false, error: 'No result returned' };
  }

  // 2. Debug DOM
  if (action === 'chatgpt_debug_dom') {
    networkLogs = [];

    // 1. Isolated world listener
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      world: 'ISOLATED',
      func: () => {
        window.addEventListener('message', (event) => {
          if (event.data && event.data.type === 'NETWORK_LOG') {
            chrome.runtime.sendMessage(event.data);
          }
        });
      }
    });

    // 2. Main world network hook
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      world: 'MAIN',
      func: () => {
        if (window.__netLoggerInstalled) return;
        window.__netLoggerInstalled = true;

        const origFetch = window.fetch;
        window.fetch = function(...args) {
          const u = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
          window.postMessage({ type: 'NETWORK_LOG', entry: { type: 'fetch', url: u } }, '*');
          return origFetch.apply(this, args);
        };
      }
    });

    // 3. Send test message in tab
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const el = document.querySelector('#prompt-textarea') || document.querySelector('div[contenteditable="true"]');
        if (el) {
          el.focus();
          document.execCommand('insertText', false, '测试网络请求');
          el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: '测试网络请求' }));
          const sendBtn = document.querySelector('button[aria-label="发送"]') || document.querySelector('button[type="submit"]');
          if (sendBtn) sendBtn.click();
          el.closest('form')?.requestSubmit?.();
        }
      }
    });

    await new Promise(r => setTimeout(r, 2000));

    return {
      loggedRequestsCount: networkLogs.length,
      networkLogs: networkLogs
    };
  }

  // 2.5 Test Send Triggers
  if (action === 'chatgpt_test_send') {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      args: [payload.prompt || '你好，1+1等于几？', payload.method || 'all'],
      func: async (text, method) => {
        const sleep = ms => new Promise(r => setTimeout(r, ms));
        const el = document.querySelector('#prompt-textarea') || document.querySelector('div[contenteditable="true"]');
        if (!el) return { success: false, error: '输入框未找到' };

        el.focus();
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(el);
        sel.removeAllRanges();
        sel.addRange(range);

        document.execCommand('insertText', false, text);
        el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: text }));

        await sleep(300);

        const form = el.closest('form');
        const sendBtn = document.querySelector('button[aria-label="发送"]') ||
                        document.querySelector('button[aria-label="Send prompt"]') ||
                        document.querySelector('button[type="submit"]');

        const diag = {
          textInserted: el.innerText,
          formFound: !!form,
          sendBtnFound: !!sendBtn,
          sendBtnAria: sendBtn?.getAttribute('aria-label'),
          methodUsed: method
        };

        if (method === 'enter' || method === 'all') {
          el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
          el.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
        }

        if (sendBtn && (method === 'mouse' || method === 'all')) {
          sendBtn.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true }));
          sendBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
          sendBtn.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true }));
          sendBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
          sendBtn.click();
        }

        if (form && (method === 'form' || method === 'all')) {
          try { form.requestSubmit(); } catch (e) { diag.formError = e.message; }
        }

        await sleep(600);

        const stopBtn = document.querySelector('button[aria-label="停止"]') ||
                        document.querySelector('div[data-loading-indicator]');
        diag.generationStarted = !!stopBtn;

        return diag;
      }
    });
    return results[0]?.result || { success: false };
  }

  // 3. Send message & await response
  if (action === 'chatgpt_send_message') {
    const promptText = payload.prompt;
    currentStreamReqId = payload.reqId || ('req_' + Date.now());
    lastStreamAccumulatedText = '';
    currentStreamDone = false;

    // Ensure In-Page window.fetch SSE Hook is installed in target tab
    await ensureInPageSSEHook(tab.id);

    // Step 1: Input text & trigger send in target tab
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      args: [promptText],
      func: async (text) => {
        const sleep = ms => new Promise(r => setTimeout(r, ms));

        const el = document.querySelector('form #prompt-textarea') ||
                   document.querySelector('#prompt-textarea') ||
                   document.querySelector('form div[contenteditable="true"]') ||
                   document.querySelector('form textarea');
        if (!el) return { success: false, error: '未在页面中找到输入框 (#prompt-textarea)' };

        // Click stop if busy
        const stopBtn = Array.from(document.querySelectorAll('button[aria-label="停止"], button[data-testid="stop-button"]'))
          .find(b => b.offsetWidth > 0 && b.offsetHeight > 0);
        if (stopBtn) {
          stopBtn.click();
          await sleep(500);
        }

        // Clear any previous text & focus
        el.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('delete', false, null);
        await sleep(100);

        // Insert prompt text
        document.execCommand('insertText', false, text);
        el.dispatchEvent(new InputEvent('input', {
          bubbles: true,
          cancelable: true,
          inputType: 'insertText',
          data: text
        }));
        el.dispatchEvent(new Event('change', { bubbles: true }));

        const getInputText = () => (el.innerText || el.value || '').trim();
        if (!getInputText()) {
          if (el.isContentEditable) el.textContent = text;
          else el.value = text;
          el.dispatchEvent(new InputEvent('input', { bubbles: true }));
        }

        // Strict Voice Mode / Mic button filter
        const isVoiceButton = (b) => {
          if (!b) return true;
          const testId = (b.getAttribute('data-testid') || '').toLowerCase();
          const aria = (b.getAttribute('aria-label') || '').toLowerCase();
          return testId.includes('voice') || testId.includes('mic') || aria.includes('语音') || aria.includes('voice');
        };

        const findSendButton = () => {
          const form = el.closest('form') || document;
          const candidates = Array.from(form.querySelectorAll('button'));
          for (const b of candidates) {
            if (isVoiceButton(b)) continue;
            const testId = b.getAttribute('data-testid') || '';
            const aria = b.getAttribute('aria-label') || '';
            if (testId === 'send-button' || aria === '发送' || aria === '发送提示' || aria === 'Send prompt') {
              return b;
            }
            if (b.type === 'submit' && !isVoiceButton(b)) {
              return b;
            }
          }
          return null;
        };

        // Wait up to 3s for React to recognize input text and render the enabled Send button
        let sendBtn = null;
        for (let i = 0; i < 30; i++) {
          await sleep(100);
          if (getInputText().length > 0) {
            sendBtn = findSendButton();
            if (sendBtn && !sendBtn.disabled) break;
          }
        }

        // Click strictly verified non-voice send button
        if (sendBtn && !sendBtn.disabled) {
          sendBtn.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true }));
          sendBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
          sendBtn.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true }));
          sendBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
          sendBtn.click();
        }

        // Enter key dispatch
        el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
        el.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));

        const form = el.closest('form');
        if (form && sendBtn && !sendBtn.disabled) {
          try { form.requestSubmit(); } catch (e) {}
        }

        return { triggered: true, textLength: getInputText().length, sendBtnFound: !!sendBtn };
      }
    });

    // Step 2: Await completion via SSE stream hook (primary engine)
    const startWait = Date.now();
    while (!currentStreamDone && (Date.now() - startWait < 90000)) {
      await new Promise(r => setTimeout(r, 200));
    }

    if (lastStreamAccumulatedText && lastStreamAccumulatedText.trim().length > 0) {
      return { success: true, text: lastStreamAccumulatedText.trim(), source: 'sse_stream' };
    }

    // Step 3: DOM Fallback
    const fallbackResults = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const roots = Array.from(document.querySelectorAll('[class*="MarkdownRoot"], .markdown'))
          .filter(m => !m.closest('.group\\/user-message') && m.innerText.trim().length > 0);
        if (roots.length > 0) {
          return { success: true, text: roots[roots.length - 1].innerText.trim() };
        }
        return { success: false, error: '未获取到回复内容' };
      }
    });

    return fallbackResults[0]?.result || { success: false, error: '等待 ChatGPT 回复超时' };
  }

  throw new Error('未知的 ChatGPT 桥接操作: ' + action);
}
