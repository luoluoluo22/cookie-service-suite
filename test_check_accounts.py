import sqlite3
import json
import urllib.request
import time

db_path = r"d:\Projects\cookie-service-suite\candidate_repos\gemini-web2api-go\gemini_pool.db"

# Check accounts
conn = sqlite3.connect(db_path)
cur = conn.cursor()
print("Accounts in gemini_pool.db:")
for row in cur.execute("SELECT id, label, authuser, status, last_used_at, fail_count FROM accounts").fetchall():
    print(" ", row)
conn.close()
