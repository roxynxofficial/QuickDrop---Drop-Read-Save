"""SQLite-based persistence layer for QuickDrop.

Stores clipboard history, favorite folders, notes, and settings in a single
database file located in the user's application data directory.
"""
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


class Database:
    _instance: "Database | None" = None
    _lock = threading.Lock()

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._connect()
        self._create_tables()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def _create_tables(self) -> None:
        assert self._conn is not None
        cur = self._conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS clipboard_entries (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                content         TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                is_pinned       INTEGER DEFAULT 0,
                is_favorite     INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                path            TEXT NOT NULL UNIQUE,
                name            TEXT NOT NULL,
                added_at        TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                title           TEXT NOT NULL,
                content         TEXT NOT NULL DEFAULT '',
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key             TEXT PRIMARY KEY,
                value           TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS overview_recents (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type       TEXT NOT NULL,
                item_id         INTEGER NOT NULL,
                last_accessed   TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_recents_unique
            ON overview_recents (item_type, item_id)
        """)

        self._conn.commit()

    @classmethod
    def get_default_path(cls) -> Path:
        import os
        local = os.environ.get("QUICKDROP_DB_PATH")
        if local:
            return Path(local)
        appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if appdata:
            p = Path(appdata) / "QuickDrop" / "quickdrop.db"
        else:
            p = Path.home() / ".local" / "share" / "QuickDrop" / "quickdrop.db"
        return p

    @classmethod
    def instance(cls, db_path: Path | None = None) -> "Database":
        with cls._lock:
            if cls._instance is None:
                path = db_path or cls.get_default_path()
                cls._instance = cls(path)
            return cls._instance

    @classmethod
    def close_instance(cls) -> None:
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None

    def close(self) -> None:
        if self._conn is not None:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def get_setting(self, key: str, default: Any = None) -> Any:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        val = row["value"]
        if val in ("true", "false"):
            return val == "true"
        try:
            return int(val)
        except ValueError:
            return val

    def set_setting(self, key: str, value: Any) -> None:
        assert self._conn is not None
        if isinstance(value, bool):
            val = "true" if value else "false"
        else:
            val = str(value)
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, val),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Clipboard entries
    # ------------------------------------------------------------------
    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    def add_clipboard_entry(self, content: str) -> int:
        assert self._conn is not None
        cur = self._conn.execute(
            "INSERT INTO clipboard_entries (content, timestamp, is_pinned, is_favorite) "
            "VALUES (?, ?, 0, 0)",
            (content, self._now()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_clipboard_entries(self) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT id, content, timestamp, is_pinned, is_favorite "
            "FROM clipboard_entries ORDER BY is_pinned DESC, id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def update_clipboard_entry(self, entry_id: int, **kwargs: Any) -> None:
        assert self._conn is not None
        cols = []
        vals: list[Any] = []
        for k, v in kwargs.items():
            cols.append(f"{k} = ?")
            vals.append(1 if v is True else 0 if v is False else v)
        vals.append(entry_id)
        self._conn.execute(
            f"UPDATE clipboard_entries SET {', '.join(cols)} WHERE id = ?",
            vals,
        )
        self._conn.commit()

    def delete_clipboard_entry(self, entry_id: int) -> None:
        assert self._conn is not None
        self._conn.execute("DELETE FROM clipboard_entries WHERE id = ?", (entry_id,))
        self._conn.commit()

    def clear_clipboard_history(self) -> int:
        assert self._conn is not None
        cur = self._conn.execute("DELETE FROM clipboard_entries")
        self._conn.commit()
        return cur.rowcount

    def count_clipboard_entries(self) -> int:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM clipboard_entries"
        ).fetchone()
        return row["cnt"] if row else 0

    def _prune_clipboard(self, limit: int) -> None:
        assert self._conn is not None
        self._conn.execute(
            "DELETE FROM clipboard_entries WHERE id NOT IN ("
            "    SELECT id FROM clipboard_entries "
            "    WHERE is_pinned = 1 OR is_favorite = 1 "
            "    UNION ALL "
            "    SELECT id FROM clipboard_entries "
            "    WHERE is_pinned = 0 AND is_favorite = 0 "
            "    ORDER BY id DESC LIMIT ? "
            ")",
            (limit,),
        )

    def get_unpinned_clipboard_count(self) -> int:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM clipboard_entries "
            "WHERE is_pinned = 0 AND is_favorite = 0"
        ).fetchone()
        return row["cnt"] if row else 0

    def prune_clipboard_to_limit(self, max_size: int) -> None:
        assert self._conn is not None
        unpinned = self._conn.execute(
            "SELECT id FROM clipboard_entries "
            "WHERE is_pinned = 0 AND is_favorite = 0 "
            "ORDER BY id ASC"
        ).fetchall()
        over = len(unpinned) - max_size
        if over > 0:
            ids = [r["id"] for r in unpinned[:over]]
            placeholders = ", ".join("?" * len(ids))
            self._conn.execute(
                f"DELETE FROM clipboard_entries WHERE id IN ({placeholders})",
                ids,
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Folders
    # ------------------------------------------------------------------
    def add_folder(self, path: str, name: str | None = None) -> bool:
        assert self._conn is not None
        if name is None:
            p = Path(path)
            name = p.name or path
        try:
            self._conn.execute(
                "INSERT INTO folders (path, name, added_at) VALUES (?, ?, ?)",
                (str(path), name, self._now()),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_folders(self) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT id, path, name, added_at FROM folders ORDER BY added_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_folder(self, folder_id: int) -> None:
        assert self._conn is not None
        self._conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        self._conn.commit()

    def count_folders(self) -> int:
        assert self._conn is not None
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM folders").fetchone()
        return row["cnt"] if row else 0

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------
    def add_note(self, title: str, content: str = "") -> int:
        assert self._conn is not None
        ts = self._now_ts()
        cur = self._conn.execute(
            "INSERT INTO notes (title, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (title, content, ts, ts),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_notes(self) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT id, title, content, created_at, updated_at "
            "FROM notes ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_note(self, note_id: int) -> dict | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT id, title, content, created_at, updated_at "
            "FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()
        return dict(row) if row else None

    def update_note(self, note_id: int, title: str, content: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            "UPDATE notes SET title = ?, content = ?, updated_at = ? WHERE id = ?",
            (title, content, self._now_ts(), note_id),
        )
        self._conn.commit()

    def delete_note(self, note_id: int) -> None:
        assert self._conn is not None
        self._conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self._conn.commit()

    def count_notes(self) -> int:
        assert self._conn is not None
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM notes").fetchone()
        return row["cnt"] if row else 0

    # ------------------------------------------------------------------
    # Overview recents
    # ------------------------------------------------------------------
    @classmethod
    def _now_ts(cls) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def add_or_update_recent(self, item_type: str, item_id: int) -> None:
        assert self._conn is not None
        ts = self._now_ts()
        self._conn.execute(
            "INSERT INTO overview_recents (item_type, item_id, last_accessed) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(item_type, item_id) DO UPDATE SET last_accessed=excluded.last_accessed",
            (item_type, item_id, ts),
        )
        self._conn.commit()

    def get_recents(self, limit: int = 10) -> list[dict]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT item_type, item_id, last_accessed "
            "FROM overview_recents ORDER BY last_accessed DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def clear_recents(self) -> None:
        assert self._conn is not None
        self._conn.execute("DELETE FROM overview_recents")
        self._conn.commit()
