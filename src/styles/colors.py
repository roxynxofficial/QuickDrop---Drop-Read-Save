"""Theme color constants and style substitution.

Provides color values for dark and light themes, and a helper to
substitute `var(--name)` references in inline stylesheets.
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget


class ThemeColors:
    DARK = {
        "bg_primary": "#000000",
        "bg_secondary": "#000000",
        "bg_tertiary": "#000000",
        "bg_hover": "#000000",
        "bg_selection": "#1a2a1a",
        "bg_accent": "#000000",
        "border_color": "#000000",
        "border_light": "#000000",
        "text_primary": "#ffffff",
        "text_secondary": "#ffffff",
        "text_tertiary": "#ffffff",
        "accent_green": "#4ade80",
        "accent_hover": "#3db76b",
        "accent_bg": "#1a2a1a",
    }

    LIGHT = {
        "bg_primary": "#000000",
        "bg_secondary": "#000000",
        "bg_tertiary": "#000000",
        "bg_hover": "#000000",
        "bg_selection": "#a0d0ff",
        "bg_accent": "#000000",
        "border_color": "#000000",
        "border_light": "#000000",
        "text_primary": "#ffffff",
        "text_secondary": "#ffffff",
        "text_tertiary": "#ffffff",
        "accent_green": "#22c55e",
        "accent_hover": "#16a34a",
        "accent_bg": "#d6f5d6",
    }

    _var_to_key = {
        "--bg-primary": "bg_primary",
        "--bg-secondary": "bg_secondary",
        "--bg-tertiary": "bg_tertiary",
        "--bg-hover": "bg_hover",
        "--bg-selection": "bg_selection",
        "--bg-accent": "bg_accent",
        "--border-color": "border_color",
        "--border-light": "border_light",
        "--text-primary": "text_primary",
        "--text-secondary": "text_secondary",
        "--text-tertiary": "text_tertiary",
        "--accent-green": "accent_green",
        "--accent-hover": "accent_hover",
        "--accent-bg": "accent_bg",
    }

    _current: dict[str, str] = DARK

    @classmethod
    def get(cls, name: str) -> str:
        return cls._current.get(cls._var_to_key.get(name, name), "")

    @classmethod
    def set_theme(cls, theme: str) -> None:
        if theme == "light":
            cls._current = cls.LIGHT
        else:
            cls._current = cls.DARK

    @classmethod
    def substitute(cls, style_str: str) -> str:
        if not style_str or "var(" not in style_str:
            return style_str
        result = style_str
        for var, key in cls._var_to_key.items():
            result = result.replace(f"var({var})", cls._current[key])
        return result


_style_templates: dict[int, str] = {}
_original_set_style_sheet = QWidget.setStyleSheet


def _substituting_set_style_sheet(self, style_sheet: str) -> None:
    if style_sheet and "var(" in style_sheet:
        _style_templates[id(self)] = style_sheet
        style_sheet = ThemeColors.substitute(style_sheet)
    else:
        _style_templates.pop(id(self), None)
    _original_set_style_sheet(self, style_sheet)


def install_style_patch() -> None:
    QWidget.setStyleSheet = _substituting_set_style_sheet


def reapply_styles(root_widget: QWidget) -> None:
    for child in root_widget.findChildren(QWidget):
        template = _style_templates.get(id(child))
        if template:
            child.setStyleSheet(template)
