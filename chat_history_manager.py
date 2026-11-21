"""
Chat History & Audit Logging Manager for Cookie Service Suite.
Persistent SQLite storage with strict 100MB file size limit and FIFO pruning.
Note: No emoji characters in Python code per rule.
"""

import os
import json
import time
import sqlite3
import threading
import datetime
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME_DIR = os.path.join(BASE_DIR, "runtime_state")
os.makedirs(RUNTIME_DIR, exist_ok=True)

DB_PATH = os.path.join(RUNTIME_DIR, "chat_history.db")
MAX_DB_BYTES = 100 * 1024 * 1024  # 100MB limit


def extract_text_from_chunk(raw_chunk: Any) -> str:
    """Robust extractor that pulls text deltas from OpenAI SSE, Gemini, or raw chunks."""
    if isinstance(raw_chunk, bytes):
        text = raw_chunk.decode("utf-8", errors="replace")
    else:
        text = str(raw_chunk)

    extracted = []
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_part = line[5:].strip()
            if data_part == "[DONE]":
                continue
            try:
                obj = json.loads(data_part)
                # 1. OpenAI choices[0].delta.content
                if isinstance(obj, dict):
                    choices = obj.get("choices")
                    if isinstance(choices, list) and choices:
                        c0 = choices[0]
                        if isinstance(c0, dict):
                            delta = c0.get("delta")
                            if isinstance(delta, dict):
                                if "content" in delta and delta.get("content"):
                                    extracted.append(str(delta.get("content")))
                                    continue
                                if isinstance(delta.get("tool_calls"), list) and delta["tool_calls"]:
                                    for tc in delta["tool_calls"]:
                                        if isinstance(tc, dict):
                                            fn = tc.get("function") or {}
                                            if isinstance(fn, dict) and fn.get("name"):
                                                extracted.append(f"[tool_call: {fn.get('name')}({fn.get('arguments', '{}')})]")
                                    continue
                            if "text" in c0:
                                extracted.append(str(c0.get("text") or ""))
                                continue
                    # 2. Google Gemini candidates[0].content.parts[0].text
                    candidates = obj.get("candidates")
                    if isinstance(candidates, list) and candidates:
                        cand0 = candidates[0]
                        if isinstance(cand0, dict):
                            content_obj = cand0.get("content", {})
                            parts = content_obj.get("parts", []) if isinstance(content_obj, dict) else []
                            for p in parts:
                                if isinstance(p, dict) and "text" in p:
                                    extracted.append(str(p["text"]))
                            if extracted:
                                continue
                    # 3. Custom reply/delta
                    if "delta" in obj and isinstance(obj["delta"], str):
                        extracted.append(obj["delta"])
                        continue
                    if "reply" in obj and isinstance(obj["reply"], str):
                        extracted.append(obj["reply"])
                        continue
            except Exception:
                pass
    return "".join(extracted)


def extract_error_from_chunk(raw_chunk: Any) -> str:
    """Extract upstream SSE error message if the chunk represents an error event."""
    if isinstance(raw_chunk, bytes):
        text = raw_chunk.decode("utf-8", errors="replace")
    else:
        text = str(raw_chunk)

    for line in text.split("\n"):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data_part = line[5:].strip()
        if not data_part or data_part == "[DONE]":
            continue
        try:
            obj = json.loads(data_part)
        except Exception:
            continue
        if isinstance(obj, dict) and "error" in obj and obj["error"]:
            err = obj["error"]
            if isinstance(err, dict):
                return str(err.get("message") or json.dumps(err, ensure_ascii=False))
            return str(err)
    return ""


class ChatHistoryManager:
    """Thread-safe Chat History Manager backed by SQLite with 100MB cap."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(ChatHistoryManager, cls).__new__(cls)
                    cls._instance._init_db()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        self._write_lock = threading.Lock()
        with self._write_lock:
            conn = self._get_connection()
            try:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT,
                    created_at TEXT,
                    timestamp REAL,
                    endpoint TEXT,
                    model TEXT,
                    actual_model TEXT,
                    is_stream INTEGER DEFAULT 0,
                    status INTEGER DEFAULT 200,
                    latency_ms INTEGER DEFAULT 0,
                    prompt_summary TEXT,
                    messages_json TEXT,
                    response_text TEXT,
                    error_message TEXT,
                    meta_json TEXT
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_logs_ts ON chat_logs(timestamp DESC);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_logs_model ON chat_logs(model);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_logs_status ON chat_logs(status);")
                conn.commit()
            finally:
                conn.close()
        try:
            self.expire_stale_running(max_age_seconds=1800)
        except Exception:
            pass

    def expire_stale_running(self, max_age_seconds: int = 1800) -> int:
        """Mark long-abandoned in-flight rows (status 0 or 102) as timed out."""
        cutoff = time.time() - max(60, int(max_age_seconds))
        with self._write_lock:
            conn = self._get_connection()
            try:
                cur = conn.execute(
                    "UPDATE chat_logs SET status = 504, "
                    "error_message = CASE WHEN COALESCE(error_message, '') = '' THEN ? ELSE error_message END "
                    "WHERE status IN (0, 102) AND timestamp IS NOT NULL AND timestamp < ?",
                    ("任务中断或超时未完成", cutoff),
                )
                conn.commit()
                return cur.rowcount or 0
            except Exception as e:
                print(f"[ChatHistory] Failed to expire stale running chats: {e}")
                return 0
            finally:
                conn.close()

    def get_db_size_bytes(self) -> int:
        """Calculate total disk usage including WAL and SHM files."""
        total = 0
        for ext in ["", "-wal", "-shm"]:
            fpath = DB_PATH + ext
            if os.path.exists(fpath):
                try:
                    total += os.path.getsize(fpath)
                except OSError:
                    pass
        return total

    def _prune_if_exceeds_cap(self, conn: sqlite3.Connection):
        """If database files exceed 100MB, prune the oldest 20% records."""
        current_size = self.get_db_size_bytes()
        if current_size < MAX_DB_BYTES:
            return

        try:
            total_count = conn.execute("SELECT COUNT(1) FROM chat_logs").fetchone()[0]
            if total_count <= 10:
                return

            delete_count = max(int(total_count * 0.2), 1)
            oldest_cutoff_id_row = conn.execute(
                "SELECT id FROM chat_logs ORDER BY id ASC LIMIT 1 OFFSET ?",
                (delete_count - 1,)
            ).fetchone()

            if oldest_cutoff_id_row:
                cutoff_id = oldest_cutoff_id_row[0]
                conn.execute("DELETE FROM chat_logs WHERE id <= ?", (cutoff_id,))
                conn.commit()
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        except Exception:
            pass

    def record_chat(
        self,
        endpoint: str,
        model: str,
        messages: Any,
        response_text: str = "",
        status: int = 200,
        latency_ms: int = 0,
        is_stream: bool = False,
        actual_model: str = "",
        error_message: str = "",
        trace_id: str = "",
        meta: Optional[Dict[str, Any]] = None
    ) -> int:
        """Record a chat request and response into the audit log."""
        if not trace_id:
            trace_id = f"chat-{int(time.time() * 1000)}"

        now_ts = time.time()
        now_dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        prompt_summary = ""
        if isinstance(messages, str):
            prompt_summary = messages.strip()
            messages_json_str = json.dumps([{"role": "user", "content": messages}], ensure_ascii=False)
        elif isinstance(messages, list):
            for m in reversed(messages):
                if isinstance(m, dict) and m.get("role") == "user":
                    prompt_summary = str(m.get("content", "")).strip()
                    break
            if not prompt_summary and messages:
                first = messages[0]
                prompt_summary = str(first.get("content", "")) if isinstance(first, dict) else str(first)
            messages_json_str = json.dumps(messages, ensure_ascii=False)
        else:
            prompt_summary = str(messages)
            messages_json_str = json.dumps(messages, ensure_ascii=False)

        if len(prompt_summary) > 200:
            prompt_summary = prompt_summary[:197] + "..."

        meta_json_str = json.dumps(meta or {}, ensure_ascii=False)

        with self._write_lock:
            conn = self._get_connection()
            inserted_id = -1
            try:
                self._prune_if_exceeds_cap(conn)
                cursor = conn.execute(
                    """
                    INSERT INTO chat_logs (
                        trace_id, created_at, timestamp, endpoint, model, actual_model,
                        is_stream, status, latency_ms, prompt_summary, messages_json,
                        response_text, error_message, meta_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trace_id,
                        now_dt,
                        now_ts,
                        endpoint,
                        model or "default",
                        actual_model or model or "default",
                        1 if is_stream else 0,
                        int(status),
                        int(latency_ms),
                        prompt_summary,
                        messages_json_str,
                        response_text or "",
                        error_message or "",
                        meta_json_str
                    )
                )
                conn.commit()
                inserted_id = cursor.lastrowid
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
            finally:
                conn.close()

            return inserted_id

    def start_chat(self, endpoint: str, model: str, messages: Any, is_stream: bool = False, actual_model: str = '', trace_id: str = '', meta: Optional[Dict[str, Any]] = None) -> int:
        return self.record_chat(endpoint=endpoint, model=model, messages=messages, response_text='', status=0, latency_ms=0, is_stream=is_stream, actual_model=actual_model, error_message='', trace_id=trace_id, meta=meta)

    def finish_chat(self, chat_id: int, response_text: str = '', status: int = 200, latency_ms: int = 0, actual_model: str = '', error_message: str = '', meta: Optional[Dict[str, Any]] = None) -> bool:
        if not chat_id or int(chat_id) <= 0:
            return False
        with self._write_lock:
            conn = self._get_connection()
            try:
                if meta is not None:
                    conn.execute(
                        "UPDATE chat_logs SET status = ?, latency_ms = ?, response_text = ?, error_message = ?, "
                        "actual_model = COALESCE(NULLIF(?, ''), actual_model), meta_json = ? WHERE id = ?",
                        (int(status), int(latency_ms), response_text or "", error_message or "", actual_model or "", json.dumps(meta, ensure_ascii=False), int(chat_id)),
                    )
                else:
                    conn.execute(
                        "UPDATE chat_logs SET status = ?, latency_ms = ?, response_text = ?, error_message = ?, "
                        "actual_model = COALESCE(NULLIF(?, ''), actual_model) WHERE id = ?",
                        (int(status), int(latency_ms), response_text or "", error_message or "", actual_model or "", int(chat_id)),
                    )
                conn.commit()
                return True
            except Exception as e:
                print(f'[ChatHistory] Failed to finish chat {chat_id}: {e}')
                return False
            finally:
                conn.close()

    def list_chats(
        self,
        page: int = 1,
        page_size: int = 15,
        model: Optional[str] = None,
        keyword: Optional[str] = None,
        status: Optional[int] = None
    ) -> Dict[str, Any]:
        """Fetch paginated summary of chat records with lightweight payloads."""
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size

        where_clauses = []
        params = []

        if model and model.strip():
            where_clauses.append("model LIKE ?")
            params.append(f"%{model.strip()}%")

        if keyword and keyword.strip():
            kw = f"%{keyword.strip()}%"
            where_clauses.append("(prompt_summary LIKE ? OR response_text LIKE ? OR trace_id LIKE ?)")
            params.extend([kw, kw, kw])

        if status is not None:
            where_clauses.append("status = ?")
            params.append(int(status))

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        conn = self._get_connection()
        try:
            total_count = conn.execute(
                f"SELECT COUNT(1) FROM chat_logs {where_sql}", params
            ).fetchone()[0]

            query_sql = f"""
                SELECT id, trace_id, created_at, timestamp, endpoint, model, actual_model,
                       is_stream, status, latency_ms, prompt_summary,
                       SUBSTR(response_text, 1, 200) AS response_summary,
                       error_message, LENGTH(response_text) AS response_len
                FROM chat_logs
                {where_sql}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(query_sql, params + [page_size, offset]).fetchall()

            items = []
            for r in rows:
                items.append({
                    "id": r[0],
                    "trace_id": r[1],
                    "created_at": r[2],
                    "timestamp": r[3],
                    "endpoint": r[4],
                    "model": r[5],
                    "actual_model": r[6],
                    "is_stream": bool(r[7]),
                    "status": r[8],
                    "latency_ms": r[9],
                    "prompt_summary": r[10],
                    "response_summary": (r[11] or "") + ("..." if (r[13] or 0) > 200 else ""),
                    "error_message": r[12] or "",
                    "response_len": r[13] or 0,
                })

            return {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "items": items,
                "stats": self.get_stats_dict(total_count=total_count)
            }
        finally:
            conn.close()

    def get_chat_detail(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Fetch full conversation details for a single record."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT id, trace_id, created_at, timestamp, endpoint, model, actual_model,
                       is_stream, status, latency_ms, prompt_summary, messages_json,
                       response_text, error_message, meta_json
                FROM chat_logs WHERE id = ?
                """,
                (chat_id,)
            ).fetchone()

            if not row:
                return None

            try:
                parsed_messages = json.loads(row[11]) if row[11] else []
            except Exception:
                parsed_messages = row[11]

            try:
                parsed_meta = json.loads(row[14]) if row[14] else {}
            except Exception:
                parsed_meta = row[14]

            return {
                "id": row[0],
                "trace_id": row[1],
                "created_at": row[2],
                "timestamp": row[3],
                "endpoint": row[4],
                "model": row[5],
                "actual_model": row[6],
                "is_stream": bool(row[7]),
                "status": row[8],
                "latency_ms": row[9],
                "prompt_summary": row[10],
                "messages": parsed_messages,
                "response_text": row[12] or "",
                "error_message": row[13] or "",
                "meta": parsed_meta
            }
        finally:
            conn.close()

    def delete_chat(self, chat_id: int) -> bool:
        """Delete a single chat log record."""
        with self._write_lock:
            conn = self._get_connection()
            try:
                conn.execute("DELETE FROM chat_logs WHERE id = ?", (chat_id,))
                conn.commit()
                return True
            except Exception:
                return False
            finally:
                conn.close()

    def clear_all(self) -> bool:
        """Wipe all chat history and reclaim SQLite storage space."""
        with self._write_lock:
            conn = self._get_connection()
            try:
                conn.execute("DELETE FROM chat_logs")
                conn.commit()
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                conn.execute("VACUUM;")
                return True
            except Exception:
                return False
            finally:
                conn.close()

    def get_stats_dict(self, total_count: Optional[int] = None) -> Dict[str, Any]:
        """Return disk usage and record count statistics."""
        conn = self._get_connection()
        try:
            if total_count is None:
                total_count = conn.execute("SELECT COUNT(1) FROM chat_logs").fetchone()[0]
        except Exception:
            total_count = 0
        finally:
            conn.close()

        size_bytes = self.get_db_size_bytes()
        size_mb = round(size_bytes / (1024 * 1024), 2)
        pct = round((size_bytes / MAX_DB_BYTES) * 100, 2)

        return {
            "total_count": total_count,
            "db_size_bytes": size_bytes,
            "db_size_mb": size_mb,
            "max_size_mb": 100,
            "used_percent": min(100.0, pct)
        }


# Global Singleton
chat_history_manager = ChatHistoryManager()


def wrap_chat_stream(
    generator,
    endpoint: str,
    model: str,
    messages: Any,
    actual_model: str = "",
    trace_id: str = "",
    meta: Optional[Dict[str, Any]] = None,
    manager: Optional[ChatHistoryManager] = None,
    start_time: Optional[float] = None,
):
    """
    Wrap an SSE stream generator to capture full text asynchronously without buffering.
    """
    if manager is None:
        manager = chat_history_manager

    if start_time is None:
        start_time = time.time()
    collected_texts = []
    error_occurred = None
    status_code = 200
    chat_id = -1
    try:
        chat_id = manager.start_chat(endpoint=endpoint, model=model, messages=messages, is_stream=True, actual_model=actual_model or model, trace_id=trace_id, meta=meta)
    except Exception:
        chat_id = -1

    def _save_record(full_text: str, status: int, err: str):
        try:
            latency = int((time.time() - start_time) * 1000)
            if chat_id and chat_id > 0:
                manager.finish_chat(chat_id, response_text=full_text, status=status, latency_ms=latency, actual_model=actual_model or model, error_message=err, meta=meta)
            else:
                manager.record_chat(endpoint=endpoint, model=model, messages=messages, response_text=full_text, status=status, latency_ms=latency, is_stream=True, actual_model=actual_model or model, error_message=err, trace_id=trace_id, meta=meta)
        except Exception:
            pass

    try:
        for chunk in generator:
            try:
                txt = extract_text_from_chunk(chunk)
                if txt:
                    collected_texts.append(txt)
                chunk_err = extract_error_from_chunk(chunk)
                if chunk_err and not error_occurred:
                    error_occurred = chunk_err
                    low = chunk_err.lower()
                    status_code = 504 if ("timed out" in low or "timeout" in low or "超时" in chunk_err) else 502
            except Exception:
                pass
            yield chunk
    except Exception as e:
        error_occurred = str(e)
        status_code = 500
        raise
    finally:
        full_response = "".join(collected_texts)
        threading.Thread(
            target=_save_record,
            args=(full_response, status_code, error_occurred or ""),
            daemon=True
        ).start()
