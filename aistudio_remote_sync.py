# -*- coding: utf-8 -*-
"""Synchronize verified Cookie Hub sessions to an AIStudio2API over SSH.

Cookie values stay in memory and cross the network only inside the SSH tunnel.
"""
import argparse
import ctypes
from contextlib import closing
import hashlib
import json
import logging
import logging.handlers
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

from aistudio_service import AIStudioService, _LOCAL_OPENER, _NoRedirectHandler
from web_api_switches import get_google_sync_settings, is_service_enabled, AISTUDIO_REMOTE_SYNC_PID

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "runtime_state" / "aistudio_remote_sync.json"
STATE = ROOT / "runtime_state" / "aistudio_remote_sync_state.json"
LOG = ROOT / "logs" / "aistudio_remote_sync.log"
GEMINI_DB = ROOT / "candidate_repos" / "gemini-web2api-go" / "gemini_pool.db"
EMAIL_PATTERN = re.compile(r'"oPEP7c":("(?:[^"\\]|\\.)*")')
AUTH_COOKIE_NAMES = frozenset({
    "SID", "HSID", "SSID", "APISID", "SAPISID", "LSID", "OSID",
    "__Secure-1PSID", "__Secure-3PSID", "__Secure-1PAPISID", "__Secure-3PAPISID",
    "__Secure-1PSIDTS", "__Secure-3PSIDTS", "__Secure-1PSIDCC", "__Secure-3PSIDCC",
})
logger = logging.getLogger("aistudio_remote_sync")


def blocked_accounts():
    # Fail closed if account policy cannot be read; never silently resume a disabled account.
    with closing(sqlite3.connect(f"file:{GEMINI_DB.as_posix()}?mode=ro", uri=True)) as conn:
        rows = conn.execute("SELECT label, note FROM accounts WHERE status IN ('disabled', 'deleted')").fetchall()
    return {email.casefold() for label, note in rows if '同一登录' not in (note or '')
            for email in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", f"{label or ''} {note or ''}")}


def json_request(url, *, payload=None, timeout=15):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"} if body else {})
    with _LOCAL_OPENER.open(request, timeout=timeout) as response:
        return json.load(response)


def cookie_fingerprint(cookies):
    values = [{k: c.get(k) for k in ("name", "value", "domain", "path", "secure", "httpOnly", "expirationDate", "sameSite")}
              for c in cookies if c.get("name") in AUTH_COOKIE_NAMES]
    if not values:
        raise ValueError("没有可同步的 Google 登录 Cookie")
    values.sort(key=lambda c: (str(c["domain"]), str(c["path"]), str(c["name"])))
    data = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def verify_identity(service, cookies, account_id, auth_user):
    if not isinstance(auth_user, int) or not 0 <= auth_user <= 9:
        return False
    url = f"https://aistudio.google.com/u/{auth_user}/prompts/new_chat"
    header = service._cookie_header_for_url(cookies, url)
    if not header:
        return False
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": service.proxy, "https": service.proxy}) if service.proxy
        else urllib.request.ProxyHandler({}), _NoRedirectHandler())
    request = urllib.request.Request(url, headers={"Cookie": header, "User-Agent": "Mozilla/5.0"})
    try:
        with opener.open(request, timeout=20) as response:
            body = response.read(8 * 1024 * 1024).decode("utf-8", "replace")
        match = EMAIL_PATTERN.search(body)
        if not match:
            logger.warning("账号 %s 身份预检未找到邮箱标记 (HTTP 200, body_len=%d)", account_id, len(body))
            return False
        found = json.loads(match.group(1))
        if str(found).casefold() != account_id.casefold():
            logger.warning("账号 %s 身份预检邮箱不匹配 (未记录实际邮箱)", account_id)
            return False
        return True
    except (OSError, ValueError, urllib.error.URLError) as exc:
        logger.warning("账号 %s 身份预检网络或解析失败: %s HTTP=%s", account_id, type(exc).__name__, getattr(exc, 'code', 'n/a'))
        return False


def load_local_accounts(service):
    root = Path(service.base_dir) / "auth"
    result = {}
    for directory in root.iterdir():
        if not directory.is_dir() or directory.name.startswith("."):
            continue
        try:
            data = json.loads((directory / "account.json").read_text(encoding="utf-8"))
            if data.get("enabled", True):
                result[directory.name.casefold()] = (directory.name, data.get("auth_user", 0))
        except (OSError, ValueError, TypeError):
            continue
    return result


def active_task_for(tasks, account):
    names = {str(account.get("id", "")).casefold(), str(account.get("label", "")).casefold()}
    return any(task.get("state") in ("pending", "running") and
               any(str(item.get("label", "")).casefold() in names for item in task.get("items", []))
               for task in tasks)


def choose_accounts(local, remote, tasks, fingerprints, fingerprint):
    selected = []
    for account in remote:
        key = str(account.get("id", "")).casefold()
        if (key not in local or not account.get("enabled") or account.get("active_requests", 0)
                or active_task_for(tasks, account)):
            continue
        if fingerprints.get(key) != fingerprint or account.get("state") == "auth_required":
            selected.append((account, local[key]))
    return selected


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, STATE)


def ssh_tunnel(config):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    destination = config["ssh_user"] + "@" + config["ssh_host"]
    command = ["ssh", "-N", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "ConnectTimeout=10", "-o", "ExitOnForwardFailure=yes",
               "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
               "-L", f"127.0.0.1:{port}:127.0.0.1:{int(config.get('remote_port', 2048))}", destination]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(30):
            if process.poll() is not None:
                raise RuntimeError("SSH 隧道无法连接")
            try:
                status = json_request(base + "/api/status", timeout=1)
                if process.poll() is not None:
                    raise RuntimeError("SSH 隧道未能建立")
                if not status.get("version"):
                    raise RuntimeError("远程服务身份无法确认")
                return process, base
            except (OSError, urllib.error.URLError):
                time.sleep(0.5)
        raise RuntimeError("SSH 隧道连接超时")
    except BaseException:
        process.terminate()
        process.wait(timeout=5)
        raise


def wait_task(base, task_id, account, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        tasks = json_request(base + "/api/accounts/tasks").get("tasks", [])
        task = next((task for task in tasks if task.get("id") == task_id), None)
        if task is None:
            raise RuntimeError("远程任务已消失")
        if task.get("state") in ("done", "failed"):
            items = task.get("items", [])
            if task["state"] == "done" and len(items) == 1 and items[0].get("state") == "done":
                accepted = {str(account.get("id", "")).casefold(), str(account.get("label", "")).casefold()}
                if str(items[0].get("label", "")).casefold() not in accepted:
                    raise RuntimeError("远程任务返回的账号不匹配")
                return
            code = str(items[0].get("code") or "unknown") if items else "unknown"
            raise RuntimeError("远程账号导入失败: " + code)
        time.sleep(2)
    raise RuntimeError("远程任务仍在运行，稍后检查")


def sync_once(config):
    if not is_service_enabled("aistudio"):
        logger.info("AI Studio 网页 API 已关闭，跳过远端 Cookie 同步")
        return
    service = AIStudioService()
    hub = json_request(service.bridge_url + "/cookies?domain=google.com")
    cookies = hub.get("cookies") or []
    if not hub.get("success") or not cookies:
        raise RuntimeError("Cookie Hub 未连接或没有 Google 登录态")
    fingerprint = cookie_fingerprint(cookies)
    local = load_local_accounts(service)
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        state = {}
    fingerprints = state.setdefault("fingerprints", {})
    process, base = ssh_tunnel(config)
    try:
        remote = json_request(base + "/api/accounts").get("accounts", [])
        tasks = json_request(base + "/api/accounts/tasks").get("tasks", [])
        selected = choose_accounts(local, remote, tasks, fingerprints, fingerprint)
        for account, (account_id, auth_user) in selected:
            key = account_id.casefold()
            if key in blocked_accounts():
                continue
            identity_ok = verify_identity(service, cookies, account_id, auth_user)
            if not identity_ok:
                logger.warning("账号 %s 的扩展登录态未通过身份验证，跳过", account_id)
                continue
            if key in blocked_accounts():
                continue
            payload = {"items": [{"email": account_id, "auth_user": auth_user,
                                   "cookies": json.dumps(cookies, ensure_ascii=False)}]}
            response = json_request(base + "/api/accounts/import/cookies", payload=payload, timeout=20)
            task_id = response.get("task", {}).get("id")
            if not task_id:
                raise RuntimeError("远程服务未返回导入任务")
            try:
                wait_task(base, task_id, account)
            except RuntimeError as exc:
                logger.warning("账号 %s 同步失败: %s", account_id, exc)
                continue
            fingerprints[key] = fingerprint
            save_state(state)
            logger.info("账号 %s 已同步到远端", account_id)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def acquire_mutex():
    if sys.platform != "win32":
        return True
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateMutexW
    create.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    create.restype = ctypes.c_void_p
    global _mutex_handle
    _mutex_handle = create(None, False, "Local\\CookieServiceSuite_AIStudioRemoteSync")
    if not _mutex_handle:
        raise OSError(ctypes.get_last_error(), "CreateMutexW failed")
    return ctypes.get_last_error() != 183


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if not acquire_mutex():
        return
    LOG.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(LOG, maxBytes=1024 * 1024, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    if not args.once:
        try:
            AISTUDIO_REMOTE_SYNC_PID.parent.mkdir(parents=True, exist_ok=True)
            AISTUDIO_REMOTE_SYNC_PID.write_text(str(os.getpid()), encoding="utf-8")
        except OSError:
            pass
    try:
        while True:
            try:
                if not is_service_enabled("aistudio"):
                    logger.info("AI Studio 网页 API 已关闭，远端同步守护进程退出。")
                    return
                gs = get_google_sync_settings()
                if not gs.get("auto_sync_enabled", True) or gs.get("cookie_sync_interval_sec", 0) <= 0:
                    logger.info("Google 自动 Cookie 监听与同步已暂停，跳过本轮同步。")
                else:
                    config = json.loads(CONFIG.read_text(encoding="utf-8"))
                    if config.get("enabled"):
                        sync_once(config)
            except Exception as exc:
                logger.warning("远端同步未完成: %s", type(exc).__name__)
                if args.once:
                    raise
            if args.once:
                return
            gs_sleep = get_google_sync_settings()
            interval = int(gs_sleep.get("cookie_sync_interval_sec", 1800) or 1800)
            time.sleep(max(60, interval))
    finally:
        if not args.once:
            try:
                if AISTUDIO_REMOTE_SYNC_PID.is_file() and AISTUDIO_REMOTE_SYNC_PID.read_text(encoding="utf-8").strip() == str(os.getpid()):
                    AISTUDIO_REMOTE_SYNC_PID.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    main()
