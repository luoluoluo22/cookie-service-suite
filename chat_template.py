CHAT_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="theme-color" content="#0b101b">
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" href="/assets/app_icon.png">
  <link rel="apple-touch-icon" href="/assets/app_icon.png">
  <title>Gemini Chat</title>
  <style>
    :root { --bg:#0b101b; --panel:#111827; --border:#1f2937; --text:#e5e7eb; --accent:#38bdf8; --user-bg:#1e3a5f; }
    * { box-sizing:border-box; margin:0; padding:0; }
    body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background:var(--bg); color:var(--text); height:100dvh; display:flex; overflow:hidden; }
    .sidebar { width:268px; background:var(--panel); border-right:1px solid var(--border); display:flex; flex-direction:column; flex-shrink:0; transition:transform .2s; z-index:40; }
    .sb-head { padding:12px; display:flex; gap:8px; border-bottom:1px solid var(--border); }
    .sb-foot { padding:10px 12px; border-top:1px solid var(--border); display:flex; flex-direction:column; gap:6px; background:#0f1624; }
    .sb-link { display:flex; align-items:center; justify-content:space-between; padding:8px 10px; border-radius:8px; font-size:13px; color:#d1d5db; text-decoration:none; cursor:pointer; background:transparent; border:1px solid transparent; width:100%; text-align:left; }
    .sb-link:hover { background:#1f2937; color:#fff; border-color:#374151; }
    .btn { background:#1f2937; color:var(--text); border:1px solid #374151; border-radius:8px; padding:7px 10px; font-size:12px; cursor:pointer; }
    .btn-primary { background:#0284c7; border-color:#0284c7; color:#fff; }
    .conv-list { flex:1; overflow-y:auto; padding:8px; display:flex; flex-direction:column; gap:4px; }
    .conv-item { padding:9px 10px; border-radius:8px; font-size:13px; cursor:pointer; display:flex; justify-content:space-between; align-items:center; gap:6px; color:#d1d5db; }
    .conv-item:hover, .conv-item.active { background:#1f2937; color:#fff; }
    .conv-title { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1; }
    .conv-del { opacity:0.5; color:#9ca3af; font-size:12px; padding:2px 5px; }
    .main { flex:1; display:flex; flex-direction:column; min-width:0; height:100dvh; }
    .topbar { height:50px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; padding:0 14px; background:var(--panel); }
    .menu-btn { display:none; background:none; border:none; color:var(--text); font-size:20px; cursor:pointer; }
    .msgs { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:14px; max-width:860px; width:100%; margin:0 auto; }
    .msg { display:flex; flex-direction:column; max-width:86%; }
    .msg.user { align-self:flex-end; }
    .msg.assistant { align-self:flex-start; max-width:94%; }
    .bubble { padding:10px 14px; border-radius:14px; font-size:14px; line-height:1.6; white-space:pre-wrap; word-break:break-word; }
    .msg.user .bubble { background:var(--user-bg); border-bottom-right-radius:4px; }
    .msg.assistant .bubble { background:#161e2e; border:1px solid var(--border); border-bottom-left-radius:4px; }
    .composer-wrap { border-top:1px solid var(--border); background:var(--panel); padding:10px 14px; }
    .composer { max-width:860px; margin:0 auto; display:flex; flex-direction:column; gap:8px; position:relative; }
    .controls { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
    .chip { display:inline-flex; align-items:center; gap:5px; background:#0c4a6e; border:1px solid #0284c7; color:#bae6fd; font-size:12px; padding:3px 9px; border-radius:999px; }
    .chip button { background:none; border:none; color:#bae6fd; cursor:pointer; font-size:12px; }
    select { background:#0b101b; color:var(--text); border:1px solid #374151; border-radius:8px; padding:5px 8px; font-size:12px; }
    .input-row { display:flex; gap:8px; align-items:flex-end; position:relative; }
    .plus-btn { width:44px; height:44px; border-radius:10px; background:#1f2937; border:1px solid #374151; color:#e5e7eb; font-size:20px; cursor:pointer; flex-shrink:0; display:flex; align-items:center; justify-content:center; }
    .plus-menu { position:absolute; bottom:52px; left:0; background:#161e2e; border:1px solid #374151; border-radius:12px; padding:6px; min-width:190px; display:none; flex-direction:column; gap:4px; box-shadow:0 10px 25px rgba(0,0,0,.5); z-index:45; }
    .plus-menu.open { display:flex; }
    .plus-item { padding:9px 10px; border-radius:8px; font-size:13px; color:#e5e7eb; cursor:pointer; display:flex; align-items:center; justify-content:space-between; background:none; border:none; text-align:left; }
    .plus-item:hover { background:#1f2937; }
    textarea { flex:1; background:#0b101b; color:var(--text); border:1px solid #374151; border-radius:10px; padding:10px 12px; font-size:14px; resize:none; min-height:44px; max-height:160px; font-family:inherit; outline:none; }
    .modal { position:fixed; inset:0; background:rgba(0,0,0,.75); display:none; align-items:center; justify-content:center; z-index:50; }
    .modal-box { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:20px; width:90%; max-width:380px; display:flex; flex-direction:column; gap:12px; }
    .modal-box input { background:#0b101b; color:var(--text); border:1px solid #374151; border-radius:8px; padding:9px 10px; font-size:13px; width:100%; }
    .quota-bars { display:flex; align-items:center; gap:12px; }
    .q-item { display:flex; flex-direction:column; gap:3px; min-width:118px; }
    .q-top { display:flex; align-items:center; justify-content:space-between; gap:6px; font-size:11px; color:#cbd5e1; font-family:ui-monospace,monospace; }
    .q-track { height:5px; background:#1f2937; border-radius:999px; overflow:hidden; }
    .q-fill { height:100%; border-radius:999px; transition:width .3s ease; }
    .q-dot { width:7px; height:7px; border-radius:50%; display:inline-block; flex-shrink:0; }
    @media (max-width:560px) { .quota-bars { gap:8px; } .q-item { min-width:92px; } .q-top { font-size:10px; } }
    .sb-backdrop { display:none; position:fixed; inset:0; background:rgba(0,0,0,.5); z-index:35; }
    @media (max-width:768px) { .sidebar { position:fixed; top:0; bottom:0; left:0; transform:translateX(-100%); } .sidebar.open { transform:translateX(0); } .sidebar.open + .sb-backdrop { display:block; } .menu-btn { display:block; } }
  </style>
</head>
<body>
  <aside class="sidebar" id="sidebar">
    <div class="sb-head">
      <button class="btn btn-primary" style="flex:1" onclick="newChat()">+ 新对话</button>
      <button class="btn" id="sync-btn" onclick="syncHistory()">同步历史</button>
    </div>
    <div class="conv-list" id="conv-list"></div>
    <div class="sb-foot">
      <a class="sb-link" href="/" target="_blank"><span>管理后台</span><span style="color:#6b7280">↗</span></a>
      <button class="sb-link" onclick="openSettings()"><span>设置与凭证</span><span style="color:#6b7280">›</span></button>
    </div>
  </aside>
  <div class="sb-backdrop" onclick="toggleSidebar(false)"></div>
  <main class="main">
    <header class="topbar">
      <div style="display:flex;align-items:center;gap:10px">
        <button class="menu-btn" onclick="toggleSidebar()">☰</button>
        <span style="font-weight:600;font-size:14px" id="chat-title">Gemini</span>
      </div>
      <div id="quota-bars" class="quota-bars" title="点击刷新额度" style="cursor:pointer" onclick="loadQuota(true)"></div>
    </header>
    <div class="msgs" id="msgs"></div>
    <div class="composer-wrap">
      <div class="composer">
        <div class="controls">
          <select id="model-sel"></select>
          <span class="chip" id="pigeon-chip" style="display:none">@鸽子 <button onclick="togglePigeon(false)">✕</button></span>
        </div>
        <div class="input-row">
          <button class="plus-btn" onclick="togglePlusMenu(event)" title="添加插件 / 工具">+</button>
          <div class="plus-menu" id="plus-menu">
            <button class="plus-item" onclick="togglePigeon(true)"><span>@鸽子 (Pigeon)</span><span style="color:#38bdf8;font-size:11px">远程控制</span></button>
          </div>
          <textarea id="prompt-in" rows="1" placeholder="输入消息，Enter 发送 / Shift+Enter 换行..."></textarea>
          <button class="btn btn-primary" id="send-btn" onclick="sendMsg()" style="height:44px;padding:0 16px">发送</button>
        </div>
      </div>
    </div>
  </main>
  <div class="modal" id="tk-modal">
    <div class="modal-box">
      <div style="font-weight:600;font-size:15px">设置与访问令牌</div>
      <label style="font-size:12px;color:#9ca3af">API 访问令牌</label>
      <input type="password" id="tk-input" placeholder="sk-css-...">
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn" style="flex:1" id="ref-cookie-btn" onclick="refreshCookie()">刷新 Gemini 凭证</button>
        <button class="btn" style="flex:1" onclick="syncHistory()">同步官网历史</button>
      </div>
      <div id="set-msg" style="font-size:12px;color:#38bdf8;min-height:16px"></div>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button class="btn" onclick="closeSettings()">取消</button>
        <button class="btn btn-primary" onclick="saveToken()">保存</button>
      </div>
    </div>
  </div>
<script>
let TOKEN = localStorage.getItem('css_api_token') || '';
const qp = new URLSearchParams(location.search).get('token');
if (qp) { TOKEN = qp; localStorage.setItem('css_api_token', qp); }
let activeCid = null, sending = false, usePigeon = false, convSyncPromise = null;
function hdrs() { return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + TOKEN }; }
function toggleSidebar(force) { const s = document.getElementById('sidebar'); if (typeof force === 'boolean') s.classList.toggle('open', force); else s.classList.toggle('open'); }
function togglePlusMenu(e) { e.stopPropagation(); document.getElementById('plus-menu').classList.toggle('open'); }
document.addEventListener('click', () => { const m = document.getElementById('plus-menu'); if (m) m.classList.remove('open'); });
function togglePigeon(on) {
  usePigeon = on;
  document.getElementById('pigeon-chip').style.display = on ? 'inline-flex' : 'none';
  document.getElementById('plus-menu').classList.remove('open');
  if (on) {
    const sel = document.getElementById('model-sel');
    if (sel && !sel.value.endsWith('-task')) {
      const tOpt = Array.from(sel.options).find(o => o.value === 'gemini-4-hydrogen-task');
      if (tOpt) sel.value = tOpt.value;
    }
    document.getElementById('prompt-in').focus();
  }
}
function openSettings() { toggleSidebar(false); document.getElementById('tk-input').value = TOKEN; document.getElementById('set-msg').textContent = ''; document.getElementById('tk-modal').style.display = 'flex'; }
function closeSettings() { document.getElementById('tk-modal').style.display = 'none'; }
function saveToken() { TOKEN = document.getElementById('tk-input').value.trim(); localStorage.setItem('css_api_token', TOKEN); closeSettings(); if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(()=>{});
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && TOKEN && Date.now() - lastQuotaAt >= 180000) loadQuota();
});
setInterval(() => {
  if (document.visibilityState === 'visible' && TOKEN && Date.now() - lastQuotaAt >= 300000) loadQuota();
}, 60000);
init(); }
async function refreshCookie() {
  const b = document.getElementById('ref-cookie-btn'), msg = document.getElementById('set-msg');
  b.textContent = '刷新中...';
  try { const d = await (await api('/api/gemini/refresh', { method: 'POST', body: '{}' })).json(); msg.textContent = d.message || '凭证已刷新'; }
  catch (e) { msg.textContent = '刷新失败: ' + e.message; } finally { b.textContent = '刷新 Gemini 凭证'; }
}
async function api(url, opt={}) { const r = await fetch(url, { ...opt, headers: { ...hdrs(), ...(opt.headers||{}) } }); if (r.status === 401) { openSettings(); throw new Error('Unauthorized'); } return r; }
function renderModels(list) {
  const sel = document.getElementById('model-sel');
  if (!sel || !list || !list.length) return;
  const prev = sel.value;
  const sig = list.map(m => m.id + ':' + (m.label || '')).join('|');
  if (sel.dataset.sig === sig) return;
  sel.dataset.sig = sig;
  sel.innerHTML = list.map(m => `<option value="${m.id}">${m.label || m.id}</option>`).join('');
  if (prev && list.some(m => m.id === prev)) sel.value = prev;
  else if (list.some(m => m.id === 'gemini-4-hydrogen')) sel.value = 'gemini-4-hydrogen';
}
async function loadModels() {
  const r = await api('/api/gemini/models');
  if (!r.ok) return;
  const d = await r.json(), list = d.models || [];
  setCache('css_models_cache', list);
  renderModels(list);
}

function addBubble(role, text) {
  const box = document.getElementById('msgs');
  const w = document.createElement('div'); w.className = 'msg ' + role;
  const b = document.createElement('div'); b.className = 'bubble'; b.textContent = text || '';
  w.appendChild(b); box.appendChild(w); box.scrollTop = box.scrollHeight; return b;
}
function newChat() {
  activeCid = null; convSyncPromise = null; localStorage.removeItem('css_active_cid');
  document.getElementById('msgs').innerHTML = '';
  document.getElementById('chat-title').textContent = 'Gemini';
  document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
  toggleSidebar(false); document.getElementById('prompt-in').focus();
}
function getCache(k, defVal) {
  try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : defVal; } catch (e) { return defVal; }
}
function setCache(k, val) {
  try { localStorage.setItem(k, JSON.stringify(val)); } catch (e) {}
}
function setConvCache(cid, d) {
  if (!cid || String(cid).startsWith('pending_')) return;
  setCache('css_conv_' + cid, d);
  const lru = getCache('css_conv_lru', []).filter(x => x !== cid);
  lru.unshift(cid);
  while (lru.length > 20) {
    const old = lru.pop();
    try { localStorage.removeItem('css_conv_' + old); } catch (e) {}
  }
  setCache('css_conv_lru', lru);
}
function convSig(c) {
  const msgs = c.messages || [];
  const last = msgs.length ? msgs[msgs.length - 1] : {};
  return JSON.stringify([c.title || '', c.model || '', msgs.length, last.content || '', c.last_prompt || '', c.last_reply || '']);
}
function renderConvDetail(d) {
  const box = document.getElementById('msgs');
  document.getElementById('chat-title').textContent = d.title || 'Gemini';
  if (d.model) { const s = document.getElementById('model-sel'); if (s && Array.from(s.options).some(o => o.value === d.model)) s.value = d.model; }
  box.innerHTML = '';
  const msgs = d.messages || [];
  if (msgs.length) { for (const m of msgs) addBubble(m.role === 'user' ? 'user' : 'assistant', m.content || ''); }
  else {
    if (d.last_prompt) addBubble('user', d.last_prompt);
    if (d.last_reply) addBubble('assistant', d.last_reply);
    if (!d.last_prompt && !d.last_reply) box.innerHTML = '<div style="color:#9ca3af;font-size:13px;padding:12px">暂无消息</div>';
  }
}
function renderConvs(list) {
  document.getElementById('conv-list').innerHTML = (list || []).map(c =>
    `<div class="conv-item ${c.cid===activeCid?'active':''}" data-cid="${c.cid}" onclick="openConv('${c.cid}')"><span class="conv-title">${(c.title||'新对话').replace(/</g,'&lt;')}</span><span class="conv-del" onclick="event.stopPropagation();delConv('${c.cid}')">×</span></div>`
  ).join('');
}

async function loadConvs() {
  const r = await api('/api/gemini/conversations?limit=60');
  if (!r.ok) throw new Error('HTTP ' + r.status);
  const d = await r.json();
  const list = d.conversations || d.items || [];
  setCache('css_convs_cache', list); renderConvs(list);
}
async function openConv(cid) {
  activeCid = cid; localStorage.setItem('css_active_cid', cid); toggleSidebar(false);
  document.querySelectorAll('.conv-item').forEach(el => el.classList.toggle('active', el.dataset.cid === cid));
  const box = document.getElementById('msgs');
  const cached = getCache('css_conv_' + cid, null);
  if (cached) renderConvDetail(cached);
  else box.innerHTML = '<div style="color:#9ca3af;font-size:13px;padding:12px">加载中...</div>';
  const task = (async () => {
    try {
      let r = await api(`/api/gemini/conversations/${encodeURIComponent(cid)}?refresh=true`);
      if (!r.ok) r = await api(`/api/gemini/conversations/${encodeURIComponent(cid)}?refresh=false`);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const raw = await r.json(), d = raw.conversation || raw;
      setConvCache(cid, d);
      if (activeCid !== cid) return;
      if (!cached || convSig(cached) !== convSig(d)) renderConvDetail(d);
    } catch (e) {
      if (!cached && activeCid === cid) box.innerHTML = `<div style="color:#f87171;font-size:13px;padding:12px">[加载失败] ${e.message}</div>`;
    } finally {
      if (convSyncPromise === task) convSyncPromise = null;
    }
  })();
  convSyncPromise = task;
  await task;
}
async function delConv(cid) {
  try {
    const r = await api(`/api/gemini/conversations/${encodeURIComponent(cid)}`, { method: 'DELETE' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    try { localStorage.removeItem('css_conv_' + cid); } catch (e) {}
    if (activeCid === cid) newChat();
    if (activeCid && !String(activeCid).startsWith('pending_')) api(`/api/gemini/conversations/${encodeURIComponent(activeCid)}?refresh=false`).then(r=>r.ok?r.json():null).then(raw=>{if(raw)setConvCache(activeCid,raw.conversation||raw);}).catch(()=>{});
    await loadConvs();
  } catch (e) { alert('删除失败: ' + e.message); }
}
async function syncHistory() {
  const btn = document.getElementById('sync-btn'), sm = document.getElementById('set-msg');
  if (btn) btn.textContent = '同步中...'; if (sm) sm.textContent = '正在同步...';
  try {
    const r = await api('/api/gemini/conversations/sync', { method: 'POST', body: '{}' });
    const d = await r.json(); if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status));
    await loadConvs(); if (sm) sm.textContent = `已同步 ${d.synced ?? 0} 条对话`;
  } catch (e) { if (sm) sm.textContent = '同步失败: ' + e.message; }
  finally { if (btn) btn.textContent = '同步历史'; }
}

async function sendMsg() {
  if (sending) return;
  const inp = document.getElementById('prompt-in'), raw = inp.value.trim(); if (!raw) return;
  const prompt = (usePigeon && !raw.toLowerCase().startsWith('@pigeon')) ? ('@pigeon ' + raw) : raw;
  inp.value = ''; sending = true; document.getElementById('send-btn').textContent = convSyncPromise ? '同步中...' : '...';
  let botEl = null;
  try {
    if (convSyncPromise) { await convSyncPromise.catch(() => {}); document.getElementById('send-btn').textContent = '...'; }
    addBubble('user', prompt); botEl = addBubble('assistant', '思考中...');
    const model = document.getElementById('model-sel').value || 'gemini-4-hydrogen';
    const ep = activeCid ? `/api/gemini/conversations/${encodeURIComponent(activeCid)}/messages` : '/api/gemini/conversations';
    const res = await api(ep, { method: 'POST', body: JSON.stringify({ prompt, model }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.error_message || ('HTTP ' + res.status));
    if (data.cid) { activeCid = data.cid; if (!String(activeCid).startsWith('pending_')) localStorage.setItem('css_active_cid', activeCid); }
    const ev = await api(`/api/gemini/runs/${encodeURIComponent(data.run_id)}/events`);
    if (!ev.ok || !ev.body) throw new Error('SSE HTTP ' + ev.status);
    const reader = ev.body.getReader(), dec = new TextDecoder();
    let buf = '', acc = '', errMsg = '';
    while (true) {
      const { value, done } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n'); buf = lines.pop() || '';
      for (const ln of lines) {
        if (!ln.startsWith('data:')) continue;
        try {
          const p = JSON.parse(ln.slice(5).trim());
          if (p.cid) { activeCid = p.cid; if (!String(activeCid).startsWith('pending_')) localStorage.setItem('css_active_cid', activeCid); }
          if (p.delta) { acc += p.delta; botEl.textContent = acc; }
          else if (typeof p.reply === 'string' && p.reply.length >= acc.length) { acc = p.reply; if (acc) botEl.textContent = acc; }
          else if (typeof p.partial_reply === 'string' && p.partial_reply.length >= acc.length) { acc = p.partial_reply; if (acc) botEl.textContent = acc; }
          else if (typeof p.text === 'string' && p.text.length >= acc.length) { acc = p.text; if (acc) botEl.textContent = acc; }
          if (p.error_message || p.error || p.status === 'error') { errMsg = p.error_message || p.error || '请求失败'; botEl.textContent = '[错误] ' + errMsg; }
        } catch (e) {}
      }
      const box = document.getElementById('msgs'); box.scrollTop = box.scrollHeight;
    }
    if (!acc && !errMsg) botEl.textContent = '（未收到回复内容）';
    await loadConvs();
  } catch (e) {
    if (/429|quota|限流|额度/i.test(e.message || '')) loadQuota(true);
    if (botEl) botEl.textContent = '[请求失败] ' + e.message;
    else addBubble('assistant', '[请求失败] ' + e.message);
  } finally { sending = false; document.getElementById('send-btn').textContent = '发送'; }
}
document.getElementById('prompt-in').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(); } });

function fmt5h(sec) {
  const s = Math.max(0, Math.round(Number(sec) || 0));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h${m}m` : `${Math.max(1, m)}m`;
}
function fmtDays(sec) {
  const d = Math.max(0, Number(sec) || 0) / 86400;
  return d >= 1 ? `${d.toFixed(1)}天` : `${Math.max(1, Math.round(d * 24))}h`;
}
let lastQuotaAt = 0;
async function loadQuota(force) {
  const el = document.getElementById('quota-bars');
  if (!el) return;
  if (!force && Date.now() - lastQuotaAt < 180000) return;
  try {
    const r = await api('/api/accounts');
    if (!r.ok) return;
    const d = await r.json();
    lastQuotaAt = Date.now();
    const acc = (d.accounts || []).find(a => a.platform === 'gemini' && a.status === 'enabled') || (d.accounts || [])[0];
    if (!acc) { el.innerHTML = ''; return; }
    const iso = acc.usage_source === 'official';
    const p5 = iso && acc.real_5h_pct != null ? Number(acc.real_5h_pct) : Math.min(100, Math.round(((acc.quota_5h_used||0)/(acc.quota_5h_limit||50))*100));
    const pw = iso && acc.real_weekly_pct != null ? Number(acc.real_weekly_pct) : Math.min(100, Math.round(((acc.quota_weekly_used||0)/(acc.quota_weekly_limit||500))*100));
    const l5 = Math.max(0, 100 - Math.round(p5)), lw = Math.max(0, 100 - Math.round(pw));
    const c5 = p5 >= 85 ? '#f43f5e' : (p5 >= 50 ? '#fbbf24' : '#34d399');
    const cw = '#38bdf8';
    const pace5 = acc.quota_5h_pace || {}, pacew = acc.quota_weekly_pace || {};
    const dotC = lv => lv === 'red' ? '#f43f5e' : (lv === 'yellow' ? '#fbbf24' : '#34d399');
    const t5 = pace5.eta_to_limit_sec != null ? ('触顶 ' + fmt5h(pace5.eta_to_limit_sec)) : (pace5.remaining_sec != null ? fmt5h(pace5.remaining_sec) : (acc.real_5h_reset_str || ''));
    const tw = pacew.eta_to_limit_sec != null ? ('触顶 ' + fmtDays(pacew.eta_to_limit_sec)) : (pacew.remaining_sec != null ? fmtDays(pacew.remaining_sec) : (acc.real_weekly_reset_str || ''));
    const tip5 = `5h已用 ${p5}% · 速率 ${Number(pace5.rate_per_hour||0).toFixed(1)}%/h · 预计 ${Number(pace5.projected_pct||0).toFixed(1)}% · ${acc.real_5h_reset_str||''}`;
    const tipw = `周已用 ${pw}% · 速率 ${Number(pacew.rate_per_day||0).toFixed(1)}%/天 · 预计 ${Number(pacew.projected_pct||0).toFixed(1)}% · ${acc.real_weekly_reset_str||''}`;
    el.innerHTML = `
      <div class="q-item" title="${tip5}">
        <div class="q-top"><span>5h 剩${l5}% · ${t5}</span><span class="q-dot" style="background:${dotC(pace5.level)}"></span></div>
        <div class="q-track"><div class="q-fill" style="width:${Math.min(100,p5)}%;background:${c5}"></div></div>
      </div>
      <div class="q-item" title="${tipw}">
        <div class="q-top"><span>周 剩${lw}% · ${tw}</span><span class="q-dot" style="background:${dotC(pacew.level)}"></span></div>
        <div class="q-track"><div class="q-fill" style="width:${Math.min(100,pw)}%;background:${cw}"></div></div>
      </div>`;
  } catch (e) {}
}

async function init() {
  if (!TOKEN) { openSettings(); return; }
  const cModels = getCache('css_models_cache', null); if (cModels) renderModels(cModels);
  const cList = getCache('css_convs_cache', null); if (cList) renderConvs(cList);
  const savedCid = new URLSearchParams(location.search).get('cid') || localStorage.getItem('css_active_cid');
  if (savedCid) { activeCid = savedCid; const cDet = getCache('css_conv_' + savedCid, null); if (cDet) renderConvDetail(cDet); }
  await Promise.all([loadModels(), loadConvs(), loadQuota(true)]);
  if (savedCid) await openConv(savedCid);
}
init();
</script>
</body>
</html>"""

def render_chat_html() -> str:
    return CHAT_HTML
