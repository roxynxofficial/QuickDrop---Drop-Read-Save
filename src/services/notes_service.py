"""Local notes management service.

Creates, edits, renames, searches, and deletes notes stored locally in the
SQLite database. All changes are saved immediately.
"""
from __future__ import annotations

from typing import Callable

from src.storage.database import Database


class NotesService:
    MAX_TITLE_LEN = 200

    def __init__(self, db: Database) -> None:
        self._db = db
        self._on_changed: Callable[[], None] | None = None

    def set_callback(self, callback: Callable[[], None]) -> None:
        self._on_changed = callback

    def _emit_changed(self) -> None:
        if self._on_changed is not None:
            self._on_changed()

    def create_note(self, title: str = "Untitled Note", content: str = "") -> int:
        title = self._validate_title(title)
        note_id = self._db.add_note(title, content)
        self._emit_changed()
        return note_id

    def _validate_title(self, title: str) -> str:
        t = (title or "").strip()
        if not t:
            t = "Untitled Note"
        t = t[: self.MAX_TITLE_LEN]
        return t

    def get_notes(self) -> list[dict]:
        return self._db.get_notes()

    def get_note(self, note_id: int) -> dict | None:
        return self._db.get_note(note_id)

    def save_note(self, note_id: int, title: str, content: str) -> None:
        title = self._validate_title(title)
        self._db.update_note(note_id, title, content)
        self._emit_changed()

    def rename_note(self, note_id: int, new_title: str) -> None:
        title = self._validate_title(new_title)
        note = self._db.get_note(note_id)
        if note is None:
            return
        self._db.update_note(note_id, title, note["content"])
        self._emit_changed()

    def delete_note(self, note_id: int) -> None:
        self._db.delete_note(note_id)
        self._emit_changed()

    def search_notes(self, query: str) -> list[dict]:
        if not query.strip():
            return self.get_notes()
        all_notes = self._db.get_notes()
        q = query.strip().lower()
        return [
            n for n in all_notes
            if q in n["title"].lower() or q in n["content"].lower()
        ]

    def count(self) -> int:
        return self._db.count_notes()

    def cleanup(self) -> None:
        pass
