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


def default_config_path() -> str:
    home = os.path.expanduser("~")
    return os.path.join(home, ".config", "opencode", "opencode.json")


def _display_name(model: Dict[str, Any]) -> str:
    mid = str(model.get("id") or "").strip()
    desc = str(model.get("description") or "").strip()
    if "]" in desc:
        desc = desc.split("]", 1)[1].strip()
    desc = desc.replace("（当前账号未开通）", "").strip()
    if desc and len(desc) <= 40 and "。" not in desc and "reasoning" not in desc.lower():
        return desc
    return mid


def _limits(model_id: str) -> Dict[str, int]:
    if model_id.startswith(("gemini", "gemma")):
        output = 32768 if any(token in model_id for token in ("argon", "carbon")) else 65536
        return {"context": 1048576, "output": output}
    return {"context": 128000, "output": 32768}


def _skip_model(model: Dict[str, Any]) -> bool:
    """语音、绘图和当前账号用不了的型号不放进编程对话列表。"""
    mid = str(model.get("id") or "").strip()
    if not mid:
        return True
    desc = str(model.get("description") or "")
    if mid.startswith(("speech-", "tts-")):
        return True
    if mid in {"gpt-image-2", "codex-gpt-image-2", "gemini-image", "gemini-video", "gemini-music"}:
        return True
    if "没有这个 slug" in desc or "未开通" in desc:
        return True
    return False


def models_for_opencode(raw_models: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    catalog: Dict[str, Dict[str, Any]] = {}
    for item in raw_models:
        if _skip_model(item):
            continue
        mid = str(item["id"]).strip()
        if mid in catalog:
            continue
        catalog[mid] = {
            "name": _display_name(item),
            "limit": _limits(mid),
        }
    return catalog


def build_provider(raw_models: List[Dict[str, Any]], base_url: str = DEFAULT_BASE_URL) -> Dict[str, Any]:
    return {
        "npm": "@ai-sdk/openai-compatible",
        "name": PROVIDER_NAME,
        "options": {
            "baseURL": base_url.rstrip("/"),
            "apiKey": DEFAULT_API_KEY,
        },
        "models": models_for_opencode(raw_models),
    }


def merge_config(
    config: Dict[str, Any],
    raw_models: List[Dict[str, Any]],
    base_url: str = DEFAULT_BASE_URL,
    set_default: bool = False,
    default_model: str = "gemini-3.5-flash-lite",
) -> Dict[str, Any]:
    provider = build_provider(raw_models, base_url=base_url)
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
) -> Dict[str, Any]:
    target = path or default_config_path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    config: Dict[str, Any] = {}
    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            config = loaded
    merge_config(config, raw_models, base_url=base_url, set_default=set_default)
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
