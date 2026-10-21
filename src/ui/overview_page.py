"""Overview page - application dashboard with statistics and quick actions."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFrame,
)

from src.ui.widgets import StatCard, SectionHeader, PageContainer


class OverviewPage(QWidget):
    def __init__(self, clipboard_count: int = 0, folders_count: int = 0,
                 notes_count: int = 0, parent=None) -> None:
        super().__init__(parent)
        self._clipboard_count = clipboard_count
        self._folders_count = folders_count
        self._notes_count = notes_count

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._page = PageContainer()
        layout.addWidget(self._page)

        self._build_stats()
        self._build_quick_actions()
        self._build_recents()

        self.setLayout(layout)

    def _build_stats(self) -> None:
        grid = QWidget()
        grid_layout = QVBoxLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(12)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self._stat_clipboard = StatCard("Clipboard Entries", str(self._clipboard_count))
        self._stat_folders = StatCard("Favorite Folders", str(self._folders_count))
        self._stat_notes = StatCard("Saved Notes", str(self._notes_count))

        stats_row.addWidget(self._stat_clipboard, 1)
        stats_row.addWidget(self._stat_folders, 1)
        stats_row.addWidget(self._stat_notes, 1)
        grid_layout.addLayout(stats_row)

        grid.setLayout(grid_layout)
        self._page.add_widget(grid)

    def _build_quick_actions(self) -> None:
        header = SectionHeader("Quick Actions")
        self._page.add_widget(header)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        self._btn_note = self._make_action_btn("Add Note")
        self._btn_folder = self._make_action_btn("Open Folder")
        self._btn_history = self._make_action_btn("Clipboard History")

        actions.addWidget(self._btn_note, 1)
        actions.addWidget(self._btn_folder, 1)
        actions.addWidget(self._btn_history, 1)

        actions_widget = QWidget()
        actions_widget.setLayout(actions)
        self._page.add_widget(actions_widget)

        self._page.add_spacer()

    def _make_action_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(60)
        btn.setStyleSheet("""
            QPushButton {
                background-color: var(--bg-secondary);
                color: var(--text-primary);
                border: 1px solid var(--border-color);
                border-radius: 6px;
                padding: 18px 16px;
                font-size: 14px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: var(--bg-hover);
                border-color: var(--border-light);
                color: var(--accent-green);
            }
        """)
        return btn

    def _build_recents(self) -> None:
        header = SectionHeader("Recent Items")
        self._page.add_widget(header)

        self._recents_container = QWidget()
        self._recents_layout = QVBoxLayout()
        self._recents_layout.setContentsMargins(0, 0, 0, 0)
        self._recents_layout.setSpacing(2)
        self._recents_container.setLayout(self._recents_layout)
        self._page.add_widget(self._recents_container)

        self._empty_label = QLabel("No recent items.")
        self._empty_label.setStyleSheet("color: var(--text-tertiary); font-size: 12px; padding: 8px 0;")
        self._recents_layout.addWidget(self._empty_label)
        self._empty_label.hide()

    def connect_quick_actions(self, on_note: Callable, on_folder: Callable, on_history: Callable) -> None:
        self._btn_note.clicked.connect(on_note)
        self._btn_folder.clicked.connect(on_folder)
        self._btn_history.clicked.connect(on_history)

    def update_stats(self, clipboard: int, folders: int, notes: int) -> None:
        self._stat_clipboard.set_value(str(clipboard))
        self._stat_folders.set_value(str(folders))
        self._stat_notes.set_value(str(notes))

    def set_recents(self, recents: list[dict]) -> None:
        for i in reversed(range(self._recents_layout.count())):
            item = self._recents_layout.takeAt(i)
            if item and item.widget() is not self._empty_label:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        if not recents:
            self._empty_label.setText("No recent items.")
            self._empty_label.show()
            return

        self._empty_label.hide()
        for item in recents:
            label = QLabel(item.get("title", "Unknown item"))
            label.setStyleSheet(
                "color: var(--text-secondary); font-size: 12px; padding: 4px 0;"
            )
            self._recents_layout.addWidget(label)

    def get_action_buttons(self) -> dict:
        return {
            "note": self._btn_note,
            "folder": self._btn_folder,
            "history": self._btn_history,
        }
