"""
Gemini Conversation & Run Manager for Cookie Service Suite.
Provides persistent SQLite storage, real-time StreamGenerate execution,
live output monitoring, completion notifications, immediate stop/abort,
and multi-turn continuation (plus MaZiqc / hNvQHb sync) without a browser UI.
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import sqlite3
import threading
import time
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional, Tuple

from curl_cffi import requests as curl_requests

from web_api_switches import require_service_enabled

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME_DIR = os.path.join(BASE_DIR, "runtime_state")
os.makedirs(RUNTIME_DIR, exist_ok=True)

CONV_DB_PATH = os.path.join(RUNTIME_DIR, "gemini_conversations.db")
POOL_DB_PATH = os.path.join(
    BASE_DIR, "candidate_repos", "gemini-web2api-go", "gemini_pool.db"
)
POOL_CONFIG_PATH = os.path.join(
    BASE_DIR, "candidate_repos", "gemini-web2api-go", "config_pool.json"
)

# Model registry matching gemini-web2api-go/internal/app/gemini.go
MODEL_SPECS: Dict[str, Dict[str, Any]] = {
    "gemini-3.5-flash-lite": {"hex": "cf41b0e0dd7d53e5", "mode": 6, "think": 1},
    "gemini-3.5-flash-lite-thinking": {"hex": "cf41b0e0dd7d53e5", "mode": 6, "think": 2},
    "gemini-3.6-flash": {"hex": "fbb127bbb056c959", "mode": 1, "think": 1},
    "gemini-3.6-flash-thinking": {"hex": "fbb127bbb056c959", "mode": 1, "think": 2},
    "gemini-3.1-pro": {"hex": "9d8ca3786ebdfbea", "mode": 3, "think": 1},
    "gemini-3.1-pro-thinking": {"hex": "9d8ca3786ebdfbea", "mode": 3, "think": 2},
    "gemini-3.8-flash": {"hex": "56fdd199312815e2", "mode": 1, "think": 1},
    "gemini-3.8-flash-thinking": {"hex": "56fdd199312815e2", "mode": 1, "think": 2},
    "gemini-3.7-flash": {"hex": "56fdd199312815e2", "mode": 1, "think": 1},
    "gemini-4-argon": {"hex": "95a4c0abcba24364", "mode": 8, "think": 1},
    "gemini-4-argon-medium": {"hex": "95a4c0abcba24364", "mode": 8, "think": 4},
    "gemini-4-argon-thinking": {"hex": "95a4c0abcba24364", "mode": 8, "think": 2},
    # Friendly aliases used in dashboard/API
    "gemini-4-hydrogen": {"hex": "56fdd199312815e2", "mode": 1, "think": 1},
    "gemini-4-hydrogen-thinking": {"hex": "56fdd199312815e2", "mode": 1, "think": 2},
    # Task mode (任务模式, inner[49]=40): supports multi-turn tool calling
    "gemini-4-hydrogen-task": {"hex": "56fdd199312815e2", "mode": 1, "think": 1, "tool": 40},
    "gemini-4-argon-task": {"hex": "95a4c0abcba24364", "mode": 8, "think": 1, "tool": 40},
    "gemini-4-neon": {"hex": "e6fa609c3fa255c0", "mode": 8, "think": 1},
    "gemini-4-neon-task": {"hex": "e6fa609c3fa255c0", "mode": 8, "think": 1, "tool": 40},
}

_RCID_RE = re.compile(r'"(rc_[A-Za-z0-9_-]{6,})"')
_SNLM0E_RE = re.compile(r'"SNlM0e":"([^"]+)"')
_CFB2H_RE = re.compile(r'"cfb2h":"([^"]+)"')


def _gemini_base(authuser: int) -> str:
    if authuser and authuser > 0:
        return f"https://gemini.google.com/u/{authuser}"
    return "https://gemini.google.com"


def _cookie_value(cookie_str: str, name: str) -> str:
    target = name + "="
    for part in (cookie_str or "").split(";"):
        part = part.strip()
        if part.startswith(target):
            return part[len(target):]
    return ""


def _make_sapisidhash(sapisid: str, origin: str = "https://gemini.google.com") -> str:
    ts = int(time.time())
    digest = hashlib.sha1(f"{ts} {sapisid} {origin}".encode("utf-8")).hexdigest()
    return f"SAPISIDHASH {ts}_{digest}"


def _clean_gemini_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("\r\n", "\n").strip()


def _parse_wrb_payloads(raw: str, target_rpc: Optional[str] = None) -> List[Any]:
    out: List[Any] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("[["):
            continue
        try:
            arr = json.loads(line)
        except Exception:
            continue
        if not isinstance(arr, list):
            continue
        for item in arr:
            if not isinstance(item, list) or len(item) < 3 or item[0] != "wrb.fr":
                continue
            if target_rpc and item[1] != target_rpc:
                continue
            payload_str = item[2]
            if not isinstance(payload_str, str):
                continue
            try:
                out.append(json.loads(payload_str))
            except Exception:
                continue
    return out


def _extract_texts_and_reasoning_from_line(line: str) -> Tuple[List[str], str, Dict[str, str]]:
    """Parse a single StreamGenerate wrb.fr line for texts, reasoning, and conv IDs."""
    texts: List[str] = []
    reasoning = ""
    meta: Dict[str, str] = {}

    if '"wrb.fr"' not in line:
        return texts, reasoning, meta
    try:
        arr = json.loads(line)
    except Exception:
        return texts, reasoning, meta
    if not isinstance(arr, list):
        return texts, reasoning, meta

    for item in arr:
        if not isinstance(item, list) or len(item) < 3 or item[0] != "wrb.fr":
            continue
        inner_str = item[2]
        if not isinstance(inner_str, str):
            continue
        try:
            inner = json.loads(inner_str)
        except Exception:
            continue
        if not isinstance(inner, list):
            continue

        # Conv IDs: inner[1] = [cid, rid], inner[26] = tok26
        if len(inner) > 1 and isinstance(inner[1], list) and len(inner[1]) >= 2:
            if isinstance(inner[1][0], str) and inner[1][0]:
                meta["cid"] = inner[1][0]
            if isinstance(inner[1][1], str) and inner[1][1]:
                meta["rid"] = inner[1][1]
        if len(inner) > 26 and isinstance(inner[26], str) and inner[26]:
            meta["tok26"] = inner[26]

        # Content & reasoning: inner[4]
        if len(inner) > 4 and isinstance(inner[4], list):
            parts = inner[4]
            if parts and isinstance(parts[0], list) and len(parts[0]) > 37:
                lvl1 = parts[0][37]
                if isinstance(lvl1, list) and lvl1 and isinstance(lvl1[0], list) and lvl1[0]:
                    if isinstance(lvl1[0][0], str):
                        reasoning = lvl1[0][0]
            for p in parts:
                if not isinstance(p, list) or len(p) < 2:
                    continue
                if isinstance(p[0], str) and p[0].startswith("rc_"):
                    meta["rcid"] = p[0]
                tl = p[1]
                if isinstance(tl, list):
                    for t in tl:
                        if isinstance(t, str) and t:
                            texts.append(t)

    if "rcid" not in meta:
        m = _RCID_RE.search(line)
        if m:
            meta["rcid"] = m.group(1)
    return texts, reasoning, meta


class _ActiveRun:
    def __init__(self, run_id: str, cid: str):
        self.run_id = run_id
        self.cid = cid
        self.stop_event = threading.Event()
        self.resp_lock = threading.Lock()
        self.resp = None

    def set_response(self, resp: Any) -> None:
        with self.resp_lock:
            self.resp = resp
            if self.stop_event.is_set() and resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass

    def abort(self) -> None:
        self.stop_event.set()
        with self.resp_lock:
            if self.resp is not None:
                try:
                    self.resp.close()
                except Exception:
                    pass


class GeminiConversationManager:
    """Thread-safe manager for persistent Gemini conversations & active runs."""

    def __init__(
        self,
        conv_db_path: str = CONV_DB_PATH,
        pool_db_path: str = POOL_DB_PATH,
        pool_config_path: str = POOL_CONFIG_PATH,
    ) -> None:
        self.conv_db_path = conv_db_path
        self.pool_db_path = pool_db_path
        self.pool_config_path = pool_config_path
        self._db_lock = threading.Lock()
        self._xsrf_lock = threading.Lock()
        self._xsrf_cache: Dict[int, Tuple[str, str, float]] = {}  # authuser -> (xsrf, bl, ts)
        self._runs_lock = threading.Lock()
        self._active_runs: Dict[str, _ActiveRun] = {}
        self._task_sessions_lock = threading.Lock()
        self._task_sessions: Dict[str, Dict[str, Any]] = {}
        self._run_subs: Dict[str, List[queue.Queue]] = {}
        self._global_subs: List[queue.Queue] = []
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.conv_db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._db_lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        cid TEXT PRIMARY KEY,
                        title TEXT NOT NULL DEFAULT '',
                        account_id INTEGER NOT NULL DEFAULT 0,
                        authuser INTEGER NOT NULL DEFAULT 0,
                        account_label TEXT NOT NULL DEFAULT '',
                        model TEXT NOT NULL DEFAULT 'gemini-3.6-flash',
                        rid TEXT NOT NULL DEFAULT '',
                        rcid TEXT NOT NULL DEFAULT '',
                        tok26 TEXT NOT NULL DEFAULT '',
                        turn INTEGER NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'idle',
                        active_run_id TEXT NOT NULL DEFAULT '',
                        last_prompt TEXT NOT NULL DEFAULT '',
                        last_reply TEXT NOT NULL DEFAULT '',
                        error_message TEXT NOT NULL DEFAULT '',
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_runs (
                        run_id TEXT PRIMARY KEY,
                        cid TEXT NOT NULL,
                        account_id INTEGER NOT NULL DEFAULT 0,
                        authuser INTEGER NOT NULL DEFAULT 0,
                        model TEXT NOT NULL DEFAULT '',
                        prompt TEXT NOT NULL DEFAULT '',
                        partial_reply TEXT NOT NULL DEFAULT '',
                        partial_reasoning TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'running',
                        error_message TEXT NOT NULL DEFAULT '',
                        started_at REAL NOT NULL,
                        finished_at REAL NOT NULL DEFAULT 0
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cid TEXT NOT NULL,
                        run_id TEXT NOT NULL DEFAULT '',
                        role TEXT NOT NULL,
                        content TEXT NOT NULL DEFAULT '',
                        reasoning TEXT NOT NULL DEFAULT '',
                        rid TEXT NOT NULL DEFAULT '',
                        rcid TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'completed',
                        created_at REAL NOT NULL
                    );
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_conv_updated ON conversations(updated_at DESC);"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_msg_cid ON conversation_messages(cid, id ASC);"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_runs_cid ON conversation_runs(cid, started_at DESC);"
                )
                # Recover any stale 'running' rows from an abrupt server restart
                now = time.time()
                conn.execute(
                    "UPDATE conversations SET status='stopped', active_run_id='', updated_at=? WHERE status='running'",
                    (now,),
                )
                conn.execute(
                    "UPDATE conversation_runs SET status='stopped', finished_at=? WHERE status='running'",
                    (now,),
                )
                conn.execute(
                    "UPDATE conversation_messages SET status='stopped' WHERE status='running'"
                )
                conn.commit()
            finally:
                conn.close()

    def _get_proxy(self) -> str:
        try:
            with open(self.pool_config_path, "r", encoding="utf-8") as fh:
                p = str(json.load(fh).get("proxy") or "").strip()
                if p:
                    return p
        except Exception:
            pass
        from gemini_service import _detect_local_proxy

        return _detect_local_proxy() or ""

    def sync_cookie_from_hub_if_changed(self, force: bool = False) -> bool:
        if not hasattr(self, "_hub_sync_lock"):
            self._hub_sync_lock, self._hub_last_check, self._hub_last_force = threading.Lock(), 0.0, 0.0
        now, gap = time.time(), (60.0 if force else 300.0)
        if now - (self._hub_last_force if force else self._hub_last_check) < gap: return False
        with self._hub_sync_lock:
            now = time.time()
            if now - (self._hub_last_force if force else self._hub_last_check) < gap: return False
            self._hub_last_check = now
            if force: self._hub_last_force = now
            try:
                hub_ep = "http://127.0.0.1:18888/gemini/auto_fetch" if force else "http://127.0.0.1:18888/cookies?domain=google.com"
                with urllib.request.urlopen(hub_ep, timeout=(25 if force else 3)) as r:
                    cs = (json.loads(r.read().decode("utf-8", "ignore")).get("cookies") or [])
                d = {x["name"]: x["value"] for x in cs if x.get("domain") in (".google.com", "gemini.google.com") and x.get("name") and x.get("value")}
                if "__Secure-1PSID" not in d or "SAPISID" not in d: return False
                ck = "; ".join(f"{k}={v}" for k, v in d.items())
                nh = hashlib.sha256(ck.encode("utf-8")).hexdigest()
                conn = sqlite3.connect(self.pool_db_path, timeout=10.0)
                try:
                    row = conn.execute("SELECT id, cookie FROM accounts WHERE status='enabled' ORDER BY id ASC LIMIT 1").fetchone()
                    if not row or hashlib.sha256((row[1] or "").encode("utf-8")).hexdigest() == nh: return False
                    conn.execute("UPDATE accounts SET cookie=?, fail_count=0 WHERE id=?", (ck, row[0]))
                    conn.commit()
                finally: conn.close()
                with self._xsrf_lock: self._xsrf_cache.clear()
                print("[Gemini Task] Cookie Hub hash changed -> synced", flush=True)
                return True
            except Exception: return False

    def _get_account(
        self, account_id: Optional[int] = None, authuser: Optional[int] = None
    ) -> Dict[str, Any]:
        if not os.path.exists(self.pool_db_path):
            raise RuntimeError("未找到 Gemini 多账号数据库 gemini_pool.db")
        conn = sqlite3.connect(self.pool_db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            if account_id:
                row = conn.execute(
                    "SELECT id, label, cookie, status, authuser FROM accounts WHERE id = ?",
                    (account_id,),
                ).fetchone()
            elif authuser is not None:
                row = conn.execute(
                    "SELECT id, label, cookie, status, authuser FROM accounts WHERE authuser = ? LIMIT 1",
                    (authuser,),
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT id, label, cookie, status, authuser FROM accounts
                       WHERE status = 'enabled' AND cookie != ''
                       ORDER BY last_used_at ASC, id ASC LIMIT 1"""
                ).fetchone()
            if not row:
                raise RuntimeError("没有可用的已启用 Gemini 账号，请先检查账号看板并同步 Cookie")
            if not row["cookie"]:
                raise RuntimeError(f"账号 {row['label'] or row['id']} Cookie 为空，请先刷新凭证")
            return dict(row)
        finally:
            conn.close()

    def _list_enabled_accounts(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.pool_db_path):
            return []
        conn = sqlite3.connect(self.pool_db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT id, label, cookie, status, authuser FROM accounts WHERE status='enabled' AND cookie != '' ORDER BY authuser ASC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _proxies_dict(self) -> Optional[Dict[str, str]]:
        proxy = self._get_proxy()
        if not proxy:
            return None
        return {"http": proxy, "https": proxy}

    def _curl_request(self, method: str, url: str, retries: int = 3, **kwargs: Any):
        last_exc: Optional[Exception] = None
        for attempt in range(retries):
            try:
                return curl_requests.request(method, url, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt < retries - 1:
                    time.sleep(0.35 * (attempt + 1))
        raise last_exc  # type: ignore[misc]

    def _get_xsrf_and_bl(
        self, cookie: str, authuser: int, force_refresh: bool = False
    ) -> Tuple[str, str]:
        now = time.time()
        if not hasattr(self, "_fsid_cache"):
            self._fsid_cache = {}
        with self._xsrf_lock:
            cached = self._xsrf_cache.get(authuser)
            if cached and not force_refresh and (now - cached[2] < 1200) and authuser in self._fsid_cache:
                return cached[0], cached[1]

        if self.sync_cookie_from_hub_if_changed(force=False):
            try: cookie = self._get_account(authuser=authuser)["cookie"]
            except Exception: pass
        base = _gemini_base(authuser)
        sess = curl_requests.Session(impersonate="chrome")
        def _fetch_app(ck: str):
            hdrs = {"Cookie": ck, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
            r = sess.get(f"{base}/app?hl=zh-CN", headers=hdrs, proxies=self._proxies_dict(), timeout=20)
            if r.status_code != 200: return r.status_code, "", "", ""
            h = r.text
            xm, bm, fm = _SNLM0E_RE.search(h), _CFB2H_RE.search(h), re.search(r'"FdrFJe":"([^"]+)"', h)
            return r.status_code, (xm.group(1) if xm else ""), (bm.group(1) if bm else "boq_gemini-web-uiserver_20261120.16_p0"), (fm.group(1) if fm else "")
        code, xsrf, bl, fsid = _fetch_app(cookie)
        if (code != 200 or not xsrf) and self.sync_cookie_from_hub_if_changed(force=True):
            try: cookie = self._get_account(authuser=authuser)["cookie"]
            except Exception: pass
            sess = curl_requests.Session(impersonate="chrome")
            code, xsrf, bl, fsid = _fetch_app(cookie)
        if code != 200: raise RuntimeError(f"请求 Gemini /app 失败: HTTP {code}")
        if not xsrf: raise RuntimeError("未能从 /app 页面提取 XSRF (SNlM0e)，账号登录态可能已过期")
        with self._xsrf_lock:
            self._xsrf_cache[authuser] = (xsrf, bl, time.time())
            self._fsid_cache[authuser] = (fsid, sess)
        return xsrf, bl

    def _batchexecute(
        self,
        rpcid: str,
        inner_payload: Any,
        account: Dict[str, Any],
    ) -> List[Any]:
        cookie = account["cookie"]
        authuser = int(account.get("authuser") or 0)
        sapisid = _cookie_value(cookie, "SAPISID")
        xsrf, bl = self._get_xsrf_and_bl(cookie, authuser)
        try:
            cookie = self._get_account(authuser=authuser)["cookie"]
            sapisid = _cookie_value(cookie, "SAPISID")
        except Exception: pass
        fsid, sess = self._fsid_cache.get(authuser, ("", curl_requests.Session(impersonate="chrome")))

        freq = json.dumps([[[rpcid, json.dumps(inner_payload, separators=(",", ":")), None, "generic"]]])
        form = urllib.parse.urlencode({"f.req": freq, "at": xsrf})
        reqid = int(time.time() * 1000) % 900000 + 100000
        base = _gemini_base(authuser)
        sp = f"/u/{authuser}/app" if authuser else "/app"
        url = f"{base}/_/BardChatUi/data/batchexecute?rpcids={rpcid}&source-path={urllib.parse.quote(sp, safe='')}&bl={urllib.parse.quote(bl)}&f.sid={urllib.parse.quote(fsid)}&hl=zh-CN&_reqid={reqid}&rt=c"
        headers = {
            "Cookie": cookie,
            "Origin": "https://gemini.google.com",
            "Referer": f"{base}/app",
            "X-Same-Domain": "1",
            "X-Goog-AuthUser": str(authuser),
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }
        if sapisid:
            headers["Authorization"] = _make_sapisidhash(sapisid)

        resp = sess.post(url, data=form, headers=headers, proxies=self._proxies_dict(), timeout=25)
        if resp.status_code != 200:
            raise RuntimeError(f"batchexecute({rpcid}) HTTP {resp.status_code}")
        return _parse_wrb_payloads(resp.text, target_rpc=rpcid)

    # ------------------------------------------------------------------
    # Event broadcasting (global + per-run SSE)
    # ------------------------------------------------------------------
    def subscribe_global(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=200)
        with self._runs_lock:
            self._global_subs.append(q)
        return q

    def unsubscribe_global(self, q: queue.Queue) -> None:
        with self._runs_lock:
            if q in self._global_subs:
                self._global_subs.remove(q)

    def subscribe_run(self, run_id: str) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=400)
        with self._runs_lock:
            self._run_subs.setdefault(run_id, []).append(q)
        return q

    def unsubscribe_run(self, run_id: str, q: queue.Queue) -> None:
        with self._runs_lock:
            lst = self._run_subs.get(run_id)
            if lst and q in lst:
                lst.remove(q)
            if lst is not None and not lst:
                self._run_subs.pop(run_id, None)

    def _emit_event(self, event_type: str, payload: Dict[str, Any], run_id: str = "") -> None:
        msg = {"event": event_type, "data": payload}
        with self._runs_lock:
            g_subs = list(self._global_subs)
            r_subs = list(self._run_subs.get(run_id, [])) if run_id else []
        for q in g_subs:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass
        for q in r_subs:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass

    # ------------------------------------------------------------------
    # Upstream sync: MaZiqc (list) & hNvQHb (turns)
    # ------------------------------------------------------------------
    def sync_conversations(
        self, account_id: Optional[int] = None, limit: int = 20
    ) -> Dict[str, Any]:
        require_service_enabled("gemini")
        accounts = (
            [self._get_account(account_id=account_id)]
            if account_id
            else self._list_enabled_accounts()
        )
        if not accounts:
            raise RuntimeError("没有可用的已启用 Gemini 账号")

        synced = 0
        errors: List[str] = []
        now = time.time()
        for acct in accounts:
            try:
                payloads = self._batchexecute("MaZiqc", [limit, None, [0, None, 1]], acct)
                for p in payloads:
                    if not isinstance(p, list) or len(p) < 3 or not isinstance(p[2], list):
                        continue
                    for item in p[2]:
                        if not isinstance(item, list) or len(item) < 2:
                            continue
                        cid = item[0] if isinstance(item[0], str) else ""
                        title = item[1] if isinstance(item[1], str) else ""
                        if not cid:
                            continue
                        updated = now
                        if len(item) >= 6 and isinstance(item[5], list) and item[5]:
                            try:
                                updated = float(item[5][0])
                            except Exception:
                                pass
                        with self._db_lock:
                            conn = self._conn()
                            try:
                                existing = conn.execute(
                                    "SELECT cid, status FROM conversations WHERE cid=?",
                                    (cid,),
                                ).fetchone()
                                if existing:
                                    conn.execute(
                                        """UPDATE conversations
                                           SET title=CASE WHEN ?!='' THEN ? ELSE title END,
                                               account_id=?, authuser=?, account_label=?,
                                               updated_at=MAX(updated_at, ?)
                                           WHERE cid=?""",
                                        (
                                            title,
                                            title,
                                            acct["id"],
                                            acct["authuser"],
                                            acct["label"],
                                            updated,
                                            cid,
                                        ),
                                    )
                                else:
                                    conn.execute(
                                        """INSERT INTO conversations
                                           (cid, title, account_id, authuser, account_label, model, status, created_at, updated_at)
                                           VALUES (?, ?, ?, ?, ?, 'gemini-3.6-flash', 'idle', ?, ?)""",
                                        (
                                            cid,
                                            title or cid,
                                            acct["id"],
                                            acct["authuser"],
                                            acct["label"],
                                            updated,
                                            updated,
                                        ),
                                    )
                                conn.commit()
                                synced += 1
                            finally:
                                conn.close()
            except Exception as exc:
                errors.append(f"{acct.get('label') or acct['id']}: {exc}")

        return {"synced": synced, "errors": errors}

    def sync_conversation_detail(self, cid: str) -> Dict[str, Any]:
        require_service_enabled("gemini")
        conv = self.get_conversation(cid, include_messages=False)
        if not conv:
            raise RuntimeError(f"未找到对话 {cid}")
        acct = self._get_account(account_id=conv["account_id"] or None, authuser=conv["authuser"])
        payloads = self._batchexecute(
            "hNvQHb", [cid, 20, None, 1, [0], [4], None, 1], acct
        )
        parsed_turns: List[Dict[str, Any]] = []
        for p in payloads:
            if not isinstance(p, list) or not p or not isinstance(p[0], list):
                continue
            # hNvQHb returns turns newest-first; reverse to chronological order
            raw_turns = list(reversed(p[0]))
            for t in raw_turns:
                if not isinstance(t, list) or not t:
                    continue
                ids = t[0] if isinstance(t[0], list) else []
                rid = ids[1] if len(ids) >= 2 and isinstance(ids[1], str) else ""
                prompt_text = ""
                try:
                    prompt_text = str(t[2][0][0])
                except Exception:
                    pass
                reply_text = ""
                reasoning_text = ""
                rcid = ""
                try:
                    cand = t[3][0][0]
                    if isinstance(cand, list):
                        if len(cand) > 0 and isinstance(cand[0], str):
                            rcid = cand[0]
                        if len(cand) > 1 and isinstance(cand[1], list) and cand[1]:
                            reply_text = str(cand[1][0] or "")
                        if len(cand) > 37 and isinstance(cand[37], list):
                            c37 = cand[37]
                            step_parts: List[str] = []
                            if len(c37) > 0 and isinstance(c37[0], list) and c37[0]:
                                if isinstance(c37[0][0], str) and c37[0][0].strip():
                                    step_parts.append(c37[0][0].strip())
                            if len(c37) > 1 and isinstance(c37[1], list):
                                tools_seen: List[str] = []
                                for step in c37[1]:
                                    if (
                                        isinstance(step, list)
                                        and len(step) > 2
                                        and isinstance(step[1], str)
                                        and "tool_name_placeholder" in step[1]
                                        and isinstance(step[2], str)
                                        and step[2].strip()
                                    ):
                                        tname = step[2].strip()
                                        if tname not in tools_seen:
                                            tools_seen.append(tname)
                                if tools_seen:
                                    step_parts.insert(0, f"[已连接工具: {', '.join(tools_seen)}]")
                            reasoning_text = "\n\n".join(step_parts).strip()
                except Exception:
                    pass
                parsed_turns.append(
                    {
                        "rid": rid,
                        "rcid": rcid,
                        "prompt": prompt_text,
                        "reply": reply_text,
                        "reasoning": reasoning_text,
                    }
                )

        if parsed_turns:
            last = parsed_turns[-1]
            now = time.time()
            with self._db_lock:
                conn = self._conn()
                try:
                    # Only replace messages if not currently running locally
                    row = conn.execute(
                        "SELECT status FROM conversations WHERE cid=?", (cid,)
                    ).fetchone()
                    if row and row["status"] != "running":
                        conn.execute(
                            "DELETE FROM conversation_messages WHERE cid=?", (cid,)
                        )
                        for idx, tr in enumerate(parsed_turns):
                            if tr["prompt"]:
                                conn.execute(
                                    """INSERT INTO conversation_messages
                                       (cid, role, content, rid, status, created_at)
                                       VALUES (?, 'user', ?, ?, 'completed', ?)""",
                                    (cid, tr["prompt"], tr["rid"], now + idx * 0.001),
                                )
                            if tr["reply"] or tr["reasoning"]:
                                conn.execute(
                                    """INSERT INTO conversation_messages
                                       (cid, role, content, reasoning, rid, rcid, status, created_at)
                                       VALUES (?, 'assistant', ?, ?, ?, ?, 'completed', ?)""",
                                    (
                                        cid,
                                        tr["reply"],
                                        tr["reasoning"],
                                        tr["rid"],
                                        tr["rcid"],
                                        now + idx * 0.001 + 0.0005,
                                    ),
                                )
                    conn.execute(
                        """UPDATE conversations
                           SET rid=CASE WHEN ?!='' THEN ? ELSE rid END,
                               rcid=CASE WHEN ?!='' THEN ? ELSE rcid END,
                               turn=?,
                               last_prompt=CASE WHEN ?!='' THEN ? ELSE last_prompt END,
                               last_reply=CASE WHEN ?!='' THEN ? ELSE last_reply END,
                               status=CASE WHEN status='running' THEN 'running' WHEN ?!='' THEN 'completed' ELSE status END,
                               updated_at=?
                           WHERE cid=?""",
                        (
                            last["rid"],
                            last["rid"],
                            last["rcid"],
                            last["rcid"],
                            len(parsed_turns),
                            last["prompt"],
                            last["prompt"],
                            last["reply"],
                            last["reply"],
                            last["reply"],
                            now,
                            cid,
                        ),
                    )
                    conn.commit()
                finally:
                    conn.close()
        return self.get_conversation(cid, include_messages=True) or {}

    # ------------------------------------------------------------------
    # Query persisted conversations & runs
    # ------------------------------------------------------------------
    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._db_lock:
            conn = self._conn()
            try:
                rows = conn.execute(
                    "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
                    (max(1, min(200, int(limit))),),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def get_conversation(
        self, cid: str, include_messages: bool = True
    ) -> Optional[Dict[str, Any]]:
        with self._db_lock:
            conn = self._conn()
            try:
                row = conn.execute(
                    "SELECT * FROM conversations WHERE cid=?", (cid,)
                ).fetchone()
                if not row:
                    return None
                item = dict(row)
                if include_messages:
                    msgs = conn.execute(
                        "SELECT * FROM conversation_messages WHERE cid=? ORDER BY id ASC",
                        (cid,),
                    ).fetchall()
                    item["messages"] = [dict(m) for m in msgs]
                    if item.get("active_run_id"):
                        run_row = conn.execute(
                            "SELECT * FROM conversation_runs WHERE run_id=?",
                            (item["active_run_id"],),
                        ).fetchone()
                        if run_row:
                            item["active_run"] = dict(run_row)
                return item
            finally:
                conn.close()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._db_lock:
            conn = self._conn()
            try:
                row = conn.execute(
                    "SELECT * FROM conversation_runs WHERE run_id=?", (run_id,)
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

    def delete_local_conversation(self, cid: str, delete_upstream: bool = False) -> bool:
        conv = self.get_conversation(cid, include_messages=False)
        if not conv:
            return False
        if conv.get("active_run_id"):
            self.stop_run(conv["active_run_id"])
        if delete_upstream and cid.startswith("c_"):
            try:
                acct = self._get_account(
                    account_id=conv["account_id"] or None, authuser=conv["authuser"]
                )
                self._batchexecute("GzXR5e", [cid], acct)
            except Exception:
                pass
        with self._db_lock:
            conn = self._conn()
            try:
                conn.execute("DELETE FROM conversation_messages WHERE cid=?", (cid,))
                conn.execute("DELETE FROM conversation_runs WHERE cid=?", (cid,))
                conn.execute("DELETE FROM conversations WHERE cid=?", (cid,))
                conn.commit()
            finally:
                conn.close()
        self._emit_event("conversation_deleted", {"cid": cid})
        return True

    # ------------------------------------------------------------------
    # Start, stream, monitor, stop, and continue conversations
    # ------------------------------------------------------------------
    def start_run(
        self,
        prompt: str,
        cid: Optional[str] = None,
        model: str = "gemini-3.6-flash",
        account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        require_service_enabled("gemini")
        prompt = (prompt or "").strip()
        if not prompt:
            raise ValueError("消息内容不能为空")

        is_continuation = bool(cid)
        conv_state: Dict[str, Any] = {}
        if is_continuation:
            existing = self.get_conversation(cid, include_messages=False)
            if not existing:
                raise RuntimeError(f"对话 {cid} 不存在")
            if existing.get("status") == "running" and existing.get("active_run_id"):
                raise RuntimeError("该对话正在生成中，请先停止或等待当前消息完成")
            # Hydrate rid/rcid from upstream if this conversation was imported via MaZiqc
            # or was previously stopped mid-stream without a complete rcid
            if cid.startswith("c_") and (not existing.get("rid") or not existing.get("rcid") or existing.get("status") == "stopped"):
                try:
                    existing = self.sync_conversation_detail(cid)
                except Exception:
                    pass
            conv_state = existing
            account = self._get_account(
                account_id=existing.get("account_id") or None,
                authuser=existing.get("authuser"),
            )
            if not model:
                model = existing.get("model") or "gemini-3.6-flash"
        else:
            account = self._get_account(account_id=account_id)
            cid = f"pending_{uuid.uuid4().hex[:12]}"

        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now = time.time()
        title_preview = prompt[:36] + ("..." if len(prompt) > 36 else "")

        with self._db_lock:
            conn = self._conn()
            try:
                if not is_continuation:
                    conn.execute(
                        """INSERT INTO conversations
                           (cid, title, account_id, authuser, account_label, model, status, active_run_id, last_prompt, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?, ?, ?)""",
                        (
                            cid,
                            title_preview,
                            account["id"],
                            account["authuser"],
                            account["label"],
                            model,
                            run_id,
                            prompt,
                            now,
                            now,
                        ),
                    )
                else:
                    conn.execute(
                        """UPDATE conversations
                           SET status='running', active_run_id=?, model=?, last_prompt=?, error_message='', updated_at=?
                           WHERE cid=?""",
                        (run_id, model, prompt, now, cid),
                    )
                conn.execute(
                    """INSERT INTO conversation_runs
                       (run_id, cid, account_id, authuser, model, prompt, status, started_at)
                       VALUES (?, ?, ?, ?, ?, ?, 'running', ?)""",
                    (
                        run_id,
                        cid,
                        account["id"],
                        account["authuser"],
                        model,
                        prompt,
                        now,
                    ),
                )
                conn.execute(
                    """INSERT INTO conversation_messages
                       (cid, run_id, role, content, status, created_at)
                       VALUES (?, ?, 'user', ?, 'completed', ?)""",
                    (cid, run_id, prompt, now),
                )
                cur = conn.execute(
                    """INSERT INTO conversation_messages
                       (cid, run_id, role, content, status, created_at)
                       VALUES (?, ?, 'assistant', '', 'running', ?)""",
                    (cid, run_id, now + 0.001),
                )
                assistant_msg_id = cur.lastrowid
                conn.commit()
            finally:
                conn.close()

        active = _ActiveRun(run_id=run_id, cid=cid)
        with self._runs_lock:
            self._active_runs[run_id] = active

        self._emit_event(
            "run_started",
            {
                "run_id": run_id,
                "cid": cid,
                "model": model,
                "account_label": account["label"],
                "prompt": prompt,
            },
            run_id=run_id,
        )

        t = threading.Thread(
            target=self._execute_run,
            args=(active, account, prompt, model, conv_state, assistant_msg_id),
            daemon=True,
        )
        t.start()

        return {
            "run_id": run_id,
            "cid": cid,
            "status": "running",
            "account_id": account["id"],
            "account_label": account["label"],
            "model": model,
        }

    def stop_run(self, run_id: str) -> Dict[str, Any]:
        with self._runs_lock:
            active = self._active_runs.get(run_id)
        if active:
            active.abort()
            return {"stopped": True, "run_id": run_id, "cid": active.cid}
        run = self.get_run(run_id)
        if not run:
            return {"stopped": False, "run_id": run_id, "reason": "run not found"}
        if run["status"] == "running":
            now = time.time()
            with self._db_lock:
                conn = self._conn()
                try:
                    conn.execute(
                        "UPDATE conversation_runs SET status='stopped', finished_at=? WHERE run_id=?",
                        (now, run_id),
                    )
                    conn.execute(
                        "UPDATE conversations SET status='stopped', active_run_id='', updated_at=? WHERE cid=?",
                        (now, run["cid"]),
                    )
                    conn.execute(
                        "UPDATE conversation_messages SET status='stopped' WHERE run_id=? AND role='assistant'",
                        (run_id,),
                    )
                    conn.commit()
                finally:
                    conn.close()
        return {"stopped": True, "run_id": run_id, "cid": run["cid"]}

    def stop_conversation(self, cid: str) -> Dict[str, Any]:
        conv = self.get_conversation(cid, include_messages=False)
        if not conv:
            raise RuntimeError(f"对话 {cid} 不存在")
        run_id = conv.get("active_run_id") or ""
        if run_id:
            return self.stop_run(run_id)
        return {"stopped": False, "cid": cid, "reason": "no active run"}

    def _migrate_pending_cid(self, old_cid: str, real_cid: str, run_id: str) -> None:
        if not real_cid or real_cid == old_cid:
            return
        with self._db_lock:
            conn = self._conn()
            try:
                # If real_cid somehow already exists, merge into it
                exists = conn.execute(
                    "SELECT cid FROM conversations WHERE cid=?", (real_cid,)
                ).fetchone()
                if exists:
                    conn.execute(
                        "UPDATE conversation_messages SET cid=? WHERE cid=?",
                        (real_cid, old_cid),
                    )
                    conn.execute(
                        "UPDATE conversation_runs SET cid=? WHERE cid=?",
                        (real_cid, old_cid),
                    )
                    conn.execute(
                        """UPDATE conversations
                           SET status='running', active_run_id=?, updated_at=?
                           WHERE cid=?""",
                        (run_id, time.time(), real_cid),
                    )
                    conn.execute("DELETE FROM conversations WHERE cid=?", (old_cid,))
                else:
                    conn.execute(
                        "UPDATE conversations SET cid=? WHERE cid=?",
                        (real_cid, old_cid),
                    )
                    conn.execute(
                        "UPDATE conversation_messages SET cid=? WHERE cid=?",
                        (real_cid, old_cid),
                    )
                    conn.execute(
                        "UPDATE conversation_runs SET cid=? WHERE cid=?",
                        (real_cid, old_cid),
                    )
                conn.commit()
            finally:
                conn.close()

    def _execute_run(
        self,
        active: _ActiveRun,
        account: Dict[str, Any],
        prompt: str,
        model: str,
        conv_state: Dict[str, Any],
        assistant_msg_id: int,
    ) -> None:
        run_id = active.run_id
        current_cid = active.cid
        authuser = int(account.get("authuser") or 0)
        cookie = account["cookie"]
        sapisid = _cookie_value(cookie, "SAPISID")

        spec = MODEL_SPECS.get(model, MODEL_SPECS["gemini-3.6-flash"])
        hex_id = spec["hex"]
        mode = spec["mode"]
        think = spec["think"]
        tool = spec.get("tool")

        reply_text = ""
        reasoning_text = ""
        meta_cid = ""
        meta_rid = ""
        meta_rcid = ""
        meta_tok26 = ""
        final_status = "completed"
        error_message = ""

        try:
            xsrf, bl = self._get_xsrf_and_bl(cookie, authuser)
            try:
                cookie = self._get_account(account_id=account["id"])["cookie"]
                sapisid = _cookie_value(cookie, "SAPISID")
            except Exception: pass
            req_uuid = str(uuid.uuid4())
            header_uuid = str(uuid.uuid4())

            inner: List[Any] = [None] * 97
            inner[0] = [prompt, 0, None, None, None, None, 0]
            inner[1] = ["en"]
            if conv_state and conv_state.get("cid", "").startswith("c_") and conv_state.get("rid"):
                inner[2] = [
                    conv_state["cid"],
                    conv_state.get("rid", ""),
                    conv_state.get("rcid", ""),
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    conv_state.get("tok26", ""),
                ]
                turn_idx = int(conv_state.get("turn") or 0)
            else:
                inner[2] = ["", "", "", None, None, None, None, None, None, ""]
                turn_idx = 0

            inner[6] = [0]
            inner[7] = 1
            inner[10] = 1
            inner[11] = 0
            inner[17] = [[turn_idx]]
            inner[18] = 0
            inner[27] = 1
            inner[30] = [4]
            inner[41] = [1]
            if tool:
                inner[49] = tool
            inner[53] = 0
            inner[59] = req_uuid
            inner[61] = []
            inner[68] = 1
            inner[79] = mode
            inner[80] = think
            inner[91] = 0
            inner[96] = 1 if think != 1 else 0

            inner_json = json.dumps(inner, separators=(",", ":"))
            outer_json = json.dumps([None, inner_json], separators=(",", ":"))
            form_body = urllib.parse.urlencode({"f.req": outer_json, "at": xsrf})

            base = _gemini_base(authuser)
            reqid = int(time.time() * 1000) % 900000 + 100000
            endpoint = f"{base}/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate?bl={urllib.parse.quote(bl)}&hl=en&_reqid={reqid}&rt=c"

            model_hdr = f'[1,null,null,null,"{hex_id}",null,null,0,[4,5,6,8],null,null,1,null,null,{mode},{think},"{header_uuid}"]'
            headers = {
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Origin": "https://gemini.google.com",
                "Referer": f"{base}/app",
                "X-Same-Domain": "1",
                "X-Goog-AuthUser": str(authuser),
                "Cookie": cookie,
                "x-goog-ext-73010989-jspb": "[0]",
                "x-goog-ext-73010990-jspb": "[0,0,0]",
                "x-goog-ext-525001261-jspb": model_hdr,
                "x-goog-ext-525005358-jspb": f'["{req_uuid}",1]',
            }
            if sapisid:
                headers["Authorization"] = _make_sapisidhash(sapisid)

            resp = self._curl_request(
                "POST",
                endpoint,
                retries=3,
                data=form_body,
                headers=headers,
                proxies=self._proxies_dict(),
                impersonate="chrome",
                stream=True,
                timeout=300,
            )
            active.set_response(resp)
            if resp.status_code != 200:
                raise RuntimeError(f"StreamGenerate HTTP {resp.status_code}")

            last_flush = time.time()
            for raw_line in resp.iter_lines():
                if active.stop_event.is_set():
                    final_status = "stopped"
                    break
                if not raw_line:
                    continue
                line = (
                    raw_line.decode("utf-8", errors="replace")
                    if isinstance(raw_line, (bytes, bytearray))
                    else str(raw_line)
                ).strip()
                if not line.startswith("[["):
                    continue

                texts, r_str, line_meta = _extract_texts_and_reasoning_from_line(line)
                if line_meta.get("cid") and not meta_cid:
                    meta_cid = line_meta["cid"]
                    if current_cid.startswith("pending_") and meta_cid.startswith("c_"):
                        self._migrate_pending_cid(current_cid, meta_cid, run_id)
                        current_cid = meta_cid
                        active.cid = current_cid
                        self._emit_event(
                            "cid_assigned",
                            {"run_id": run_id, "cid": current_cid},
                            run_id=run_id,
                        )
                if line_meta.get("rid"):
                    meta_rid = line_meta["rid"]
                if line_meta.get("rcid"):
                    meta_rcid = line_meta["rcid"]
                if line_meta.get("tok26"):
                    meta_tok26 = line_meta["tok26"]

                updated_text = False
                if r_str and len(r_str) > len(reasoning_text):
                    reasoning_text = _clean_gemini_text(r_str)
                    self._emit_event(
                        "run_reasoning",
                        {
                            "run_id": run_id,
                            "cid": current_cid,
                            "reasoning": reasoning_text,
                        },
                        run_id=run_id,
                    )
                    updated_text = True

                for t in texts:
                    cleaned = _clean_gemini_text(t)
                    if len(cleaned) > len(reply_text):
                        delta = cleaned[len(reply_text):] if cleaned.startswith(reply_text) else cleaned
                        reply_text = cleaned
                        self._emit_event(
                            "run_delta",
                            {
                                "run_id": run_id,
                                "cid": current_cid,
                                "delta": delta,
                                "reply": reply_text,
                            },
                            run_id=run_id,
                        )
                        updated_text = True

                if updated_text and (time.time() - last_flush >= 0.6):
                    last_flush = time.time()
                    self._flush_partial(
                        run_id, current_cid, assistant_msg_id, reply_text, reasoning_text
                    )

            if active.stop_event.is_set():
                final_status = "stopped"
            elif not reply_text and not meta_cid and conv_state and conv_state.get("cid", "").startswith("c_"):
                # Previous turn may have just been stopped and still committing upstream;
                # wait briefly, re-hydrate rid/rcid via hNvQHb, and retry once.
                time.sleep(1.5)
                try:
                    refreshed = self.sync_conversation_detail(conv_state["cid"])
                except Exception:
                    refreshed = conv_state
                if refreshed.get("rid"):
                    inner[2] = [
                        refreshed["cid"],
                        refreshed.get("rid", ""),
                        refreshed.get("rcid", ""),
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        refreshed.get("tok26", ""),
                    ]
                    inner[17] = [[int(refreshed.get("turn") or turn_idx)]]
                    form_body_retry = urllib.parse.urlencode(
                        {"f.req": json.dumps([None, json.dumps(inner, separators=(",", ":"))], separators=(",", ":")), "at": xsrf}
                    )
                    resp2 = self._curl_request(
                        "POST",
                        endpoint,
                        retries=2,
                        data=form_body_retry,
                        headers=headers,
                        proxies=self._proxies_dict(),
                        impersonate="chrome",
                        stream=True,
                        timeout=300,
                    )
                    active.set_response(resp2)
                    if resp2.status_code == 200:
                        for raw_line in resp2.iter_lines():
                            if active.stop_event.is_set():
                                final_status = "stopped"
                                break
                            if not raw_line:
                                continue
                            line = (
                                raw_line.decode("utf-8", errors="replace")
                                if isinstance(raw_line, (bytes, bytearray))
                                else str(raw_line)
                            ).strip()
                            if not line.startswith("[["):
                                continue
                            texts, r_str, line_meta = _extract_texts_and_reasoning_from_line(line)
                            if line_meta.get("cid") and not meta_cid:
                                meta_cid = line_meta["cid"]
                            if line_meta.get("rid"):
                                meta_rid = line_meta["rid"]
                            if line_meta.get("rcid"):
                                meta_rcid = line_meta["rcid"]
                            if line_meta.get("tok26"):
                                meta_tok26 = line_meta["tok26"]
                            if r_str and len(r_str) > len(reasoning_text):
                                reasoning_text = _clean_gemini_text(r_str)
                            for t in texts:
                                cleaned = _clean_gemini_text(t)
                                if len(cleaned) > len(reply_text):
                                    delta = cleaned[len(reply_text):] if cleaned.startswith(reply_text) else cleaned
                                    reply_text = cleaned
                                    self._emit_event(
                                        "run_delta",
                                        {"run_id": run_id, "cid": current_cid, "delta": delta, "reply": reply_text},
                                        run_id=run_id,
                                    )
                if active.stop_event.is_set():
                    final_status = "stopped"
                elif not reply_text and not meta_cid:
                    final_status = "error"
                    error_message = "上游未返回有效内容帧（Cookie 可能已失效或触发风控）"
            elif not reply_text and not meta_cid:
                final_status = "error"
                error_message = "上游未返回有效内容帧（Cookie 可能已失效或触发风控）"
        except Exception as exc:
            if active.stop_event.is_set():
                final_status = "stopped"
            else:
                final_status = "error"
                error_message = str(exc)
        finally:
            with self._runs_lock:
                self._active_runs.pop(run_id, None)

        finished_at = time.time()
        next_turn = (
            int(conv_state.get("turn") or 0) + 1
            if conv_state
            else (1 if meta_cid else 0)
        )
        with self._db_lock:
            conn = self._conn()
            try:
                conn.execute(
                    """UPDATE conversation_runs
                       SET partial_reply=?, partial_reasoning=?, status=?, error_message=?, finished_at=?
                       WHERE run_id=?""",
                    (
                        reply_text,
                        reasoning_text,
                        final_status,
                        error_message,
                        finished_at,
                        run_id,
                    ),
                )
                conn.execute(
                    """UPDATE conversation_messages
                       SET content=?, reasoning=?, rid=CASE WHEN ?!='' THEN ? ELSE rid END,
                           rcid=CASE WHEN ?!='' THEN ? ELSE rcid END, status=?
                       WHERE id=?""",
                    (
                        reply_text,
                        reasoning_text,
                        meta_rid,
                        meta_rid,
                        meta_rcid,
                        meta_rcid,
                        final_status,
                        assistant_msg_id,
                    ),
                )
                conn.execute(
                    """UPDATE conversations
                       SET rid=CASE WHEN ?!='' THEN ? ELSE rid END,
                           rcid=CASE WHEN ?!='' THEN ? ELSE rcid END,
                           tok26=CASE WHEN ?!='' THEN ? ELSE tok26 END,
                           turn=?,
                           status=?,
                           active_run_id='',
                           last_reply=?,
                           error_message=?,
                           updated_at=?
                       WHERE cid=?""",
                    (
                        meta_rid,
                        meta_rid,
                        meta_rcid,
                        meta_rcid,
                        meta_tok26,
                        meta_tok26,
                        next_turn,
                        final_status,
                        reply_text,
                        error_message,
                        finished_at,
                        current_cid,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        self._emit_event(
            "run_finished",
            {
                "run_id": run_id,
                "cid": current_cid,
                "status": final_status,
                "reply": reply_text,
                "reasoning": reasoning_text,
                "error": error_message,
                "finished_at": finished_at,
            },
            run_id=run_id,
        )

    def _flush_partial(
        self,
        run_id: str,
        cid: str,
        assistant_msg_id: int,
        reply: str,
        reasoning: str,
    ) -> None:
        now = time.time()
        with self._db_lock:
            conn = self._conn()
            try:
                conn.execute(
                    "UPDATE conversation_runs SET partial_reply=?, partial_reasoning=? WHERE run_id=?",
                    (reply, reasoning, run_id),
                )
                conn.execute(
                    "UPDATE conversation_messages SET content=?, reasoning=? WHERE id=?",
                    (reply, reasoning, assistant_msg_id),
                )
                conn.execute(
                    "UPDATE conversations SET last_reply=?, updated_at=? WHERE cid=?",
                    (reply, now, cid),
                )
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _msg_prefix_hash(messages: List[Dict[str, Any]]) -> str:
        """Compute a stable hash for an OpenAI message prefix."""
        canonical: List[Dict[str, Any]] = []
        for m in messages:
            if not isinstance(m, dict):
                continue
            item: Dict[str, Any] = {
                "role": m.get("role"),
                "content": m.get("content"),
            }
            if m.get("tool_call_id"):
                item["tool_call_id"] = m.get("tool_call_id")
            if m.get("name"):
                item["name"] = m.get("name")
            if m.get("tool_calls"):
                item["tool_calls"] = m.get("tool_calls")
            canonical.append(item)
        raw = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _format_incremental_task_prompt(
        delta_messages: List[Dict[str, Any]],
        all_messages: List[Dict[str, Any]],
        tools_active: bool,
    ) -> str:
        """Format only the new messages after a matched prefix for Gemini continuation."""
        from gpt_tool_bridge import _content_to_text, _format_tool_result

        call_id_to_name: Dict[str, str] = {}
        for msg in all_messages:
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                for tc in msg.get("tool_calls") or []:
                    if isinstance(tc, dict) and tc.get("id"):
                        fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
                        if fn.get("name"):
                            call_id_to_name[str(tc["id"])] = str(fn["name"])

        # Skip leading assistant turn(s) since Gemini server already holds its reply via rcid
        idx = 0
        while idx < len(delta_messages) and str(delta_messages[idx].get("role") or "").lower() == "assistant":
            idx += 1

        tool_blocks: List[str] = []
        user_blocks: List[str] = []
        for msg in delta_messages[idx:]:
            role = str(msg.get("role") or "").strip().lower()
            if role == "tool":
                call_id = str(msg.get("tool_call_id") or "")
                tname = str(msg.get("name") or call_id_to_name.get(call_id) or "tool")
                raw_out = _content_to_text(msg.get("content"))
                tool_blocks.append(_format_tool_result(tname, call_id, raw_out))
            elif role == "user":
                txt = _content_to_text(msg.get("content")).strip()
                if txt:
                    user_blocks.append(txt)
            elif role == "assistant":
                txt = _content_to_text(msg.get("content")).strip()
                if txt:
                    user_blocks.append(f"[Assistant]\n{txt}")

        sections: List[str] = []
        if tool_blocks:
            sections.append("[Tool Results]\n" + "\n\n".join(tool_blocks))
        if user_blocks:
            sections.append("\n\n".join(user_blocks))
        if tools_active and tool_blocks and not user_blocks:
            sections.append(
                "Proceed with the next step. If you need another tool, respond ONLY with a ```tool_call``` block."
            )
        return "\n\n".join(sections).strip()

    def _find_task_session(
        self, messages: List[Dict[str, Any]], model: str
    ) -> Optional[Dict[str, Any]]:
        """Find the longest matching cached Gemini continuation session for messages."""
        with self._task_sessions_lock:
            if not self._task_sessions:
                return None
            best: Optional[Dict[str, Any]] = None
            best_len = -1
            for sess in self._task_sessions.values():
                if sess.get("model") != model:
                    continue
                cnt = int(sess.get("msg_count") or 0)
                if cnt <= 0 or cnt >= len(messages) or cnt <= best_len:
                    continue
                if self._msg_prefix_hash(messages[:cnt]) == sess.get("prefix_hash"):
                    best = dict(sess)
                    best_len = cnt
            return best

    def _save_task_session(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        account: Dict[str, Any],
        meta: Dict[str, str],
        turn_idx: int,
    ) -> None:
        cid = meta.get("cid") or ""
        rid = meta.get("rid") or ""
        rcid = meta.get("rcid") or ""
        if not (cid.startswith("c_") and rid and rcid):
            return
        prefix_hash = self._msg_prefix_hash(messages)
        now = time.time()
        with self._task_sessions_lock:
            self._task_sessions[cid] = {
                "cid": cid,
                "rid": rid,
                "rcid": rcid,
                "tok26": meta.get("tok26") or "",
                "turn": turn_idx + 1,
                "account_id": account["id"],
                "authuser": int(account.get("authuser") or 0),
                "model": model,
                "msg_count": len(messages),
                "prefix_hash": prefix_hash,
                "updated_at": now,
            }
            if len(self._task_sessions) > 64:
                oldest_cid = min(
                    self._task_sessions.keys(),
                    key=lambda k: self._task_sessions[k].get("updated_at", 0.0),
                )
                self._task_sessions.pop(oldest_cid, None)

    def stream_openai_task_chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gemini-4-hydrogen-task",
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = None,
        timeout: int = 180,
    ):
        """Stream OpenAI-compatible SSE lines using Gemini Task Mode (inner[49]=40) with multi-turn continuation."""
        from gpt_tool_bridge import (
            adapt_stream_chunks,
            normalize_tool_definitions,
            parse_tool_choice,
            prepare_tool_messages,
        )

        require_service_enabled("gemini")
        tool_defs = normalize_tool_definitions(tools)
        tc_mode, _forced = parse_tool_choice(tool_choice)
        allowed_names = {t["name"] for t in tool_defs}
        tools_active = bool(allowed_names) and tc_mode != "none"

        def _build_full_prompt() -> str:
            converted, _an, _md = prepare_tool_messages(
                messages, tools=tools, tool_choice=tool_choice
            )
            parts: List[str] = []
            for msg in converted:
                role = str(msg.get("role") or "user").strip().lower()
                content = str(msg.get("content") or "").strip()
                if not content:
                    continue
                if len(converted) == 1 and role == "user":
                    parts.append(content)
                else:
                    tag = {"system": "System", "user": "User", "assistant": "Assistant"}.get(
                        role, role.capitalize()
                    )
                    parts.append(f"[{tag}]\n{content}")
            return "\n\n".join(parts).strip()

        matched = self._find_task_session(messages, model)
        cont_session = None
        if matched:
            inc_prompt = self._format_incremental_task_prompt(
                messages[matched["msg_count"]:], messages, tools_active=tools_active
            )
            if inc_prompt:
                cont_session = matched
                prompt = inc_prompt
            else:
                prompt = _build_full_prompt()
        else:
            prompt = _build_full_prompt()

        spec = MODEL_SPECS.get(model, MODEL_SPECS["gemini-4-hydrogen-task"])
        hex_id = spec["hex"]
        m_code = spec["mode"]
        think = spec["think"]
        tool_code = spec.get("tool") or 40

        completion_id = f"chatcmpl-gemini-task-{uuid.uuid4().hex[:12]}"
        created_ts = int(time.time())

        def _execute_stream(prompt_text: str, cont: Optional[Dict[str, Any]]):
            if cont:
                account = self._get_account(
                    account_id=cont.get("account_id"),
                    authuser=cont.get("authuser"),
                )
                turn_idx = int(cont.get("turn") or 1)
                inner2 = [
                    cont["cid"],
                    cont["rid"],
                    cont["rcid"],
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    cont.get("tok26") or "",
                ]
            else:
                self.sync_cookie_from_hub_if_changed(force=False)
                account = self._get_account()
                turn_idx = 0
                inner2 = ["", "", "", None, None, None, None, None, None, ""]

            authuser = int(account.get("authuser") or 0)
            cookie = account["cookie"]
            sapisid = _cookie_value(cookie, "SAPISID")
            xsrf, bl = self._get_xsrf_and_bl(cookie, authuser)

            req_uuid = str(uuid.uuid4())
            header_uuid = str(uuid.uuid4())
            inner: List[Any] = [None] * 97
            inner[0] = [prompt_text, 0, None, None, None, None, 0]
            inner[1] = ["en"]
            inner[2] = inner2
            inner[6] = [0]
            inner[7] = 1
            inner[10] = 1
            inner[11] = 0
            inner[17] = [[turn_idx]]
            inner[18] = 0
            inner[27] = 1
            inner[30] = [4]
            inner[41] = [1]
            inner[49] = tool_code
            inner[53] = 0
            inner[59] = req_uuid
            inner[61] = []
            inner[68] = 1
            inner[79] = m_code
            inner[80] = think
            inner[91] = 0
            inner[96] = 1 if think != 1 else 0

            form_body = urllib.parse.urlencode(
                {
                    "f.req": json.dumps(
                        [None, json.dumps(inner, separators=(",", ":"))],
                        separators=(",", ":"),
                    ),
                    "at": xsrf,
                }
            )
            base = _gemini_base(authuser)
            reqid = int(time.time() * 1000) % 900000 + 100000
            endpoint = (
                f"{base}/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate"
                f"?bl={urllib.parse.quote(bl)}&hl=en&_reqid={reqid}&rt=c"
            )
            model_hdr = (
                f'[1,null,null,null,"{hex_id}",null,null,0,[4,5,6,8],'
                f'null,null,1,null,null,{m_code},{think},"{header_uuid}"]'
            )
            headers = {
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Origin": "https://gemini.google.com",
                "Referer": f"{base}/app",
                "X-Same-Domain": "1",
                "X-Goog-AuthUser": str(authuser),
                "Cookie": cookie,
                "x-goog-ext-73010989-jspb": "[0]",
                "x-goog-ext-73010990-jspb": "[0,0,0]",
                "x-goog-ext-525001261-jspb": model_hdr,
                "x-goog-ext-525005358-jspb": f'["{req_uuid}",1]',
            }
            if sapisid:
                headers["Authorization"] = _make_sapisidhash(sapisid)

            print(
                f"[Gemini Task] {'续接' if cont else '新建'}会话 "
                f"(turn={turn_idx}, cid={cont['cid'] if cont else 'new'}, prompt_chars={len(prompt_text)})",
                flush=True,
            )

            resp = self._curl_request(
                "POST",
                endpoint,
                retries=2,
                data=form_body,
                headers=headers,
                timeout=timeout,
                stream=True,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"StreamGenerate HTTP {resp.status_code}")

            best_text = ""
            best_reasoning = ""
            latest_meta: Dict[str, str] = {}
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = (
                    raw_line.decode("utf-8", errors="replace")
                    if isinstance(raw_line, (bytes, bytearray))
                    else str(raw_line)
                )
                texts, reasoning, lmeta = _extract_texts_and_reasoning_from_line(line)
                latest_meta.update(lmeta)
                delta_obj: Dict[str, Any] = {}
                if reasoning and len(reasoning) > len(best_reasoning):
                    if reasoning.startswith(best_reasoning):
                        delta_obj["reasoning_content"] = reasoning[len(best_reasoning):]
                    else:
                        delta_obj["reasoning_content"] = reasoning
                    best_reasoning = reasoning
                for t in texts:
                    if len(t) > len(best_text):
                        if t.startswith(best_text):
                            delta_obj["content"] = t[len(best_text):]
                        else:
                            delta_obj["content"] = t
                        best_text = t
                if delta_obj:
                    yield {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created_ts,
                        "model": model,
                        "choices": [{"index": 0, "delta": delta_obj, "finish_reason": None}],
                    }

            if not best_text and cont:
                raise RuntimeError("续接返回空响应")
            self._save_task_session(messages, model, account, latest_meta, turn_idx)

        def _raw_chunks_with_fallback():
            emitted_any = False
            try:
                for ch in _execute_stream(prompt, cont_session):
                    emitted_any = True
                    yield ch
            except Exception as err:
                es = str(err).lower()
                if not emitted_any and ("snlm0e" in es or "302" in es or "401" in es or "cookie" in es):
                    if self.sync_cookie_from_hub_if_changed(force=True):
                        for ch in _execute_stream(prompt if not cont_session else _build_full_prompt(), cont_session): yield ch
                        return
                if cont_session and not emitted_any:
                    print(
                        f"⚠️ [Gemini Task] 续接失败 ({err})，自动回退为全量单轮发送",
                        flush=True,
                    )
                    for ch in _execute_stream(_build_full_prompt(), None):
                        yield ch
                else:
                    raise

        for chunk in adapt_stream_chunks(
            _raw_chunks_with_fallback(), model=model, allowed_names=allowed_names, mode=tc_mode
        ):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


gemini_conv_manager = GeminiConversationManager()
