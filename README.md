# 🍪 Cookie Service Suite (浏览器 Cookie 动态提取与多平台服务调用套件)

本项目是一套完整、自闭环的**浏览器 Cookie 动态提取与免密 Web 服务调用解决方案**。

通过自主研发的 Chrome / Edge / Ego 浏览器扩展（Manifest V3）与本地守护通信服务，实现了**从浏览器前台无感、按需获取任意已登录网站的实时 Cookie**，并成功对 **ChatGPT Web（原生桥接突破 Cloudflare / Arkose / Turnstile，兼容 OpenAI 格式）**、**Bilibili（4K视频/大会员特权/yt-dlp联动）** 与 **百度网盘（BDUSS/配额查询/目录遍历）** 等主流服务完成了真实 API 验证。

---

## 🌟 核心架构

```
[ 浏览器端 (Edge / Chrome / Ego) ]
   └── 🧩 Cookie Hub 扩展 (Manifest V3)
         │  (通过 WebSocket 与 127.0.0.1:18888 实时互联)
         │  (支持同源 Content Script / In-Page 注入与原生执行)
         ▼
[ 本地 Bridge 守护服务 (server.js:18888) ]
         ▲  (暴露 HTTP REST 接口: /cookies, /v1/chat/completions)
         │
[ 业务层 SDK 与 CLI 工具 (Python) ]
   ├── 🔌 cookie_bridge.py    (通用 Cookie 获取 SDK)
   ├── 🤖 chatgpt_service.py  (ChatGPT 页面桥接、会话提取与 OpenAI 兼容对话)
   ├── 🎵 suno_service.py     (Suno AI 音乐创作、Clerk 令牌兑换、状态轮询与 MP3 下载)
   ├── 📺 bilibili_service.py  (B 站用户信息、Dash 4K 流解析、yt-dlp 高清下载)
   ├── 💾 baidu_pan_service.py (百度网盘 BDUSS 鉴权、配额计算、文件遍历)
   └── 🧪 test_suite.py        (全套自动化端到端测试套件)
```

---

## 📊 真实接口实测通过清单

| 服务平台 | 实测提取凭证 / 桥接技术 | 测试场景 / 接口 | 实测结果 | 数据反馈与能力 |
| :--- | :--- | :--- | :--- | :--- |
| **OpenAI ChatGPT Web** | 浏览器原生桥接<br>`Bearer AccessToken`<br>`__Secure-next-auth`<br>**SSE Stream Hook** | 1. 登录会话与用户提取 (`/chatgpt/session`)<br>2. 账号可用模型列表 (`/chatgpt/models`)<br>3. 标准兼容对话 (`/v1/chat/completions`)<br>4. 实时流式响应 (`stream: true`) | 🟢 **100% 通过** | 彻底绕过 Cloudflare Turnstile 403 拦截，提取账号 `7501243@qq.com` 会话与实时模型库；通过页面主环境 (`MAIN` world) 挂载 `window.fetch` 流式拦截器，毫秒级逐字提取 SSE 数据块 (`text/event-stream`)，兼具 DOM 兜底保底，实现长文本无截断完整输出。 |
| **Suno AI 音乐创作** | Clerk 动态 Token 换取<br>`__client`<br>`Bearer JWT`<br>`curl_cffi` 真实指纹伪装 | 1. 账户总积分与曲目配额 (`/api/suno/quota`)<br>2. 历史曲库与音频直链 (`/api/suno/feed`)<br>3. 灵感/歌词模式生成 (`/api/suno/generate`)<br>4. 本地 MP3 流式自动下载 | 🟢 **集成完毕** | 依托本地 Cookie Hub 自动提取 `suno.com` 与 `clerk.suno.com` 凭证，免手动 F12 抓包；基于 `curl_cffi` 原生模拟浏览器 TLS 指纹突破 Cloudflare 风控；实现从提示词输入到自动轮询、两组变体曲目渲染完成、MP3 流式下载入库的全闭环。 |
| **百度网盘 (Baidu Pan)** | `BDUSS`<br>`STOKEN`<br>`PANPSC` | 1. 账号与会员鉴权<br>2. 网盘总配额/剩余容量<br>3. 目录与文件实时遍历 | 🟢 **100% 通过** | 自动提取 `BDUSS`，成功查询容量配额 **2055.0 GB**（已用 1913.86 GB，剩余 141.14 GB），成功遍历根目录下 19 项文件与文件夹。 |
| **Bilibili (哔哩哔哩)** | `SESSDATA`<br>`bili_jct`<br>`DedeUserID` | 1. 个人中心与资产查询<br>2. 高清分P与Dash流解析<br>3. `yt-dlp` 高清下载 | 🟢 **100% 通过** | 自动提取 `SESSDATA`，成功识别账号等级 Lv.5、大会员特权与硬币，解锁 1080P+ / 4K 高码率视频流。 |
| **yt-dlp 联动下载** | Netscape 格式 cookies.txt | B 站 1080P+ / 4K 原画视频解析提取 | 🟢 **100% 通过** | 本地服务自动导出标准 Netscape 格式，yt-dlp 无感绕过画质限制并自动下载。 |

---

## 🛠️ 项目目录结构

```text
cookie-service-suite/
├── extension/            # Chrome / Edge / Ego 浏览器扩展源码 (Manifest V3)
│   ├── manifest.json     # 扩展清单 (注册 Service Worker、权限等)
│   ├── background.js     # 后台通信 Worker (保持本地 WebSocket 连接)
│   ├── server.js         # 本地 Bridge 守护服务 (监听 127.0.0.1:18888)
│   ├── chatgpt_bridge.js # ChatGPT 同源注入桥接脚本
│   ├── popup.html/js/css # 开发者弹窗界面 (支持一键复制 Header/JSON/Netscape)
│   └── reload.js         # 命令行一键重载扩展工具
├── app_service.py        # 统一本地 RESTful API 服务与可视化管理控制台 (FastAPI)
├── tray_service.py       # Windows 系统托盘守护程序 (pystray + Pillow)
├── run_service.py        # 一键启动服务与托盘程序命令行脚本
├── generate_icon.py      # 应用图标生成与多分辨率 ICO 转换工具
├── assets/               # 桌面与系统托盘图标资源 (app_icon.png, app_icon.ico)
├── cookie_bridge.py      # 通用 Python SDK：向本地 Bridge 请求实时 Cookie
├── gemini_service.py     # Gemini 多账号池化调度管理器 (支持 /u/0 ~ /u/3 与故障自愈)
├── run_gemini_cli.py     # Gemini 4 账号命令行管理工具
├── monitor_gemini_workflow.py # 长时间稳定性与多账号自动化轮询监控脚本
├── chatgpt_service.py    # ChatGPT 客户端 SDK：会话提取、模型列表、问答对话
├── suno_service.py       # Suno 音乐生成服务：Clerk 令牌兑换、状态轮询与 MP3 下载
├── suno_cli.py           # Suno 独立免服务客户端：免启动后台服务，直接查配额与生成下载
├── suno_cli.bat          # Windows 一键执行批处理脚本
├── run_suno_cli.py       # Suno 音乐生成命令行工具：与套件服务联动
├── baidu_pan_service.py  # 百度网盘业务实现：账号鉴权、配额计算、文件列表遍历
├── run_baidu_cli.py      # 百度网盘命令行工具：查看配额、用户信息、列出文件
├── bilibili_service.py   # Bilibili 业务封装：用户信息、Dash 直链提取、yt-dlp 联动
├── run_bili_cli.py       # Bilibili 命令行工具：一键查询账号、视频画质与高清下载
├── autostart.py          # Windows 开机自启管理模块 (注册表 HKCU Run 与状态切换)
├── 开启开机自启.bat      # Windows 一键开启开机自启
├── 关闭开机自启.bat      # Windows 一键关闭开机自启
├── 启动服务与系统托盘.bat # Windows 后台静默启动本地套件与托盘常驻
├── 启动服务(带命令行窗口).bat # 命令行调试模式启动服务与托盘
├── 停止全部服务.bat      # 一键终止所有后台子服务与端口占用
├── test_suite.py         # 自动化测试套件：覆盖全流程 6 项关键测试
└── README.md             # 本项目文档
```

---

## 🚀 快速上手与运行

### 0. 一键启动服务与系统托盘常驻 (推荐)
```powershell
# 启动本地完整套件 (FastAPI :18800 + Cookie Hub :18888 + Gemini 池 :18083 + ChatGPT 逆向 :18084 + 系统托盘)
python run_service.py
```
> **或者直接双击运行根目录批处理脚本**：
> - `启动服务与系统托盘.bat`：静默后台启动，图标常驻 Windows 右下角通知区域。
> - `启动服务(带命令行窗口).bat`：带终端实时日志输出，适合调试排错。

#### 🖥️ 系统托盘实时状态与交互特性：
1. **鼠标悬停 (Tooltip)**：实时显示统一控制台端口 (18800)、Cookie Hub 状态 (18888)、浏览器扩展连接状态与 Gemini 账号可用数。
2. **右键菜单实时状态栏**：
   - `📊 服务总览`: 显示当前运行时间与整体健康度。
   - `├─ 🌐 Web 控制台`: 实时标示在线状态与端口。
   - `├─ 🔌 Cookie Hub`: 实时标示 Node 守护进程状态。
   - `├─ 🧩 浏览器插件`: 实时检测已接入浏览器客户端数量 (未连接时点击弹出配置指引)。
   - `├─ 🤖 Gemini 统一池`: 实时显示多账号池接入与可用账号数。
   - `└─ ⚡ ChatGPT 逆向`: 实时显示端口与一键启停开关。
3. **开机自启动一键切换**：右键菜单直接勾选/取消 `🚀 开机自启动: [√] 已开启`，或使用 `autostart.py`。
4. **服务运行诊断报告**：点击 `📋 查看服务运行详细诊断报告` 即可弹出全套服务健康参数弹窗。

---

### 1. Windows 开机自启动管理
本项目支持完全静默无控制台黑框的 Windows 开机自启（开机登录后自动后台启动系统托盘）：
```powershell
# 开启开机自启
python autostart.py --enable

# 关闭开机自启
python autostart.py --disable

# 检查当前开机自启配置
python autostart.py --status
```
> **图形化方式**：
> 1. 在右下角系统托盘图标上右键，直接点击 `🚀 开机自启动` 即可一键切换；
> 2. 或直接双击 `开启开机自启.bat` / `关闭开机自启.bat`。

---

### 2. 加载浏览器 Cookie Hub 扩展
```powershell
# 启动本地守护服务 (监听 127.0.0.1:18888)
cd extension
npm install ws
node server.js
```
* 在浏览器中打开 `edge://extensions/` 或 `chrome://extensions/`，开启开发者模式；
* 点击「加载已解压的扩展程序」，选择 `extension` 文件夹。

### 2. 运行六合一全自动测试套件
```powershell
$env:PYTHONIOENCODING="utf-8"
python test_suite.py
```

### 3. ChatGPT 双引擎：chatgpt2api 深度网页逆向 + 浏览器同源桥接
本套件支持 **无头深度逆向引擎** 与 **浏览器同源桥接** 双模智能协同：

#### (1) 逆向原理解析：Cookie 与请求构造机制
- **核心对话与生图**：OpenAI 官方 Web 前端在发起实际对话（`/backend-api/conversation`）或生图接口时，**并不在 Cookie 中传递鉴权**，而是使用 `Authorization: Bearer <access_token>`，并配合设备指纹、`curl_cffi` 模拟的 Chrome TLS 指纹以及 Sentinel PoW（Proof of Work，基于 Fnv1a-32 哈希与 Seed 碰撞）算力证明请求头。
- **与 Cookie 的关键桥梁**：浏览器已登录用户的 `__Secure-next-auth.session-token` Cookie 可通过同源请求 `/api/auth/session` 换取有效期内的 `accessToken`。本套件支持 **一键从浏览器 Cookie Hub 自动提取该 Token 注入逆向号池**，省去人工复制与邮箱密码登录环节！

#### (2) Python 代码直接调用
```python
from chatgpt_service import chatgpt_service

# 1. 自动从当前前台浏览器同步已登录 Token 入池
sync_res = chatgpt_service.sync_token_from_browser()
print("已导入账号:", sync_res.get("email"), "方案:", sync_res.get("plan"))

# 2. 智能对话 (支持 auto, gpt-5-6, gpt-4o 等模型)
reply = chatgpt_service.ask("请用一句话做个自我介绍！")
print("回复:", reply)

# 3. 实时打字机流式输出 (SSE Stream)
for token in chatgpt_service.ask("写一首关于春天的五言绝句", stream=True):
    print(token, end="", flush=True)

# 4. 逆向文生图与图像编辑 (gpt-image-2 / DALL-E 3)
img_res = chatgpt_service.generate_image("一只在太空漫步的赛博朋克猫咪", model="gpt-image-2")
print("生图任务结果:", img_res.get("data", [{}])[0].get("b64_json")[:50], "...")
```

#### (3) 标准 OpenAI 兼容 API 与流式输出 (Stream: true)
本地服务开放了标准 `/v1/chat/completions` 与 `/v1/images/generations`：
```bash
# 1. OpenAI 兼容流式调用 (auto / gpt-5-6 / gpt-4o)
curl -N -X POST http://127.0.0.1:18800/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [
      {"role": "user", "content": "用Python写一个快速排序算法并解释原理"}
    ],
    "stream": true
  }'

# 2. OpenAI 兼容图片生成 (gpt-image-2)
curl -X POST http://127.0.0.1:18800/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "水彩插画风格的一只橙色猫咪在木质窗台晒太阳",
    "n": 1
  }'
```

---

## ⚡ ChatGPT Web 双引擎流式与长文本完整性保障机制

针对网页端 ChatGPT 获取回复的行业痛点（DOM 截断、代码块折叠、长文本丢失、渲染延迟），本套件设计了业内顶尖的**双引擎协同机制**：

1. **主环境 SSE 网络流挂钩引擎 (优先生效 - 极致速度与完整度)**:
   - 注入浏览器页面主环境 (`world: 'MAIN'`) 劫持原生 `window.fetch`；
   - 识别 ChatGPT 核心对话接口（`/conversation` 与 `/backend-api/f/conversation`）；
   - 通过 `response.clone().body.getReader()` 在底层克隆流，对浏览器原有 UI 渲染零干扰；
   - 实时解析服务端推送的 SSE 增量数据块 (`parts: [...]`)，按 delta 增量毫秒级回传本地桥接服务；
   - 彻底摆脱 DOM 虚拟列表、滚动条限制与代码框折叠影响，保证数千字长篇代码/文章无任何截断。

2. **DOM 语义树稳定扫描引擎 (兜底保底 - 极致鲁棒性)**:
   - 当遇到网络异常或特殊接口变动时，底层自动无缝降级至 DOM 监控器；
   - 通过稳定轮询与状态机（侦测发送按钮、停止生成按钮、思考指示器与 Markdown 根容器渲染稳定性）；
   - 确保在任何极端网络波动场景下均能稳定获取完整模型回答。

### 4. 百度网盘命令行使用
```powershell
# 查看网盘总容量、已用空间与剩余空间
python run_baidu_cli.py quota

# 查看网盘用户信息与 UID
python run_baidu_cli.py user

# 列出网盘指定目录下的文件 (默认根目录)
python run_baidu_cli.py list /
```

### 5. Bilibili 命令行使用
```powershell
# 查看当前登录的 B 站个人中心数据
python run_bili_cli.py user

# 查询任意视频信息与大会员可用最高画质
python run_bili_cli.py video BV1GJ411x7h7

# 携带大会员 Cookie 高清下载视频至 ./downloads
python run_bili_cli.py download BV1GJ411x7h7
```

### 6. Google Gemini 4 账号统一池与负载均衡
针对用户浏览器同时登录的多个 Google 账号（以 `/u/0`, `/u/1`, `/u/2`, `/u/3` 区分），本项目打造了池化管理套件：
- **多账号自动轮换**：动态计算 `SAPISIDHASH` 签名，通过 `X-Goog-AuthUser` 区分多账号，基于最久未用 (LRU) 自动负载均衡。
- **自愈保活机制**：后台主动周期性续期短效会话票据，遇到异常自动从 Cookie Hub (18888) 热刷新凭证并注入 SQLite。
- **OpenAI 兼容接口**：开放 `http://127.0.0.1:18083/v1/chat/completions`。

```powershell
# 1. 查看 4 个已接入账号状态与轮询统计
python run_gemini_cli.py list

# 2. 命令行提问 (自动在 4 个账号间负载均衡轮转)
python run_gemini_cli.py ask "量子纠缠是什么？"

# 3. 启动 / 停止后台统一 API 服务 (端口 18083)
python run_gemini_cli.py start
python run_gemini_cli.py stop

# 4. 执行长时间稳定性与自治轮询测试
python monitor_gemini_workflow.py
```

### 7. 本地统一 API 服务与系统托盘管理控制台 (FastAPI + pystray)
本项目采用成熟的 **FastAPI + Uvicorn + pystray** 封装了统一的本地服务总线：
- **系统托盘常驻**：生成定制高科技质感应用图标 (`assets/app_icon.png` 与 `app_icon.ico`)，在 Windows 系统任务栏托盘中无感驻留。
- **一键可视化管理界面**：点击或右键托盘图标即可在浏览器直接弹出现代化 Web 控制台 (`http://127.0.0.1:18800/`)。
- **实时看板与在线调试**：
  - 实时监控 Cookie Hub、Gemini 4账号槽位、ChatGPT 状态与运行时间。
  - 内置在线 API 调试工作台 (Playground)，可直接对任何接口一键发送请求并即时渲染响应。
  - 提供账号检测、令牌保活与浏览器全量 Cookie 重新提取功能。
- **标准化 API 规范**：开箱即用内置 Swagger UI (`/docs`)、ReDoc (`/redoc`) 与标准 OpenAI 路由 (`/v1/chat/completions`)。

```powershell
# 1. 启动本地服务 + 系统托盘 + 自动打开管理控制台
python run_service.py

# 2. 纯命令行服务模式 (不驻留托盘，适合无界面环境)
python run_service.py --no-tray

# 3. 访问入口
# Web 控制台:    http://127.0.0.1:18800/
# Swagger UI:    http://127.0.0.1:18800/docs
# ReDoc 规范:    http://127.0.0.1:18800/redoc
# OpenAI 接口:   http://127.0.0.1:18800/v1/chat/completions
```

### 8. Suno AI 音乐创作 (Cookie 免密自动化与高清 MP3 下载)
无需手动按 F12 抓包，只需在浏览器中登录一次 `suno.com`：
- **自动换票与保活**：基于 Clerk 基础设施自动兑换短效 JWT 访问令牌，避免 Token 过期。
- **TLS 指纹穿透**：通过 `curl_cffi` 完美模拟真实 Edge/Chrome 客户端指纹，突破 Cloudflare 拦截。
- **全流程一键搞定**：提交灵感提示词 $\rightarrow$ 异步状态轮询 $\rightarrow$ 获取双版本变体 $\rightarrow$ 流式自动下载 MP3 到本地 `downloads/suno`。

#### (1) 独立免服务模式 CLI (`suno_cli.py` / `suno_cli.bat` - 推荐)
**即便不启动任何本地守护进程或 Bridge 服务**，也可直接运行：
```powershell
# 1. 首次配置 Cookie 凭证 (仅需配置一次，自动加密持久化至本地安全缓存 .suno_cookie)
python suno_cli.py login

# 2. 查询当前积分与可用生成额度
python suno_cli.py quota

# 3. 灵感描述模式快速生成 (自动流式下载 MP3 到 ./downloads/suno)
python suno_cli.py gen "一段欢快的夏日海滩吉他流行曲，男女双人对唱"

# 4. 纯伴奏模式 (无主唱人声)
python suno_cli.py gen "赛博朋克电子音乐，强劲节拍与低音" --instrumental

# 5. 自定义歌词与风格流派模式
python suno_cli.py custom "[Verse]\n海风吹拂...\n[Chorus]\n夏天的歌..." --tags "acoustic pop, guitar" --title "夏日恋曲"

# 6. 单独使用 AI 创作歌词
python suno_cli.py lyrics "写一首关于秋天落叶与远方思念的流行歌词"

# 7. 查看历史生成的曲库列表与直链
python suno_cli.py feed

# 8. 通过 Clip ID 或直链补下载音频
python suno_cli.py download <clip_id_or_url>
```

#### (2) 套件统一命令行联动 (`run_suno_cli.py`)
与本地 Cookie Hub 守护服务联动，自动无感同步浏览器 Cookie：
```powershell
python run_suno_cli.py quota
python run_suno_cli.py gen "温暖治愈的民谣木吉他弹唱"
```

#### (3) Python 代码调用示例
```python
from suno_service import SunoService

suno = SunoService()

# 1. 查看额度
credits_info = suno.get_credits()
print("剩余可生成次数:", credits_info["songs_left"])

# 2. 一键生成并下载到本地
results = suno.generate_and_download(
    prompt="温暖治愈的民谣木吉他弹唱，温柔男声",
    output_dir="./downloads/suno",
    progress_callback=print
)

for r in results:
    print("曲名:", r.get("title"))
    print("本地音频文件:", r.get("local_file"))
    print("在线试听:", r.get("audio_url"))
```

---

---

## 🔒 安全与隐私原则
* 本地 Bridge 服务仅监听 `127.0.0.1` 本地回环地址，不接受任何外部网络请求。
* Cookie 凭证与 Token 仅留存于本地内存与临时会话中，严禁写入 Git 仓库。
