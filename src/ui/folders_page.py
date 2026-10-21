"""Quick folders management page."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QFontMetrics, QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMenu, QFileDialog, QMessageBox,
    QAbstractItemView,
)

from src.ui.widgets import SectionHeader, PageContainer


class FoldersPage(QWidget):
    folder_opened = Signal(str)
    folder_added = Signal()
    folder_removed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._service = None
        self._folder_data: dict[int, dict] = {}
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._page = PageContainer()
        layout.addWidget(self._page)

        self._build_header()
        self._build_list()

        self.setLayout(layout)

    def _build_header(self) -> None:
        header = SectionHeader("Favorite Folders", "Add Folder")
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
            header.action_button.setIcon(self._folder_icon())
            header.action_button.clicked.connect(self._on_add_folder)

        self._page.add_widget(header)

    def _folder_icon(self) -> QIcon:
        return QIcon.fromTheme("folder", QPixmap(16, 16))

    def _build_list(self) -> None:
        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setStyleSheet("""
            QListWidget {
                background-color: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 4px;
                outline: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 14px 16px;
                min-height: 60px;
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

        self._empty_label = QLabel("No favorite folders added yet.")
        self._empty_label.setStyleSheet("color: var(--text-tertiary); font-size: 12px; padding: 16px 0;")
        self._page.add_widget(self._empty_label)

    def _on_add_folder(self) -> None:
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, False)
        dialog.setWindowTitle("Select Folder")
        if dialog.exec() == 1:
            selected = dialog.selectedFiles()
            if selected:
                from pathlib import Path
                p = Path(selected[0])
                if not p.exists():
                    return
                name = p.name or str(p)
                msg = QMessageBox(self)
                msg.setWindowTitle("Add Folder")
                msg.setText(f'Add "{name}" to QuickDrop favorites?')
                msg.setInformativeText(f"Path: {selected[0]}")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
                msg.setDefaultButton(QMessageBox.StandardButton.Ok)
                if msg.exec() == QMessageBox.StandardButton.Ok:
                    if self._service is not None:
                        self._service.add_folder(str(p))

    def set_service(self, service) -> None:
        self._service = service

    def populate(self, folders: list[dict]) -> None:
        self._list.clear()
        self._folder_data: dict[int, dict] = {}

        for f in folders:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole + 1, f["path"])
            item.setData(Qt.ItemDataRole.UserRole + 2, f["id"])

            widget = self._create_item_widget(f["name"], f["path"], f.get("exists", True))
            hint = widget.sizeHint()
            item_height = max(hint.height(), 100)
            widget.setFixedHeight(item_height)
            item.setSizeHint(QSize(hint.width(), item_height))
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)
            self._folder_data[self._list.row(item)] = f

        self._empty_label.setVisible(len(folders) == 0)

    def _create_item_widget(self, name: str, path: str, exists: bool) -> QWidget:
        from pathlib import Path
        widget = QWidget()
        widget.setStyleSheet("background-color: var(--bg-secondary);")
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(16)

        icon_label = QLabel("\U0001F4C1" if exists else "\U0001F4C1" + " (missing)")
        icon_label.setStyleSheet("font-size: 26px; font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif;")
        if not exists:
            icon_label.setStyleSheet("font-size: 26px; color: var(--text-tertiary); font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif;")
        layout.addWidget(icon_label)

        name_layout = QVBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(6)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 16px; font-weight: 600; color: var(--text-primary);")
        name_label.setToolTip(path)

        path_label = QLabel(path)
        path_label.setStyleSheet("font-size: 13px; color: #ffffff;")
        path_label.setToolTip(path)
        fm = QFontMetrics(QFont("Segoe UI", 11))
        elided = fm.elidedText(path, Qt.TextElideMode.ElideRight, 400)
        path_label.setText(elided)

        name_layout.addWidget(name_label)
        name_layout.addWidget(path_label)

        layout.addLayout(name_layout)
        layout.addStretch()

        open_btn = QPushButton("Open")
        open_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid var(--border-color);
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 14px;
                color: var(--text-primary);
            }
            QPushButton:hover {
                background-color: var(--bg-hover);
                color: var(--accent-green);
            }
        """)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(open_btn)

        widget.setLayout(layout)
        widget._open_btn = open_btn
        return widget

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole + 1)
        self.folder_opened.emit(path)

    def setup_item_signals(self) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            widget = self._list.itemWidget(item)
            if widget and hasattr(widget, '_open_btn'):
                path = item.data(Qt.ItemDataRole.UserRole + 1)
                widget._open_btn.clicked.connect(lambda checked=False, p=path: self.folder_opened.emit(p))

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        open_action = menu.addAction("Open in Explorer")
        remove_action = menu.addAction("Remove from Favorites")

        path = item.data(Qt.ItemDataRole.UserRole + 1)
        folder_id = item.data(Qt.ItemDataRole.UserRole + 2)

        open_action.triggered.connect(lambda: self.folder_opened.emit(path))
        remove_action.triggered.connect(lambda: self.folder_removed.emit(folder_id))

        menu.exec(self._list.mapToGlobal(pos))

    def get_list(self) -> QListWidget:
        return self._list
