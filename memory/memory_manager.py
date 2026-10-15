"""SQLite-backed memory: command history + a small key/value preference/fact store.
Scope deliberately kept to 2-3 categories (preferences, facts) per the P1 decision -
not a full multi-category memory system.
"""
import json
import sqlite3
from datetime import datetime
from core.logger import get_logger
from core.narrator import narrate
from core.paths import DATA_DIR

log = get_logger()
DB_PATH = DATA_DIR / "memory.db"


class MemoryManager:
    def __init__(self, db_path=DB_PATH, max_history=1000):
        self.db_path = db_path
        self.max_history = max_history
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, raw_text TEXT, intent_json TEXT, status TEXT)""")
            c.execute("""CREATE TABLE IF NOT EXISTS facts (
                key TEXT PRIMARY KEY, value TEXT, ts TEXT)""")

    def log_command(self, step, result):
        with self._conn() as c:
            c.execute("INSERT INTO history (ts, raw_text, intent_json, status) VALUES (?, ?, ?, ?)",
                      (datetime.now().isoformat(), step.get("raw_text", ""), json.dumps(step), result.get("status")))
            c.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)",
                      (self.max_history,))

    def remember(self, fact_text):
        if not fact_text:
            return {"status": "error", "message": "Nothing to remember", "data": None}
        key = f"fact_{int(datetime.now().timestamp()*1000)}"
        with self._conn() as c:
            c.execute("INSERT INTO facts (key, value, ts) VALUES (?, ?, ?)",
                      (key, fact_text, datetime.now().isoformat()))
        narrate("Got it, I'll remember that")
        return {"status": "success", "message": "Remembered", "data": {"key": key}}

    def set_pref(self, pref_name, value):
        if not pref_name or value is None:
            return {"status": "error", "message": "Need a preference name and value", "data": None}
        key = f"pref_{pref_name.lower().strip().replace(' ', '_')}"
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO facts (key, value, ts) VALUES (?, ?, ?)",
                      (key, value, datetime.now().isoformat()))
        narrate(f"Set {pref_name} to {value}")
        return {"status": "success", "message": f"{pref_name} = {value}", "data": None}

    def get_pref(self, pref_name):
        key = f"pref_{pref_name.lower().strip().replace(' ', '_')}"
        with self._conn() as c:
            row = c.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def recall(self, limit=10):
        with self._conn() as c:
            rows = c.execute("SELECT value, ts FROM facts ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        if not rows:
            narrate("I don't have anything remembered yet")
            return {"status": "not_found", "message": "Nothing remembered", "data": []}
        narrate(f"I remember {len(rows)} thing(s)")
        return {"status": "success", "message": f"{len(rows)} item(s)", "data": [r[0] for r in rows]}

    def forget(self, text):
        with self._conn() as c:
            cur = c.execute("DELETE FROM facts WHERE value LIKE ?", (f"%{text}%",))
            deleted = cur.rowcount
        narrate(f"Forgot {deleted} matching item(s)" if deleted else "Nothing matched")
        return {"status": "success" if deleted else "not_found", "message": f"Deleted {deleted}", "data": None}

    def history(self, limit=10):
        with self._conn() as c:
            rows = c.execute("SELECT raw_text, status, ts FROM history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        narrate(f"Last {len(rows)} commands")
        return {"status": "success", "message": f"{len(rows)} command(s)",
                "data": [{"text": r[0], "status": r[1], "ts": r[2]} for r in rows]}

    def handle(self, intent):
        action, name, dest = intent.get("action"), intent.get("name"), intent.get("destination_ref")
        if action == "remember":
            return self.remember(name)
        if action == "recall":
            return self.recall()
        if action == "forget":
            return self.forget(name)
        if action == "history":
            return self.history()
        if action == "set_pref":
            return self.set_pref(name, dest)
        return {"status": "unhandled", "message": f"Memory action '{action}' not implemented yet", "data": None}
