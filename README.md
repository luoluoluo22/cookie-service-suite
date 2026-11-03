# 🍪 Cookie Service Suite (浏览器 Cookie 动态提取与多平台服务调用套件)

本项目是一套完整、自闭环的**浏览器 Cookie 动态提取与免密 Web 服务调用解决方案**。

通过自主研发的 Chrome / Edge 浏览器扩展（Manifest V3）与本地守护通信服务，实现了**从浏览器前台无感、按需获取任意已登录网站的实时 Cookie**，并成功对 **Bilibili（4K视频/大会员特权/yt-dlp联动）** 与 **百度网盘（BDUSS/配额查询/目录遍历）** 等主流服务完成了真实 API 验证。

---

## 🌟 核心架构

```
[ 浏览器端 (Edge / Chrome / Ego) ]
   └── 🧩 Cookie Hub 扩展 (Manifest V3)
         │  (通过 WebSocket 与 127.0.0.1:18888 实时互联)
         ▼
[ 本地 Bridge 守护服务 (server.js:18888) ]
         ▲  (暴露 HTTP REST 接口: /cookies?domain=...)
         │
[ 业务层 SDK 与 CLI 工具 (Python) ]
   ├── 🔌 cookie_bridge.py   (通用 Cookie 获取 SDK)
   ├── 📺 bilibili_service.py (B 站用户信息、Dash 4K 流解析、yt-dlp 高清下载)
   ├── 💾 baidu_pan_service.py (百度网盘 BDUSS 鉴权、配额计算、文件遍历)
   └── 🧪 test_suite.py       (自动化端到端测试套件)
```

---

## 📊 真实 Cookie 接口实测通过清单

| 服务平台 | 实测提取凭证 | 测试场景 / 接口 | 实测结果 | 数据反馈与能力 |
| :--- | :--- | :--- | :--- | :--- |
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
│   ├── popup.html/js/css # 开发者弹窗界面 (支持一键复制 Header/JSON/Netscape)
│   └── reload.js         # 命令行一键重载扩展工具
├── cookie_bridge.py      # 通用 Python SDK：向本地 Bridge 请求实时 Cookie
├── baidu_pan_service.py  # 百度网盘业务实现：账号鉴权、配额计算、文件列表遍历
├── run_baidu_cli.py      # 百度网盘命令行工具：查看配额、用户信息、列出文件
├── bilibili_service.py   # Bilibili 业务封装：用户信息、Dash 直链提取、yt-dlp 联动
├── run_bili_cli.py       # Bilibili 命令行工具：一键查询账号、视频画质与高清下载
├── test_suite.py         # 自动化测试套件：覆盖全流程 5 项关键测试
└── README.md             # 本项目文档
```

---

## 🚀 快速上手与运行

### 1. 启动本地 Bridge 服务并加载扩展
```powershell
# 启动本地守护服务 (监听 127.0.0.1:18888)
cd extension
npm install ws
node server.js
```
* 在浏览器中打开 `edge://extensions/` 或 `chrome://extensions/`，开启开发者模式；
* 点击「加载已解压的扩展程序」，选择 `extension` 文件夹。

### 2. 运行五合一全自动测试套件
```powershell
$env:PYTHONIOENCODING="utf-8"
python test_suite.py
```

### 3. 百度网盘命令行使用
```powershell
# 查看网盘总容量、已用空间与剩余空间
python run_baidu_cli.py quota

# 查看网盘用户信息与 UID
python run_baidu_cli.py user

# 列出网盘指定目录下的文件 (默认根目录)
python run_baidu_cli.py list /
```

### 4. Bilibili 命令行使用
```powershell
# 查看当前登录的 B 站个人中心数据
python run_bili_cli.py user

# 查询任意视频信息与大会员可用最高画质
python run_bili_cli.py video BV1GJ411x7h7

# 携带大会员 Cookie 高清下载视频至 ./downloads
python run_bili_cli.py download BV1GJ411x7h7
```

---

## 💡 协议与免责声明

* 本项目仅用于个人学习、自动化测试与 API 研究用途。
* 所有 Cookie 数据均保存在本机本地回环地址（`127.0.0.1`），不会向任何第三方服务器上传任何个人凭证。
