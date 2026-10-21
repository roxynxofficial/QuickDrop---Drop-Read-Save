"""Settings management service.

Handles application preferences: theme, clipboard behavior, start page,
and related configuration stored in the SQLite database.
"""
from __future__ import annotations

from typing import Any

from src.storage.database import Database


DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "start_page": "overview",
    "max_clipboard_history": 20,
    "clipboard_monitoring_enabled": True,
    "always_on_top": False,
    "minimize_to_tray": False,
}

VALID_THEMES = ("dark", "light")
VALID_START_PAGES = ("overview", "clipboard", "folders", "notes")


class SettingsService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get(self, key: str, default: Any = None) -> Any:
        val = self._db.get_setting(key, default)
        if val is None:
            val = DEFAULTS.get(key)
        return val

    def set(self, key: str, value: Any) -> None:
        self._db.set_setting(key, value)

    @property
    def theme(self) -> str:
        t = self._db.get_setting("theme", DEFAULTS["theme"])
        if t not in VALID_THEMES:
            t = DEFAULTS["theme"]
        return t

    @theme.setter
    def theme(self, value: str) -> None:
        if value not in VALID_THEMES:
            raise ValueError(f"Invalid theme: {value}")
        self._db.set_setting("theme", value)

    @property
    def start_page(self) -> str:
        p = self._db.get_setting("start_page", DEFAULTS["start_page"])
        if p not in VALID_START_PAGES:
            p = DEFAULTS["start_page"]
        return p

    @start_page.setter
    def start_page(self, value: str) -> None:
        if value not in VALID_START_PAGES:
            raise ValueError(f"Invalid start page: {value}")
        self._db.set_setting("start_page", value)

    @property
    def max_clipboard_history(self) -> int:
        val = self._db.get_setting("max_clipboard_history", DEFAULTS["max_clipboard_history"])
        try:
            n = int(val)
        except (TypeError, ValueError):
            n = DEFAULTS["max_clipboard_history"]
        return max(1, min(n, 200))

    @max_clipboard_history.setter
    def max_clipboard_history(self, value: int) -> None:
        n = int(value)
        if n < 1:
            n = 1
        if n > 200:
            n = 200
        self._db.set_setting("max_clipboard_history", n)

    @property
    def clipboard_monitoring_enabled(self) -> bool:
        val = self._db.get_setting("clipboard_monitoring_enabled", DEFAULTS["clipboard_monitoring_enabled"])
        if val is None:
            return DEFAULTS["clipboard_monitoring_enabled"]
        return bool(val)

    @clipboard_monitoring_enabled.setter
    def clipboard_monitoring_enabled(self, value: bool) -> None:
        self._db.set_setting("clipboard_monitoring_enabled", bool(value))

    @property
    def always_on_top(self) -> bool:
        val = self._db.get_setting("always_on_top", DEFAULTS["always_on_top"])
        if val is None:
            return DEFAULTS["always_on_top"]
        return bool(val)

    @always_on_top.setter
    def always_on_top(self, value: bool) -> None:
        self._db.set_setting("always_on_top", bool(value))

    @property
    def minimize_to_tray(self) -> bool:
        val = self._db.get_setting("minimize_to_tray", DEFAULTS["minimize_to_tray"])
        if val is None:
            return DEFAULTS["minimize_to_tray"]
        return bool(val)

    @minimize_to_tray.setter
    def minimize_to_tray(self, value: bool) -> None:
        self._db.set_setting("minimize_to_tray", bool(value))

    def reset_to_defaults(self) -> None:
        for key, value in DEFAULTS.items():
            self._db.set_setting(key, value)

    def delete_all_data(self) -> None:
        assert self._db._conn is not None
        conn = self._db._conn
        for table in ("clipboard_entries", "folders", "notes", "overview_recents", "settings"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
        self.reset_to_defaults()

    @property
    def version(self) -> str:
        return "1.0.0"
