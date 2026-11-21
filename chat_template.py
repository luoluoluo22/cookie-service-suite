CHAT_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover" />
  <meta name="theme-color" content="#131314" />
  <link rel="manifest" href="/manifest.webmanifest" />
  <title>Gemini</title>
  <style>
    :root { --bg:#131314; --panel:#1e1f20; --surface:#282a2c; --hover:#333537; --border:#2e2f30; --text:#e3e3e3; --muted:#9aa0a6; --accent:#a8c7fa; --user-bg:#282a2c; }
    * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
    html,body { margin:0; height:100%; background:var(--bg); color:var(--text); font-family:'Google Sans','Roboto',-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif; letter-spacing:0.01em; }
    body { display:flex; overflow:hidden; }
    .icon { width:20px; height:20px; fill:currentColor; flex-shrink:0; display:block; }
    .icon-sm { width:16px; height:16px; fill:currentColor; flex-shrink:0; display:block; }
    .sidebar { width:276px; background:var(--panel); display:flex; flex-direction:column; flex-shrink:0; transition:transform .22s cubic-bezier(.4,0,.2,1); z-index:40; }
    .sb-top { padding:14px 12px 10px; display:flex; gap:8px; align-items:center; }
    .pill-btn { background:var(--surface); color:var(--text); border:none; border-radius:999px; padding:9px 14px; font-size:13px; font-weight:500; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; gap:7px; transition:background .15s; }
    .pill-btn:hover { background:var(--hover); }
    .pill-btn.primary { background:#004a77; color:#c2e7ff; }
    .pill-btn.primary:hover { background:#005a92; }
    .conv-list { flex:1; overflow-y:auto; padding:4px 10px 10px; }
    .conv-item { padding:10px 12px; border-radius:999px; font-size:13.5px; color:#c4c7c5; cursor:pointer; display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:2px; transition:background .12s; }
    .conv-item:hover { background:var(--surface); color:var(--text); }
    .conv-item.active { background:#004a77; color:#c2e7ff; font-weight:500; }
    .conv-title { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1; }
    .conv-del { opacity:0; color:var(--muted); width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
    .conv-item:hover .conv-del, .conv-item.active .conv-del { opacity:.75; }
    .conv-del:hover { background:rgba(255,255,255,.1); color:#f28b82; opacity:1; }
    .sb-foot { border-top:1px solid var(--border); padding:8px 10px calc(10px + env(safe-area-inset-bottom)); display:flex; flex-direction:column; gap:2px; }
    .sb-link { display:flex; align-items:center; gap:12px; padding:10px 12px; border-radius:999px; font-size:13.5px; color:var(--text); text-decoration:none; background:none; border:none; width:100%; text-align:left; cursor:pointer; font-family:inherit; }
    .sb-link:hover { background:var(--surface); }
    .main { flex:1; display:flex; flex-direction:column; min-width:0; height:100%; background:var(--bg); }
    .topbar { min-height:56px; padding:8px 14px; display:flex; align-items:center; justify-content:space-between; gap:10px; flex-shrink:0; }
    .icon-btn { width:40px; height:40px; border-radius:50%; background:none; border:none; color:var(--text); display:inline-flex; align-items:center; justify-content:center; cursor:pointer; flex-shrink:0; }
    .icon-btn:hover { background:var(--surface); }
    .brand { display:flex; align-items:center; gap:8px; font-size:17px; font-weight:500; color:var(--text); min-width:0; }
    #chat-title { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:42vw; }
    .quota-bars { display:flex; align-items:center; gap:12px; flex-shrink:0; }
    .q-item { display:flex; flex-direction:column; gap:3px; min-width:108px; }
    .q-top { display:flex; align-items:center; justify-content:space-between; gap:5px; font-size:11px; color:var(--muted); font-family:ui-monospace,monospace; }
    .q-track { height:4px; background:var(--surface); border-radius:999px; overflow:hidden; }
    .q-fill { height:100%; border-radius:999px; transition:width .3s ease; }
    .q-dot { width:6px; height:6px; border-radius:50%; display:inline-block; flex-shrink:0; }
    .msgs { flex:1; overflow-y:auto; padding:12px 16px 24px; display:flex; flex-direction:column; gap:22px; max-width:820px; width:100%; margin:0 auto; }
    .msg { display:flex; flex-direction:column; max-width:100%; }
    .msg.user { align-self:flex-end; max-width:82%; }
    .msg.assistant { align-self:flex-start; width:100%; flex-direction:row; align-items:flex-start; gap:12px; }
    .bot-avatar { width:26px; height:26px; margin-top:2px; flex-shrink:0; color:var(--accent); display:flex; align-items:center; justify-content:center; }
    .bubble { font-size:15.5px; line-height:1.68; white-space:pre-wrap; word-break:break-word; color:var(--text); }
    .msg.user .bubble { background:var(--user-bg); padding:11px 16px; border-radius:20px 20px 4px 20px; font-size:15px; line-height:1.55; }
    .msg.assistant .bubble { background:transparent; padding:2px 0; flex:1; min-width:0; }
    .composer-wrap { padding:4px 12px calc(12px + env(safe-area-inset-bottom)); background:var(--bg); }
    .composer { max-width:820px; margin:0 auto; background:var(--panel); border:1px solid var(--border); border-radius:26px; padding:10px 12px 8px 16px; display:flex; flex-direction:column; gap:6px; position:relative; transition:border-color .15s; }
    .composer:focus-within { border-color:#444746; }
    textarea { width:100%; background:transparent; color:var(--text); border:none; padding:4px 2px; font-size:15.5px; line-height:1.5; resize:none; min-height:28px; max-height:160px; font-family:inherit; outline:none; }
    textarea::placeholder { color:#8e918f; }
    .c-bar { display:flex; align-items:center; justify-content:space-between; gap:8px; }
    .c-left { display:flex; align-items:center; gap:6px; flex-wrap:wrap; min-width:0; }
    .plus-btn { width:36px; height:36px; border-radius:50%; background:transparent; border:none; color:var(--text); cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
    .plus-btn:hover { background:var(--surface); }
    .plus-menu { position:absolute; bottom:56px; left:10px; background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:6px; min-width:200px; display:none; flex-direction:column; gap:2px; box-shadow:0 8px 24px rgba(0,0,0,.5); z-index:45; }
    .plus-menu.open { display:flex; }
    .plus-item { padding:10px 12px; border-radius:10px; font-size:13.5px; color:var(--text); cursor:pointer; display:flex; align-items:center; justify-content:space-between; gap:8px; background:none; border:none; text-align:left; font-family:inherit; }
    .plus-item:hover { background:var(--hover); }
    .chip { display:inline-flex; align-items:center; gap:5px; background:#004a77; color:#c2e7ff; font-size:12px; font-weight:500; padding:4px 10px; border-radius:999px; }
    .chip button { background:none; border:none; color:#c2e7ff; cursor:pointer; padding:0; display:flex; align-items:center; }
    select { background:transparent; color:var(--muted); border:none; border-radius:999px; padding:5px 8px; font-size:12.5px; font-weight:500; font-family:inherit; cursor:pointer; outline:none; max-width:170px; }
    select:hover { background:var(--surface); color:var(--text); }
    select option { background:var(--panel); color:var(--text); }
    .send-btn { width:36px; height:36px; border-radius:50%; background:#e3e3e3; color:#131314; border:none; cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:transform .1s, background .15s; font-size:12px; font-weight:600; }
    .send-btn:hover { background:#ffffff; }
    .send-btn:active { transform:scale(.94); }
    .modal { position:fixed; inset:0; background:rgba(0,0,0,.68); display:none; align-items:center; justify-content:center; z-index:50; padding:16px; }
    .modal-box { background:var(--panel); border:1px solid var(--border); border-radius:20px; padding:20px; width:100%; max-width:380px; display:flex; flex-direction:column; gap:12px; }
    .modal-box input { background:var(--bg); color:var(--text); border:1px solid var(--border); border-radius:12px; padding:10px 12px; font-size:13.5px; width:100%; outline:none; }
    .modal-box input:focus { border-color:var(--accent); }
    .sb-backdrop { display:none; position:fixed; inset:0; background:rgba(0,0,0,.55); z-index:35; }
    @media (max-width:768px) { .sidebar { position:fixed; top:0; bottom:0; left:0; transform:translateX(-100%); } .sidebar.open { transform:translateX(0); } .sidebar.open + .sb-backdrop { display:block; } }
    @media (max-width:560px) { .quota-bars { gap:8px; } .q-item { min-width:86px; } .q-top { font-size:10px; } .msgs { padding:10px 12px 18px; } .msg.user { max-width:88%; } }
  </style>
</head>
<body>
  <aside class="sidebar" id="sidebar">
    <div class="sb-top">
      <button class="pill-btn primary" style="flex:1" onclick="newChat()"><svg class="icon-sm" viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg><span>新对话</span></button>
      <button class="pill-btn" id="sync-btn" onclick="syncHistory()" title="同步历史"><svg class="icon-sm" viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg></button>
    </div>
    <div class="conv-list" id="conv-list"></div>
    <div class="sb-foot">
      <a class="sb-link" href="/" target="_blank"><svg class="icon" viewBox="0 0 24 24"><path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/></svg><span>管理后台</span></a>
      <button class="sb-link" onclick="openSettings()"><svg class="icon" viewBox="0 0 24 24"><path d="M19.14 12.94c.04-.31.06-.63.06-.94s-.02-.63-.06-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.48.48 0 0 0-.48-.41h-3.84a.48.48 0 0 0-.48.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.49.49 0 0 0-.59.22L2.74 8.87a.48.48 0 0 0 .12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.26.41.48.41h3.84c.24 0 .44-.17.48-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.49.49 0 0 0-.12-.61l-2.01-1.58zM12 15.6A3.6 3.6 0 1 1 12 8.4a3.6 3.6 0 0 1 0 7.2z"/></svg><span>设置与凭证</span></button>
    </div>
  </aside>
  <div class="sb-backdrop" onclick="toggleSidebar(false)"></div>
  <main class="main">
    <header class="topbar">
      <div style="display:flex;align-items:center;gap:6px;min-width:0">
        <button class="icon-btn" onclick="toggleSidebar()" aria-label="菜单"><svg class="icon" viewBox="0 0 24 24"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg></button>
        <div class="brand">
          <svg class="icon" style="color:#a8c7fa" viewBox="0 0 24 24"><path d="M12 2L14.8 9.2L22 12L14.8 14.8L12 22L9.2 14.8L2 12L9.2 9.2L12 2Z"/></svg>
          <span id="chat-title">Gemini</span>
        </div>
      </div>
      <div id="quota-bars" class="quota-bars" title="点击刷新额度" style="cursor:pointer" onclick="loadQuota(true)"></div>
    </header>
    <div class="msgs" id="msgs"></div>
    <div class="composer-wrap">
      <div class="composer">
        <textarea id="prompt-in" rows="1" placeholder="问问 Gemini..."></textarea>
        <div class="c-bar">
          <div class="c-left">
            <div class="plus-menu" id="plus-menu">
              <button class="plus-item" onclick="togglePigeon(true)"><span>@鸽子 (Pigeon)</span><span style="color:#a8c7fa;font-size:12px">调用设备</span></button>
            </div>
            <button class="plus-btn" onclick="togglePlusMenu(event)" title="工具与插件"><svg class="icon" viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg></button>
            <span class="chip" id="pigeon-chip" style="display:none">@鸽子 <button onclick="togglePigeon(false)" aria-label="取消"><svg class="icon-sm" style="width:14px;height:14px" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg></button></span>
            <select id="model-sel"></select>
          </div>
          <button class="send-btn" id="send-btn" onclick="sendMsg()" aria-label="发送"><svg class="icon-sm" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button>
        </div>
      </div>
    </div>
  </main>
  <div class="modal" id="tk-modal">
    <div class="modal-box">
      <div style="font-weight:500;font-size:16px;display:flex;align-items:center;gap:8px"><svg class="icon" style="color:#a8c7fa" viewBox="0 0 24 24"><path d="M12 2L14.8 9.2L22 12L14.8 14.8L12 22L9.2 14.8L2 12L9.2 9.2L12 2Z"/></svg>设置与凭证</div>
      <label style="font-size:12px;color:#9aa0a6">API 访问令牌</label>
      <input type="password" id="tk-input" placeholder="sk-css-...">
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="pill-btn" style="flex:1" id="ref-cookie-btn" onclick="refreshCookie()">刷新 Cookie</button>
        <button class="pill-btn" style="flex:1" onclick="syncHistory()">同步全部历史</button>
      </div>
      <div id="set-msg" style="font-size:12px;color:#a8c7fa;min-height:16px"></div>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button class="pill-btn" onclick="closeSettings()">取消</button>
        <button class="pill-btn primary" onclick="saveToken()">保存</button>
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
  if (role === 'assistant') {
    const av = document.createElement('div'); av.className = 'bot-avatar';
    av.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><path d="M12 2L14.8 9.2L22 12L14.8 14.8L12 22L9.2 14.8L2 12L9.2 9.2L12 2Z"/></svg>';
    w.appendChild(av);
  }
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
  if (btn) btn.disabled = true; if (sm) sm.textContent = '正在同步...';
  try {
    const r = await api('/api/gemini/conversations/sync', { method: 'POST', body: '{}' });
    const d = await r.json(); if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status));
    await loadConvs(); if (sm) sm.textContent = `已同步 ${d.synced ?? 0} 条对话`;
  } catch (e) { if (sm) sm.textContent = '同步失败: ' + e.message; }
  finally { if (btn) btn.disabled = false; }
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
  } finally { sending = false; document.getElementById('send-btn').innerHTML = '<svg class="icon-sm" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>'; }
}
document.getElementById('prompt-in').addEventListener('input', e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(160, e.target.scrollHeight) + 'px'; });
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
