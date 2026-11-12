// Cookie Hub - Udio In-Page Native Bridge
// Runs in the context of udio.com tabs

console.log('🎵 [CookieHub] Udio In-Page Bridge loaded into udio.com');

chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
  if (req.action === 'udio_get_user') {
    (async () => {
      try {
        const res = await fetch('/api/users/current');
        const data = await res.json();
        sendResponse({ success: true, data });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (req.action === 'udio_get_songs') {
    (async () => {
      try {
        const res = await fetch('/api/songs?page=1&perPage=20');
        const data = await res.json();
        sendResponse({ success: true, songs: data.songs || data || [] });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (req.action === 'udio_inspect_dom') {
    try {
      const inputs = [...document.querySelectorAll('textarea, input')].map(i => ({
        tag: i.tagName,
        type: i.type,
        placeholder: i.placeholder,
        value: i.value
      }));
      const buttons = [...document.querySelectorAll('button,[role="button"]')].map(b => ({
        text: (b.innerText || b.getAttribute('aria-label') || '').trim(),
        disabled: b.disabled
      })).filter(b => b.text).slice(0, 40);

      sendResponse({
        success: true,
        title: document.title,
        url: window.location.href,
        inputs,
        buttons
      });
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
    return true;
  }

  if (req.action === 'udio_generate') {
    (async () => {
      try {
        const promptText = req.prompt || '';
        const isInstrumental = req.is_instrumental !== false;

        // 1. 查找提示词输入框
        const textareas = [...document.querySelectorAll('textarea, input[type="text"]')];
        const promptInput = textareas.find(el => {
          const ph = (el.placeholder || '').toLowerCase();
          return ph.includes('prompt') || ph.includes('describe') || ph.includes('song') || ph.includes('music') || ph.includes('create');
        }) || textareas[0];

        if (!promptInput) {
          throw new Error('未找到 Udio 描述词输入框，请确认页面停留在 https://www.udio.com/create');
        }

        promptInput.focus();
        const proto = Object.getPrototypeOf(promptInput);
        const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
        if (setter) {
          setter.call(promptInput, promptText);
        } else {
          promptInput.value = promptText;
        }
        promptInput.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: promptText }));
        promptInput.dispatchEvent(new Event('change', { bubbles: true }));

        // 2. 纯伴奏 (Instrumental) 按钮切换
        if (isInstrumental) {
          const buttons = [...document.querySelectorAll('button,[role="button"]')];
          const instBtn = buttons.find(b => {
            const t = (b.innerText || b.getAttribute('aria-label') || '').toLowerCase();
            return t.includes('instrumental') || t.includes('器乐') || t.includes('伴奏');
          });
          if (instBtn) {
            const isPressed = instBtn.getAttribute('aria-pressed') === 'true' ||
                              instBtn.classList.contains('active') ||
                              instBtn.className.includes('bg-');
            if (!isPressed) instBtn.click();
          }
        }

        // 等待 500ms 让 React 渲染状态
        await new Promise(r => setTimeout(r, 500));

        // 3. 寻找并点击 Create 按钮
        const allBtns = [...document.querySelectorAll('button,[role="button"]')];
        const createBtn = allBtns.find(b => {
          const t = (b.innerText || b.getAttribute('aria-label') || '').trim().toLowerCase();
          return (t === 'create' || t.startsWith('create ') || t === '生成') && !b.disabled;
        });

        if (!createBtn) {
          throw new Error('未找到可点击的 Create 按钮，请确认已登录且当前额度充足');
        }

        createBtn.click();

        sendResponse({
          success: true,
          message: '已成功在 Udio 页面触发生成任务',
          prompt: promptText,
          isInstrumental
        });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }
});
