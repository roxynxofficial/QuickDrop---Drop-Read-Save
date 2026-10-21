"""Reusable UI widgets used across QuickDrop pages."""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QFontMetrics, QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QSizePolicy, QStyle, QStyleOption, QFrame,
)


class StatCard(QWidget):
    """Compact statistic display used on the Overview page."""

    def __init__(self, title: str, value: str, icon_name: str = "") -> None:
        super().__init__()
        self.setObjectName("StatCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 28, 24, 28)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        icon_label = QLabel(icon_name)
        icon_label.setStyleSheet("font-size: 22px;")
        icon_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        top_row.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setProperty("style", "subtitle")
        title_font = QFont("Segoe UI", 12, QFont.Weight.Normal)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: var(--text-secondary); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;")
        top_row.addWidget(title_label)
        top_row.addStretch()

        value_label = QLabel(value)
        value_font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        value_label.setFont(value_font)
        value_label.setStyleSheet("color: var(--text-primary); font-size: 28px; font-weight: 700;")

        self._value_label = value_label
        layout.addLayout(top_row)
        layout.addWidget(value_label)
        self.setLayout(layout)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)


class IconButton(QPushButton):
    """Icon button with a fixed icon size and consistent styling."""

    def __init__(self, icon: QIcon | str, text: str = "", size: int = 18, parent=None) -> None:
        super().__init__(parent)
        if isinstance(icon, str):
            icon = QIcon(icon)
        self.setIcon(icon)
        self.setIconSize(QSize(size, size))
        if text:
            self.setText(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("IconButton")
        if text:
            self.setStyleSheet("text-align: left; padding-left: 8px;")


class SectionHeader(QWidget):
    """Section title with optional action button."""

    def __init__(self, title: str, action_text: str = "", parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setStyleSheet("font-size: 14px; font-weight: 600; color: var(--text-primary);")

        layout.addWidget(label)
        layout.addStretch()

        self._action_btn: QPushButton | None = None
        if action_text:
            self._action_btn = QPushButton(action_text)
            self._action_btn.setObjectName("SectionAction")
            self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._action_btn.setStyleSheet("""
                QPushButton#SectionAction {
                    background: transparent;
                    border: 1px solid var(--border-color);
                    border-radius: 3px;
                    padding: 4px 10px;
                    font-size: 11px;
                    color: var(--text-secondary);
                }
                QPushButton#SectionAction:hover {
                    background-color: var(--bg-hover);
                    color: var(--accent-green);
                }
            """)
            layout.addWidget(self._action_btn)

        self.setLayout(layout)

    @property
    def action_button(self) -> QPushButton | None:
        return self._action_btn


class PageContainer(QWidget):
    """A scrollable page container with a vertical layout."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        from PySide6.QtWidgets import QScrollArea
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)

        self._scroll.setWidget(self._content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._scroll)

        self._scroll.viewport().installEventFilter(self)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout

    def add_widget(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)

    def add_spacer(self) -> None:
        self._layout.addStretch()

    def clear(self) -> None:
        while item := self._layout.takeAt(0):
            widget = item.widget()
            if widget:
                widget.deleteLater()
