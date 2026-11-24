"""SQLite-backed conversation and message store for the local BrandMind service."""

import os
import sqlite3
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationStore:
    def __init__(self, database_path: Optional[str] = None):
        self.path = Path(database_path or os.getenv("BRANDMIND_CONVERSATIONS_DB", "results/conversations.sqlite3"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _initialize(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, brand_id TEXT NOT NULL, customer_name TEXT NOT NULL,
                    email TEXT NOT NULL DEFAULT '', order_id TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'ai_active', assigned_to TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, archived_at TEXT,
                    last_message TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,
                    transparency TEXT, attachments TEXT NOT NULL DEFAULT '[]',
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                );
                CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id);
            """)
            db.execute("CREATE TABLE IF NOT EXISTS customer_sessions (session_hash TEXT PRIMARY KEY, csrf_token TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            session_columns = {row["name"] for row in db.execute("PRAGMA table_info(customer_sessions)")}
            if "customer_number" not in session_columns:
                db.execute("ALTER TABLE customer_sessions ADD COLUMN customer_number INTEGER")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(conversations)")}
            if "archived_at" not in columns:
                db.execute("ALTER TABLE conversations ADD COLUMN archived_at TEXT")
            customer_number_migration = "20261125_persistent_customer_numbers"
            if not db.execute("SELECT 1 FROM schema_migrations WHERE version=?", (customer_number_migration,)).fetchone():
                if "customer_number" not in columns:
                    db.execute("ALTER TABLE conversations ADD COLUMN customer_number INTEGER")
                legacy_rows = db.execute(
                    "SELECT id FROM conversations ORDER BY created_at ASC, id ASC"
                ).fetchall()
                for number, row in enumerate(legacy_rows, start=1):
                    db.execute("UPDATE conversations SET customer_number=? WHERE id=?", (number, row["id"]))
                db.execute("INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)",
                           (customer_number_migration, _now()))
            message_number_migration = "20261125_customer_numbers_require_messages"
            if not db.execute("SELECT 1 FROM schema_migrations WHERE version=?", (message_number_migration,)).fetchone():
                db.execute("UPDATE conversations SET customer_number=NULL WHERE NOT EXISTS "
                           "(SELECT 1 FROM messages WHERE messages.conversation_id=conversations.id)")
                numbered_rows = db.execute(
                    "SELECT c.id FROM conversations c WHERE EXISTS "
                    "(SELECT 1 FROM messages m WHERE m.conversation_id=c.id) "
                    "ORDER BY c.customer_number ASC, c.created_at ASC, c.id ASC"
                ).fetchall()
                for number, row in enumerate(numbered_rows, start=1):
                    db.execute("UPDATE conversations SET customer_number=? WHERE id=?", (number, row["id"]))
                db.execute("INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)",
                           (message_number_migration, _now()))
            if "customer_session_id" not in columns:
                db.execute("ALTER TABLE conversations ADD COLUMN customer_session_id TEXT REFERENCES customer_sessions(session_hash)")
                columns.add("customer_session_id")
            db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_customer_session ON conversations(customer_session_id)")
            session_number_migration = "20261125_customer_identity_numbers"
            if not db.execute("SELECT 1 FROM schema_migrations WHERE version=?", (session_number_migration,)).fetchone():
                identities = db.execute("""
                    SELECT customer_session_id AS identity_id, MIN(created_at) AS first_seen
                    FROM conversations
                    WHERE customer_session_id IS NOT NULL
                      AND EXISTS (SELECT 1 FROM messages WHERE messages.conversation_id=conversations.id)
                    GROUP BY customer_session_id
                    UNION ALL
                    SELECT id AS identity_id, created_at AS first_seen
                    FROM conversations
                    WHERE customer_session_id IS NULL
                      AND EXISTS (SELECT 1 FROM messages WHERE messages.conversation_id=conversations.id)
                    ORDER BY first_seen ASC, identity_id ASC
                """).fetchall()
                for number, identity in enumerate(identities, start=1):
                    identity_id = identity["identity_id"]
                    if db.execute("SELECT 1 FROM customer_sessions WHERE session_hash=?", (identity_id,)).fetchone():
                        db.execute("UPDATE customer_sessions SET customer_number=? WHERE session_hash=?", (number, identity_id))
                        db.execute("UPDATE conversations SET customer_number=? WHERE customer_session_id=?", (number, identity_id))
                    else:
                        db.execute("UPDATE conversations SET customer_number=? WHERE id=?", (number, identity_id))
                db.execute("INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)",
                           (session_number_migration, _now()))
            ignored_marker_migration = "20261125_customer_ignore_marker"
            if not db.execute("SELECT 1 FROM schema_migrations WHERE version=?", (ignored_marker_migration,)).fetchone():
                if "ignored_by_customer" not in columns:
                    db.execute("ALTER TABLE conversations ADD COLUMN ignored_by_customer INTEGER NOT NULL DEFAULT 0")
                db.execute("INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)",
                           (ignored_marker_migration, _now()))
            message_columns = {row["name"] for row in db.execute("PRAGMA table_info(messages)")}
            if "attachments" not in message_columns:
                db.execute("ALTER TABLE messages ADD COLUMN attachments TEXT NOT NULL DEFAULT '[]'")
            migration = "20261124_customer_session_ownership"
            applied = db.execute("SELECT 1 FROM schema_migrations WHERE version=?", (migration,)).fetchone()
            if not applied:
                if "customer_session_id" not in columns:
                    db.execute("ALTER TABLE conversations ADD COLUMN customer_session_id TEXT REFERENCES customer_sessions(session_hash)")
                db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_customer_session ON conversations(customer_session_id)")
                db.execute("INSERT INTO schema_migrations(version,applied_at) VALUES(?,?)", (migration, _now()))
            db.execute("UPDATE conversations SET archived_at=updated_at WHERE status IN ('resolved','ignored') AND archived_at IS NULL")
    def purge_expired_archived(self):
        """Delete customer-ignored chats after the configured two-day retention window."""
        retention_hours = max(1, int(os.getenv("BRANDMIND_CUSTOMER_IGNORED_TTL_HOURS", "48")))
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=retention_hours)).isoformat()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            expired = [row["id"] for row in db.execute(
                "SELECT id FROM conversations WHERE ignored_by_customer=1 AND status='ignored' "
                "AND archived_at IS NOT NULL AND archived_at<=?", (cutoff,)
            ).fetchall()]
            for conversation_id in expired:
                db.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
                db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
            return expired

    @staticmethod
    def _conversation(row):
        item = dict(row)
        item.pop("customer_session_id", None)
        item["message_count"] = item.pop("_message_count", 0)
        return item

    def create(self, brand_id="rlvnt", customer_name="Guest", email="", order_id="", customer_session_id=None):
        cid, now = uuid.uuid4().hex, _now()
        with self._connect() as db:
            session = db.execute("SELECT customer_number FROM customer_sessions WHERE session_hash=?", (customer_session_id,)).fetchone() if customer_session_id else None
            customer_number = session["customer_number"] if session else None
            db.execute("INSERT INTO conversations(id,brand_id,customer_name,email,order_id,created_at,updated_at,customer_session_id,customer_number) VALUES(?,?,?,?,?,?,?,?,?)",
                       (cid, brand_id, customer_name, email, order_id, now, now, customer_session_id, customer_number))
        return self.get(cid)

    @staticmethod
    def hash_session(secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    def create_customer_session(self, session_hash: str, csrf_token: str, created_at: str, expires_at: str):
        with self._connect() as db:
            db.execute("INSERT INTO customer_sessions(session_hash,csrf_token,created_at,expires_at) VALUES(?,?,?,?)",
                       (session_hash, csrf_token, created_at, expires_at))

    def get_customer_session(self, session_hash: str):
        with self._connect() as db:
            row = db.execute("SELECT * FROM customer_sessions WHERE session_hash=?", (session_hash,)).fetchone()
            return dict(row) if row else None

    def customer_conversations(self, session_hash: str):
        with self._connect() as db:
            rows = db.execute("SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) AS _message_count FROM conversations c WHERE customer_session_id=? AND ignored_by_customer=0 ORDER BY updated_at DESC", (session_hash,)).fetchall()
            return [self._conversation(row) for row in rows]

    def belongs_to_customer_session(self, conversation_id: str, session_hash: str) -> bool:
        with self._connect() as db:
            return db.execute("SELECT 1 FROM conversations WHERE id=? AND customer_session_id=? AND ignored_by_customer=0", (conversation_id, session_hash)).fetchone() is not None

    def get(self, conversation_id: str):
        with self._connect() as db:
            row = db.execute("""SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) AS _message_count
                FROM conversations c WHERE c.id=?""", (conversation_id,)).fetchone()
            return self._conversation(row) if row else None

    def list(self, brand_id="rlvnt", status=None, query="", limit=100):
        sql = """SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) AS _message_count
                 FROM conversations c WHERE c.brand_id=?
                 AND EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id=c.id)"""
        params: List[Any] = [brand_id]
        if status == "archive":
            sql += " AND c.status IN ('resolved','ignored')"
        elif status and status != "all":
            sql += " AND c.status=?"; params.append(status)
        else:
            sql += " AND c.status NOT IN ('resolved','ignored')"
        sql += " ORDER BY c.updated_at DESC"
        if not query.strip():
            sql += " LIMIT ?"; params.append(limit)
        with self._connect() as db:
            rows = [dict(r) for r in db.execute(sql, params).fetchall()]
            term = query.strip()
            if term:
                def normalize_search(value):
                    return "".join(str(value or "").split()).casefold()

                needle = normalize_search(term)
                message_matches = set()
                conversation_ids = [row["id"] for row in rows]
                for offset in range(0, len(conversation_ids), 400):
                    batch = conversation_ids[offset:offset + 400]
                    placeholders = ",".join("?" for _ in batch)
                    for message in db.execute(
                        f"SELECT conversation_id, content FROM messages WHERE conversation_id IN ({placeholders})",
                        batch,
                    ):
                        if needle in normalize_search(message["content"]):
                            message_matches.add(message["conversation_id"])
                matches = []
                for row in rows:
                    searchable = (row.get("customer_name"), row.get("email"), row.get("order_id"), row.get("id"), row.get("last_message"))
                    matched = any(needle in normalize_search(value) for value in searchable)
                    if not matched and row["id"] in message_matches:
                        matched = True
                    generic_guest = not row.get("email") and row.get("customer_name") in (None, "", "RLVNT Customer", "Guest")
                    if not matched and generic_guest:
                        customer_number = row["customer_number"]
                        labels = (f"Customer {customer_number:02d}", f"Customer {customer_number}")
                        matched = any(needle in normalize_search(label) for label in labels)
                    if matched:
                        matches.append(row)
                rows = matches[:limit]

            return [self._conversation(row) for row in rows]

    def messages(self, conversation_id: str, after_id=0):
        import json
        with self._connect() as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM messages WHERE conversation_id=? AND id>? ORDER BY id",
                                                (conversation_id, after_id)).fetchall()]
            for row in rows:
                try:
                    row["attachments"] = json.loads(row.get("attachments") or "[]")
                except json.JSONDecodeError:
                    row["attachments"] = []
            return rows

    def add_message(self, conversation_id: str, role: str, content: str, transparency=None, attachments=None):
        now = _now()
        import json
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            conversation = db.execute("SELECT customer_number,customer_session_id FROM conversations WHERE id=?", (conversation_id,)).fetchone()
            if conversation and conversation["customer_number"] is None:
                number = db.execute("SELECT COALESCE(MAX(customer_number),0)+1 FROM conversations").fetchone()[0]
                session_id = conversation["customer_session_id"]
                if session_id:
                    session = db.execute("SELECT customer_number FROM customer_sessions WHERE session_hash=?", (session_id,)).fetchone()
                    if session and session["customer_number"] is not None:
                        number = session["customer_number"]
                    elif session:
                        db.execute("UPDATE customer_sessions SET customer_number=? WHERE session_hash=?", (number, session_id))
                    db.execute("UPDATE conversations SET customer_number=? WHERE customer_session_id=?", (number, session_id))
                else:
                    db.execute("UPDATE conversations SET customer_number=? WHERE id=?", (number, conversation_id))
            cur = db.execute("INSERT INTO messages(conversation_id,role,content,created_at,transparency,attachments) VALUES(?,?,?,?,?,?)",
                             (conversation_id, role, content, now, json.dumps(transparency, ensure_ascii=False) if transparency else None,
                              json.dumps(attachments or [], ensure_ascii=False)))
            preview = content[:500] if content else (f"📎 {attachments[0].get('name', 'Attachment')}" if attachments else "")
            db.execute("UPDATE conversations SET updated_at=?,last_message=? WHERE id=?", (now, preview, conversation_id))
            row = dict(db.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone())
            row["attachments"] = attachments or []
            return row

    def set_status(self, conversation_id: str, status: str, assigned_to="", ignored_by_customer=False):
        with self._connect() as db:
            now = _now()
            archived_at = now if status in {"resolved", "ignored"} else None
            db.execute("UPDATE conversations SET status=?,assigned_to=?,updated_at=?,archived_at=?,ignored_by_customer=? WHERE id=?",
                       (status, assigned_to, now, archived_at, int(ignored_by_customer), conversation_id))
        return self.get(conversation_id)

    def set_order_id(self, conversation_id: str, order_id: str):
        with self._connect() as db:
            db.execute("UPDATE conversations SET order_id=?,updated_at=? WHERE id=?", (order_id, _now(), conversation_id))
        return self.get(conversation_id)

    def set_customer_name(self, conversation_id: str, customer_name: str):
        name = (customer_name or "").strip()
        if not name:
            return self.get(conversation_id)
        with self._connect() as db:
            db.execute("UPDATE conversations SET customer_name=?,updated_at=? WHERE id=?",
                       (name, _now(), conversation_id))
        return self.get(conversation_id)

    def stats(self, brand_id="rlvnt"):
        with self._connect() as db:
            counts = {r["status"]: r["n"] for r in db.execute(
                "SELECT c.status,COUNT(*) n FROM conversations c WHERE c.brand_id=? "
                "AND EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id=c.id) GROUP BY c.status", (brand_id,))}
            return {"total": sum(counts.values()), "open": sum(n for status, n in counts.items() if status not in {"resolved", "ignored"}),
                    "waiting": counts.get("waiting", 0), "human_active": counts.get("human_active", 0),
                    "ai_active": counts.get("ai_active", 0), "resolved": counts.get("resolved", 0),
                    "ignored": counts.get("ignored", 0)}

    def analytics(self, brand_id="rlvnt"):
        import json
        turns, latencies, tools, escalations = 0, [], 0, 0
        intents, languages = {}, {}
        with self._connect() as db:
            rows = db.execute("""SELECT m.transparency FROM messages m
                JOIN conversations c ON c.id=m.conversation_id
                WHERE c.brand_id=? AND m.transparency IS NOT NULL""", (brand_id,)).fetchall()
        for row in rows:
            try:
                trace = json.loads(row["transparency"])
            except (TypeError, json.JSONDecodeError):
                continue
            turns += 1
            latencies.append(float(trace.get("latency_ms") or 0))
            tools += len(trace.get("tools_executed") or [])
            escalations += bool(trace.get("is_escalated"))
            intent = str(trace.get("detected_intent", "unknown"))
            language = str(trace.get("language", "unknown"))
            intents[intent] = intents.get(intent, 0) + 1
            languages[language] = languages.get(language, 0) + 1
        return {"ai_responses": turns, "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
                "escalations": escalations, "tool_executions": tools, "intents": intents, "languages": languages}
