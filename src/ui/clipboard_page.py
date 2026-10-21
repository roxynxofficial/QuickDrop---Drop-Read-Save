"""Clipboard history management page."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMenu,
)

from src.ui.widgets import SectionHeader, PageContainer


class ClipboardPage(QWidget):
    copy_requested = Signal(str)
    pin_toggled = Signal(int, bool)
    favorite_toggled = Signal(int, bool)
    entry_deleted = Signal(int)
    clear_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._page = PageContainer()
        layout.addWidget(self._page)

        self._build_search()
        self._build_toolbar()
        self._build_list()

        self.setLayout(layout)

    def _build_search(self) -> None:
        search_container = QWidget()
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(12)

        search_label = QLabel("Search clipboard:")
        search_label.setStyleSheet("color: var(--text-secondary); font-size: 12px;")

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search entries...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search_changed)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self._search, 1)
        search_container.setLayout(search_layout)
        self._page.add_widget(search_container)

    def _build_toolbar(self) -> None:
        header = SectionHeader("Clipboard History", "Clear All")
        if header.action_button:
            header.action_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: 1px solid var(--border-color);
                    border-radius: 3px;
                    padding: 4px 10px;
                    font-size: 11px;
                    color: var(--text-secondary);
                }
                QPushButton:hover {
                    background-color: #cf6679;
                    color: #ffffff;
                    border-color: #cf6679;
                }
            """)
            header.action_button.clicked.connect(self.clear_requested.emit)

        self._page.add_widget(header)

        self._monitor_label = QLabel()
        self._monitor_label.setStyleSheet("font-size: 11px; color: var(--text-secondary);")
        self._page.add_widget(self._monitor_label)

    def _build_list(self) -> None:
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.setStyleSheet("""
            QListWidget {
                background-color: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 4px;
                outline: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 12px 16px;
                min-height: 50px;
                border-bottom: 1px solid var(--border-color);
            }
            QListWidget::item:selected {
                background-color: var(--bg-selection);
            }
            QListWidget::item:hover {
                background-color: var(--bg-hover);
            }
        """)

        wrapper = QWidget()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(self._list)
        wrapper.setLayout(vbox)
        self._page.add_widget(wrapper)

    def _on_search_changed(self, text: str) -> None:
        search = text.lower()
        for i in range(self._list.count()):
            item = self._list.item(i)
            content = item.data(Qt.ItemDataRole.UserRole + 1) or ""
            if search in content.lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        content = item.data(Qt.ItemDataRole.UserRole + 1) or ""
        if content:
            self.copy_requested.emit(content)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        content = item.data(Qt.ItemDataRole.UserRole + 1) or ""
        self.copy_requested.emit(content)

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        copy_action = menu.addAction("Copy to Clipboard")
        pin_action = menu.addAction("Pin" if not item.data(Qt.ItemDataRole.UserRole) else "Unpin")
        favorite_action = menu.addAction("Add to Favorites" if not item.data(Qt.ItemDataRole.UserRole + 2) else "Remove from Favorites")
        delete_action = menu.addAction("Delete")

        copy_action.triggered.connect(lambda: self.copy_requested.emit(item.data(Qt.ItemDataRole.UserRole + 1)))
        pin_action.triggered.connect(lambda: self.pin_toggled.emit(item.data(Qt.ItemDataRole.UserRole + 3), not item.data(Qt.ItemDataRole.UserRole)))
        favorite_action.triggered.connect(lambda: self.favorite_toggled.emit(item.data(Qt.ItemDataRole.UserRole + 3), not item.data(Qt.ItemDataRole.UserRole + 2)))
        delete_action.triggered.connect(lambda: self.entry_deleted.emit(item.data(Qt.ItemDataRole.UserRole + 3)))

        menu.exec(QCursor.pos())

    def set_monitoring_status(self, enabled: bool, count: int) -> None:
        if enabled:
            self._monitor_label.setText(f"Monitoring active — {count} entries captured")
            self._monitor_label.setStyleSheet("font-size: 11px; color: var(--accent-green);")
        else:
            self._monitor_label.setText(f"Monitoring disabled — {count} entries stored")
            self._monitor_label.setStyleSheet("font-size: 11px; color: var(--text-tertiary);")

    def populate(self, entries: list[dict]) -> None:
        self._list.clear()
        for entry in entries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole + 3, entry["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, entry["content"])
            pin = entry.get("is_pinned", False)
            fav = entry.get("is_favorite", False)
            item.setData(Qt.ItemDataRole.UserRole, bool(pin))
            item.setData(Qt.ItemDataRole.UserRole + 2, bool(fav))

            content = entry["content"]
            preview = content if len(content) <= 100 else content[:97] + "..."
            preview = preview.replace("\n", " ").replace("\t", " ")

            widget = self._create_item_widget(preview, entry["timestamp"], pin, fav)
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _create_item_widget(self, preview: str, timestamp: str, pinned: bool, favorited: bool) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(14)

        icon_label = QLabel("📋" if not pinned else "📌")
        icon_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_label)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(3)

        preview_label = QLabel(preview)
        preview_label.setStyleSheet("font-size: 13px; color: var(--text-primary);")
        preview_label.setToolTip(preview)
        preview_label.setWordWrap(True)
        content_layout.addWidget(preview_label)

        time_label = QLabel(timestamp)
        time_label.setStyleSheet("font-size: 11px; color: var(--text-tertiary);")
        content_layout.addWidget(time_label)

        layout.addLayout(content_layout)
        layout.addStretch()

        if favorited:
            star = QLabel("★")
            star.setStyleSheet("font-size: 18px; color: var(--accent-green);")
            layout.addWidget(star)
        else:
            star = QLabel("☆")
            star.setStyleSheet("font-size: 18px; color: var(--text-tertiary);")
            layout.addWidget(star)

        widget.setLayout(layout)
        return widget

    def get_search_field(self) -> QLineEdit:
        return self._search

    def get_list(self) -> QListWidget:
        return self._list
