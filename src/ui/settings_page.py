"""Settings page for QuickDrop configuration."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox,
)

from src.ui.widgets import SectionHeader, PageContainer
from src.services.settings_service import VALID_THEMES, VALID_START_PAGES


class SettingsPage(QWidget):
    theme_changed = Signal(str)
    monitoring_changed = Signal(bool)
    max_history_changed = Signal(int)
    start_page_changed = Signal(str)

    def __init__(self, settings_service, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings_service
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self._page = PageContainer()
        layout.addWidget(self._page)

        self._build_theme_section()
        self._build_clipboard_section()
        self._build_behavior_section()
        self._build_about_section()
        self._page.add_spacer()

    def _build_theme_section(self) -> None:
        header = SectionHeader("Appearance")
        self._page.add_widget(header)

        group = QGroupBox()
        group.setStyleSheet("QGroupBox { border: 1px solid var(--border-color); border-radius: 6px; margin-top: 8px; } QGroupBox::title { color: var(--text-secondary); font-size: 11px; padding-left: 8px; }")
        form = QFormLayout(group)
        form.setContentsMargins(12, 16, 12, 12)
        form.setSpacing(12)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Dark", "Light"])
        theme_index = 0 if VALID_THEMES[0] == self._settings.theme else 1
        self._theme_combo.setCurrentIndex(theme_index)
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        form.addRow("Theme:", self._theme_combo)

        self._page.add_widget(group)

    def _build_clipboard_section(self) -> None:
        header = SectionHeader("Clipboard")
        self._page.add_widget(header)

        group = QGroupBox()
        group.setStyleSheet("QGroupBox { border: 1px solid var(--border-color); border-radius: 6px; margin-top: 8px; } QGroupBox::title { color: var(--text-secondary); font-size: 11px; padding-left: 8px; }")
        form = QFormLayout(group)
        form.setContentsMargins(12, 16, 12, 12)
        form.setSpacing(12)

        self._monitor_checkbox = QCheckBox("Enable clipboard monitoring")
        self._monitor_checkbox.setChecked(self._settings.clipboard_monitoring_enabled)
        self._monitor_checkbox.stateChanged.connect(self._on_monitor_changed)
        form.addRow("", self._monitor_checkbox)

        self._max_history_spin = QSpinBox()
        self._max_history_spin.setRange(1, 200)
        self._max_history_spin.setValue(self._settings.max_clipboard_history)
        self._max_history_spin.setSuffix(" entries")
        self._max_history_spin.setToolTip("Maximum number of clipboard entries to keep (pinned entries are not affected).")
        self._max_history_spin.valueChanged.connect(self._on_max_history_changed)
        form.addRow("Max history size:", self._max_history_spin)

        self._page.add_widget(group)

    def _build_behavior_section(self) -> None:
        header = SectionHeader("Application")
        self._page.add_widget(header)

        group = QGroupBox()
        group.setStyleSheet("QGroupBox { border: 1px solid var(--border-color); border-radius: 6px; margin-top: 8px; } QGroupBox::title { color: var(--text-secondary); font-size: 11px; padding-left: 8px; }")
        form = QFormLayout(group)
        form.setContentsMargins(12, 16, 12, 12)
        form.setSpacing(12)

        self._start_page_combo = QComboBox()
        for label, value in zip(["Overview", "Clipboard", "Quick Folders", "Notes"], VALID_START_PAGES):
            self._start_page_combo.addItem(label, value)
        current = self._settings.start_page
        idx = self._start_page_combo.findData(current)
        if idx >= 0:
            self._start_page_combo.setCurrentIndex(idx)
        self._start_page_combo.currentIndexChanged.connect(self._on_start_page_changed)
        form.addRow("Start page:", self._start_page_combo)

        self._always_on_top_checkbox = QCheckBox("Keep window on top")
        self._always_on_top_checkbox.setChecked(self._settings.always_on_top)
        form.addRow("", self._always_on_top_checkbox)

        self._page.add_widget(group)

    def _build_about_section(self) -> None:
        header = SectionHeader("About")
        self._page.add_widget(header)

        group = QGroupBox()
        group.setStyleSheet("QGroupBox { border: 1px solid var(--border-color); border-radius: 6px; } QGroupBox::title { color: var(--text-secondary); font-size: 11px; padding-left: 8px; }")
        form = QFormLayout(group)
        form.setContentsMargins(12, 16, 12, 12)
        form.setSpacing(8)

        version_label = QLabel(f"QuickDrop v{self._settings.version}")
        version_label.setStyleSheet("font-weight: 600;")
        form.addRow("Version:", version_label)

        python_label = QLabel("Python 3.11+ with PySide6")
        form.addRow("Runtime:", python_label)

        desc_label = QLabel("A lightweight local clipboard and notes manager for Windows.")
        desc_label.setStyleSheet("color: var(--text-secondary); font-size: 12px;")
        desc_label.setWordWrap(True)
        form.addRow(desc_label)

        self._page.add_widget(group)

        data_row = QHBoxLayout()
        data_row.setContentsMargins(0, 8, 0, 0)
        data_row.setSpacing(12)

        self._clear_data_btn = QPushButton("Clear All Application Data")
        self._clear_data_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_data_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid var(--border-color);
                border-radius: 3px;
                padding: 6px 14px;
                font-size: 12px;
                color: var(--text-secondary);
            }
            QPushButton:hover {
                background-color: #cf6679;
                color: #ffffff;
                border-color: #cf6679;
            }
        """)
        self._clear_data_btn.clicked.connect(self._on_clear_data)
        data_row.addWidget(self._clear_data_btn)
        data_row.addStretch()

        self._page.add_widget(QWidget())
        self._page.content_layout.addLayout(data_row)

    @property
    def always_on_top(self) -> bool:
        return self._always_on_top_checkbox.isChecked()

    @property
    def monitor_checkbox(self) -> QCheckBox:
        return self._monitor_checkbox

    @property
    def clear_data_button(self) -> QPushButton:
        return self._clear_data_btn

    def _on_theme_changed(self, text: str) -> None:
        new_theme = VALID_THEMES[0] if text == "Dark" else VALID_THEMES[1]
        self._settings.theme = new_theme
        self.theme_changed.emit(new_theme)

    def _on_monitor_changed(self, state: int) -> None:
        enabled = state != 0
        self._settings.clipboard_monitoring_enabled = enabled
        self.monitoring_changed.emit(enabled)

    def _on_max_history_changed(self, value: int) -> None:
        self._settings.max_clipboard_history = value
        self.max_history_changed.emit(value)

    def _on_start_page_changed(self, index: int) -> None:
        value = self._start_page_combo.itemData(index)
        if value:
            self._settings.start_page = value
            self.start_page_changed.emit(value)

    def _on_clear_data(self) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("Clear All Data")
        msg.setText("Permanently delete all QuickDrop data?")
        msg.setInformativeText("This will remove all clipboard history, folders, notes, and settings. This action cannot be undone.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        msg.setIcon(QMessageBox.Icon.Warning)
        result = msg.exec()
        if result == QMessageBox.StandardButton.Ok:
            self._settings.delete_all_data()
