const http = require('http');
const { WebSocketServer } = require('ws');
const { URL } = require('url');
const fs = require('fs');
const path = require('path');

const PORT = 18888;
const HOST = '127.0.0.1'; // 严格绑定到本地回环地址

// Store active extension WebSocket connections
const extensionSockets = new Set();
// Store pending HTTP requests waiting for extension response: reqId -> { resolve, reject, timer }
const pendingRequests = new Map();

// Map to route SSE streaming events to active HTTP responses: reqId -> { onChunk, onDone }
const activeStreams = new Map();
let currentBridgeTabId = null;

// Create HTTP Server
const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const parsedUrl = new URL(req.url, `http://${req.headers.host || '127.0.0.1'}`);
  const pathname = parsedUrl.pathname;

  // 1. Health / Status Check
  if (pathname === '/' || pathname === '/status' || pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({
      status: 'ok',
      service: 'Cookie Hub Local Bridge Server',
      port: PORT,
      extensionConnected: extensionSockets.size > 0,
      connectedClients: extensionSockets.size,
      autoReloadWatching: true,
      endpoints: {
        cookies: '/cookies?domain=bilibili.com',
        activeTab: '/active',
        reload: '/reload',
        status: '/status'
      }
    }, null, 2));
    return;
  }

  // 2. Command Triggered Extension Reload (/reload)
  if (pathname === '/reload') {
    if (extensionSockets.size === 0) {
      res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        error: '扩展尚未连接本地服务，请先在浏览器扩展页确认 Cookie Hub 已加载或开启。'
      }));
      return;
    }

    try {
      await dispatchToExtension('reload', { trigger: 'manual_command' });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        success: true,
        message: '🟢 已向 Edge / Chrome 扩展发送重载指令 (chrome.runtime.reload)'
      }, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.5 Browser-native fetch via extension (bypasses Cloudflare TLS fingerprinting)
  if (pathname === '/proxy_fetch' && req.method === 'POST') {
    if (extensionSockets.size === 0) {
      res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: '浏览器扩展未连接' }));
      return;
    }

    try {
      const body = await readRequestBody(req);
      const json = JSON.parse(body || '{}');
      const result = await dispatchToExtension('proxy_fetch', json);
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(result, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.7 Tab Management (/tabs and /chatgpt/open)
  if (pathname === '/tabs') {
    try {
      const data = await dispatchToExtension('list_tabs', {});
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  if (pathname === '/chatgpt/open') {
    try {
      const data = await dispatchToExtension('open_chatgpt_tab', {});
      if (data && data.tabId) currentBridgeTabId = Number(data.tabId);
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  if (pathname === '/chatgpt/set_tab') {
    try {
      const tabId = parsedUrl.searchParams.get('tabId');
      if (tabId) currentBridgeTabId = Number(tabId);
      const data = await dispatchToExtension('set_bridge_tab', { tabId });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.8 ChatGPT In-Page Bridge: Get Session (/chatgpt/session)
  if (pathname === '/chatgpt/session') {
    if (extensionSockets.size === 0) {
      res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: '浏览器扩展未连接' }));
      return;
    }
    try {
      const data = await dispatchToExtension('chatgpt_get_session', { tabId: currentBridgeTabId });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.82 ChatGPT Models (/chatgpt/models)
  if (pathname === '/chatgpt/models') {
    try {
      const data = await dispatchToExtension('chatgpt_get_models', { tabId: currentBridgeTabId });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.83 ChatGPT Sentinel Requirements (/chatgpt/requirements)
  if (pathname === '/chatgpt/requirements') {
    try {
      const data = await dispatchToExtension('chatgpt_test_requirements', {});
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.85 ChatGPT Debug DOM (/chatgpt/debug)
  if (pathname === '/chatgpt/debug') {
    try {
      const data = await dispatchToExtension('chatgpt_debug_dom', {});
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.86 ChatGPT Read Latest Reply (/chatgpt/latest)
  if (pathname === '/chatgpt/latest') {
    try {
      const tabId = parsedUrl.searchParams.get('tabId') || currentBridgeTabId;
      const data = await dispatchToExtension('chatgpt_get_latest_reply', { tabId: tabId ? Number(tabId) : null });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.87 ChatGPT Send Prompt Direct (/chatgpt/send_prompt)
  if (pathname === '/chatgpt/send_prompt') {
    try {
      const tabId = parsedUrl.searchParams.get('tabId') || currentBridgeTabId;
      const prompt = parsedUrl.searchParams.get('prompt') || '继续';
      const data = await dispatchToExtension('chatgpt_send_message', {
        prompt: prompt,
        tabId: tabId ? Number(tabId) : null
      });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.88 ChatGPT Inspect Tab (/chatgpt/inspect)
  if (pathname === '/chatgpt/inspect') {
    try {
      const tabId = parsedUrl.searchParams.get('tabId') || currentBridgeTabId;
      const data = await dispatchToExtension('chatgpt_inspect_tab', { tabId: tabId ? Number(tabId) : null });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.86 ChatGPT Test Input (/chatgpt/test_input)
  if (pathname === '/chatgpt/test_input') {
    try {
      const text = parsedUrl.searchParams.get('text') || '你好测试';
      const data = await dispatchToExtension('chatgpt_test_input', { text });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.87 ChatGPT Test Send (/chatgpt/test_send)
  if (pathname === '/chatgpt/test_send') {
    try {
      const prompt = parsedUrl.searchParams.get('prompt') || '你好，1+1等于几？';
      const method = parsedUrl.searchParams.get('method') || 'all';
      const data = await dispatchToExtension('chatgpt_test_send', { prompt, method });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 2.89 OpenAI Compatible Models (/v1/models) -> 自动代理至统一中枢服务 (18800)
  if (pathname === '/v1/models' && req.method === 'GET') {
    const proxyReq = http.request({
      hostname: '127.0.0.1',
      port: 18800,
      path: '/v1/models',
      method: 'GET',
      headers: { ...(req.headers.authorization ? { 'Authorization': req.headers.authorization } : {}) }
    }, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });
    proxyReq.on('error', (err) => {
      res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: `模型列表代理失败 (18800): ${err.message}` }));
    });
    proxyReq.end();
    return;
  }

  // 2.9 ChatGPT Chat / OpenAI Compatible Completions (/v1/chat/completions or /chatgpt/chat)
  if ((pathname === '/chatgpt/chat' || pathname === '/v1/chat/completions') && req.method === 'POST') {
    try {
      const body = await readRequestBody(req);
      const json = JSON.parse(body || '{}');

      const reqModel = String(json.model || '').toLowerCase().trim();
      const isMoniModel = reqModel.includes('moni') || reqModel === 'chatgpt-web' || reqModel === 'chatgpt-web-moni';

      // 严格分流：如果不是显式的 moni / chatgpt-web 模拟输入模型，一律代理转发至 18800 逆向引擎，绝不触碰浏览器！
      if (!isMoniModel && reqModel && reqModel !== 'default') {
        const proxyReq = http.request({
          hostname: '127.0.0.1',
          port: 18800,
          path: '/v1/chat/completions',
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(req.headers.authorization ? { 'Authorization': req.headers.authorization } : {})
          }
        }, (proxyRes) => {
          res.writeHead(proxyRes.statusCode, proxyRes.headers);
          proxyRes.pipe(res);
        });
        proxyReq.on('error', (err) => {
          res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
          res.end(JSON.stringify({ error: { message: `逆向引擎代理转发失败 (18800): ${err.message}`, type: 'proxy_error' } }));
        });
        proxyReq.write(body);
        proxyReq.end();
        return;
      }

      // 仅当为 moni 或 chatgpt-web 时，才需要浏览器扩展注入
      if (extensionSockets.size === 0) {
        res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: '浏览器扩展未连接，无法执行网页模拟输入' }));
        return;
      }

      let promptText = json.prompt || '';
      if (!promptText && Array.isArray(json.messages)) {
        const lastUser = [...json.messages].reverse().find(m => m.role === 'user');
        promptText = lastUser ? (typeof lastUser.content === 'string' ? lastUser.content : JSON.stringify(lastUser.content)) : '';
      }

      if (!promptText) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: '缺少 prompt 或 messages 参数' }));
        return;
      }

      const isStream = json.stream === true;
      const streamReqId = 'stream_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);

      if (isStream) {
        res.writeHead(200, {
          'Content-Type': 'text/event-stream; charset=utf-8',
          'Cache-Control': 'no-cache, no-transform',
          'Connection': 'keep-alive',
          'Access-Control-Allow-Origin': '*'
        });
        if (typeof res.flushHeaders === 'function') res.flushHeaders();

        let streamClosed = false;
        let receivedAnyChunk = false;
        const sendChunk = (delta) => {
          if (!streamClosed && delta) {
            receivedAnyChunk = true;
            const chunkObj = {
              id: 'chatcmpl-' + Date.now(),
              object: 'chat.completion.chunk',
              created: Math.floor(Date.now() / 1000),
              model: json.model || 'chatgpt-web',
              choices: [
                {
                  index: 0,
                  delta: { content: delta },
                  finish_reason: null
                }
              ]
            };
            res.write(`data: ${JSON.stringify(chunkObj)}\n\n`);
          }
        };

        const finishStream = (force = false) => {
          if (!streamClosed) {
            if (!force && !receivedAnyChunk) return;
            const endObj = {
              id: 'chatcmpl-' + Date.now(),
              object: 'chat.completion.chunk',
              created: Math.floor(Date.now() / 1000),
              model: json.model || 'chatgpt-web',
              choices: [
                {
                  index: 0,
                  delta: {},
                  finish_reason: 'stop'
                }
              ]
            };
            res.write(`data: ${JSON.stringify(endObj)}\n\n`);
            res.write('data: [DONE]\n\n');
            res.end();
            streamClosed = true;
            activeStreams.delete(streamReqId);
          }
        };

        activeStreams.set(streamReqId, {
          onChunk: (delta) => sendChunk(delta),
          onDone: () => finishStream(false)
        });

        req.on('close', () => {
          streamClosed = true;
          activeStreams.delete(streamReqId);
        });

        dispatchToExtension('chatgpt_send_message', { reqId: streamReqId, prompt: promptText, tabId: currentBridgeTabId }).then((result) => {
          // If stream not closed yet, send result text if not sent, then finish
          if (!streamClosed) {
            if (result && result.text && !receivedAnyChunk) sendChunk(result.text);
            finishStream(true);
          }
        }).catch(err => {
          if (!streamClosed) {
            res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
            res.write('data: [DONE]\n\n');
            res.end();
            streamClosed = true;
            activeStreams.delete(streamReqId);
          }
        });
        return;
      }

      // Non-stream mode: accumulate SSE stream tokens for 100% purity, fallback to DOM result
      let accumulatedSSEText = '';
      activeStreams.set(streamReqId, {
        onChunk: (delta, fullText) => {
          accumulatedSSEText = fullText || (accumulatedSSEText + delta);
        },
        onDone: (finalText) => {
          if (finalText) accumulatedSSEText = finalText;
          activeStreams.delete(streamReqId);
        }
      });

      const result = await dispatchToExtension('chatgpt_send_message', { reqId: streamReqId, prompt: promptText, tabId: currentBridgeTabId });
      activeStreams.delete(streamReqId);

      const finalContent = (accumulatedSSEText && accumulatedSSEText.trim()) ? accumulatedSSEText.trim() : (result.text || '');

      const openaiResp = {
        id: 'chatcmpl-' + Date.now(),
        object: 'chat.completion',
        created: Math.floor(Date.now() / 1000),
        model: json.model || 'chatgpt-web',
        choices: [
          {
            index: 0,
            message: {
              role: 'assistant',
              content: finalContent
            },
            finish_reason: 'stop'
          }
        ]
      };

      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(openaiResp, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 3. Fetch Cookies by Domain / URL
  if (pathname === '/cookies') {
    let domain = parsedUrl.searchParams.get('domain') || parsedUrl.searchParams.get('url');
    let format = parsedUrl.searchParams.get('format') || 'full';

    if (!domain && req.method === 'POST') {
      try {
        const body = await readRequestBody(req);
        const json = JSON.parse(body || '{}');
        domain = json.domain || json.url;
        if (json.format) format = json.format;
      } catch (e) {
        // ignore parse error
      }
    }

    if (!domain) {
      res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        error: '缺少必填参数 domain 或 url，例如: /cookies?domain=bilibili.com'
      }));
      return;
    }

    if (extensionSockets.size === 0) {
      res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        error: '浏览器扩展未连接本地服务。请确保 Edge / Chrome 浏览器已打开，且 Cookie Hub 扩展已加载。',
        tip: '可在浏览器扩展页面检查 Cookie Hub 是否已启用，或点击插件图标唤醒。'
      }));
      return;
    }

    try {
      const data = await dispatchToExtension('get_cookies', { domain });

      if (format === 'header') {
        res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end(data.header || '');
      } else if (format === 'netscape' || format === 'txt') {
        const netscapeLines = [
          '# Netscape HTTP Cookie File',
          '# https://curl.se/docs/http-cookies.html',
          '# Generated by Cookie Hub',
          ''
        ];
        (data.cookies || []).forEach(c => {
          const initialDot = c.domain.startsWith('.');
          const tailmatch = initialDot ? 'TRUE' : 'FALSE';
          const d = c.domain;
          const p = c.path || '/';
          const secure = c.secure ? 'TRUE' : 'FALSE';
          const expires = c.expirationDate ? Math.round(c.expirationDate) : 0;
          netscapeLines.push(`${d}\t${tailmatch}\t${p}\t${secure}\t${expires}\t${c.name}\t${c.value}`);
        });
        res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end(netscapeLines.join('\n'));
      } else if (format === 'json' || format === 'kv') {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(data.kv || {}, null, 2));
      } else {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify(data, null, 2));
      }
    } catch (err) {
      res.writeHead(504, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 4. Fetch Cookies of Currently Active Tab
  if (pathname === '/active') {
    if (extensionSockets.size === 0) {
      res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        error: '浏览器扩展未连接本地服务。请确保浏览器已打开。'
      }));
      return;
    }

    try {
      const data = await dispatchToExtension('get_active_tab_cookies', {});
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(504, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 5. Suno Auto-Fetch & Session Wakeup (/suno/auto_fetch or /suno/cookies)
  if (pathname === '/suno/auto_fetch' || pathname === '/suno/cookies') {
    if (extensionSockets.size === 0) {
      res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        success: false,
        error: '浏览器扩展未连接本地服务，请在浏览器中确认 Cookie Hub 扩展已加载并启用。'
      }));
      return;
    }

    try {
      const forceVisit = parsedUrl.searchParams.get('force') === 'true' || parsedUrl.searchParams.get('visit') === 'true';
      const timeout = parseInt(parsedUrl.searchParams.get('timeout')) || 25000;
      const data = await dispatchToExtension('suno_auto_fetch', { forceVisit, timeout });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
    return;
  }


  // 5.05 Suno 页面 DOM 自动化（由本地 Cookie Hub 扩展在登录页面内执行）
  if (pathname === '/suno/execute' && req.method === 'POST') {
    if (extensionSockets.size === 0) {
      res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: '浏览器扩展未连接本地服务' }));
      return;
    }
    try {
      const body = await readRequestBody(req);
      const json = JSON.parse(body || '{}');
      const data = await dispatchToExtension('suno_execute', {
        operation: json.operation || 'inspect',
        payload: json.payload || {},
        timeout: json.timeout || 30000
      });
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(data, null, 2));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
    return;
  }

  // 5.1 Suno Save In-Page Decrypted Audio (/suno/save_audio) -> 浏览器播放解密音频无损复用与持久化
  if (pathname === '/suno/save_audio' && req.method === 'POST') {
    try {
      const clipId = req.headers['x-suno-clip-id'] || `clip_${Date.now()}`;
      const format = req.headers['x-suno-format'] || 'm4a';

      const chunks = [];
      req.on('data', chunk => chunks.push(chunk));
      req.on('end', () => {
        const buffer = Buffer.concat(chunks);
        const downloadDir = path.join(__dirname, '..', 'downloads', 'suno');
        if (!fs.existsSync(downloadDir)) {
          fs.mkdirSync(downloadDir, { recursive: true });
        }
        const fileName = `${clipId}.${format}`;
        const filePath = path.join(downloadDir, fileName);
        fs.writeFileSync(filePath, buffer);
        console.log(`[Bridge Server] 🎵 成功复用并保存浏览器播放解密音频: ${fileName} (${(buffer.length / 1024 / 1024).toFixed(2)} MB)`);
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ success: true, clipId, path: filePath, size: buffer.length }));
      });
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
    return;
  }

  // Fallback 404
  res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify({ error: 'Endpoint not found' }));
});

// Create WebSocket Server
const wss = new WebSocketServer({ noServer: true });

server.on('upgrade', (request, socket, head) => {
  const parsed = new URL(request.url, `http://${request.headers.host || '127.0.0.1'}`);
  if (parsed.pathname === '/ws') {
    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit('connection', ws, request);
    });
  } else {
    socket.destroy();
  }
});

wss.on('connection', (ws) => {
  console.log(`[Bridge Server] 🟢 浏览器扩展已成功建立本地连接！(当前在线: ${extensionSockets.size + 1})`);
  extensionSockets.add(ws);

  ws.on('message', (raw) => {
    try {
      const msg = JSON.parse(raw);

      // Handle real-time SSE stream events from in-page fetch hook
      if (msg.action === 'log_raw_chunk') {
        console.log('[SSE Raw Chunk Sample]', msg.raw);
        return;
      }
      if (msg.action === 'chatgpt_sse_chunk') {
        if (msg.delta) console.log(`[SSE Stream Delta] ${msg.delta}`);
        if (msg.isDone) console.log('[SSE Stream Done]');
        const handler = activeStreams.get(msg.reqId);
        if (handler) {
          if (msg.isDone) {
            handler.onDone(msg.text);
          } else if (msg.delta) {
            handler.onChunk(msg.delta, msg.text);
          }
        }
        return;
      }

      if (msg.id && pendingRequests.has(msg.id)) {
        const { resolve, timer } = pendingRequests.get(msg.id);
        clearTimeout(timer);
        pendingRequests.delete(msg.id);
        resolve(msg);
      }
    } catch (e) {
      console.error('[Bridge Server] 解析扩展消息失败:', e);
    }
  });

  ws.on('close', () => {
    extensionSockets.delete(ws);
    console.log(`[Bridge Server] ⚪ 浏览器扩展断开连接。(当前在线: ${extensionSockets.size})`);
  });

  ws.on('error', (err) => {
    console.error('[Bridge Server] WebSocket 异常:', err.message);
  });
});

// Heartbeat to keep MV3 background service worker active
setInterval(() => {
  if (extensionSockets.size > 0) {
    const pingMsg = JSON.stringify({ action: 'ping', id: 'hb_' + Date.now() });
    for (const ws of extensionSockets) {
      if (ws.readyState === ws.OPEN) {
        ws.send(pingMsg);
      }
    }
  }
}, 20000);

// Helper: Dispatch request to connected extension and await reply
function dispatchToExtension(action, payload) {
  return new Promise((resolve, reject) => {
    if (extensionSockets.size === 0) {
      return reject(new Error('无在线的扩展客户端连接'));
    }

    let targetWs = null;
    for (const ws of extensionSockets) {
      if (ws.readyState === ws.OPEN) {
        targetWs = ws;
        break;
      }
    }

    if (!targetWs) {
      return reject(new Error('扩展连接未就绪'));
    }

    const reqId = 'req_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    const timeoutMs = (action === 'chatgpt_send_message' || payload.timeout) ? (payload.timeout || 120000) : 8000;

    const timer = setTimeout(() => {
      pendingRequests.delete(reqId);
      reject(new Error(`等待浏览器扩展响应超时 (${timeoutMs}ms)`));
    }, timeoutMs);

    pendingRequests.set(reqId, { resolve, reject, timer });

    targetWs.send(JSON.stringify({
      id: reqId,
      action: action,
      ...payload
    }));
  });
}

function readRequestBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => resolve(body));
  });
}

// ==========================================
// 🔍 文件改动自动热重载 (File Watcher Auto-Reload)
// ==========================================
let reloadDebounceTimer = null;
const watchedExts = ['.js', '.json', '.html', '.css'];

try {
  fs.watch(__dirname, { recursive: false }, (eventType, filename) => {
    if (!filename) return;
    const ext = path.extname(filename).toLowerCase();
    
    // Ignore temp or package lock files
    if (filename === 'package.json' || filename === 'package-lock.json' || filename.startsWith('.')) {
      return;
    }

    if (watchedExts.includes(ext)) {
      if (reloadDebounceTimer) clearTimeout(reloadDebounceTimer);
      reloadDebounceTimer = setTimeout(async () => {
        if (extensionSockets.size > 0) {
          console.log(`[Auto-Reload] 📁 检测到 ${filename} 发生改动，正在自动重载扩展...`);
          try {
            await dispatchToExtension('reload', { trigger: filename });
            console.log(`[Auto-Reload] 🟢 浏览器扩展热重载完成！`);
          } catch (e) {
            console.log(`[Auto-Reload] 重载提示:`, e.message);
          }
        }
      }, 350);
    }
  });
  console.log(`👀 文件热重载监听器已激活 (保存任何 .js/.css/.html 即可自动刷新扩展)`);
} catch (e) {
  console.error('启动文件监听失败:', e.message);
}

// Start Server
server.listen(PORT, HOST, () => {
  console.log(`====================================================`);
  console.log(`🚀 Cookie Hub 本地通信与自动重载服务已启动!`);
  console.log(`📡 监听地址: http://${HOST}:${PORT}`);
  console.log(`🔌 WebSocket: ws://${HOST}:${PORT}/ws`);
  console.log(`🔄 扩展重载接口: http://${HOST}:${PORT}/reload`);
  console.log(`====================================================`);
});
