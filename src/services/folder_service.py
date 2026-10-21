"""Favorite-folder management service.

Adds, removes, validates, and opens favorite folders using native Windows
dialogs and shell operations.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable

from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from src.storage.database import Database


class FolderService:
    def __init__(self, db: Database) -> None:
        self._db = db
        self._on_changed: Callable[[], None] | None = None

    def set_callback(self, callback: Callable[[], None]) -> None:
        self._on_changed = callback

    def _emit_changed(self) -> None:
        if self._on_changed is not None:
            self._on_changed()

    def add_folder(self, path: str | None = None, parent=None) -> str | None:
        if path is None:
            path = self._show_folder_dialog(parent)
        if path is None:
            return None
        p = Path(path)
        if not p.exists():
            return None
        name = p.name or str(p)
        added = self._db.add_folder(str(p), name)
        if added:
            self._emit_changed()
            return str(p)
        return None

    def _show_folder_dialog(self, parent=None) -> str | None:
        dialog = QFileDialog(parent)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, False)
        dialog.setWindowTitle("Select Folder")
        if dialog.exec() == 1:
            selected = dialog.selectedFiles()
            if selected:
                return selected[0]
        return None

    def get_folders(self) -> list[dict]:
        folders = self._db.get_folders()
        for f in folders:
            p = Path(f["path"])
            f["exists"] = p.exists()
            f["display_name"] = p.name or f["path"]
        return folders

    def open_folder(self, path: str) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        try:
            QDesktopServices.openUrl(f.as_uri())
            return True
        except Exception:
            try:
                os.startfile(str(p))
                return True
            except Exception:
                try:
                    subprocess.run(["explorer.exe", str(p)], check=False)
                    return True
                except Exception:
                    return False

    def remove_folder(self, folder_id: int) -> None:
        self._db.delete_folder(folder_id)
        self._emit_changed()

    def get_missing_folders(self) -> list[dict]:
        return [f for f in self.get_folders() if not f["exists"]]

    def count(self) -> int:
        return self._db.count_folders()

    def cleanup(self) -> None:
        pass
