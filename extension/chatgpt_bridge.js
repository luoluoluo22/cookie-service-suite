// Cookie Hub - ChatGPT In-Page Bridge
// Runs in the context of chatgpt.com tabs

console.log('🤖 [CookieHub] ChatGPT In-Page Bridge loaded into chatgpt.com');

// Listen for messages from background.js
chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
  if (req.action === 'chatgpt_get_session') {
    handleGetSession(sendResponse);
    return true; // Async reply
  }

  if (req.action === 'chatgpt_send_message') {
    handleSendMessage(req.prompt, sendResponse);
    return true; // Async reply
  }

  if (req.action === 'chatgpt_get_models') {
    handleGetModels(sendResponse);
    return true;
  }

  if (req.action === 'chatgpt_debug_dom') {
    const el = document.querySelector('#prompt-textarea') || document.querySelector('div[contenteditable="true"]');
    const form = el ? (el.closest('form') || el.parentElement?.parentElement) : null;
    const buttons = form ? Array.from(form.querySelectorAll('button')).map(b => ({
      testId: b.getAttribute('data-testid'),
      ariaLabel: b.getAttribute('aria-label'),
      disabled: b.disabled,
      className: b.className,
      fullHTML: b.outerHTML
    })) : [];

    const articles = Array.from(document.querySelectorAll('article')).map(a => a.innerText.substring(0, 200));
    const roleMessages = Array.from(document.querySelectorAll('[data-message-author-role]')).map(el => ({
      role: el.getAttribute('data-message-author-role'),
      text: el.innerText.substring(0, 100)
    }));

    sendResponse({
      inputFound: !!el,
      tag: el ? el.tagName : null,
      isContentEditable: el ? el.isContentEditable : false,
      formFound: !!form,
      buttonsInForm: buttons,
      inputHTML: el ? el.innerHTML : null,
      articlesCount: articles.length,
      roleMessages: roleMessages
    });
    return true;
  }

  if (req.action === 'chatgpt_test_input') {
    (async () => {
      const el = document.querySelector('#prompt-textarea') || document.querySelector('div[contenteditable="true"]');
      if (!el) {
        return sendResponse({ success: false, error: '未找到输入框' });
      }

      el.focus();
      // Select all contents
      const sel = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(el);
      sel.removeAllRanges();
      sel.addRange(range);

      // Insert text via execCommand
      const inserted = document.execCommand('insertText', false, req.text || '测试消息');
      el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: req.text }));

      await sleep(300);

      const sendBtn = document.querySelector('button[aria-label="发送"]') ||
                      document.querySelector('button[aria-label="Send prompt"]') ||
                      document.querySelector('button[type="submit"]');

      sendResponse({
        success: true,
        inserted,
        newHTML: el.innerHTML,
        sendBtnFound: !!sendBtn,
        sendBtnAriaLabel: sendBtn ? sendBtn.getAttribute('aria-label') : null,
        sendBtnDisabled: sendBtn ? sendBtn.disabled : null
      });
    })();
    return true;
  }
});

// 1. Get Session Info (accessToken, email, name)
async function handleGetSession(sendResponse) {
  try {
    const res = await fetch('/api/auth/session', {
      headers: {
        'Accept': 'application/json'
      }
    });
    if (!res.ok) {
      return sendResponse({ success: false, status: res.status, error: `Session request failed: ${res.statusText}` });
    }
    const data = await res.json();
    sendResponse({ success: true, session: data });
  } catch (err) {
    sendResponse({ success: false, error: err.message });
  }
}

// 2. Get Available Models
async function handleGetModels(sendResponse) {
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
    if (!res.ok) {
      return sendResponse({ success: false, status: res.status, error: `Models request failed: ${res.statusText}` });
    }
    const data = await res.json();
    sendResponse({ success: true, models: data });
  } catch (err) {
    sendResponse({ success: false, error: err.message });
  }
}

// 3. Send message via native DOM input & wait for completion
async function handleSendMessage(promptText, sendResponse) {
  try {
    const el = document.querySelector('#prompt-textarea') || document.querySelector('div[contenteditable="true"]');
    if (!el) {
      return sendResponse({ success: false, error: '未在页面中找到输入框 (#prompt-textarea)' });
    }

    // Check if previous generation is still running; if so, click stop first
    const stopBtn = document.querySelector('button[aria-label="停止"]') ||
                    document.querySelector('button[data-testid="stop-button"]');
    if (stopBtn) {
      stopBtn.click();
      await sleep(600);
    }

    // Record initial count of assistant messages
    let initialAssistantCount = document.querySelectorAll('[data-message-author-role="assistant"]').length;
    if (initialAssistantCount === 0) {
      initialAssistantCount = document.querySelectorAll('article').length;
    }

    // Focus & set text
    el.focus();
    const sel = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(el);
    sel.removeAllRanges();
    sel.addRange(range);

    // Insert text via native execCommand to trigger Lexical editor state
    document.execCommand('insertText', false, promptText);
    el.dispatchEvent(new InputEvent('input', {
      bubbles: true,
      cancelable: true,
      inputType: 'insertText',
      data: promptText
    }));

    await sleep(350);

    // Find send button
    const sendBtn = document.querySelector('button[aria-label="发送"]') ||
                    document.querySelector('button[aria-label="Send prompt"]') ||
                    document.querySelector('button[aria-label="发送提示"]') ||
                    document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[type="submit"].bg-composer-primary') ||
                    document.querySelector('button[type="submit"]') ||
                    document.querySelector('.icon-primary-action')?.closest('button');

    if (!sendBtn || sendBtn.disabled) {
      return sendResponse({
        success: false,
        error: `发送按钮未就绪 (found: ${!!sendBtn}, disabled: ${sendBtn?.disabled})`
      });
    }

    // Click to send!
    sendBtn.click();

    // Wait for assistant reply
    const reply = await waitForAssistantReply(initialAssistantCount, 90000);
    sendResponse({ success: true, text: reply });
  } catch (err) {
    sendResponse({ success: false, error: err.message });
  }
}

// Helper: Polling until generation finishes
function waitForAssistantReply(initialCount, timeoutMs = 90000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    let lastContent = '';
    let stableTimes = 0;

    const interval = setInterval(() => {
      if (Date.now() - start > timeoutMs) {
        clearInterval(interval);
        if (lastContent) {
          resolve(lastContent);
        } else {
          reject(new Error('等待 ChatGPT 回复超时'));
        }
        return;
      }

      // Check if generation is still actively in progress
      const isBusy = !!document.querySelector('button[aria-label="停止"]') ||
                     !!document.querySelector('div[data-loading-indicator]') ||
                     !!document.querySelector('button[data-testid="stop-button"]') ||
                     !!document.querySelector('.result-streaming');

      // Find assistant message elements
      let assistantEls = document.querySelectorAll('[data-message-author-role="assistant"]');
      if (!assistantEls || assistantEls.length === 0) {
        assistantEls = document.querySelectorAll('article');
      }

      if (assistantEls.length > initialCount) {
        const targetEl = assistantEls[assistantEls.length - 1];
        const contentEl = targetEl.querySelector('.markdown') ||
                          targetEl.querySelector('.prose') ||
                          targetEl;
        const currentText = contentEl.innerText.trim();

        if (currentText) {
          if (currentText === lastContent && !isBusy) {
            stableTimes++;
            if (stableTimes >= 2) {
              clearInterval(interval);
              resolve(currentText);
              return;
            }
          } else {
            lastContent = currentText;
            stableTimes = 0;
          }
        }
      }
    }, 600);
  });
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
