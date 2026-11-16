import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path

import aistudio_remote_sync as sync
from aistudio_remote_sync import active_task_for, choose_accounts, cookie_fingerprint


class RemoteSyncTests(unittest.TestCase):
    def test_fingerprint_ignores_order_but_detects_value_change(self):
        cookies = [dict(name="SID", value="secret-a", domain=".google.com", path="/"),
                   dict(name="SAPISID", value="secret-b", domain=".google.com", path="/")]
        self.assertEqual(cookie_fingerprint(cookies), cookie_fingerprint(list(reversed(cookies))))
        changed = [dict(c) for c in cookies]
        changed[0]["value"] = "new-secret"
        self.assertNotEqual(cookie_fingerprint(cookies), cookie_fingerprint(changed))

    def test_unrelated_google_cookie_does_not_trigger_sync(self):
        cookies = [dict(name="SID", value="session", domain=".google.com", path="/")]
        self.assertEqual(cookie_fingerprint(cookies), cookie_fingerprint(cookies + [
            dict(name="NID", value="changing", domain=".google.com", path="/")]))

    def test_only_matched_enabled_idle_accounts_are_selected(self):
        local = {"a@example.com": ("a@example.com", 0), "b@example.com": ("b@example.com", 1)}
        remote = [dict(id="a@example.com", label="a@example.com", enabled=True, active_requests=0, state="ready"),
                  dict(id="b@example.com", label="b@example.com", enabled=True, active_requests=1, state="auth_required"),
                  dict(id="other@example.com", enabled=True, active_requests=0, state="auth_required")]
        self.assertEqual([x[0]["id"] for x in choose_accounts(local, remote, [], {}, "hash")], ["a@example.com"])
        self.assertEqual(choose_accounts(local, remote, [], {"a@example.com": "hash"}, "hash"), [])
        remote[0]["state"] = "auth_required"
        self.assertEqual(len(choose_accounts(local, remote, [], {"a@example.com": "hash"}, "hash")), 1)

    def test_existing_pending_task_prevents_duplicate(self):
        account = dict(id="a@example.com", label="a@example.com")
        tasks = [dict(state="running", items=[dict(label="a@example.com")])]
        self.assertTrue(active_task_for(tasks, account))

    def test_identity_mismatch_never_submits_cookies(self):
        class Tunnel:
            def terminate(self):
                pass
            def wait(self, timeout):
                return 0

        calls = []
        def request(url, *, payload=None, timeout=15):
            calls.append((url, payload is not None))
            if "18888" in url:
                return {"success": True, "cookies": [dict(name="SID", value="secret", domain=".google.com", path="/")]}
            if url.endswith("/api/accounts"):
                return {"accounts": [dict(id="a@example.com", label="a@example.com", enabled=True, state="ready", active_requests=0)]}
            if url.endswith("/api/accounts/tasks"):
                return {"tasks": []}
            raise AssertionError("unexpected request")

        with tempfile.TemporaryDirectory() as directory, \
             patch.object(sync, "STATE", Path(directory) / "state.json"), \
             patch.object(sync, "json_request", side_effect=request), \
             patch.object(sync, "ssh_tunnel", return_value=(Tunnel(), "http://127.0.0.1:1234")), \
             patch.object(sync, "load_local_accounts", return_value={"a@example.com": ("a@example.com", 0)}), \
             patch.object(sync, "blocked_accounts", return_value=set()), \
             patch.object(sync, "verify_identity", return_value=False):
            sync.sync_once({})
        self.assertFalse(any(is_post for _, is_post in calls))
        self.assertFalse(any("/aistudio/auto_fetch" in url for url, _ in calls))


if __name__ == "__main__":
    unittest.main()
