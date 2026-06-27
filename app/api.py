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
        self._current_mod_name = ""

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

    # --- current mod loading only set within loader ---
    def set_current_mod(self, name):
        self._current_mod_name = name
    
    def current_mod_id(self):
        return self._current_mod_name

    # --- Menu ---
    def add_menu_action(self, menu_title: str, action_label: str, callback: Callable):
        """Tambahkan item menu ke menubar dengan dukungan nested/sub-menu."""
        from PySide6.QtGui import QAction
        
        # 1. Pecah menu_title berdasarkan karakter '/'
        # Contoh: "File/Export/PDF" -> ['File', 'Export', 'PDF']
        menu_titles = [title.strip() for title in menu_title.split('/') if title.strip()]
        
        if not menu_titles:
            return

        # 2. Mulai pencarian/pembuatan dari menubar utama
        current_container = self._menubar
        
        for title in menu_titles:
            found_menu: Optional[QMenu] = None
            
            # Cari apakah menu dengan teks tersebut sudah ada di container saat ini
            for action in current_container.actions():
                if action.text() == title and action.menu():
                    found_menu = cast(QMenu, action.menu())
                    break
            
            # Jika belum ada, buat menu baru
            if found_menu is None:
                found_menu = current_container.addMenu(title)
                
            # Geser kontainer saat ini ke menu yang baru ditemukan/dibuat untuk iterasi berikutnya
            current_container = found_menu

        # 3. Setelah loop selesai, current_container berada di level paling dalam (QMenu)
        # Tinggal tambahkan QAction terakhir ke menu tersebut
        act = QAction(action_label, self._menubar)
        act.triggered.connect(callback)
        current_container.addAction(act)
    
    # --- Mod Handler ---
    def register_handler(self, mod_id, raw_handler):
        if mod_id in self._mod_handler.keys():
            print(f"[Mod Handler : {mod_id}] Tertimpah...")
        self._mod_handler[mod_id] = raw_handler

    def get_handler(self, mod_id):
        if mod_id in self._mod_handler.keys():
            print(f"[Mod Handler : {mod_id}] Tertimpah...")
        self._mod_handler.get(mod_id, None)