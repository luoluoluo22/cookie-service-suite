/**
 * Gemini In-Page Network & Task-Mode Hook
 * ========================================
 * Runs in gemini.google.com main world (world: MAIN, run_at: document_start).
 * Passively captures fetch / XHR requests to processSession, StreamGenerate,
 * and batchexecute so callers can inspect exact request headers & payloads
 * (including Task Mode / MCP tool invocations) without violating CSP.
 */
(function () {
  'use strict';
  if (window.__gemini_hook_installed__) return;
  window.__gemini_hook_installed__ = true;

  const MAX_CALLS = 40;
  const calls = [];
  window.__gemini_captured_calls = calls;
  window.__gemini_clear_calls = function () {
    calls.length = 0;
    return true;
  };

  function isInteresting(url) {
    if (!url || typeof url !== 'string') return false;
    return (
      url.includes('processSession') ||
      url.includes('StreamGenerate') ||
      url.includes('batchexecute') ||
      url.includes('BardFrontendService')
    );
  }

  function pushCall(entry) {
    calls.push(entry);
    if (calls.length > MAX_CALLS) {
      calls.shift();
    }
  }

  function serializeHeaders(h) {
    const out = {};
    if (!h) return out;
    try {
      if (typeof h.forEach === 'function') {
        h.forEach((v, k) => {
          out[k] = v;
        });
      } else if (Array.isArray(h)) {
        for (const pair of h) {
          if (Array.isArray(pair) && pair.length >= 2) {
            out[pair[0]] = pair[1];
          }
        }
      } else if (typeof h === 'object') {
        Object.assign(out, h);
      }
    } catch (_) {}
    return out;
  }

  // 1. Hook window.fetch
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    let url = '';
    let method = 'GET';
    let headers = {};
    let body = null;
    try {
      const input = args[0];
      const init = args[1] || {};
      url = typeof input === 'string' ? input : (input && input.url) || '';
      method = (init.method || (input && input.method) || 'GET').toUpperCase();
      headers = serializeHeaders(init.headers || (input && input.headers));
      if (typeof init.body === 'string') {
        body = init.body;
      } else if (init.body && typeof init.body.toString === 'function') {
        body = String(init.body);
      }
    } catch (_) {}

    const interesting = isInteresting(url);
    const entry = interesting
      ? {
          id: calls.length + 1,
          ts: Date.now(),
          transport: 'fetch',
          method,
          url,
          headers,
          body: body ? body.slice(0, 16000) : null,
          status: null,
          respPreview: null,
        }
      : null;

    if (entry) pushCall(entry);

    const resp = await origFetch.apply(this, args);
    if (entry && resp) {
      entry.status = resp.status;
      try {
        // Clone only for non-huge responses or read first chunk safely
        const clone = resp.clone();
        clone
          .text()
          .then((txt) => {
            entry.respPreview = txt ? txt.slice(0, 8000) : '';
          })
          .catch(() => {});
      } catch (_) {}
    }
    return resp;
  };

  // 2. Hook XMLHttpRequest
  const origOpen = XMLHttpRequest.prototype.open;
  const origSetHeader = XMLHttpRequest.prototype.setRequestHeader;
  const origSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this.__gh_method = (method || 'GET').toUpperCase();
    this.__gh_url = typeof url === 'string' ? url : String(url || '');
    this.__gh_headers = {};
    return origOpen.apply(this, [method, url, ...rest]);
  };

  XMLHttpRequest.prototype.setRequestHeader = function (k, v) {
    if (this.__gh_headers) {
      this.__gh_headers[k] = v;
    }
    return origSetHeader.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function (body) {
    if (isInteresting(this.__gh_url)) {
      const entry = {
        id: calls.length + 1,
        ts: Date.now(),
        transport: 'xhr',
        method: this.__gh_method || 'POST',
        url: this.__gh_url,
        headers: this.__gh_headers || {},
        body: typeof body === 'string' ? body.slice(0, 16000) : body ? String(body).slice(0, 4000) : null,
        status: null,
        respPreview: null,
      };
      pushCall(entry);
      this.addEventListener('loadend', () => {
        entry.status = this.status;
        try {
          if (typeof this.responseText === 'string') {
            entry.respPreview = this.responseText.slice(0, 8000);
          }
        } catch (_) {}
      });
    }
    return origSend.apply(this, arguments);
  };
})();
