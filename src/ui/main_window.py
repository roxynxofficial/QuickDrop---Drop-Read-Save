"""Main application window for QuickDrop.

Combines the sidebar navigation, top bar, and stacked content pages.
Manages service lifecycle and navigation between pages.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QTimer, QRect
from PySide6.QtGui import QFont, QIcon, QAction, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QLabel, QPushButton, QGraphicsDropShadowEffect,
)

from src.storage.database import Database
from src.services.settings_service import SettingsService
from src.services.clipboard_service import ClipboardService
from src.services.folder_service import FolderService
from src.services.notes_service import NotesService

from src.ui.sidebar import Sidebar
from src.ui.overview_page import OverviewPage
from src.ui.clipboard_page import ClipboardPage
from src.ui.folders_page import FoldersPage
from src.ui.notes_page import NotesPage
from src.ui.settings_page import SettingsPage
from src.styles.colors import install_style_patch, reapply_styles, ThemeColors


class TitleBar(QWidget):
    """Custom window title bar with drag support and window controls."""

    def __init__(self, parent_window: QMainWindow) -> None:
        super().__init__()
        self._window = parent_window
        self.setFixedHeight(38)
        self._drag_active = False
        self._drag_position: QPoint | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(12)

        icon_label = QLabel()
        icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "app_icon.ico"
        if icon_path.exists():
            pixmap = QIcon(str(icon_path)).pixmap(18, 18)
            icon_label.setPixmap(pixmap)
        icon_label.setFixedSize(18, 18)
        layout.addWidget(icon_label)

        title = QLabel("QuickDrop")
        title.setStyleSheet("font-size: 12px; font-weight: 600; color: var(--text-secondary);")
        layout.addWidget(title)

        layout.addStretch()

        self._min_btn = self._make_window_btn("_", "minimize")
        self._max_btn = self._make_window_btn("□", "maximize")
        self._close_btn = self._make_window_btn("✕", "close")

        layout.addWidget(self._min_btn)
        layout.addWidget(self._max_btn)
        layout.addWidget(self._close_btn)

        self.setLayout(layout)

    def _make_window_btn(self, text: str, role: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(46, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if role == "close":
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff5f57;
                    color: var(--text-primary);
                    border: none;
                    border-radius: 0;
                }
                QPushButton:hover {
                    background-color: #ff2d20;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: var(--bg-tertiary);
                    color: var(--text-primary);
                    border: none;
                    border-radius: 0;
                }
                QPushButton:hover {
                    background-color: var(--bg-hover);
                    color: var(--accent-green);
                }
            """)
        btn.clicked.connect(self._on_window_btn_clicked(role))
        return btn

    def _on_window_btn_clicked(self, role: str):
        def _handler() -> None:
            if role == "minimize":
                self._animate_minimize()
            elif role == "maximize":
                self._animate_maximize()
            elif role == "close":
                self._animate_close()
        return _handler

    def _animate_minimize(self) -> None:
        self._fade_out_then(self._window.showMinimized, duration=150)

    def _animate_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def _animate_close(self) -> None:
        self._fade_out_then(lambda: None, duration=300, on_done=self._do_close)

    def _fade_out_then(self, final_action, duration: int = 200, on_done=None) -> None:
        anim = QPropertyAnimation(self._window, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InQuad)
        def _finish():
            self._window.setWindowOpacity(1.0)
            if on_done:
                on_done()
            else:
                final_action()
        anim.finished.connect(_finish)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._active_anim = anim

    def _do_close(self) -> None:
        app = QApplication.instance()
        for w in app.allWidgets():
            if w.isVisible():
                w.close()
        app.quit()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_position = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_active and self._drag_position is not None:
            self._window.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_active = False
        self._drag_position = None
        event.accept()


class MainWindow(QMainWindow):
    PAGE_TITLES = {
        "overview": "Overview",
        "clipboard": "Clipboard History",
        "folders": "Quick Folders",
        "notes": "Notes",
        "settings": "Settings",
    }

    PAGE_DESCRIPTIONS = {
        "overview": "Application dashboard and quick actions",
        "clipboard": "Manage your clipboard history",
        "folders": "Favorite folders for quick access",
        "notes": "Create and organize local notes",
        "settings": "Application preferences and configuration",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("QuickDrop")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.resize(1100, 750)
        self.setMinimumSize(900, 650)

        db = Database.instance()
        self._db = db
        self._settings = SettingsService(db)
        self._clipboard_service = ClipboardService(db, self._settings.clipboard_monitoring_enabled)
        self._folder_service = FolderService(db)
        self._notes_service = NotesService(db)

        self._clipboard_service.max_size = self._settings.max_clipboard_history
        self._clipboard_service.set_callback(self._on_clipboard_changed)
        self._clipboard_service.enabled = self._settings.clipboard_monitoring_enabled

        self._folder_service.set_callback(self._on_folders_changed)
        self._notes_service.set_callback(self._on_notes_changed)

        self._init_services()
        self._build_ui()
        self._connect_signals()
        self._apply_theme(self._settings.theme)
        self._apply_glow()
        self._connect_page_actions()

    def _init_services(self) -> None:
        self._current_page_key = self._settings.start_page

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._title_bar = TitleBar(self)
        self._title_bar.setObjectName("TitleBar")
        main_layout.addWidget(self._title_bar)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        main_layout.addLayout(content_layout)

        self._sidebar = Sidebar(version=self._settings.version)
        content_layout.addWidget(self._sidebar)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        content_layout.addLayout(right_layout)

        self._top_bar = self._build_top_bar()
        self._top_bar.setObjectName("TopBar")
        right_layout.addWidget(self._top_bar)

        self._stack = QStackedWidget()
        self._stack.setObjectName("MainStack")
        right_layout.addWidget(self._stack)

        central.setLayout(main_layout)

        self._glow = QGraphicsDropShadowEffect()
        self._glow.setColor(QColor("#ff5f57"))
        self._glow.setBlurRadius(25)
        self._glow.setXOffset(0)
        self._glow.setYOffset(0)
        self.setGraphicsEffect(self._glow)

        self._pages: dict[str, QWidget] = {}
        self._create_pages()

    def _apply_glow(self) -> None:
        if self._glow is not None:
            self.setGraphicsEffect(self._glow)

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        layout = QHBoxLayout()
        layout.setContentsMargins(24, 0, 16, 0)
        layout.setSpacing(16)

        self._page_title = QLabel("Overview")
        title_font = QFont("Segoe UI", 16, QFont.Weight.DemiBold)
        self._page_title.setFont(title_font)
        self._page_title.setStyleSheet("color: var(--text-primary);")
        layout.addWidget(self._page_title)

        self._page_desc = QLabel("Application dashboard and quick actions")
        self._page_desc.setStyleSheet("color: var(--text-secondary); font-size: 13px;")
        layout.addWidget(self._page_desc)

        layout.addStretch()

        self._theme_toggle = QPushButton()
        self._theme_toggle.setCheckable(True)
        self._theme_toggle.setFixedSize(42, 32)
        self._theme_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_toggle.setStyleSheet("""
            QPushButton {
                background-color: var(--bg-tertiary);
                border: 1px solid var(--border-color);
                border-radius: 5px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: var(--bg-hover);
                color: var(--accent-green);
            }
        """)
        layout.addWidget(self._theme_toggle)

        bar.setLayout(layout)
        return bar

    def _create_pages(self) -> None:
        self._overview = OverviewPage()
        self._clipboard_page = ClipboardPage()
        self._folders = FoldersPage()
        self._notes = NotesPage()
        self._settings_page = SettingsPage(self._settings)

        self._folders.set_service(self._folder_service)

        self._pages["overview"] = self._overview
        self._pages["clipboard"] = self._clipboard_page
        self._pages["folders"] = self._folders
        self._pages["notes"] = self._notes
        self._pages["settings"] = self._settings_page

        for key, page in self._pages.items():
            self._stack.addWidget(page)

        self._refresh_all_pages()

    def _connect_signals(self) -> None:
        self._sidebar.item_selected.connect(self._on_page_selected)

        self._settings_page.theme_changed.connect(self._on_theme_changed)
        self._settings_page.monitoring_changed.connect(self._on_monitoring_changed)
        self._settings_page.max_history_changed.connect(self._on_max_history_changed)
        self._settings_page.start_page_changed.connect(self._on_start_page_changed)

    def _connect_page_actions(self) -> None:
        self._clipboard_service.set_callback(self._on_clipboard_changed)

        self._clipboard_page.copy_requested.connect(self._clipboard_service.copy_to_clipboard)
        self._clipboard_page.pin_toggled.connect(self._clipboard_service.pin_entry)
        self._clipboard_page.favorite_toggled.connect(self._clipboard_service.favorite_entry)
        self._clipboard_page.entry_deleted.connect(self._clipboard_service.delete_entry)
        self._clipboard_page.clear_requested.connect(self._on_clear_history)

        self._overview.get_action_buttons()["note"].clicked.connect(self._switch_to_notes)
        self._overview.get_action_buttons()["folder"].clicked.connect(self._switch_to_folders)
        self._overview.get_action_buttons()["history"].clicked.connect(self._switch_to_clipboard)

        self._folders.folder_added.connect(self._on_folder_added)
        self._folders.folder_opened.connect(self._folder_service.open_folder)
        self._folders.folder_removed.connect(self._folder_service.remove_folder)
        self._folders.setup_item_signals()

        self._notes.note_created.connect(self._on_notes_changed)
        self._notes.note_deleted.connect(self._delete_note)
        self._notes.note_renamed.connect(self._rename_note)
        self._notes.note_selected.connect(self._on_note_selected)

        self._setup_theme_toggle()

    def _setup_theme_toggle(self) -> None:
        self._update_theme_toggle()
        self._theme_toggle.clicked.connect(self._on_theme_toggle_clicked)

    def _update_theme_toggle(self) -> None:
        theme = self._settings.theme
        if theme == "dark":
            self._theme_toggle.setProperty("theme", "dark")
            self._theme_toggle.setToolTip("Switch to Light Theme")
        else:
            self._theme_toggle.setProperty("theme", "light")
            self._theme_toggle.setToolTip("Switch to Dark Theme")
        self._theme_toggle.style().unpolish(self._theme_toggle)
        self._theme_toggle.style().polish(self._theme_toggle)

    def _on_theme_toggle_clicked(self) -> None:
        new_theme = "light" if self._settings.theme == "dark" else "dark"
        self._settings.theme = new_theme
        self._apply_theme(new_theme)
        self._update_theme_toggle()

    def _on_theme_changed(self, theme: str) -> None:
        self._apply_theme(theme)
        self._update_theme_toggle()

    def _apply_theme(self, theme: str) -> None:
        ThemeColors.set_theme(theme)
        qss_path = Path(__file__).resolve().parent.parent / "styles" / "theme.qss"
        app = QApplication.instance()
        if app is None:
            return

        if qss_path.exists():
            qss = qss_path.read_text(encoding="utf-8")
            qss = self._substitute_theme_vars(qss, theme)
            app.setStyleSheet(qss)

        reapply_styles(self)

        if theme == "light":
            self._apply_light_palette()
        else:
            self._apply_dark_palette()

    @staticmethod
    def _substitute_theme_vars(qss: str, theme: str) -> str:
        return ThemeColors.substitute(qss)

    def _apply_dark_palette(self) -> None:
        from PySide6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.BrightText, QColor("#4ade80"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#1a2a1a"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#4ade80"))
        QApplication.instance().setPalette(palette)

    def _apply_light_palette(self) -> None:
        from PySide6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#a0d0ff"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#0060ad"))
        QApplication.instance().setPalette(palette)

    def _on_page_selected(self, key: str) -> None:
        self._current_page_key = key
        idx = list(self._pages.keys()).index(key)
        self._stack.setCurrentIndex(idx)
        self._page_title.setText(self.PAGE_TITLES.get(key, ""))
        self._page_desc.setText(self.PAGE_DESCRIPTIONS.get(key, ""))
        self._sidebar.set_active(key)

    def _on_clipboard_changed(self) -> None:
        self._clipboard_page.populate(self._clipboard_service.get_entries())
        self._clipboard_service.max_size = self._settings.max_clipboard_history
        self._refresh_overview()

    def _on_folders_changed(self) -> None:
        self._folders.populate(self._folder_service.get_folders())
        self._folders.setup_item_signals()
        self._refresh_overview()

    def _on_notes_changed(self) -> None:
        self._notes.populate(self._notes_service.get_notes())
        self._refresh_overview()

    def _refresh_overview(self) -> None:
        self._overview.update_stats(
            self._clipboard_service.count(),
            self._folder_service.count(),
            self._notes_service.count(),
        )
        self._update_recents()

    def _update_recents(self) -> None:
        db = self._db
        recents: list[dict] = []

        recent_items = db.get_recents(5)
        entries = {e["id"]: e for e in self._clipboard_service.get_entries()}
        folders = {f["id"]: f for f in self._folder_service.get_folders()}
        notes = {n["id"]: n for n in self._notes_service.get_notes()}

        for r in recent_items:
            if r["item_type"] == "clipboard" and r["item_id"] in entries:
                e = entries[r["item_id"]]
                content = e["content"]
                preview = content[:50] + "..." if len(content) > 50 else content
                preview = preview.replace("\n", " ").replace("\t", " ")
                recents.append({"title": f"Clipboard: {preview}", "type": "clipboard", "id": r["item_id"]})
            elif r["item_type"] == "folder" and r["item_id"] in folders:
                f = folders[r["item_id"]]
                recents.append({"title": f"Folder: {f['name']}", "type": "folder", "id": r["item_id"]})
            elif r["item_type"] == "note" and r["item_id"] in notes:
                n = notes[r["item_id"]]
                recents.append({"title": f"Note: {n['title']}", "type": "note", "id": r["item_id"]})

        self._overview.set_recents(recents[:8])

    def _refresh_all_pages(self) -> None:
        self._overview.update_stats(
            self._clipboard_service.count(),
            self._folder_service.count(),
            self._notes_service.count(),
        )
        self._clipboard_page.populate(self._clipboard_service.get_entries())
        self._clipboard_page.set_monitoring_status(
            self._clipboard_service.enabled,
            self._clipboard_service.count(),
        )
        self._folders.populate(self._folder_service.get_folders())
        self._folders.setup_item_signals()
        self._notes.populate(self._notes_service.get_notes())
        self._update_recents()

    def _on_folder_added(self) -> None:
        pass

    def _on_clear_history(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Clear Clipboard History")
        msg.setText("Delete all clipboard history?")
        msg.setInformativeText("This will remove all non-pinned entries. This action cannot be undone.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        msg.setIcon(QMessageBox.Icon.Question)
        result = msg.exec()
        if result == QMessageBox.StandardButton.Ok:
            self._clipboard_service.clear_history()
            self._clipboard_page.populate([])
            self._clipboard_page.set_monitoring_status(
                self._clipboard_service.enabled,
                self._clipboard_service.count(),
            )
            self._refresh_overview()

    def _on_monitoring_changed(self, enabled: bool) -> None:
        self._clipboard_service.enabled = enabled
        self._clipboard_page.set_monitoring_status(enabled, self._clipboard_service.count())

    def _on_max_history_changed(self, value: int) -> None:
        self._clipboard_service.max_size = value
        self._db.prune_clipboard_to_limit(value)

    def _on_start_page_changed(self, value: str) -> None:
        self._current_page_key = value
        self._on_page_selected(value)

    def _switch_to_notes(self) -> None:
        self._on_page_selected("notes")

    def _switch_to_folders(self) -> None:
        self._on_page_selected("folders")

    def _switch_to_clipboard(self) -> None:
        self._on_page_selected("clipboard")

    def _delete_note(self, note_id: int) -> None:
        self._notes_service.delete_note(note_id)
        self._notes.populate(self._notes_service.get_notes())
        self._refresh_overview()
        if self._notes._current_note_id == note_id:
            self._notes._current_note_id = None
            self._notes._title_label.setText("No note selected")
            self._notes._modified_label.setText("")
            self._notes._editor.setText("")

    def _rename_note(self, note_id: int, new_title: str) -> None:
        self._notes_service.rename_note(note_id, new_title)
        self._notes.populate(self._notes_service.get_notes())
        if self._notes._current_note_id == note_id:
            self._notes._title_label.setText(new_title)

    def _on_note_selected(self, note_id: int) -> None:
        self._db.add_or_update_recent("note", note_id)
        self._update_recents()

    def closeEvent(self, event):
        self._clipboard_service.cleanup()
        self._folder_service.cleanup()
        self._notes_service.cleanup()
        self._db.close_instance()
        super().closeEvent(event)
