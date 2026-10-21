"""Lightweight local notes management page."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QMenu,
    QInputDialog, QMessageBox, QAbstractItemView, QSplitter,
    QLineEdit,
)

from src.ui.widgets import SectionHeader, PageContainer


class NotesPage(QWidget):
    note_selected = Signal(int)
    note_created = Signal()
    note_deleted = Signal(int)
    note_renamed = Signal(int, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_note_id: int | None = None
        self._list: QListWidget | None = None
        self._editor: QTextEdit | None = None
        self._title_label: QLabel | None = None
        self._modified_label: QLabel | None = None
        self._save_timer: QTimer | None = None
        self._service = None
        self._notes_cache: dict[int, dict] = {}
        self._search_text = ""

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self._page = PageContainer()
        layout.addWidget(self._page)

        self._build_header()
        self._build_content()

    def _build_header(self) -> None:
        header = SectionHeader("My Notes", "New Note")
        if header.action_button:
            header.action_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: 1px solid var(--accent-green);
                    border-radius: 3px;
                    padding: 4px 10px;
                    font-size: 11px;
                    color: var(--accent-green);
                }
                QPushButton:hover {
                    background-color: var(--accent-bg);
                }
            """)
            header.action_button.clicked.connect(self._on_new_note)
        self._page.add_widget(header)

    def _build_content(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        panel = QWidget()
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(8)

        search_label = QLabel("Search notes:")
        search_label.setStyleSheet("color: var(--text-secondary); font-size: 11px;")
        panel_layout.addWidget(search_label)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter notes...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search_changed)
        panel_layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_list_context_menu)
        self._list.itemClicked.connect(self._on_list_item_clicked)
        panel_layout.addWidget(self._list)

        panel.setLayout(panel_layout)

        editor_panel = QWidget()
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)

        self._title_label = QLabel("No note selected")
        self._title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: var(--text-primary);")
        editor_layout.addWidget(self._title_label)

        self._modified_label = QLabel("")
        self._modified_label.setStyleSheet("font-size: 10px; color: var(--text-tertiary);")
        editor_layout.addWidget(self._modified_label)

        self._editor = QTextEdit()
        self._editor.setPlaceholderText("Enter your note content...")
        self._editor.textChanged.connect(self._on_text_changed)
        editor_layout.addWidget(self._editor, 1)

        editor_panel.setLayout(editor_layout)

        splitter.addWidget(panel)
        splitter.addWidget(editor_panel)
        splitter.setSizes([300, 700])
        splitter.setStyleSheet("""
            QSplitter::handle {
                border: 1px solid var(--border-color);
                background-color: var(--border-color);
            }
            QSplitter::handle:hover {
                background-color: var(--accent-green);
            }
        """)

        self._page.add_widget(splitter)

    def set_service(self, service) -> None:
        self._service = service
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_note)

    def populate(self, notes: list[dict]) -> None:
        self._notes_cache = {n["id"]: n for n in notes}
        current_id = self._current_note_id
        self._list.blockSignals(True)
        self._apply_filter()
        self._list.blockSignals(False)
        if current_id is not None:
            self._select_note_in_list(current_id)

    def _apply_filter(self) -> None:
        self._list.clear()
        search = self._search_text.strip().lower()
        for note in self._notes_cache.values():
            title = note["title"].lower()
            content = (note["content"] or "").lower()
            if search and search not in title and search not in content:
                continue
            item = QListWidgetItem(note["title"])
            item.setData(Qt.ItemDataRole.UserRole, note["id"])
            self._list.addItem(item)

    def _on_search_changed(self, text: str) -> None:
        self._search_text = text
        self._apply_filter()

    def _on_list_item_clicked(self, item: QListWidgetItem) -> None:
        note_id = item.data(Qt.ItemDataRole.UserRole)
        note = self._notes_cache.get(note_id)
        if note is None:
            return
        self._start_editing(note)

    def _start_editing(self, note: dict) -> None:
        if self._editor is not None and self._title_label is not None and self._modified_label is not None:
            self._editor.textChanged.disconnect(self._on_text_changed)
            self._current_note_id = note["id"]
            self._title_label.setText(note["title"])
            self._modified_label.setText(f"Updated: {note.get('updated_at', '')}")
            self._editor.setText(note["content"])
            self._editor.textChanged.connect(self._on_text_changed)
            self.note_selected.emit(note["id"])

    def _on_text_changed(self) -> None:
        if self._save_timer is not None:
            self._save_timer.start(1000)
        if self._modified_label:
            self._modified_label.setText("Updated: now")

    def _save_note(self) -> None:
        if self._current_note_id is None or self._service is None or self._editor is None or self._title_label is None:
            return
        title = self._title_label.text()
        content = self._editor.toPlainText()
        note = self._notes_cache.get(self._current_note_id)
        if note:
            note["title"] = title
            note["content"] = content
        self._service.save_note(self._current_note_id, title, content)

    def _on_new_note(self) -> None:
        if self._service is None:
            return
        title, ok = QInputDialog.getText(self, "New Note", "Note title:", text="Untitled Note")
        if ok and title:
            title = title.strip() or "Untitled Note"
            note_id = self._service.create_note(title)
            self._select_note_in_list(note_id)

    def _select_note_in_list(self, note_id: int) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == note_id:
                self._list.setCurrentItem(item)
                return

    def _on_list_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if not item:
            return
        note_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")

        rename_action.triggered.connect(lambda: self._rename_note(note_id))
        delete_action.triggered.connect(lambda: self._delete_note(note_id))

        menu.exec(self._list.mapToGlobal(pos))

    def _rename_note(self, note_id: int) -> None:
        note = self._notes_cache.get(note_id)
        if note is None:
            return
        current_title = note.get("title", "")
        new_title, ok = QInputDialog.getText(self, "Rename Note", "New title:", text=current_title)
        if ok and new_title:
            self.note_renamed.emit(note_id, new_title.strip() or "Untitled Note")

    def _delete_note(self, note_id: int) -> None:
        note = self._notes_cache.get(note_id)
        if note is None:
            return
        title = note.get("title", "")
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Note")
        msg.setText(f"Delete note \"{title}\"?")
        msg.setInformativeText("This action cannot be undone.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        result = msg.exec()
        if result == QMessageBox.StandardButton.Ok:
            self.note_deleted.emit(note_id)

    def get_list(self) -> QListWidget:
        return self._list

    def get_editor(self) -> QTextEdit:
        return self._editor

    def get_title_label(self) -> QLabel:
        return self._title_label

    def get_modified_label(self) -> QLabel:
        return self._modified_label
