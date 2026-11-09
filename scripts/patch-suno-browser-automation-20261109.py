from pathlib import Path
import shutil
from datetime import datetime

root = Path(r"D:\Projects\cookie-service-suite")
bg = root / "extension" / "background.js"
server = root / "extension" / "server.js"
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
for p in (bg, server):
    backup = p.with_name(p.name + ".bak-suno-dom-" + stamp)
    shutil.copy2(p, backup)
    print("BACKUP", backup)

bg_text = bg.read_text(encoding="utf-8")
bg_anchor = "        // 6. Suno 自动后台访问并提取 Cookie (免手动 F12)\n"
if "req.action === 'suno_execute'" not in bg_text:
    handler = r"""
        // 5.9 Suno 页面 DOM 自动化（仅限已打开的 Suno 标签页）
        if (req.action === 'suno_execute') {
          try {
            const tabs = await chrome.tabs.query({ url: 'https://suno.com/*' });
            const tab = tabs.find(t => (t.url || '').includes('/create')) || tabs[0];
            if (!tab) throw new Error('未找到已打开的 Suno 页面');
            const results = await chrome.scripting.executeScript({
              target: { tabId: tab.id },
              func: (operation, payload) => {
                const rect = (el) => {
                  const r = el.getBoundingClientRect();
                  return { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) };
                };
                if (operation === 'inspect') {
                  const fields = [...document.querySelectorAll('textarea,input,[contenteditable="true"],[role="textbox"]')].map((el, index) => ({
                    index, tag: el.tagName, type: el.getAttribute('type'),
                    placeholder: el.getAttribute('placeholder') || el.getAttribute('data-placeholder') || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    role: el.getAttribute('role') || '',
                    className: String(el.className || '').slice(0, 180),
                    disabled: !!el.disabled, valueLength: String(el.value || el.innerText || '').length,
                    rect: rect(el)
                  }));
                  const buttons = [...document.querySelectorAll('button,[role="button"],a')].map((el, index) => ({
                    index, text: String(el.innerText || el.getAttribute('aria-label') || el.title || '').trim().replace(/\s+/g, ' ').slice(0, 100),
                    ariaLabel: el.getAttribute('aria-label') || '',
                    title: el.title || '', disabled: !!el.disabled,
                    testId: el.getAttribute('data-testid') || '', rect: rect(el)
                  })).filter(x => x.text || x.ariaLabel || x.title).slice(0, 100);
                  return { success: true, title: document.title, url: location.href, bodyText: (document.body.innerText || '').slice(0, 6000), fields, buttons };
                }
                if (operation === 'fill') {
                  let el = payload.selector ? document.querySelector(payload.selector) : null;
                  if (!el && Number.isInteger(payload.index)) {
                    el = [...document.querySelectorAll('textarea,input,[contenteditable="true"],[role="textbox"]')][payload.index] || null;
                  }
                  if (!el) throw new Error('找不到指定的输入控件');
                  const value = String(payload.value ?? '');
                  el.focus();
                  if (el.isContentEditable) {
                    el.textContent = value;
                  } else {
                    const proto = Object.getPrototypeOf(el);
                    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
                    if (setter) setter.call(el, value); else el.value = value;
                  }
                  el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                  return { success: true, tag: el.tagName, placeholder: el.getAttribute('placeholder') || '', valueLength: value.length, rect: rect(el) };
                }
                if (operation === 'click_text') {
                  const needle = String(payload.text || '').trim();
                  const candidates = [...document.querySelectorAll('button,[role="button"],a')];
                  const el = candidates.find(node => String(node.innerText || node.getAttribute('aria-label') || node.title || '').trim().replace(/\s+/g, ' ').includes(needle));
                  if (!el) throw new Error('找不到按钮文本：' + needle);
                  if (el.disabled) throw new Error('目标按钮当前不可用：' + needle);
                  el.click();
                  return { success: true, clicked: needle, rect: rect(el) };
                }
                if (operation === 'click_selector') {
                  const el = document.querySelector(String(payload.selector || ''));
                  if (!el) throw new Error('找不到选择器：' + payload.selector);
                  if (el.disabled) throw new Error('目标控件当前不可用');
                  el.click();
                  return { success: true, clicked: payload.selector, rect: rect(el) };
                }
                if (operation === 'media') {
                  return {
                    success: true,
                    audios: [...document.querySelectorAll('audio')].map(a => ({ src: a.currentSrc || a.src, paused: a.paused, duration: a.duration, currentTime: a.currentTime })),
                    videos: [...document.querySelectorAll('video')].map(v => ({ src: v.currentSrc || v.src, paused: v.paused, duration: v.duration, currentTime: v.currentTime }))
                  };
                }
                throw new Error('不支持的 Suno 页面操作：' + operation);
              },
              args: [req.operation || 'inspect', req.payload || {}]
            });
            ws.send(JSON.stringify({
              id: req.id, action: 'suno_execute', success: true,
              result: results && results[0] ? results[0].result : null,
              tabId: tab.id
            }));
          } catch (err) {
            ws.send(JSON.stringify({ id: req.id, action: 'suno_execute', success: false, error: err.message }));
          }
          return;
        }

"""
    if bg_anchor not in bg_text:
        raise SystemExit("background.js insertion anchor not found")
    bg_text = bg_text.replace(bg_anchor, handler + bg_anchor, 1)
    bg.write_text(bg_text, encoding="utf-8", newline="\n")
    print("PATCHED background.js")
else:
    print("background.js already patched")

server_text = server.read_text(encoding="utf-8")
route_anchor = "  // 5.1 Suno Save In-Page Decrypted Audio"
if "pathname === '/suno/execute'" not in server_text:
    route = r"""
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

"""
    if route_anchor not in server_text:
        raise SystemExit("server.js insertion anchor not found")
    server_text = server_text.replace(route_anchor, route + route_anchor, 1)
    server.write_text(server_text, encoding="utf-8", newline="\n")
    print("PATCHED server.js")
else:
    print("server.js already patched")
print("DONE")
