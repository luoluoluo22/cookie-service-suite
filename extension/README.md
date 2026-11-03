# 🍪 Cookie Hub - 开发者 Cookie 提取与本地通信服务

专为开发者打造的轻量级浏览器扩展 + 本地通信服务（基于 Chrome / Edge Extension **Manifest V3**）。

不仅能在前台弹窗中直接查看和复制 Cookie，还**支持与本地 Python / Node / 终端脚本双向通信**，并内置**自动热重载 (Hot-Reload) 与命令行一键重载 (CLI Reload)** 机制！

---

## 🌟 架构与工作原理

```
[ 本地代码修改 / 终端命令 / AI 助手 ]
         │ (保存代码 触发自动热重载 或 命令行发送 GET /reload)
         ▼
[ 本地 Bridge 守护服务 (127.0.0.1:18888) ]
         │ (通过 WebSocket 触发 action: 'reload')
         ▼
[ 浏览器扩展后台 (background.js) ] ──▶ 执行 chrome.runtime.reload() ──▶ 扩展无感自动重启
```

* **文件保存自动刷新**：修改项目里的任意代码文件（`.js`、`.html`、`.css`），扩展在后台 0.3 秒内自动重启生效。
* **命令一键触发**：终端执行 `npm run reload` 或 `node reload.js` 即可直接让前台浏览器扩展重启。
* **按需按域读取**：需要哪个网站的 Cookie，本地接口秒级提取回传。

---

## 🚀 启动与首次激活

> [!IMPORTANT]
> **首次激活说明**：因为扩展加入了后台通信 Worker (`background.js`) 与清单变更，需要浏览器**首次**加载最新配置：
> 1. 打开 Edge 浏览器地址栏：`edge://extensions/`
> 2. 找到 **Cookie Hub** 插件卡片。
> 3. 点击卡片上的 **「重新加载」 (↻ 旋转图标)** 一次。
> 4. 点击插件图标，左上角将点亮：`🟢 本地通信已连接`。
> 
> **只要初次建立连接后，后续所有改动和重载均可通过命令或文件保存自动完成，无需再打开扩展管理页面！**

---

## 🔄 命令行与自动重载命令

### 方式 1：终端命令行重载
在项目目录下执行：
```bash
npm run reload
# 或
node reload.js
```
或者通过任何 HTTP 客户端：
```bash
curl http://127.0.0.1:18888/reload
```

### 方式 2：代码保存自动热重载 (Hot-Reload)
本地服务 `server.js` 内置了 `fs.watch` 文件监听器，只要你编辑并保存了 `popup.js`、`popup.html`、`background.js` 等任意文件，服务端就会自动下发重载指令，扩展立即在 Edge 浏览器中无感重新加载！

---

## 📡 Cookie 提取与接口调用

### 1. 终端命令行快速测试
```powershell
# 获取 B 站 Cookie (包含 SESSDATA 等)
node get_cookie.js bilibili.com

# 获取网易云音乐 Cookie（JSON 格式）
node get_cookie.js music.163.com --json

# 获取当前浏览器正在浏览页面的 Cookie
node get_cookie.js --active
```

### 2. HTTP API 接口
```bash
# 获取直接可用于请求头的 Header 格式（key=val; key2=val2）
curl "http://127.0.0.1:18888/cookies?domain=bilibili.com&format=header"

# 获取键值对 JSON
curl "http://127.0.0.1:18888/cookies?domain=baidu.com&format=json"

# 获取当前活动标签页
curl "http://127.0.0.1:18888/active"
```

---

## 🐍 Python 自动化调用示例

```python
import requests

def get_cookies_by_domain(domain: str) -> str:
    """向本地通信服务实时索取指定域名的 Cookie Header"""
    res = requests.get(
        "http://127.0.0.1:18888/cookies",
        params={"domain": domain, "format": "header"},
        timeout=5
    )
    return res.text

# 实时按需获取：
cookie_header = get_cookies_by_domain("bilibili.com")
headers = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": cookie_header
}
info = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=headers).json()
print("B站登录用户:", info)
```
