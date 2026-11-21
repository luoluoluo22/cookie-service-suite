# -*- coding: utf-8 -*-
"""Persistent API access token store for Cookie Service Suite."""

import datetime
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
from typing import Dict, Optional

DEFAULT_TOKEN_PATH = Path(__file__).resolve().parent / "runtime_state" / "api_token.json"
TOKEN_PREFIX = "sk-css-"


def generate_token() -> str:
    """Create a cryptographically random API access token."""
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(24)}"


def mask_token(token: str) -> str:
    """Return a display-safe masked preview of a token."""
    value = str(token or "")
    if len(value) <= 12:
        return "*" * len(value)
    return f"{value[:10]}...{value[-4:]}"


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


class AccessTokenStore:
    """Thread-safe persistent store for the Cookie Service Suite API token."""

    def __init__(self, token_path: Optional[Path] = None):
        self.token_path = Path(token_path) if token_path else DEFAULT_TOKEN_PATH
        self._lock = threading.Lock()
        self._state: Optional[Dict[str, str]] = None

    def _read_disk(self) -> Optional[Dict[str, str]]:
        try:
            raw = json.loads(self.token_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        if not isinstance(raw, dict):
            return None
        token = str(raw.get("token") or "").strip()
        if not token:
            return None
        now = _utc_now_iso()
        return {
            "token": token,
            "created_at": str(raw.get("created_at") or now),
            "updated_at": str(raw.get("updated_at") or now),
        }

    def _write_disk(self, state: Dict[str, str]) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.token_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, self.token_path)

    def _ensure_state_locked(self) -> Dict[str, str]:
        if self._state is None:
            loaded = self._read_disk()
            if loaded is None:
                now = _utc_now_iso()
                loaded = {
                    "token": generate_token(),
                    "created_at": now,
                    "updated_at": now,
                }
                self._write_disk(loaded)
            self._state = loaded
        return self._state

    def get_token(self) -> str:
        """Return the active access token (env override takes precedence)."""
        env_token = os.environ.get("COOKIE_SUITE_TOKEN", "").strip()
        if env_token:
            return env_token
        with self._lock:
            return self._ensure_state_locked()["token"]

    def get_info(self) -> Dict[str, object]:
        """Return active token metadata for authenticated control-panel queries."""
        env_token = os.environ.get("COOKIE_SUITE_TOKEN", "").strip()
        with self._lock:
            state = self._ensure_state_locked()
            active = env_token or state["token"]
            return {
                "token": active,
                "masked": mask_token(active),
                "created_at": state["created_at"],
                "updated_at": state["updated_at"],
                "env_override": bool(env_token),
            }

    def rotate(self) -> Dict[str, object]:
        """Generate and persist a fresh access token."""
        with self._lock:
            prev = self._ensure_state_locked()
            now = _utc_now_iso()
            state = {
                "token": generate_token(),
                "created_at": prev.get("created_at") or now,
                "updated_at": now,
            }
            self._write_disk(state)
            self._state = state
            return {
                "token": state["token"],
                "masked": mask_token(state["token"]),
                "created_at": state["created_at"],
                "updated_at": state["updated_at"],
                "env_override": bool(os.environ.get("COOKIE_SUITE_TOKEN", "").strip()),
            }

    def verify(self, candidate: Optional[str]) -> bool:
        """Constant-time comparison against the active token."""
        if not candidate:
            return False
        expected = self.get_token()
        return hmac.compare_digest(str(candidate).strip().encode("utf-8"), expected.encode("utf-8"))
