# -*- coding: utf-8 -*-
"""Persistent per-Web-API enable/disable switches and domain/daemon lifecycle helpers."""

from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_SWITCHES_PATH = ROOT_DIR / "runtime_state" / "web_api_switches.json"
AISTUDIO_REMOTE_SYNC_CONFIG = ROOT_DIR / "runtime_state" / "aistudio_remote_sync.json"
AISTUDIO_REMOTE_SYNC_PID = ROOT_DIR / "runtime_state" / "aistudio_remote_sync.pid"


WEB_API_SPECS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "gemini",
        "name": "Google Gemini",
        "short_name": "Gemini",
        "category": "AI 对话",
        "description": "Gemini 网页转 API（4 账号池与凭证同步）",
        "domains": ("gemini.google.com", "google.com"),
        "has_daemon": True,
        "daemon_label": "gemini-web2api (端口 18083)",
    },
    {
        "id": "aistudio",
        "name": "Google AI Studio",
        "short_name": "AI Studio",
        "category": "AI 对话",
        "description": "AI Studio 逆向服务与远端 SSH 同步",
        "domains": ("aistudio.google.com", "google.com"),
        "has_daemon": True,
        "daemon_label": "aistudio2api (端口 2048) + 远端同步",
    },
    {
        "id": "chatgpt",
        "name": "ChatGPT",
        "short_name": "ChatGPT",
        "category": "AI 对话",
        "description": "ChatGPT 逆向引擎与网页同源桥接",
        "domains": ("chatgpt.com", "openai.com"),
        "has_daemon": True,
        "daemon_label": "chatgpt2api (端口 18084)",
    },
    {
        "id": "suno",
        "name": "Suno AI",
        "short_name": "Suno",
        "category": "音频生成",
        "description": "Suno 网页音乐生成与 Clerk 凭证同步",
        "domains": ("suno.com", "clerk.suno.com", "auth.suno.com"),
        "has_daemon": False,
        "daemon_label": "",
    },
    {
        "id": "minimax",
        "name": "MiniMax 海螺",
        "short_name": "MiniMax",
        "category": "语音合成",
        "description": "MiniMax 海螺语音 TTS 与 Token 提取",
        "domains": ("minimax.io", "minimaxi.com", "hailuo.ai", "hailuoai.com"),
        "has_daemon": False,
        "daemon_label": "",
    },
    {
        "id": "baidupan",
        "name": "百度网盘",
        "short_name": "百度网盘",
        "category": "生态工具",
        "description": "百度网盘账号、空间配额与文件列表 API",
        "domains": ("pan.baidu.com", "baidu.com"),
        "has_daemon": False,
        "daemon_label": "",
    },
    {
        "id": "bilibili",
        "name": "哔哩哔哩",
        "short_name": "哔哩哔哩",
        "category": "生态工具",
        "description": "B站用户信息、大会员状态与视频流解析 API",
        "domains": ("bilibili.com",),
        "has_daemon": False,
        "daemon_label": "",
    },
    {
        "id": "udio",
        "name": "Udio",
        "short_name": "Udio",
        "category": "音频生成",
        "description": "Udio 网页音乐生成与 Supabase 凭证同步",
        "domains": ("udio.com",),
        "has_daemon": False,
        "daemon_label": "",
    },
)

WEB_API_SPEC_MAP: Dict[str, Dict[str, Any]] = {spec["id"]: spec for spec in WEB_API_SPECS}

SERVICE_ALIASES: Dict[str, str] = {
    "gemini": "gemini",
    "google": "gemini",
    "aistudio": "aistudio",
    "ai_studio": "aistudio",
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


class ServiceDisabledError(RuntimeError):
    """Raised when a disabled Web API is invoked or attempts to fetch/refresh cookies."""

    def __init__(self, service_id: str, message: Optional[str] = None):
        canonical = normalize_service_id(service_id)
        spec = WEB_API_SPEC_MAP.get(canonical, {})
        self.service_id = canonical
        self.service_name = str(spec.get("name") or canonical)
        default_msg = f"{self.service_name} 网页 API 已在管理控制台关闭，已停止获取/刷新 Cookie 及关联后台程序。"
        super().__init__(message or default_msg)


def normalize_service_id(service_id: str) -> str:
    """Normalize a platform/service identifier or alias to canonical Web API id."""
    cleaned = str(service_id or "").strip().lower()
    canonical = SERVICE_ALIASES.get(cleaned)
    if not canonical or canonical not in WEB_API_SPEC_MAP:
        raise ValueError(f"Unsupported web API service: {service_id}")
    return canonical


def _extract_hostname(domain_or_url: str) -> str:
    raw = str(domain_or_url or "").strip().lower()
    if not raw:
        return ""
    if "://" in raw:
        parsed = urllib.parse.urlsplit(raw)
        host = parsed.hostname or ""
    else:
        host = raw.split("/", 1)[0].split(":", 1)[0]
    return host.strip().lstrip(".")


def _host_matches_domain(host: str, domain: str) -> bool:
    if not host or not domain:
        return False
    return host == domain or host.endswith("." + domain)


class WebApiSwitchStore:
    """Thread-safe persistent store for per-Web-API enable/disable switches."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_SWITCHES_PATH
        self._lock = threading.RLock()
        self._cached_mtime: Optional[float] = None
        self._cached_states: Dict[str, Dict[str, Any]] = self._default_states()

    @staticmethod
    def _default_states() -> Dict[str, Dict[str, Any]]:
        return {
            spec["id"]: {"enabled": True, "updated_at": 0}
            for spec in WEB_API_SPECS
        }

    def _load_locked(self, force: bool = False) -> Dict[str, Dict[str, Any]]:
        try:
            stat = self.config_path.stat()
            mtime: Optional[float] = stat.st_mtime
        except FileNotFoundError:
            mtime = None
        except OSError:
            mtime = None

        if not force and mtime == self._cached_mtime:
            return self._cached_states

        states = self._default_states()
        if mtime is not None:
            try:
                raw = json.loads(self.config_path.read_text(encoding="utf-8"))
                raw_services = raw.get("services") if isinstance(raw, dict) else None
                if isinstance(raw_services, dict):
                    for sid, entry in raw_services.items():
                        try:
                            canonical = normalize_service_id(sid)
                        except ValueError:
                            continue
                        if isinstance(entry, dict):
                            states[canonical] = {
                                "enabled": bool(entry.get("enabled", True)),
                                "updated_at": int(entry.get("updated_at") or 0),
                            }
                        elif isinstance(entry, bool):
                            states[canonical] = {"enabled": entry, "updated_at": 0}
            except Exception:
                pass

        self._cached_states = states
        self._cached_mtime = mtime
        return self._cached_states

    def _save_locked(self, states: Dict[str, Dict[str, Any]]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        now = int(time.time())
        payload = {
            "services": {
                spec["id"]: {
                    "enabled": bool(states[spec["id"]]["enabled"]),
                    "updated_at": int(states[spec["id"]].get("updated_at") or 0),
                }
                for spec in WEB_API_SPECS
            },
            "updated_at": now,
        }
        tmp_path = self.config_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, self.config_path)
        try:
            self._cached_mtime = self.config_path.stat().st_mtime
        except OSError:
            self._cached_mtime = None
        self._cached_states = states

    def get_states(self) -> Dict[str, bool]:
        """Return a mapping of canonical service_id -> enabled boolean."""
        with self._lock:
            states = self._load_locked()
            return {sid: bool(entry["enabled"]) for sid, entry in states.items()}

    def is_enabled(self, service_id: str) -> bool:
        """Check whether a given Web API service (or alias) is currently enabled."""
        canonical = normalize_service_id(service_id)
        with self._lock:
            states = self._load_locked()
            return bool(states[canonical]["enabled"])

    def require_enabled(self, service_id: str) -> None:
        """Raise ServiceDisabledError if the target Web API is currently disabled."""
        canonical = normalize_service_id(service_id)
        if not self.is_enabled(canonical):
            raise ServiceDisabledError(canonical)

    def set_enabled(self, service_id: str, enabled: bool) -> Dict[str, Any]:
        """Persist the enabled state for a Web API and return its updated record."""
        canonical = normalize_service_id(service_id)
        with self._lock:
            states = self._load_locked(force=True)
            now = int(time.time())
            states[canonical] = {"enabled": bool(enabled), "updated_at": now}
            self._save_locked(states)
            spec = WEB_API_SPEC_MAP[canonical]
            return {
                "id": canonical,
                "name": spec["name"],
                "enabled": bool(enabled),
                "updated_at": now,
            }

    def toggle(self, service_id: str, enabled: Optional[bool] = None) -> Dict[str, Any]:
        """Flip or explicitly set the enabled state for a Web API."""
        canonical = normalize_service_id(service_id)
        with self._lock:
            current = self.is_enabled(canonical)
            target = (not current) if enabled is None else bool(enabled)
            return self.set_enabled(canonical, target)

    def list_specs(self) -> List[Dict[str, Any]]:
        """Return all Web API specs combined with persisted switch states."""
        with self._lock:
            states = self._load_locked()
            items: List[Dict[str, Any]] = []
            for spec in WEB_API_SPECS:
                sid = spec["id"]
                entry = states.get(sid, {"enabled": True, "updated_at": 0})
                items.append({
                    "id": sid,
                    "name": spec["name"],
                    "short_name": spec["short_name"],
                    "category": spec["category"],
                    "description": spec["description"],
                    "domains": list(spec["domains"]),
                    "has_daemon": bool(spec["has_daemon"]),
                    "daemon_label": spec["daemon_label"],
                    "enabled": bool(entry.get("enabled", True)),
                    "updated_at": int(entry.get("updated_at") or 0),
                })
            return items

    def is_domain_allowed(self, domain_or_url: str) -> Tuple[bool, List[str]]:
        """Check whether cookie retrieval for domain_or_url is permitted.

        Returns (allowed, disabled_matching_service_ids).
        Domains shared by multiple services (e.g. google.com) stay allowed as long as at
        least one owning Web API remains enabled.
        """
        host = _extract_hostname(domain_or_url)
        if not host:
            return True, []

        with self._lock:
            states = self._load_locked()

        matching: List[Tuple[int, str, bool]] = []
        for spec in WEB_API_SPECS:
            matched_len = max(
                (len(dom) for dom in spec["domains"] if _host_matches_domain(host, dom)),
                default=0,
            )
            if matched_len > 0:
                sid = spec["id"]
                matching.append((matched_len, sid, bool(states.get(sid, {}).get("enabled", True))))

        if not matching:
            return True, []

        max_len = max(item[0] for item in matching)
        specific = [item for item in matching if item[0] == max_len]
        if any(enabled for _l, _sid, enabled in specific):
            return True, []
        return False, [sid for _l, sid, _enabled in specific]


switch_store = WebApiSwitchStore()


def is_service_enabled(service_id: str) -> bool:
    return switch_store.is_enabled(service_id)


def require_service_enabled(service_id: str) -> None:
    switch_store.require_enabled(service_id)


def is_domain_cookie_allowed(domain_or_url: str) -> Tuple[bool, List[str]]:
    return switch_store.is_domain_allowed(domain_or_url)


# ---------------------------------------------------------------------------
# AI Studio remote sync daemon lifecycle helpers
# ---------------------------------------------------------------------------

_REMOTE_SYNC_CACHE_TTL = 20.0
_remote_sync_cache_lock = threading.RLock()
_remote_sync_cached_pids: Optional[List[int]] = None
_remote_sync_cached_at: float = 0.0
_remote_sync_refreshing: bool = False


def is_aistudio_remote_sync_configured() -> bool:
    try:
        data = json.loads(AISTUDIO_REMOTE_SYNC_CONFIG.read_text(encoding="utf-8"))
        return bool(isinstance(data, dict) and data.get("enabled"))
    except Exception:
        return False


def _win32_pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        open_process.restype = ctypes.c_void_p
        get_exit_code = kernel32.GetExitCodeProcess
        get_exit_code.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        get_exit_code.restype = ctypes.c_int
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int

        handle = open_process(0x1000, 0, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            exit_code = ctypes.c_uint32(0)
            if not get_exit_code(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == 259  # STILL_ACTIVE
        finally:
            close_handle(handle)
    except Exception:
        return False


def _pid_is_alive_sync_process(pid: int) -> bool:
    if pid <= 0 or pid == os.getpid():
        return False
    if sys.platform == "win32":
        if not _win32_pid_exists(pid):
            return False
        try:
            ps_cmd = (
                f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" -ErrorAction SilentlyContinue; "
                "if ($p -and $p.CommandLine -like '*aistudio_remote_sync.py*') { 'YES' }"
            )
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                text=True,
                errors="replace",
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return "YES" in out
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _scan_aistudio_remote_sync_pids(scan_all: bool = True) -> List[int]:
    """Perform a live OS process scan for running aistudio_remote_sync.py workers."""
    pids: List[int] = []
    if AISTUDIO_REMOTE_SYNC_PID.is_file():
        try:
            pid = int(AISTUDIO_REMOTE_SYNC_PID.read_text(encoding="utf-8").strip())
            if _pid_is_alive_sync_process(pid):
                pids.append(pid)
        except Exception:
            pass

    if sys.platform == "win32" and (scan_all or not pids):
        try:
            ps_cmd = (
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.CommandLine -like '*aistudio_remote_sync.py*' } | "
                "Select-Object -ExpandProperty ProcessId"
            )
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                text=True,
                errors="replace",
                timeout=6,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in out.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    pid = int(line)
                except ValueError:
                    continue
                if pid > 0 and pid != os.getpid() and pid not in pids:
                    pids.append(pid)
        except Exception:
            pass
    return pids


def find_aistudio_remote_sync_pids(force: bool = False) -> List[int]:
    """Locate any running aistudio_remote_sync.py worker PIDs (cached for 20s unless force=True)."""
    global _remote_sync_cached_pids, _remote_sync_cached_at
    if not force:
        with _remote_sync_cache_lock:
            if _remote_sync_cached_pids is not None and (time.time() - _remote_sync_cached_at) < _REMOTE_SYNC_CACHE_TTL:
                return list(_remote_sync_cached_pids)

    pids = _scan_aistudio_remote_sync_pids(scan_all=True)
    with _remote_sync_cache_lock:
        _remote_sync_cached_pids = list(pids)
        _remote_sync_cached_at = time.time()
    return pids


def _trigger_remote_sync_scan_async() -> None:
    """Refresh remote sync PID cache in a background daemon thread without blocking callers."""
    global _remote_sync_refreshing
    with _remote_sync_cache_lock:
        if _remote_sync_refreshing:
            return
        _remote_sync_refreshing = True

    def _worker():
        global _remote_sync_refreshing
        try:
            find_aistudio_remote_sync_pids(force=True)
        except Exception:
            pass
        finally:
            with _remote_sync_cache_lock:
                _remote_sync_refreshing = False

    threading.Thread(target=_worker, daemon=True, name="RemoteSyncPidScan").start()


def is_aistudio_remote_sync_running() -> bool:
    """Return cached running state for aistudio_remote_sync.py and trigger background refresh when stale."""
    now = time.time()
    need_refresh = False
    cached_result: Optional[bool] = None
    with _remote_sync_cache_lock:
        if _remote_sync_cached_pids is not None:
            cached_result = bool(_remote_sync_cached_pids)
            if (now - _remote_sync_cached_at) >= _REMOTE_SYNC_CACHE_TTL:
                need_refresh = True

    if cached_result is not None:
        if need_refresh:
            _trigger_remote_sync_scan_async()
        return cached_result

    _trigger_remote_sync_scan_async()
    if AISTUDIO_REMOTE_SYNC_PID.is_file():
        try:
            pid = int(AISTUDIO_REMOTE_SYNC_PID.read_text(encoding="utf-8").strip())
            if pid > 0 and pid != os.getpid():
                if sys.platform == "win32":
                    return _win32_pid_exists(pid)
                os.kill(pid, 0)
                return True
        except Exception:
            pass
    return False


def start_aistudio_remote_sync() -> bool:
    """Start the optional AI Studio remote SSH sync worker if enabled in both switches and config."""
    global _remote_sync_cached_pids, _remote_sync_cached_at
    if not is_service_enabled("aistudio") or not is_aistudio_remote_sync_configured():
        return False
    if find_aistudio_remote_sync_pids(force=True):
        return True
    script_path = ROOT_DIR / "aistudio_remote_sync.py"
    if not script_path.is_file():
        return False
    executable = sys.executable
    if sys.platform == "win32":
        candidate = os.path.join(os.path.dirname(executable), "pythonw.exe")
        if os.path.isfile(candidate):
            executable = candidate
    try:
        proc = subprocess.Popen(
            [executable, str(script_path)],
            cwd=str(ROOT_DIR),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        with _remote_sync_cache_lock:
            _remote_sync_cached_pids = [proc.pid] if getattr(proc, "pid", None) else []
            _remote_sync_cached_at = time.time()
        return True
    except Exception:
        return False


def stop_aistudio_remote_sync() -> int:
    """Terminate any running aistudio_remote_sync.py worker processes."""
    global _remote_sync_cached_pids, _remote_sync_cached_at
    pids = find_aistudio_remote_sync_pids(force=True)
    stopped = 0
    for pid in pids:
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            else:
                os.kill(pid, 15)
            stopped += 1
        except Exception:
            pass
    try:
        if AISTUDIO_REMOTE_SYNC_PID.is_file():
            AISTUDIO_REMOTE_SYNC_PID.unlink()
    except Exception:
        pass
    with _remote_sync_cache_lock:
        _remote_sync_cached_pids = []
        _remote_sync_cached_at = time.time()
    return stopped


# ---------------------------------------------------------------------------
# Google anti-risk sync frequency & one-click mute settings
# ---------------------------------------------------------------------------

GOOGLE_SYNC_SETTINGS_PATH = ROOT_DIR / "runtime_state" / "google_sync_settings.json"
_google_sync_lock = threading.RLock()

_DEFAULT_GOOGLE_SYNC_SETTINGS: Dict[str, Any] = {
    "auto_sync_enabled": True,
    "usage_sync_interval_sec": 1800,
    "cookie_sync_interval_sec": 1800,
    "allow_auto_fetch_tab": False,
}


def get_google_sync_settings() -> Dict[str, Any]:
    with _google_sync_lock:
        data = dict(_DEFAULT_GOOGLE_SYNC_SETTINGS)
        try:
            if GOOGLE_SYNC_SETTINGS_PATH.is_file():
                raw = json.loads(GOOGLE_SYNC_SETTINGS_PATH.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    if "auto_sync_enabled" in raw:
                        data["auto_sync_enabled"] = bool(raw["auto_sync_enabled"])
                    if "usage_sync_interval_sec" in raw:
                        data["usage_sync_interval_sec"] = max(0, int(raw["usage_sync_interval_sec"]))
                    if "cookie_sync_interval_sec" in raw:
                        data["cookie_sync_interval_sec"] = max(0, int(raw["cookie_sync_interval_sec"]))
                    if "allow_auto_fetch_tab" in raw:
                        data["allow_auto_fetch_tab"] = bool(raw["allow_auto_fetch_tab"])
        except Exception:
            pass
        return data


def update_google_sync_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    with _google_sync_lock:
        current = get_google_sync_settings()
        if "auto_sync_enabled" in patch and patch["auto_sync_enabled"] is not None:
            current["auto_sync_enabled"] = bool(patch["auto_sync_enabled"])
        if "usage_sync_interval_sec" in patch and patch["usage_sync_interval_sec"] is not None:
            current["usage_sync_interval_sec"] = max(0, min(86400, int(patch["usage_sync_interval_sec"])))
        if "cookie_sync_interval_sec" in patch and patch["cookie_sync_interval_sec"] is not None:
            current["cookie_sync_interval_sec"] = max(0, min(86400, int(patch["cookie_sync_interval_sec"])))
        if "allow_auto_fetch_tab" in patch and patch["allow_auto_fetch_tab"] is not None:
            current["allow_auto_fetch_tab"] = bool(patch["allow_auto_fetch_tab"])
        GOOGLE_SYNC_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOOGLE_SYNC_SETTINGS_PATH.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return current
