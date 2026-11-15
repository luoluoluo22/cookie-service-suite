"""把本机 OpenAI 兼容接口里的对话模型写进 OpenCode 配置。

本机 OpenCode 1.18 读的是 ~/.config/opencode/opencode.json 里的 provider 字段：
npm 用 @ai-sdk/openai-compatible，地址和密钥放在 options。
"""

import json
import os
from typing import Any, Dict, List, Optional

PROVIDER_ID = "cookie-suite"
PROVIDER_NAME = "Cookie Service Suite"
DEFAULT_BASE_URL = "http://127.0.0.1:18800/v1"
DEFAULT_API_KEY = "cookie-suite"

# 官网标准友好名称映射 (对齐官网网页选择器与前台显示)
MODEL_DISPLAY_NAMES: Dict[str, str] = {
    # ChatGPT 免费版前台主选模型
    "gpt-6": "6 Instant（日常聊天）",
    "gpt-6-t-mini": "6 Thinking（快速思考）",
    "auto": "Auto（智能优选）",
    "chatgpt-web": "ChatGPT 网页模拟",
    "chatgpt-web-moni": "ChatGPT 扩展模拟",

    # ChatGPT Plus / 高阶 / 工作台专有模型 (Plus 账号展示，免费版暂不展示)
    "research": "Deep Research（全网深度研究）",
    "gpt-5-6": "GPT-5.6 Luna（深度推理）",
    "gpt-6-thinking": "GPT-6 Thinking（深度思考）",
    "gpt-6-instant": "GPT-6 Instant（极速响应）",
    "gpt-5.6-luna-wm": "GPT-5.6 Luna（协同工作区）",
    "gpt-5.6-terra-wm": "GPT-5.6 Terra（协同工作区）",
    "gpt-6-sol-wm": "GPT-6 Sol（协同工作区）",
    "gpt-6-luna-wm": "GPT-6 Luna（协同工作区）",
    "gpt-6-astra-wm": "GPT-6 Astra（协同工作区）",
    "gpt-6.1-sol-wm": "GPT-6.1 Sol（协同工作区）",
    "gpt-6.1-terra-wm": "GPT-6.1 Terra（协同工作区）",

    # Google Gemini 多账号池与 AI Studio 原生模型
    "gemini-3.5-flash-lite": "3.5 Flash-Lite（快速解答）",
    "gemini-4-hydrogen": "4 Hydrogen（日常帮助）",
    "gemini-3.1-pro": "3.1 Pro（深度研究）",
    "gemini-4-argon": "4 Argon（代码与分析）",
    "gemini-canvas": "Gemini Canvas（协作画布）",
    "gemini-3.8-flash": "3.8 Flash（原生高频）",
    "gemini-3.6-flash": "3.6 Flash（高通量任务）",
    "gemini-3.1-pro-preview": "3.1 Pro Preview（深度预览）",
    "gemini-3.1-flash-lite": "3.1 Flash-Lite（轻量体验）",
    "gemini-4-hydrogen-search": "4 Hydrogen（智能搜索）",
    "gemini-4-argon-search": "4 Argon（深度代码+搜索）",
    "gemini-3.8-flash-search": "3.8 Flash（智能搜索）",
    "gemini-3.5-flash-lite-search": "3.5 Flash-Lite（快速+搜索）",
    "gemini-3.6-flash-search": "3.6 Flash（智能搜索）",
    "gemini-3.1-pro-preview-search": "3.1 Pro Preview（深度研究+搜索）",
    "gemini-decision-1": "Decision-1（推理决策）",
    "gemini-pro-latest": "Gemini Pro Latest",
    "gemini-flash-latest": "Gemini Flash Latest",
}

# 属于 Plus / 付费版或工作台专有模型 (免费版隐藏，Plus 账号可见，底层 API 始终保留支持)
PLUS_EXCLUSIVE_MODELS = {
    "research",
    "gpt-5-6",
    "gpt-6-thinking",
    "gpt-5-6-thinking",
    "gpt-5.6-luna-wm",
    "gpt-5.6-terra-wm",
    "gpt-6-sol-wm",
    "gpt-6-luna-wm",
    "gpt-6-astra-wm",
    "gpt-6.1-sol-wm",
    "gpt-6.1-terra-wm",
    "gpt-5.6-sol-wm",
}

# 内部灰度、超微缩、未对普通用户公开的调试/过渡模型 (在 IDE 列表中不展示，避免列表混乱)
INTERNAL_HIDDEN_MODELS = {
    "gpt-6-mini",
    "gpt-6-t-mini-mini",
    "gpt-5-6-mini",
    "gpt-5-6-t-mini",
    "gpt-5-6-t-mini-mini",
    "gpt-5-6-instant",
}


def default_config_path() -> str:
    home = os.path.expanduser("~")
    return os.path.join(home, ".config", "opencode", "opencode.json")


def _display_name(model: Dict[str, Any]) -> str:
    mid = str(model.get("id") or "").strip()
    if mid in MODEL_DISPLAY_NAMES:
        return MODEL_DISPLAY_NAMES[mid]

    desc = str(model.get("description") or "").strip()
    if "]" in desc:
        desc = desc.split("]", 1)[1].strip()
    desc = desc.replace("（当前账号未开通）", "").strip()
    if desc and len(desc) <= 40:
        cleaned = desc.split("。")[0].strip()
        if cleaned and "reasoning" not in cleaned.lower():
            return cleaned
    return mid


def _limits(model_id: str) -> Dict[str, int]:
    if model_id.startswith(("gemini", "gemma")):
        output = 32768 if any(token in model_id for token in ("argon", "carbon")) else 65536
        return {"context": 1048576, "output": output}
    return {"context": 128000, "output": 32768}


def _skip_model(model: Dict[str, Any], plan: str = "free") -> bool:
    """语音、绘图、内部测试及当前账号级别不展示的型号不放进编程对话列表。
    底层 API 依然保留所有模型的调用能力。
    """
    mid = str(model.get("id") or "").strip()
    if not mid:
        return True

    # 1. 过滤内部灰度 gate 占位符或内部微缩调试模型
    if "reserved_gate" in mid or mid in INTERNAL_HIDDEN_MODELS:
        return True

    # 2. 语音、绘图、同声传译等非文本对话模型不放入编程对话选择器
    if mid.startswith(("speech-", "tts-")) or mid.endswith(("-tts", "-translate", "-translate-preview")):
        return True
    if mid in {"gpt-image-2", "codex-gpt-image-2", "gemini-image", "gemini-video", "gemini-music"}:
        return True

    # 3. 方案权限区分：免费版不展示 Plus 专有模型，但底层绝不剥夺，Plus 账号则正常展示
    is_free = str(plan or "free").strip().lower() in ("free", "none", "")
    if is_free and mid in PLUS_EXCLUSIVE_MODELS:
        return True

    desc = str(model.get("description") or "")
    if "没有这个 slug" in desc or "未开通" in desc:
        return True
    return False


THINKING_MODEL_PREFIXES = (
    "gemini-4-hydrogen",
    "gemini-4-argon",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.1-pro",
    "gemini-decision-1",
    "gpt-6-t-mini",
    "gpt-6-thinking",
    "gpt-5-6",
)


def _supports_reasoning(model_id: str) -> bool:
    if model_id == "gpt-5-6-instant":
        return False
    return model_id.startswith(THINKING_MODEL_PREFIXES)


def models_for_opencode(raw_models: List[Dict[str, Any]], plan: str = "free") -> Dict[str, Dict[str, Any]]:
    catalog: Dict[str, Dict[str, Any]] = {}
    for item in raw_models:
        if _skip_model(item, plan=plan):
            continue
        mid = str(item["id"]).strip()
        if mid in catalog:
            continue
        entry: Dict[str, Any] = {
            "name": _display_name(item),
            "limit": _limits(mid),
        }
        if _supports_reasoning(mid):
            entry["reasoning"] = True
            entry["variants"] = {
                "low": {"reasoningEffort": "low"},
                "medium": {"reasoningEffort": "medium"},
                "high": {"reasoningEffort": "high"},
            }
        catalog[mid] = entry
    return catalog


def build_provider(
    raw_models: List[Dict[str, Any]],
    base_url: str = DEFAULT_BASE_URL,
    plan: str = "free",
) -> Dict[str, Any]:
    return {
        "npm": "@ai-sdk/openai-compatible",
        "name": PROVIDER_NAME,
        "options": {
            "baseURL": base_url.rstrip("/"),
            "apiKey": DEFAULT_API_KEY,
        },
        "models": models_for_opencode(raw_models, plan=plan),
    }


def merge_config(
    config: Dict[str, Any],
    raw_models: List[Dict[str, Any]],
    base_url: str = DEFAULT_BASE_URL,
    set_default: bool = False,
    default_model: str = "gemini-3.5-flash-lite",
    plan: str = "free",
) -> Dict[str, Any]:
    provider = build_provider(raw_models, base_url=base_url, plan=plan)
    providers = config.get("provider")
    if not isinstance(providers, dict):
        providers = {}
    providers[PROVIDER_ID] = provider
    config["provider"] = providers
    config.setdefault("$schema", "https://opencode.ai/config.json")
    if set_default and default_model in provider["models"]:
        config["model"] = f"{PROVIDER_ID}/{default_model}"
    return config


def export_to_file(
    raw_models: List[Dict[str, Any]],
    path: Optional[str] = None,
    base_url: str = DEFAULT_BASE_URL,
    set_default: bool = False,
    plan: str = "free",
) -> Dict[str, Any]:
    target = path or default_config_path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    config: Dict[str, Any] = {}
    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            config = loaded
    merge_config(config, raw_models, base_url=base_url, set_default=set_default, plan=plan)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    models = config["provider"][PROVIDER_ID]["models"]
    return {
        "path": target,
        "provider": PROVIDER_ID,
        "base_url": base_url.rstrip("/"),
        "count": len(models),
        "models": list(models.keys()),
        "example": f"opencode run -m {PROVIDER_ID}/gemini-3.5-flash-lite \"回复 pong\"",
    }
