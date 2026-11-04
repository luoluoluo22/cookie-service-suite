"""
Google Gemini Web 服务调用与多账号统一调度模块
支持 Google 浏览器多账号登录机制（/u/0, /u/1, /u/2, /u/3...）
支持多账号自动轮转（Load Balancing）、故障熔断切换与 OpenAI 兼容接口
"""

import os
import sys
import time
import json
import sqlite3
import subprocess
import urllib.request
import re
import ssl
import asyncio
from typing import Optional, Dict, Any, List, Tuple

# 保证本地回环网络请求不走外部代理（Clash 等），避免 502 Bad Gateway
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"
_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

_CANDIDATE_SRC = os.path.join(
    os.path.dirname(__file__), "candidate_repos", "Gemini-API-HanaokaYuzu", "src"
)
if os.path.exists(_CANDIDATE_SRC) and _CANDIDATE_SRC not in sys.path:
    sys.path.insert(0, _CANDIDATE_SRC)

from cookie_bridge import CookieBridge


class GeminiService:
    """Gemini 网页端单账号服务客户端，支持通过本地 Cookie Hub 自动提取凭证调用。"""

    def __init__(
        self,
        bridge_url: str = "http://127.0.0.1:18888",
        proxy: Optional[str] = "http://127.0.0.1:7897",
    ):
        self.bridge = CookieBridge(bridge_url=bridge_url)
        self.proxy = proxy
        self.client = None
        self._loop = None

    def _get_auth_cookies(self) -> Dict[str, str]:
        cookies_dict = self.bridge.get_cookies_dict("google.com")
        return {
            "psid": cookies_dict.get("__Secure-1PSID", ""),
            "psidts": cookies_dict.get("__Secure-1PSIDTS", ""),
        }

    async def _ensure_client(self):
        from gemini_webapi import GeminiClient

        curr_loop = asyncio.get_running_loop()
        if self.client is None or self._loop != curr_loop:
            self._loop = curr_loop
            auth = self._get_auth_cookies()
            if not auth["psid"]:
                raise RuntimeError(
                    "未能从浏览器中检测到 __Secure-1PSID，请确认浏览器中已登录 Google 账号！"
                )
            self.client = GeminiClient(
                secure_1psid=auth["psid"],
                secure_1psidts=auth["psidts"],
                proxy=self.proxy,
            )
            await self.client.init(timeout=30, auto_close=False, auto_refresh=False)
        return self.client

    async def async_ask(self, prompt: str, model: Optional[str] = None) -> str:
        """异步提问并获取回复文本。"""
        client = await self._ensure_client()
        response = await client.generate_content(prompt, model=model)
        return response.text

    def ask(self, prompt: str, model: Optional[str] = None) -> str:
        """同步提问快捷接口。"""
        return asyncio.run(self.async_ask(prompt, model=model))

    async def async_get_quota(self) -> Dict[str, Any]:
        """获取账号额度。"""
        client = await self._ensure_client()
        return client.quotas or {}

    def get_quota(self) -> Dict[str, Any]:
        """同步获取账号额度。"""
        return asyncio.run(self.async_get_quota())


class MultiAccountGeminiPool:
    """
    Gemini 浏览器多账号池化调度管理器。
    
    统一接管浏览器中登录的多个 Google 账号（如 /u/0, /u/1, /u/2, /u/3）：
    1. 从 Cookie Hub 自动提取完整安全凭据；
    2. 按照 authuser 裂变为独立账号池，配置最久未用（LRU）轮转；
    3. 支持故障熔断换号与额度倍增（4x 额度）；
    4. 对外提供标准 OpenAI 兼容接口 (/v1/chat/completions) 与 Python 便捷调用。
    """

    def __init__(
        self,
        bridge_url: str = "http://127.0.0.1:18888",
        port: int = 18083,
        proxy: str = "http://127.0.0.1:7897",
        account_count: int = 4,
        api_key: str = "sk-gemini-cookie-suite",
    ):
        self.bridge = CookieBridge(bridge_url=bridge_url)
        self.port = port
        self.proxy = proxy
        self.account_count = account_count
        self.api_key = api_key
        
        self.base_dir = os.path.join(
            os.path.dirname(__file__), "candidate_repos", "gemini-web2api-go"
        )
        self.db_path = os.path.join(self.base_dir, "gemini_pool.db")
        self.config_path = os.path.join(self.base_dir, "config_pool.json")
        self.exe_path = os.path.join(self.base_dir, "gemini-web2api.exe")
        self.proc: Optional[subprocess.Popen] = None

    def _extract_cookie_header(self) -> str:
        """从 Cookie Hub 提取组装 Google 必要会话鉴权串。"""
        url = f"{self.bridge.bridge_url}/cookies?domain=google.com"
        with _LOCAL_OPENER.open(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            cookies = data.get("cookies", [])

        target_keys = [
            "SID",
            "HSID",
            "SSID",
            "APISID",
            "SAPISID",
            "__Secure-1PSID",
            "__Secure-1PSIDTS",
            "__Secure-1PSIDCC",
        ]
        parts = []
        for k in target_keys:
            v = next((c["value"] for c in cookies if c.get("name") == k), "")
            if v:
                parts.append(f"{k}={v}")

        if not parts:
            raise RuntimeError("未能提取到有效的 Google 鉴权 Cookie！")
        return "; ".join(parts)

    def init_database(self, force_refresh: bool = False):
        """初始化多账号数据库与池化配额表。"""
        cookie_str = self._extract_cookie_header()
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS accounts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            label         TEXT NOT NULL DEFAULT '',
            cookie        TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'enabled',
            note          TEXT NOT NULL DEFAULT '',
            created_at    INTEGER NOT NULL,
            last_used_at  INTEGER NOT NULL DEFAULT 0,
            last_ok_at    INTEGER NOT NULL DEFAULT 0,
            last_error    TEXT NOT NULL DEFAULT '',
            fail_count    INTEGER NOT NULL DEFAULT 0,
            proxy_id      INTEGER NOT NULL DEFAULT 0,
            authuser      INTEGER NOT NULL DEFAULT 0
        );
        """
        )
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS kv (
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        );
        """
        )
        cur.execute(
            "INSERT OR REPLACE INTO kv (k, v) VALUES ('api_key', ?)", (self.api_key,)
        )

        now = int(time.time())
        existing = cur.execute("SELECT authuser FROM accounts").fetchall()
        existing_users = {row[0] for row in existing}

        for u in range(self.account_count):
            if u not in existing_users or force_refresh:
                if u in existing_users:
                    cur.execute(
                        "UPDATE accounts SET cookie=?, status='enabled', fail_count=0 WHERE authuser=?",
                        (cookie_str, u),
                    )
                else:
                    cur.execute(
                        """INSERT INTO accounts (label, cookie, status, note, created_at, authuser)
                           VALUES (?, ?, 'enabled', ?, ?, ?)""",
                        (
                            f"Google Account [u/{u}]",
                            cookie_str,
                            f"Browser Multi-Account Index {u}",
                            now,
                            u,
                        ),
                    )

        conn.commit()
        conn.close()

    def generate_config(self):
        """生成服务的 runtime 配置文件。"""
        config = {
            "port": self.port,
            "host": "127.0.0.1",
            "db_path": self.db_path,
            "admin_enabled": True,
            "admin_token": "admin_gemini_pool",
            "impersonate": "chrome_146",
            "default_model": "gemini-3.5-flash-lite",
            "proxy": self.proxy,
            "log_requests": True,
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def is_running(self) -> bool:
        """检查多账号服务是否正在运行。"""
        try:
            with _LOCAL_OPENER.open(
                f"http://127.0.0.1:{self.port}/", timeout=2
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

    def start(self, wait_timeout: int = 15) -> bool:
        """启动多账号统一代理服务。"""
        if self.is_running():
            return True

        if not os.path.exists(self.exe_path):
            raise FileNotFoundError(f"未找到 gemini-web2api.exe 核心二进制: {self.exe_path}")

        self.init_database()
        self.generate_config()

        log_path = os.path.join(self.base_dir, "gemini_pool.log")
        log_file = open(log_path, "a", encoding="utf-8", errors="replace")

        self.proc = subprocess.Popen(
            [self.exe_path, "-config", self.config_path],
            cwd=self.base_dir,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

        for _ in range(wait_timeout):
            time.sleep(1)
            if self.is_running():
                return True
        return False

    def stop(self):
        """停止多账号统一服务。"""
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()
            self.proc = None

    def fetch_account_profile(
        self, authuser: int, cookie_override: Optional[str] = None
    ) -> Tuple[str, str]:
        """通过抓取 Google Gemini /u/{authuser}/app 页面，提取该槽位的 Google 真实用户昵称与 Gmail 邮箱。"""
        cookie = cookie_override
        if not cookie:
            try:
                conn = sqlite3.connect(self.db_path)
                row = conn.execute(
                    "SELECT cookie FROM accounts WHERE authuser = ?", (authuser,)
                ).fetchone()
                conn.close()
                if row and row[0]:
                    cookie = row[0]
            except Exception:
                pass

        if not cookie:
            return "", ""

        url = f"https://gemini.google.com/u/{authuser}/app"
        req = urllib.request.Request(
            url,
            headers={
                "Cookie": cookie,
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
            },
        )
        proxy_handler = (
            urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy})
            if self.proxy
            else urllib.request.ProxyHandler({})
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))

        try:
            with opener.open(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # 匹配 aria-label="Google Account: Alena Bray  &#10;(wargowskytom404@gmail.com)" 或中文 帐号：
            m = re.search(
                r'Google\s*[^:："]*[:：]\s*([^&"\(]+?)\s*(?:&#10;|\n)?\(([^)]+@gmail\.com)\)',
                html,
            )
            if m:
                name = m.group(1).strip()
                email = m.group(2).strip()
                return name, email

            # 兜底匹配 aria-label 中任何邮箱
            m2 = re.search(r'aria-label="[^"]*?\(([^)]+@gmail\.com)\)"', html)
            if m2:
                return "", m2.group(1).strip()

            # 兜底全页面正则提取 Gmail
            gm = re.findall(r"[\w\.-]+@gmail\.com", html)
            if gm:
                return "", gm[0]
        except Exception as e:
            print(f"⚠️ [Profile 获取] u/{authuser} 提取失败: {e}")

        return "", ""

    def sync_account_profiles(self) -> Dict[int, Dict[str, str]]:
        """批量同步并更新 SQLite 数据库中所有 Google 账号的真实昵称与邮箱。"""
        results = {}
        if not os.path.exists(self.db_path):
            self.init_database()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        rows = cur.execute("SELECT authuser FROM accounts").fetchall()
        conn.close()

        for (u,) in rows:
            name, email = self.fetch_account_profile(u)
            if email:
                if name:
                    new_label = f"{name} ({email})"
                else:
                    new_label = email
                note = f"authuser={u} | {email}"
            else:
                new_label = f"Google Account [u/{u}]"
                note = f"Browser Multi-Account Index {u}"

            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "UPDATE accounts SET label = ?, note = ? WHERE authuser = ?",
                (new_label, note, u),
            )
            conn.commit()
            conn.close()
            results[u] = {"name": name, "email": email, "label": new_label}

        return results

    def list_accounts(self) -> List[Dict[str, Any]]:
        """获取账号池内所有账号的状态、真实名称与轮转统计。"""
        if not os.path.exists(self.db_path):
            self.init_database()

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT id, label, authuser, status, last_used_at, fail_count, note 
               FROM accounts ORDER BY authuser ASC"""
        ).fetchall()
        conn.close()

        res = []
        for r in rows:
            label_val = r[1]
            name = ""
            email = ""
            if "(" in label_val and label_val.endswith(")"):
                parts = label_val.rsplit("(", 1)
                name = parts[0].strip()
                email = parts[1].rstrip(")").strip()
            elif "@" in label_val:
                email = label_val.strip()

            res.append(
                {
                    "id": r[0],
                    "label": label_val,
                    "name": name,
                    "email": email,
                    "auth_user": r[2],
                    "url_prefix": f"https://gemini.google.com/u/{r[2]}",
                    "status": r[3],
                    "last_used_at": r[4],
                    "fail_count": r[5],
                    "note": r[6],
                }
            )
        return res

    def ask(self, prompt: str, model: str = "gemini-3.5-flash-lite", timeout: int = 60) -> str:
        """
        通过统一池化通道提问。
        底层自动在已接入的 4 个账号之间执行 LRU 轮转调用。
        """
        details = self.ask_with_details(prompt=prompt, model=model, timeout=timeout)
        return details["reply"]

    def ask_with_details(
        self, prompt: str, model: str = "gemini-3.5-flash-lite", timeout: int = 60
    ) -> Dict[str, Any]:
        """
        通过统一池化通道提问，并返回包含实际调用账号、耗时等详细元数据。
        """
        if not self.is_running():
            started = self.start()
            if not started:
                raise RuntimeError("无法启动本地 Gemini 多账号池代理服务！")

        # 记录调用前最大的 requests 表 ID，用于匹配本次请求实际使用的账号
        prev_max_id = 0
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute("SELECT MAX(id) FROM requests").fetchone()
            if row and row[0]:
                prev_max_id = row[0]
            conn.close()
        except Exception:
            pass

        req_data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/chat/completions",
            data=json.dumps(req_data).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        t0 = time.time()
        with _LOCAL_OPENER.open(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            reply = data["choices"][0]["message"]["content"].strip()
        took_ms = int((time.time() - t0) * 1000)

        # 从 requests 表查询调度详情 (稍作等待确保 Go 异步协程完成写入)
        account_id = None
        account_label = None
        authuser = None
        time.sleep(0.3)
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                """SELECT account_id, account_label, total_ms, status 
                   FROM requests WHERE id > ? ORDER BY id DESC LIMIT 1""",
                (prev_max_id,),
            ).fetchone()
            if row:
                account_id = row[0]
                account_label = row[1]
                if row[2]:
                    took_ms = row[2]
            if account_id:
                acct_row = conn.execute(
                    "SELECT authuser FROM accounts WHERE id = ?", (account_id,)
                ).fetchone()
                if acct_row:
                    authuser = acct_row[0]
            conn.close()
        except Exception:
            pass

        return {
            "reply": reply,
            "account_id": account_id,
            "account_label": account_label,
            "authuser": authuser,
            "took_ms": took_ms,
            "model": model,
        }

    def check_account(self, account_id: int) -> Dict[str, Any]:
        """调用管理接口检测单个账号的会话凭证健康状态。"""
        url = f"http://127.0.0.1:{self.port}/admin/api/cookies/{account_id}/check"
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer admin_gemini_pool",
            },
        )
        with _LOCAL_OPENER.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def rotate_account(self, account_id: int) -> Dict[str, Any]:
        """强制触发单个账号的会话令牌主动保活轮换。"""
        url = f"http://127.0.0.1:{self.port}/admin/api/cookies/{account_id}/rotate"
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer admin_gemini_pool",
            },
        )
        with _LOCAL_OPENER.open(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def refresh_pool_cookies(self) -> str:
        """从前台 Cookie Hub 重新拉取最新凭证并更新多账号数据库。"""
        cookie_str = self._extract_cookie_header()
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE accounts SET cookie=?, status='enabled', fail_count=0 WHERE status!='deleted'",
            (cookie_str,),
        )
        conn.commit()
        conn.close()
        return cookie_str

    def list_recent_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近请求调度记录。"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT id, ts, model, account_id, account_label, status, total_ms, error 
               FROM requests ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()
        res = []
        for r in rows:
            res.append(
                {
                    "id": r[0],
                    "timestamp": r[1],
                    "model": r[2],
                    "account_id": r[3],
                    "account_label": r[4],
                    "status": r[5],
                    "total_ms": r[6],
                    "error": r[7],
                }
            )
        return res


if __name__ == "__main__":
    print("=== 初始化并测试 Google 4 账号统一池服务 ===")
    pool = MultiAccountGeminiPool(port=18083, account_count=4)
    print("1. 同步账号池状态...")
    pool.init_database(force_refresh=True)
    
    accounts = pool.list_accounts()
    print(f"已接入 {len(accounts)} 个 Google 账号槽位:")
    for a in accounts:
        print(f"  - [{a['auth_user']}] {a['label']} -> {a['url_prefix']} (状态: {a['status']})")
        
    print("\n2. 启动/校验多账号后台服务...")
    if pool.start():
        print(f"多账号统一服务已在 http://127.0.0.1:{pool.port} 运行！")
        print("\n3. 模拟连续问答测试多账号负载均衡...")
        for i in range(2):
            q = f"请用一句话回答：当前是第 {i+1} 次多账号轮询测试，状态正常吗？"
            print(f"\n提问 {i+1}: {q}")
            t0 = time.time()
            reply = pool.ask(q)
            print(f"回复 ({time.time()-t0:.2f}s):\n{reply}")
            
        print("\n4. 查看最新轮转状态:")
        for a in pool.list_accounts():
            print(f"  - [{a['auth_user']}] 上次调用时间戳: {a['last_used_at']}, 失败计数: {a['fail_count']}")
    else:
        print("服务启动失败，请检查端口与代理连接！")
