# Google AI Studio 网页转 API (纯 Cookie 路线) 深度调研与测试报告

## 一、候选开源项目测试与评测概况

本次针对路线一（纯 Cookie 网页逆向方案）在本地 `candidate_repos/` 下拉取并测试了 3 个核心参考项目：

### 1. Mag1cFall / AIStudio2API (综合评级: ★★★★★ 首选架构)
- **技术栈**: Go + SpiderMonkey / Camoufox
- **运行表现**:
  - 本地单文件二进制 `aistudio2api.exe` 启动仅耗时 **755ms**；
  - 默认使用内置 SpiderMonkey（Firefox JS 引擎）生成官方 WAA Proof，**运行时不需要启动或安装 Chromium/Playwright 无头浏览器**，纯 HTTP 运行，内存占用极低；
  - **动态签名验证通过**: 本地代码分析发现，核心通过 `signer.go` 解析 Google 专有的 `SAPISIDHASH` 与 `SAPISID1PHASH` 授权头：
    `SHA1(timestamp + " " + SAPISID + " https://aistudio.google.com")`
    只要获取到已登录 Cookie 中的 `SAPISID` 和 `__Secure-1PAPISID`，即可纯本地算法离线签名！
  - **接口能力**: 完整导出 OpenAI `/v1/chat/completions`、Responses、Anthropic `/v1/messages` 以及 Gemini 官方格式，原生支持多账号自动轮换、故障熔断、TTS 语音与文生图。

### 2. SreejanPersonal / Gemini-AIStudio-Reverse (综合评级: ★★★★ 协议范例)
- **技术栈**: Python Requests
- **核心价值**:
  - 明确验证了 Google AI Studio 网页端的底层 Internal RPC 通信端点：
    `https://alkalimakersuite-pa.clients6.google.com/$rpc/google.internal.alkali.applications.makersuite.v1.MakerSuiteService/GenerateContent`
  - 梳理了 `application/json+protobuf` 格式的上下文历史信封和参数结构，代码仅 170 行，便于后续用 Python 实现原生无缝对接。

### 3. CJackHwang / AIstudioProxyAPI (综合评级: ★★★ 轮换与保活方案)
- **技术栈**: Python FastAPI + Camoufox + Playwright
- **核心价值**:
  - 提供了完整的多账号认证文件管理机制（`auth_profiles/active`, `saved`, `emergency`）；
  - 提供了请求后自动捕获新 Cookie 并回写持久化的机制（`cookie_refresh.py`），对长时间会话保活具有参考意义。

---

## 二、与本项目 `cookie-service-suite` 的集成落地蓝图

1. **凭证自动采集**: 利用本项目已有的 `Cookie Hub` 浏览器扩展，自动监听 `aistudio.google.com` 域下的 `SAPISID`、`__Secure-1PAPISID`、`__Secure-1PSID` 等会话 Cookie；
2. **纯 Python 离线签名**: 在 Python 端实现 `SAPISIDHASH` 计算器（仅需标准库 `hashlib.sha1` 与 `time.time()`），无需无头浏览器；
3. **多账号号池汇聚**: 结合目前已有的 Gemini 多账号池架构，直接将 Google AI Studio 作为极速号池纳入统一调度中。
