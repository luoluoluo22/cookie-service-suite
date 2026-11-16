import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aistudio_remote_sync as sync
from gemini_service import MultiAccountGeminiPool


class AccountControlTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.pool = MultiAccountGeminiPool(account_count=2)
        self.pool.db_path = str(Path(self.directory.name) / 'pool.db')
        self.pool.init_database(cookie_str='__Secure-1PSID=old')
        with closing(sqlite3.connect(self.pool.db_path)) as db, db:
            db.execute("UPDATE accounts SET label='One (one@example.com)', note='one@example.com' WHERE id=1")
            db.execute("UPDATE accounts SET label='Two (two@example.com)', note='two@example.com' WHERE id=2")

    def test_disabled_and_deleted_survive_refresh_and_block_sync(self):
        self.pool.set_account_status(1, 'disabled')
        self.pool.set_account_status(2, 'deleted')
        self.pool.init_database(force_refresh=True, cookie_str='__Secure-1PSID=new')
        with closing(sqlite3.connect(self.pool.db_path)) as db:
            rows = db.execute('SELECT status, cookie FROM accounts ORDER BY id').fetchall()
        self.assertEqual(rows, [('disabled', '__Secure-1PSID=old'), ('deleted', '')])
        with patch.object(sync, 'GEMINI_DB', Path(self.pool.db_path)):
            self.assertEqual(sync.blocked_accounts(), {'one@example.com', 'two@example.com'})
        with self.assertRaises(ValueError):
            self.pool._require_enabled_account(1)
        self.pool.set_account_status(1, 'enabled')
        with patch.object(sync, 'GEMINI_DB', Path(self.pool.db_path)):
            self.assertEqual(sync.blocked_accounts(), {'two@example.com'})
        with self.assertRaises(LookupError):
            self.pool.set_account_status(2, 'enabled')

    def test_profile_sync_skips_disabled_accounts(self):
        self.pool.set_account_status(1, 'disabled')
        with patch.object(self.pool, 'fetch_account_profile', return_value=('Two', 'two@example.com')) as fetch, \
             patch.object(self.pool, 'sync_account_usage'):
            self.pool.sync_account_profiles()
        fetch.assert_called_once_with(1)
        with closing(sqlite3.connect(self.pool.db_path)) as db:
            self.assertEqual(db.execute('SELECT status FROM accounts WHERE id=1').fetchone()[0], 'disabled')


if __name__ == '__main__':
    unittest.main()
