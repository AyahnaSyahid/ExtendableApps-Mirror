"""
Plugin API — satu-satunya hal yang mod boleh sentuh.
Mod tidak pernah import dari myapp.core secara langsung.
"""
from __future__ import annotations
from typing import Callable, TYPE_CHECKING, Optional, cast

if TYPE_CHECKING:
    from PySide6.QtWidgets import QTabWidget, QMenuBar, QMenu


class PluginAPI:
    def __init__(self, tabs: "QTabWidget", menubar: "QMenuBar", app_name: str):
        self._tabs = tabs
        self._menubar = menubar
        self._listeners: dict[str, list[Callable]] = {}
        self.app_name = app_name
        self._mod_handler = {}

    # --- Widget ---
    def add_tab(self, widget, label: str):
        """Tambahkan tab baru ke jendela utama."""
        self._tabs.addTab(widget, label)

    # --- Events ---
    def on_event(self, event_name: str, callback: Callable):
        """Daftar listener untuk sebuah event."""
        self._listeners.setdefault(event_name, []).append(callback)

    def emit_event(self, event_name: str, data=None):
        """Kirim event ke semua listener yang terdaftar."""
        for cb in self._listeners.get(event_name, []):
            cb(data)

    # --- Menu ---
    def add_menu_action(self, menu_title: str, action_label: str, callback: Callable):
        """Tambahkan item menu ke menubar."""
        from PySide6.QtGui import QAction
        menu: Optional[QMenu] = None
        for action in self._menubar.actions():
            if action.text() == menu_title:
                menu = cast(Optional[QMenu], action.menu())
                break
        if menu is None:
            menu = self._menubar.addMenu(menu_title)
        act = QAction(action_label, self._menubar)
        act.triggered.connect(callback)
        menu.addAction(act)
    
    # --- Mod Handler ---
    def register_handler(self, mod_id, raw_handler):
        if mod_id in self._mod_handler.keys():
            print(f"[Mod Handler : {mod_id}] Tertimpah...")
        self._mod_handler[mod_id] = raw_handler

    def get_handler(self, mod_id):
        if mod_id in self._mod_handler.keys():
            print(f"[Mod Handler : {mod_id}] Tertimpah...")
        self._mod_handler.get(mod_id, None)