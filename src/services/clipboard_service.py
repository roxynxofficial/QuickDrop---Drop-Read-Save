"""Clipboard history management service.

Monitors the system clipboard for text changes while enabled, captures
unique entries, enforces a maximum history size, and provides search and
management operations.

Nothing is captured unless monitoring is explicitly enabled by the user.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QTimer, QEvent
from PySide6.QtGui import QClipboard, QGuiApplication

from src.storage.database import Database


class ClipboardService(QObject):
    HISTORY_LIMIT_CAP = 200

    def __init__(self, db: Database, monitoring_enabled: bool = True) -> None:
        super().__init__()
        self._db = db
        self._enabled = False
        self._max_size = 20
        self._last_text: str | None = None
        self._timer: QTimer | None = None
        self._clip: QClipboard | None = None
        self._change_count = 0
        self._on_changed: Callable[[], None] | None = None
        if monitoring_enabled:
            self._enabled = True
            self._start_monitoring()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        if value == self._enabled:
            return
        self._enabled = value
        if value:
            self._start_monitoring()
        else:
            self._stop_monitoring()

    @property
    def max_size(self) -> int:
        return self._max_size

    @max_size.setter
    def max_size(self, value: int) -> None:
        self._max_size = max(1, min(value, self.HISTORY_LIMIT_CAP))

    def set_callback(self, callback: Callable[[], None]) -> None:
        self._on_changed = callback

    def _start_monitoring(self) -> None:
        app = QGuiApplication.instance()
        if app is None:
            return
        self._clip = app.clipboard()
        self._clip.installEventFilter(self)
        self._last_text = self._clip.text() if self._clip.text() else None

    def _stop_monitoring(self) -> None:
        if self._clip is not None:
            self._clip.removeEventFilter(self)
        self._clip = None
        self._last_text = None

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Clipboard:
            if self._enabled and self._clip is not None:
                text = self._clip.text()
                if text and text != self._last_text:
                    self._last_text = text
                    self._capture(text)
        return super().eventFilter(obj, event)

    def _capture(self, text: str) -> None:
        self._change_count += 1
        self._db.add_clipboard_entry(text)
        self._db.prune_clipboard_to_limit(self._max_size)
        if self._on_changed is not None:
            self._on_changed()

    def get_entries(self) -> list[dict]:
        return self._db.get_clipboard_entries()

    def pin_entry(self, entry_id: int, pinned: bool) -> None:
        self._db.update_clipboard_entry(entry_id, is_pinned=1 if pinned else 0)

    def favorite_entry(self, entry_id: int, favorite: bool) -> None:
        self._db.update_clipboard_entry(entry_id, is_favorite=1 if favorite else 0)

    def delete_entry(self, entry_id: int) -> None:
        self._db.delete_clipboard_entry(entry_id)

    def clear_history(self) -> None:
        self._db.clear_clipboard_history()

    def copy_to_clipboard(self, text: str) -> None:
        app = QGuiApplication.instance()
        if app is None:
            return
        cb = app.clipboard()
        cb.setText(text)

    @property
    def change_count(self) -> int:
        return self._change_count

    def count(self) -> int:
        return self._db.count_clipboard_entries()

    def force_refresh(self) -> None:
        if self._enabled and self._clip is not None:
            text = self._clip.text()
            if text:
                self._last_text = text
                if self._change_count == 0:
                    self._capture(text)

    def cleanup(self) -> None:
        self._stop_monitoring()
