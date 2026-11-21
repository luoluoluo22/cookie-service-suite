"""
Bilibili 服务接口实现
基于浏览器实时 Cookie 调用哔哩哔哩 Web 端 API 及高清视频下载
"""

import os
import time
from datetime import datetime
import subprocess
import requests
from typing import Dict, Any, List, Optional
from cookie_bridge import CookieBridge
from web_api_switches import is_service_enabled, require_service_enabled


class BilibiliService:
    def __init__(self, bridge: Optional[CookieBridge] = None):
        self.bridge = bridge or CookieBridge()
        self.cookie_header = ""
        self.cookie_dict = {}
        if is_service_enabled("bilibili"):
            try:
                self.cookie_header = self.bridge.get_cookies_header("bilibili.com")
                self.cookie_dict = self.bridge.get_cookies_dict("bilibili.com")
            except Exception:
                pass

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
            "Cookie": self.cookie_header
        })

    def refresh_cookies_from_bridge(self, force: bool = True) -> str:
        """从 Cookie Hub 提取最新 B 站 Cookie 并更新会话"""
        require_service_enabled("bilibili")
        if self.cookie_header and not force:
            return self.cookie_header
        self.cookie_header = self.bridge.get_cookies_header("bilibili.com")
        try:
            self.cookie_dict = self.bridge.get_cookies_dict("bilibili.com")
        except Exception:
            self.cookie_dict = {}
        self.session.headers["Cookie"] = self.cookie_header
        return self.cookie_header

    def _ensure_cookies(self, force: bool = False):
        require_service_enabled("bilibili")
        if force or not self.cookie_header:
            self.refresh_cookies_from_bridge(force=True)

    def refresh_auth(self) -> Dict[str, Any]:
        """强制从浏览器刷新 B 站登录态并返回账号摘要"""
        require_service_enabled("bilibili")
        hdr = self.refresh_cookies_from_bridge(force=True)
        uinfo = self.get_user_info()
        return {
            "success": True,
            "cookie_length": len(hdr),
            "uname": uinfo.get("uname", ""),
            "mid": uinfo.get("mid", 0),
        }

    def get_user_info(self) -> Dict[str, Any]:
        """获取当前登录账号的完整个人中心信息"""
        self._ensure_cookies()
        url = "https://api.bilibili.com/x/web-interface/nav"
        for retry in range(2):
            resp = self.session.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            nav_data = data.get("data", {}) if isinstance(data, dict) else {}
            if data.get("code") == 0 and nav_data.get("isLogin") is not False:
                return nav_data
            if retry == 0:
                try:
                    self.refresh_cookies_from_bridge(force=True)
                    continue
                except Exception:
                    pass
            msg = data.get("message") or ("账号未登录" if nav_data.get("isLogin") is False else "未知错误")
            raise RuntimeError(f"获取 B 站用户信息失败: {msg}")

    def get_video_info(self, bvid: str) -> Dict[str, Any]:
        """获取视频的基础信息与分P列表 (含 cid)"""
        url = "https://api.bilibili.com/x/web-interface/view"
        resp = self.session.get(url, params={"bvid": bvid}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取视频信息失败: {data.get('message')}")
        return data.get("data", {})

    def get_play_url(self, bvid: str, cid: Optional[int] = None, qn: int = 116) -> Dict[str, Any]:
        """
        获取视频播放直链流 (qn 80=1080P, 112=1080P+, 116=1080P60, 120=4K超清)
        拥有大会员 Cookie 凭证可直接获取高码率视频流
        """
        if cid is None:
            info = self.get_video_info(bvid)
            cid = info["cid"]

        url = "https://api.bilibili.com/x/player/playurl"
        params = {
            "bvid": bvid,
            "cid": cid,
            "qn": qn,
            "fnval": 16,  # 16 代表 dash 格式, 支持更高画质分离流
            "fnver": 0,
            "fourk": 1
        }
        resp = self.session.get(url, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def download_video_hd(self, video_url: str, output_dir: str = "./downloads") -> str:
        """
        使用 yt-dlp 结合实时 Cookie 自动下载最高画质视频 (1080P/4K)
        """
        os.makedirs(output_dir, exist_ok=True)
        cookie_file = os.path.join(output_dir, "bili_cookies.txt")
        self.bridge.export_netscape_file("bilibili.com", cookie_file)

        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "--cookies", cookie_file,
            "-o", output_template,
            "--no-playlist",
            video_url
        ]

        print(f"🎬 正在调用 yt-dlp 下载视频: {video_url}")
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res.returncode != 0:
            raise RuntimeError(f"yt-dlp 下载失败: {res.stderr}")
        return res.stdout

    @staticmethod
    def _format_due_ts(raw_ts: Any) -> str:
        try:
            ts = float(raw_ts)
        except (TypeError, ValueError):
            return ""
        if ts <= 0:
            return ""
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except Exception:
            return ""

    @classmethod
    def _parse_vip_info(cls, nav_data: Dict[str, Any]) -> Dict[str, Any]:
        vip_obj = nav_data.get("vip") if isinstance(nav_data.get("vip"), dict) else {}

        raw_type = nav_data.get("vipType")
        if raw_type is None:
            raw_type = vip_obj.get("type", 0)
        try:
            vip_type = int(raw_type or 0)
        except (TypeError, ValueError):
            vip_type = 0

        raw_status = nav_data.get("vipStatus")
        if raw_status is None:
            raw_status = vip_obj.get("status", 0)
        try:
            vip_status = int(raw_status or 0)
        except (TypeError, ValueError):
            vip_status = 0

        raw_label = nav_data.get("vip_label") if nav_data.get("vip_label") is not None else vip_obj.get("label")
        if isinstance(raw_label, dict):
            vip_label_text = str(raw_label.get("text") or "").strip()
        else:
            vip_label_text = str(raw_label or "").strip()

        due_raw = nav_data.get("vipDueDate") or vip_obj.get("due_date") or 0
        expire_at = cls._format_due_ts(due_raw)

        label_is_member = bool(
            vip_label_text and "普通" not in vip_label_text and "未" not in vip_label_text
        )
        is_member = vip_status == 1 and (vip_type > 0 or label_is_member)

        if is_member:
            if vip_type == 2 or "年度" in vip_label_text:
                plan_tier = "年度大会员"
                membership_label = vip_label_text or "年度大会员"
            else:
                plan_tier = "大会员"
                membership_label = vip_label_text or "大会员"
        else:
            plan_tier = "FREE"
            membership_label = "普通用户"

        return {
            "vip_type": vip_type,
            "vip_status": vip_status,
            "is_member": is_member,
            "plan_tier": plan_tier,
            "membership_label": membership_label,
            "expire_at": expire_at,
        }

    def get_dashboard_accounts(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """返回供全平台账号看板消费的标准化 B 站账号列表（未登录/断连时安全返回空列表）"""
        if not is_service_enabled("bilibili"):
            return []
        if refresh:
            try:
                self.refresh_cookies_from_bridge(force=True)
            except Exception:
                pass

        try:
            nav = self.get_user_info()
        except Exception:
            return []

        if not isinstance(nav, dict) or nav.get("isLogin") is False:
            return []

        mid = nav.get("mid")
        uname = str(nav.get("uname") or "").strip()
        if not uname and not mid:
            return []

        raw_id = str(mid or uname or "browser")
        display_name = uname or f"UID {raw_id}"
        email = str(nav.get("email") or "").strip()

        vip_info = self._parse_vip_info(nav)

        level_info = nav.get("level_info") if isinstance(nav.get("level_info"), dict) else {}
        level = level_info.get("current_level")
        coins = nav.get("money")
        wallet = nav.get("wallet") if isinstance(nav.get("wallet"), dict) else {}
        bcoin = wallet.get("bcoin_balance")
        coupon = wallet.get("coupon_balance")

        summary_parts = []
        if level is not None:
            summary_parts.append(f"Lv.{level}")
        if coins is not None:
            summary_parts.append(f"硬币 {coins}")
        if bcoin is not None:
            summary_parts.append(f"B币 {bcoin}")
        if coupon:
            summary_parts.append(f"券 {coupon}")
        quota_summary = " · ".join(summary_parts) if summary_parts else "已登录"

        note_parts = []
        if mid:
            note_parts.append(f"UID: {mid}")
        if vip_info["is_member"] and vip_info["expire_at"]:
            note_parts.append(f"到期: {vip_info['expire_at']}")
        elif vip_info["vip_type"] > 0 and vip_info["vip_status"] == 0:
            note_parts.append("大会员已过期")

        return [
            {
                "platform": "bilibili",
                "platform_name": "哔哩哔哩",
                "id": f"bilibili:{raw_id}",
                "raw_id": raw_id,
                "name": display_name,
                "email": email,
                "is_member": vip_info["is_member"],
                "plan_tier": vip_info["plan_tier"],
                "membership_label": vip_info["membership_label"],
                "quota_summary": quota_summary,
                "status": "ready",
                "visible": True,
                "note": " · ".join(note_parts),
                "source": "browser_session",
                "login_url": "https://www.bilibili.com/",
                "updated_at": int(time.time()),
                "details": {
                    "mid": mid,
                    "uname": uname,
                    "face": str(nav.get("face") or ""),
                    "level": level,
                    "coins": coins,
                    "bcoin": bcoin,
                    "coupon": coupon,
                    "vip_type": vip_info["vip_type"],
                    "vip_status": vip_info["vip_status"],
                    "expire_at": vip_info["expire_at"],
                },
            }
        ]

    def refresh_dashboard_accounts(self) -> List[Dict[str, Any]]:
        """强制刷新浏览器凭证并返回最新 B 站账号列表"""
        require_service_enabled("bilibili")
        return self.get_dashboard_accounts(refresh=True)
