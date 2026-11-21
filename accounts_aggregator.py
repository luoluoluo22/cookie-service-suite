# -*- coding: utf-8 -*-
"""Unified multi-platform account aggregation and refresh helpers for Cookie Service Suite."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, wait
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from web_api_switches import is_service_enabled


PLATFORMS_ORDER: Tuple[str, ...] = (
    "gemini",
    "chatgpt",
    "suno",
    "minimax",
    "baidupan",
    "bilibili",
    "udio",
)

PLATFORM_META: Dict[str, Dict[str, str]] = {
    "gemini": {
        "platform": "gemini",
        "platform_name": "Google Gemini",
        "login_url": "https://gemini.google.com/",
        "login_status_id": "gemini",
    },
    "chatgpt": {
        "platform": "chatgpt",
        "platform_name": "ChatGPT",
        "login_url": "https://chatgpt.com/",
        "login_status_id": "chatgpt",
    },
    "suno": {
        "platform": "suno",
        "platform_name": "Suno",
        "login_url": "https://suno.com/",
        "login_status_id": "suno",
    },
    "minimax": {
        "platform": "minimax",
        "platform_name": "MiniMax 海螺",
        "login_url": "https://www.minimax.io/audio",
        "login_status_id": "minimax",
    },
    "baidupan": {
        "platform": "baidupan",
        "platform_name": "百度网盘",
        "login_url": "https://pan.baidu.com/",
        "login_status_id": "baidu",
    },
    "bilibili": {
        "platform": "bilibili",
        "platform_name": "哔哩哔哩",
        "login_url": "https://www.bilibili.com/",
        "login_status_id": "bilibili",
    },
    "udio": {
        "platform": "udio",
        "platform_name": "Udio",
        "login_url": "https://www.udio.com/",
        "login_status_id": "udio",
    },
}

PLATFORM_ALIASES: Dict[str, str] = {
    "google": "gemini",
    "gemini": "gemini",
    "chatgpt": "chatgpt",
    "gpt": "chatgpt",
    "openai": "chatgpt",
    "suno": "suno",
    "minimax": "minimax",
    "hailuo": "minimax",
    "baidupan": "baidupan",
    "baidu": "baidupan",
    "baidu_pan": "baidupan",
    "bilibili": "bilibili",
    "bili": "bilibili",
    "udio": "udio",
}

_FREE_TIER_VALUES = {"", "FREE", "免费", "免费版", "普通用户", "NONE", "UNKNOWN"}
_ACTIVE_STATUS_VALUES = {"enabled", "ready", "active", "ok", "online", "connected", "normal"}


def normalize_platform(platform: Optional[str]) -> Optional[str]:
    """Normalize a platform query string to canonical platform id, or None for all."""
    if platform is None:
        return None
    cleaned = str(platform).strip().lower()
    if not cleaned or cleaned == "all":
        return None
    canonical = PLATFORM_ALIASES.get(cleaned)
    if not canonical:
        raise ValueError(f"Unsupported platform: {platform}")
    return canonical


def _infer_is_member(raw: Dict[str, Any], plan_tier: str, membership_label: str) -> bool:
    if raw.get("is_member") is not None:
        return bool(raw.get("is_member"))
    tier_norm = (plan_tier or "").strip().upper()
    if tier_norm and tier_norm not in _FREE_TIER_VALUES:
        return True
    label_norm = (membership_label or "").strip().upper()
    if label_norm and label_norm not in _FREE_TIER_VALUES:
        return True
    return False


def _gemini_membership_label(plan_tier: str, usage_source: str) -> str:
    tier = (plan_tier or "").strip().upper()
    mapping = {
        "ULTRA": "Google AI Ultra",
        "PRO": "Google AI Pro",
        "PLUS": "Google AI Plus",
        "FREE": "免费版",
    }
    if tier in mapping:
        return mapping[tier]
    if tier:
        return f"Google {tier}"
    return "免费版" if usage_source == "official" else ""


def _gemini_quota_summary(raw: Dict[str, Any]) -> str:
    if raw.get("usage_source") == "official" and raw.get("real_5h_pct") is not None:
        p5 = raw.get("real_5h_pct")
        pw = raw.get("real_weekly_pct")
        if pw is not None:
            return f"5h已用 {p5}% · 周已用 {pw}%"
        return f"5h已用 {p5}%"
    u5 = raw.get("quota_5h_used", 0)
    l5 = raw.get("quota_5h_limit", 50)
    uw = raw.get("quota_weekly_used", 0)
    lw = raw.get("quota_weekly_limit", 500)
    return f"5h {u5}/{l5} · 周 {uw}/{lw}"


def normalize_account_entry(raw: Dict[str, Any], platform: str, idx: int = 0) -> Dict[str, Any]:
    """Normalize a single account dict from any platform service into the unified schema."""
    meta = PLATFORM_META[platform]
    raw_id = raw.get("raw_id")
    if raw_id is None:
        raw_id = raw.get("id")
    if raw_id is None or raw_id == "":
        raw_id = idx + 1

    raw_id_str = str(raw_id)
    if raw_id_str.startswith(f"{platform}:"):
        uid = raw_id_str
        raw_id_val: Any = raw.get("raw_id", raw_id_str.split(":", 1)[1])
    else:
        uid = f"{platform}:{raw_id_str}"
        raw_id_val = raw_id

    plan_tier = str(raw.get("plan_tier") or raw.get("membership") or "").strip()
    membership_label = str(raw.get("membership_label") or "").strip()
    if platform == "gemini" and not membership_label:
        membership_label = _gemini_membership_label(plan_tier, str(raw.get("usage_source") or ""))
    if not membership_label and plan_tier:
        membership_label = "免费版" if plan_tier.upper() in _FREE_TIER_VALUES else plan_tier

    is_member = _infer_is_member(raw, plan_tier, membership_label)

    quota_summary = str(raw.get("quota_summary") or "").strip()
    if platform == "gemini" and not quota_summary:
        quota_summary = _gemini_quota_summary(raw)

    status = str(raw.get("status") or "unknown").strip() or "unknown"
    visible = raw.get("visible")
    if visible is None:
        visible = status.lower() not in {"deleted", "hidden", "not_logged_in"}
    else:
        visible = bool(visible) and status.lower() != "deleted"

    updated_at = raw.get("updated_at") or raw.get("usage_fetched_at") or raw.get("last_used_at")
    try:
        updated_at_int = int(updated_at) if updated_at else int(time.time())
    except (TypeError, ValueError):
        updated_at_int = int(time.time())

    entry: Dict[str, Any] = {
        "platform": platform,
        "platform_name": str(raw.get("platform_name") or meta["platform_name"]),
        "id": uid,
        "raw_id": raw_id_val,
        "name": str(raw.get("name") or raw.get("label") or "").strip(),
        "email": str(raw.get("email") or "").strip(),
        "is_member": is_member,
        "plan_tier": plan_tier,
        "membership_label": membership_label,
        "quota_summary": quota_summary,
        "status": status,
        "visible": visible,
        "note": str(raw.get("note") or ""),
        "source": str(raw.get("source") or ("gemini_pool" if platform == "gemini" else platform)),
        "login_url": str(raw.get("login_url") or meta["login_url"]),
        "updated_at": updated_at_int,
        "details": raw.get("details") if isinstance(raw.get("details"), dict) else {},
    }

    if "membership" in raw:
        entry["membership"] = raw["membership"]
    if "quota" in raw:
        entry["quota"] = raw["quota"]

    if platform == "gemini":
        gemini_keys = (
            "auth_user",
            "label",
            "url_prefix",
            "last_used_at",
            "fail_count",
            "quota_5h_used",
            "quota_5h_limit",
            "quota_5h_remaining",
            "quota_5h_reset_str",
            "quota_weekly_used",
            "quota_weekly_limit",
            "quota_weekly_remaining",
            "quota_status",
            "quota_status_color",
            "usage_source",
            "real_5h_pct",
            "real_5h_pct_exact",
            "real_5h_reset_str",
            "real_5h_reset_epoch",
            "real_weekly_pct",
            "real_weekly_pct_exact",
            "real_weekly_reset_str",
            "real_weekly_reset_epoch",
            "usage_fetched_at",
            "quota_5h_pace",
            "quota_weekly_pace",
        )
        for key in gemini_keys:
            if key in raw:
                entry[key] = raw[key]

    return entry


def _coerce_account_list(result: Any) -> List[Dict[str, Any]]:
    if result is None:
        return []
    if isinstance(result, dict):
        if isinstance(result.get("accounts"), list):
            return [item for item in result["accounts"] if isinstance(item, dict)]
        return [result]
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    return []


def _get_service_accounts(service: Any, platform: str) -> List[Dict[str, Any]]:
    if service is None:
        return []
    if platform == "gemini":
        return _coerce_account_list(service.list_accounts())
    if hasattr(service, "get_dashboard_accounts"):
        return _coerce_account_list(service.get_dashboard_accounts())
    if hasattr(service, "list_accounts"):
        return _coerce_account_list(service.list_accounts())
    return []


def _build_login_status_map(collect_login_status_fn: Optional[Callable[[], Dict[str, Any]]]) -> Dict[str, Optional[bool]]:
    if collect_login_status_fn is None:
        return {}
    try:
        data = collect_login_status_fn() or {}
        mapping: Dict[str, Optional[bool]] = {}
        for item in data.get("services") or []:
            if isinstance(item, dict) and item.get("id"):
                mapping[str(item["id"])] = item.get("logged_in")
        return mapping
    except Exception:
        return {}


def aggregate_accounts(
    services: Dict[str, Any],
    platform: Optional[str] = None,
    collect_login_status_fn: Optional[Callable[[], Dict[str, Any]]] = None,
    timeout_seconds: float = 12.0,
) -> Dict[str, Any]:
    """Collect and normalize accounts across all (or one) configured platforms."""
    target_platform = normalize_platform(platform)
    target_platforms = (target_platform,) if target_platform else PLATFORMS_ORDER
    enabled_map: Dict[str, bool] = {plat: is_service_enabled(plat) for plat in target_platforms}

    raw_by_platform: Dict[str, List[Dict[str, Any]]] = {p: [] for p in target_platforms}
    errors_by_platform: Dict[str, Optional[str]] = {p: None for p in target_platforms}

    enabled_platforms = [plat for plat in target_platforms if enabled_map[plat]]
    login_map: Dict[str, Optional[bool]] = {}
    if enabled_platforms or collect_login_status_fn is not None:
        worker_count = min(len(enabled_platforms) + (1 if collect_login_status_fn is not None else 0), 8) or 1
        executor = ThreadPoolExecutor(max_workers=worker_count)
        try:
            login_fut = (
                executor.submit(_build_login_status_map, collect_login_status_fn)
                if collect_login_status_fn is not None
                else None
            )
            futures = {
                plat: executor.submit(_get_service_accounts, services.get(plat), plat)
                for plat in enabled_platforms
            }
            all_futs = list(futures.values()) + ([login_fut] if login_fut is not None else [])
            if all_futs:
                wait(all_futs, timeout=timeout_seconds)

            for plat, fut in futures.items():
                if not fut.done():
                    errors_by_platform[plat] = f"{PLATFORM_META[plat]['platform_name']} 读取账号超时"
                    continue
                try:
                    raw_by_platform[plat] = fut.result(timeout=0)
                except FuturesTimeoutError:
                    errors_by_platform[plat] = f"{PLATFORM_META[plat]['platform_name']} 读取账号超时"
                except Exception as exc:
                    errors_by_platform[plat] = str(exc)
            if login_fut is not None and login_fut.done():
                try:
                    login_map = login_fut.result(timeout=0)
                except Exception:
                    login_map = {}
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    all_accounts: List[Dict[str, Any]] = []
    platforms_summary: Dict[str, Dict[str, Any]] = {}
    included_platforms: List[str] = []

    for plat in target_platforms:
        meta = PLATFORM_META[plat]
        plat_enabled = enabled_map[plat]
        if not plat_enabled:
            if plat == "udio" and target_platform != "udio":
                continue
            included_platforms.append(plat)
            platforms_summary[plat] = {
                "platform": plat,
                "platform_name": meta["platform_name"],
                "login_url": meta["login_url"],
                "enabled": False,
                "logged_in": None,
                "account_count": 0,
                "total_count": 0,
                "member_count": 0,
                "error": None,
            }
            continue
        raw_list = raw_by_platform.get(plat) or []
        norm_list = [normalize_account_entry(item, plat, idx) for idx, item in enumerate(raw_list)]

        visible_active = [
            a for a in norm_list
            if a.get("visible") and a.get("status", "").lower() not in {"not_logged_in", "deleted"}
        ]
        active_list = [
            a for a in visible_active
            if a.get("status", "").lower() in _ACTIVE_STATUS_VALUES
        ]
        has_logged_in_account = any(
            a.get("status", "").lower() not in {"not_logged_in", "offline", "error", "disabled", "deleted"}
            for a in visible_active
        )
        hub_logged_in = login_map.get(meta["login_status_id"])
        if active_list or has_logged_in_account:
            logged_in: Optional[bool] = True
        elif any(a.get("status", "").lower() == "not_logged_in" for a in norm_list):
            logged_in = False
        elif plat == "minimax" and hub_logged_in is None:
            svc = services.get("minimax")
            logged_in = bool(getattr(svc, "token", None)) if svc is not None else None
        else:
            logged_in = hub_logged_in

        # Udio is optional: include when explicitly requested or when accounts/session/error exist
        if plat == "udio" and target_platform != "udio" and not norm_list and logged_in is not True and not errors_by_platform.get(plat):
            continue

        included_platforms.append(plat)
        all_accounts.extend(norm_list)
        platforms_summary[plat] = {
            "platform": plat,
            "platform_name": meta["platform_name"],
            "login_url": meta["login_url"],
            "enabled": True,
            "logged_in": logged_in,
            "account_count": len(visible_active),
            "total_count": len(norm_list),
            "member_count": sum(1 for a in visible_active if a.get("is_member")),
            "error": errors_by_platform.get(plat),
        }

    visible_total = sum(
        1 for a in all_accounts
        if a.get("visible") and a.get("status", "").lower() not in {"not_logged_in", "deleted"}
    )
    member_total = sum(
        1 for a in all_accounts
        if a.get("visible") and a.get("status", "").lower() not in {"not_logged_in", "deleted"} and a.get("is_member")
    )

    return {
        "total": len(all_accounts),
        "visible_total": visible_total,
        "member_total": member_total,
        "platforms_order": included_platforms,
        "platforms": platforms_summary,
        "accounts": all_accounts,
        "updated_at": int(time.time()),
    }


def _refresh_single_platform(service: Any, plat: str) -> Dict[str, Any]:
    if service is None:
        return {"ok": False, "message": f"{PLATFORM_META[plat]['platform_name']} 服务未启用", "error": "service_unavailable"}

    if plat == "gemini":
        res = service.refresh_and_sync_all()
        updated_ids = res.get("updated_account_ids", []) if isinstance(res, dict) else []
        return {"ok": True, "message": f"已刷新 {len(updated_ids)} 个 Gemini 账号", "error": None}

    if hasattr(service, "refresh_dashboard_accounts"):
        res = service.refresh_dashboard_accounts()
        if isinstance(res, dict):
            ok = bool(res.get("success", True))
            err = res.get("error")
            msg = res.get("message") or (err if not ok and err else f"已刷新 {PLATFORM_META[plat]['platform_name']}")
            return {"ok": ok, "message": msg, "error": err}
        if isinstance(res, list):
            msg = (
                f"已刷新 {PLATFORM_META[plat]['platform_name']}（{len(res)} 个账号）"
                if res
                else f"已检测 {PLATFORM_META[plat]['platform_name']}（未登录或无账号）"
            )
            return {"ok": True, "message": msg, "error": None}
        return {"ok": True, "message": f"已刷新 {PLATFORM_META[plat]['platform_name']}", "error": None}

    if plat == "chatgpt" and hasattr(service, "sync_token_from_browser"):
        res = service.sync_token_from_browser()
        msg = res.get("message") if isinstance(res, dict) else None
        return {"ok": True, "message": msg or "已从浏览器同步 ChatGPT 会话", "error": None}

    if plat == "minimax" and hasattr(service, "auto_refresh_auth"):
        res = service.auto_refresh_auth(force_visit=False, timeout=15)
        ok = bool(res.get("success", True)) if isinstance(res, dict) else True
        msg = (res.get("message") if isinstance(res, dict) else None) or "已刷新 MiniMax 登录态"
        return {"ok": ok, "message": msg, "error": None if ok else msg}

    if plat == "udio" and hasattr(service, "refresh_cookie_from_browser"):
        ok = bool(service.refresh_cookie_from_browser())
        return {
            "ok": ok,
            "message": "已刷新 Udio 凭证" if ok else "未检测到 Udio 浏览器 Cookie",
            "error": None if ok else "not_logged_in",
        }

    if hasattr(service, "refresh_auth"):
        res = service.refresh_auth()
        if isinstance(res, bool):
            return {
                "ok": res,
                "message": f"已刷新 {PLATFORM_META[plat]['platform_name']}" if res else "未检测到有效登录凭证",
                "error": None if res else "refresh_failed",
            }
        msg = (res.get("message") if isinstance(res, dict) else None) or f"已刷新 {PLATFORM_META[plat]['platform_name']}"
        return {"ok": True, "message": msg, "error": None}

    if hasattr(service, "get_dashboard_accounts"):
        service.get_dashboard_accounts()
        return {"ok": True, "message": f"已重新读取 {PLATFORM_META[plat]['platform_name']} 账号", "error": None}

    return {"ok": False, "message": "未实现刷新方法", "error": "not_implemented"}


def refresh_accounts(
    services: Dict[str, Any],
    platform: Optional[str] = None,
    collect_login_status_fn: Optional[Callable[[], Dict[str, Any]]] = None,
    timeout_seconds: float = 45.0,
) -> Dict[str, Any]:
    """Refresh one or all platforms and return per-platform results plus updated snapshot."""
    target_platform = normalize_platform(platform)
    target_platforms = (target_platform,) if target_platform else PLATFORMS_ORDER

    results: Dict[str, Dict[str, Any]] = {}
    enabled_platforms = []
    for plat in target_platforms:
        if not is_service_enabled(plat):
            results[plat] = {
                "ok": False,
                "enabled": False,
                "skipped": True,
                "message": f"{PLATFORM_META[plat]['platform_name']} 网页 API 已关闭，已跳过 Cookie 刷新",
                "error": "service_disabled",
            }
        else:
            enabled_platforms.append(plat)

    if enabled_platforms:
        executor = ThreadPoolExecutor(max_workers=min(len(enabled_platforms), 7) or 1)
        try:
            futures = {
                plat: executor.submit(_refresh_single_platform, services.get(plat), plat)
                for plat in enabled_platforms
            }
            for plat, fut in futures.items():
                try:
                    results[plat] = fut.result(timeout=timeout_seconds)
                except FuturesTimeoutError:
                    results[plat] = {
                        "ok": False,
                        "message": f"{PLATFORM_META[plat]['platform_name']} 刷新超时",
                        "error": "timeout",
                    }
                except Exception as exc:
                    results[plat] = {
                        "ok": False,
                        "message": str(exc),
                        "error": str(exc),
                    }
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    snapshot = aggregate_accounts(
        services=services,
        platform=target_platform,
        collect_login_status_fn=collect_login_status_fn,
    )
    ok_count = sum(1 for r in results.values() if r.get("ok"))
    return {
        "success": ok_count > 0 or len(results) == 0,
        "message": (
            results[target_platform]["message"]
            if target_platform and target_platform in results
            else f"已刷新 {ok_count}/{len(results)} 个平台账号状态"
        ),
        "refreshed_platforms": list(target_platforms),
        "results": results,
        **snapshot,
    }
