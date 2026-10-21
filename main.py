"""QuickDrop - A lightweight Windows desktop utility.

Provides clipboard history management, quick-access folders, and local notes
in a polished, dark-themed interface.

Usage:
    python main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so `src` package is importable.
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from src.styles.colors import install_style_patch

from src.ui.main_window import MainWindow


def _load_fonts() -> None:
    fonts_dir = _PROJECT_ROOT / "assets" / "fonts"
    for f in fonts_dir.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))


def main() -> int:
    QCoreApplication.setApplicationName("QuickDrop")
    QCoreApplication.setApplicationVersion("1.0.0")
    QCoreApplication.setOrganizationName("QuickDrop")
    QCoreApplication.setOrganizationDomain("quickdrop.local")

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    install_style_patch()
    _load_fonts()

    icon_path = _PROJECT_ROOT / "assets" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()

    window.show()
    window.raise_()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
