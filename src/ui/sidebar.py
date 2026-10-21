"""Sidebar navigation widget for QuickDrop.

Displays the application logo, navigation items, and a version label.
Emitting `item_selected(str)` when a navigation item is clicked.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QSizePolicy, QSpacerItem,
)


class Sidebar(QWidget):
    item_selected = Signal(str)

    ITEMS = [
        ("overview", "Overview"),
        ("clipboard", "Clipboard"),
        ("folders", "Quick Folders"),
        ("notes", "Notes"),
        ("settings", "Settings"),
    ]

    def __init__(self, version: str = "1.0.0", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._version = version
        self._active_item = "overview"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(8)

        header = self._build_header()
        layout.addLayout(header)

        self._nav_layout = QVBoxLayout()
        self._nav_layout.setContentsMargins(12, 12, 12, 0)
        self._nav_layout.setSpacing(4)
        layout.addLayout(self._nav_layout)

        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        layout.addItem(spacer)

        footer = self._build_footer()
        layout.addLayout(footer)

        self.setLayout(layout)
        self._create_nav_items()
        self.setFixedWidth(220)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setContentsMargins(16, 8, 16, 16)
        header.setSpacing(12)

        logo = QLabel()
        logo_path = Path(__file__).resolve().parent.parent.parent / "assets" / "app_icon.ico"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path)).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(pixmap)
        else:
            logo.setFixedSize(32, 32)
            logo.setStyleSheet("background-color: var(--accent-green); border-radius: 6px;")

        name_label = QLabel("QuickDrop")
        name_label.setStyleSheet("font-size: 16px; font-weight: 700; color: var(--text-primary);")
        name_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))

        header.addWidget(logo)
        header.addWidget(name_label)
        header.addStretch()

        return header

    def _create_nav_items(self) -> None:
        for key, label in self.ITEMS:
            btn = QPushButton(label)
            btn.setObjectName(f"nav_{key}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._nav_button_style(False))
            btn.setCheckable(True)
            btn.setChecked(key == self._active_item)
            btn.clicked.connect(lambda checked, k=key: self._on_item_clicked(k))
            self._nav_layout.addWidget(btn)

    def _nav_button_style(self, active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: var(--accent-bg);
                    color: var(--accent-green);
                    border: none;
                    border-left: 3px solid var(--accent-green);
                    padding: 10px 16px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: var(--bg-hover);
                    color: var(--accent-green);
                }
            """
        return """
            QPushButton {
                background: transparent;
                color: var(--text-secondary);
                border: none;
                border-left: 3px solid transparent;
                padding: 10px 16px;
                text-align: left;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: var(--bg-hover);
                color: var(--text-primary);
            }
        """

    def _on_item_clicked(self, key: str) -> None:
        if key == self._active_item:
            return
        old_btn = self.findChild(QPushButton, f"nav_{self._active_item}")
        if old_btn:
            old_btn.setStyleSheet(self._nav_button_style(False))
            old_btn.setChecked(False)
        self._active_item = key
        new_btn = self.findChild(QPushButton, f"nav_{key}")
        if new_btn:
            new_btn.setStyleSheet(self._nav_button_style(True))
            new_btn.setChecked(True)
        self.item_selected.emit(key)

    def set_active(self, key: str) -> None:
        if key in [k for k, _ in self.ITEMS]:
            self._on_item_clicked(key)

    def _build_footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setContentsMargins(16, 0, 16, 16)
        footer.setSpacing(8)

        version_label = QLabel(f"v{self._version}")
        version_label.setStyleSheet("color: var(--text-tertiary); font-size: 11px;")

        footer.addWidget(version_label)
        footer.addStretch()

        return footer
