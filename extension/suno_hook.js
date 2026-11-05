/**
 * Suno In-Page Audio Decrypt Hook & Cache Reuse
 * ==============================================
 * 运行于 Suno 官网主页面 context (world: MAIN, run_at: document_start)
 * 作用:
 * 1. 拦截播放时的 `crypto.subtle.decrypt` 调用，抓取解密后的 100% 原始 M4A/Opus 音频 ArrayBuffer；
 * 2. 拦截 `/api/mango/rights` 授权请求，自动关联当前播放的 Clip ID 与元数据；
 * 3. 将播放过程中浏览器已下载并解密的音频，秒级直推到本地 Bridge (127.0.0.1:18888)，
 *    彻底实现“听过即保存，0 次重复网络下载”。
 */
(function() {
  'use strict';
  if (window.__suno_audio_hook_installed__) return;
  window.__suno_audio_hook_installed__ = true;

  console.log('[Suno Hook] 🎵 Suno 实时音频解密嗅探与复用拦截器已就绪!');

  let lastClipId = null;
  const processedClips = new Set();

  // 1. 拦截 fetch 捕获正在播放的歌曲 Clip ID
  const origFetch = window.fetch;
  window.fetch = async function(...args) {
    const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url ? args[0].url : '');
    if (url.includes('/api/mango/rights')) {
      try {
        const bodyStr = args[1]?.body;
        if (bodyStr) {
          const parsed = typeof bodyStr === 'string' ? JSON.parse(bodyStr) : bodyStr;
          if (parsed?.content_params?.content_id) {
            lastClipId = parsed.content_params.content_id;
            console.log('[Suno Hook] 🔑 检测到曲目播放 License 请求, Clip ID:', lastClipId);
          }
        }
      } catch (e) {}
    }
    return origFetch.apply(this, args);
  };

  // 2. 拦截 Web Crypto AES-CTR 解密管道
  if (window.crypto && window.crypto.subtle) {
    const origDecrypt = crypto.subtle.decrypt.bind(crypto.subtle);

    crypto.subtle.decrypt = async function(algorithm, key, data) {
      const result = await origDecrypt(algorithm, key, data);
      try {
        if (result instanceof ArrayBuffer && result.byteLength > 200000) {
          const u8 = new Uint8Array(result);
          const isM4A = u8.length >= 8 && u8[4] === 0x66 && u8[5] === 0x74 && u8[6] === 0x79 && u8[7] === 0x70;
          const isWebM = u8.length >= 4 && u8[0] === 0x1a && u8[1] === 0x45 && u8[2] === 0xdf && u8[3] === 0xa3;

          if (isM4A || isWebM) {
            const activeClip = lastClipId || ('clip_' + Date.now());
            if (!processedClips.has(activeClip)) {
              processedClips.add(activeClip);
              console.log(`[Suno Hook] 🎉 捕获到播放器解密就绪的音频! 大小: ${(result.byteLength / 1024 / 1024).toFixed(2)} MB, 格式: ${isM4A ? 'M4A/Opus' : 'WebM'}`);

              // 直接克隆副本并推送到本地 Bridge 存储
              const clone = result.slice(0);
              fetch('http://127.0.0.1:18888/suno/save_audio', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/octet-stream',
                  'X-Suno-Clip-Id': activeClip,
                  'X-Suno-Format': isM4A ? 'm4a' : 'webm'
                },
                body: clone
              }).then(r => r.json()).then(res => {
                console.log('[Suno Hook] 💾 播放流已成功无损暂存至本地:', res.path);
              }).catch(err => {
                console.debug('[Suno Hook] 本地 Bridge 通信提示:', err.message);
              });
            }
          }
        }
      } catch (err) {
        console.error('[Suno Hook] 处理解密音频错误:', err);
      }
      return result;
    };
  }
})();
