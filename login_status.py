# -*- coding: utf-8 -*-
"""通过 Cookie Hub 判断各站点是否已登录，并在失败时给出请登录引导。"""

import json
import urllib.parse
import urllib.request

_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HUB = "http://127.0.0.1:18888"

SERVICES = (
    {
        "id": "gemini",
        "name": "Gemini",
        "login_url": "https://gemini.google.com/",
        "domains": ("google.com",),
        "hint_in": "浏览器里已有 Google 登录 Cookie。对话若失败，通常是出口被 Google 风控，不是账号掉线。",
        "hint_out": "请登录 Gemini：在已加载 Cookie Hub 的浏览器打开 https://gemini.google.com/ 并登录 Google 账号。",
    },
    {
        "id": "aistudio",
        "name": "Google AI Studio",
        "login_url": "https://aistudio.google.com/",
        "domains": ("google.com", "aistudio.google.com"),
        "hint_in": "浏览器里已有 Google 登录凭证，可直接同步至 Google AI Studio 逆向引擎。",
        "hint_out": "请登录 Google AI Studio：在已加载 Cookie Hub 的浏览器打开 https://aistudio.google.com/ 并登录 Google 账号。",
    },
    {
        "id": "chatgpt",
        "name": "ChatGPT",
        "login_url": "https://chatgpt.com/",
        "domains": ("chatgpt.com",),
        "hint_in": "浏览器里已有 ChatGPT 登录会话。",
        "hint_out": "请登录 ChatGPT：在已加载 Cookie Hub 的浏览器打开 https://chatgpt.com/ 并登录。免费账号也可以使用。",
    },
    {
        "id": "baidu",
        "name": "百度网盘",
        "login_url": "https://pan.baidu.com/",
        "domains": ("baidu.com", "pan.baidu.com"),
        "hint_in": "浏览器里已有百度网盘登录凭证。",
        "hint_out": "请登录百度网盘：在已加载 Cookie Hub 的浏览器打开 https://pan.baidu.com/ 并登录。",
    },
    {
        "id": "suno",
        "name": "Suno",
        "login_url": "https://suno.com/",
        "domains": ("suno.com", "clerk.suno.com"),
        "hint_in": "浏览器里已有 Suno 登录凭证。",
        "hint_out": "请登录 Suno：在已加载 Cookie Hub 的浏览器打开 https://suno.com/ 并登录。",
    },
    {
        "id": "bilibili",
        "name": "哔哩哔哩",
        "login_url": "https://www.bilibili.com/",
        "domains": ("bilibili.com",),
        "hint_in": "浏览器里已有哔哩哔哩登录凭证。",
        "hint_out": "请登录哔哩哔哩：在已加载 Cookie Hub 的浏览器打开 https://www.bilibili.com/ 并登录。",
    },
)


def _cookie_names(domain: str):
    url = f"{HUB}/cookies?domain={urllib.parse.quote(domain)}"
    req = urllib.request.Request(url)
    with _LOCAL_OPENER.open(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return {str(item.get("name") or "") for item in (data.get("cookies") or []) if item.get("name")}


def _names_for(domains):
    found = set()
    errors = []
    for domain in domains:
        try:
            found.update(_cookie_names(domain))
        except Exception as exc:
            errors.append(str(exc))
    return found, errors


def _logged_in(service_id: str, names: set) -> bool:
    if service_id in ("gemini", "aistudio"):
        return "__Secure-1PSID" in names or "SAPISID" in names
    if service_id == "chatgpt":
        return any(name.startswith("__Secure-next-auth.session-token") for name in names)
    if service_id == "baidu":
        return bool(names.intersection({"BDUSS", "BDUSS_BFESS"}))
    if service_id == "suno":
        return bool(names.intersection({"__client", "__session", "__clerk_db_jwt"}))
    if service_id == "bilibili":
        return "SESSDATA" in names
    return False


# 两次打到 Google 的 Gemini 调用至少隔开这么久；撞上风控页后再暂停这么久。
GEMINI_MIN_INTERVAL_SECONDS = 12
GEMINI_BLOCK_SECONDS = 120


def gemini_failure_kind(message: str) -> str:
    """pace=本地间隔限制，blocked=风控页，unbound=槽位没有独立用户，login=真没登录。"""
    text = str(message or "")
    lowered = text.lower()
    if "请等待" in text and ("秒" in text or "结束后" in text):
        return "pace"
    if (
        "sorry" in lowered
        or "429" in text
        or "风控" in text
        or "出口被上游限流" in text
    ):
        return "blocked"
    if "1psid" in lowered or "未能提取到有效的 google" in lowered:
        return "login"
    if "gemini.google.com/app" in lowered or (
        ("302" in text or "重定向" in text or "被重定向" in text)
        and "sorry" not in lowered
        and ("gemini.google.com" in lowered or "登录页" in text)
    ):
        return "unbound"
    return "other"


def gemini_failure_should_retry(message: str) -> bool:
    """风控、未绑定槽位和本地限速都不能再立刻打一次 Google。"""
    return gemini_failure_kind(message) not in {"pace", "blocked", "unbound", "login"}


def explain_gemini_failure(message: str) -> str:
    """把号池的 302 / sorry 翻成可执行的处理说明。"""
    text = str(message or "")
    kind = gemini_failure_kind(text)
    if kind == "pace":
        return text
    if kind == "blocked":
        return (
            "Google 把这次请求拦到了风控页（/sorry 或 429）。账号仍是登录状态，Cookie 没有失效。"
            f"原因是短时间请求太密。服务端已暂停 Gemini 调用 {GEMINI_BLOCK_SECONDS} 秒，"
            "请等到这段时间结束再试，不要马上重试，也不要连续切换槽位。"
            "浏览器里手动打开 https://gemini.google.com/ 不受这次暂停影响。"
        )
    if kind == "unbound":
        return (
            "这份 Cookie 没有绑定到该槽位的 Google 用户。四个槽位共用浏览器里同一份登录，"
            "请求 /u/N 被跳回 gemini.google.com/app，说明这个槽位不是单独登录的账号。"
            "请改用浏览器当前已登录的那个账号，或先在已加载 Cookie Hub 的浏览器登录要使用的 Google 账号，再刷新凭证。"
            "这不是 Gemini 未登录，马上重试也不会把同一份 Cookie 变成多个用户。"
        )
    if kind == "login":
        return "请登录 Gemini：在已加载 Cookie Hub 的浏览器打开 https://gemini.google.com/ 并登录 Google 账号。"
    if "502" in text or "Bad Gateway" in text:
        return (
            "Gemini 账号仍是登录状态。上游返回了 502，这次既不是风控页，也不是槽位跳回应用页。"
            f"请按原文处理，不要立刻连点。原文：{text}"
        )
    return text


def collect_login_status() -> dict:
    """只读 Cookie 名称，判断哪些服务已经登录。不会打开新标签，也不会返回 Cookie 值。"""
    services = []
    hub_error = None
    try:
        req = urllib.request.Request(f"{HUB}/status")
        with _LOCAL_OPENER.open(req, timeout=3) as resp:
            hub = json.loads(resp.read().decode("utf-8"))
        if not hub.get("extensionConnected"):
            hub_error = "Cookie Hub 扩展还没连上，暂时无法判断各站点是否已登录。"
    except Exception as exc:
        hub_error = f"Cookie Hub 未响应，暂时无法判断登录状态：{exc}"

    for spec in SERVICES:
        item = {
            "id": spec["id"],
            "name": spec["name"],
            "login_url": spec["login_url"],
            "logged_in": None,
            "hint": spec["hint_out"],
        }
        if hub_error:
            item["hint"] = hub_error
            services.append(item)
            continue
        names, errors = _names_for(spec["domains"])
        if errors and not names:
            item["hint"] = "读取浏览器 Cookie 失败，暂时无法确认是否已登录。"
            services.append(item)
            continue
        logged_in = _logged_in(spec["id"], names)
        item["logged_in"] = logged_in
        item["hint"] = spec["hint_in"] if logged_in else spec["hint_out"]
        services.append(item)

    needs = [item for item in services if item["logged_in"] is False]
    names = "、".join(item["name"] for item in needs)
    return {
        "hub_connected": hub_error is None,
        "hub_error": hub_error,
        "services": services,
        "needs_login": [
            {
                "id": item["id"],
                "name": item["name"],
                "login_url": item["login_url"],
                "hint": item["hint"],
            }
            for item in needs
        ],
        "guide": f"请登录：{names}。" if names else "",
    }


def failure_payload(message: str, service_id: str) -> dict:
    """失败响应里附上当前真正没登录的服务，已登录的服务不会被写成请登录。"""
    text = explain_gemini_failure(message) if service_id == "gemini" else str(message or "")
    status = collect_login_status()
    current = next((item for item in status["services"] if item["id"] == service_id), None)
    login_required = bool(current and current.get("logged_in") is False)
    guide = status.get("guide") or ""
    if login_required and current and current["hint"] not in text:
        text = f"{text} {current['hint']}".strip()
    # 风控、槽位未绑定和本地限速要单独说清楚，不要再拼上别的站点的“请登录”。
    quiet = service_id == "gemini" and gemini_failure_kind(text) in {"pace", "blocked", "unbound"}
    if guide and guide not in text and not quiet:
        text = f"{text} {guide}".strip()
    res = {
        "message": text,
        "type": f"{service_id}_error",
        "login_required": login_required,
        "needs_login": status.get("needs_login") or [],
        "guide": guide,
    }
    import re
    m = re.search(r"(?:倒计时|等待|还剩)\s*(\d+)\s*秒", text)
    if m:
        try:
            res["retry_after"] = int(m.group(1))
        except Exception:
            pass
    m_fail = re.search(r"【上次失败原因:\s*(.+?)】", text)
    if m_fail:
        res["last_failure_reason"] = m_fail.group(1).strip()
    return res
