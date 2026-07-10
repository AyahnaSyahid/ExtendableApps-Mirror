"""
Plugin API — satu-satunya hal yang mod boleh sentuh.
Mod tidak pernah import dari myapp.core secara langsung.
"""
from __future__ import annotations
from typing import Callable, TYPE_CHECKING, Optional, cast
from pathlib import Path
from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QDockWidget

from app.services.database import DatabaseService, MigrationFunc

if TYPE_CHECKING:
    from PySide6.QtWidgets import QTabWidget, QMenuBar, QMenu, QMainWindow, QWidget
    from PySide6.QtSql import QSqlDatabase

class PluginAPI:
    def __init__(self, main: "QMainWindow", tabs: "QTabWidget", menubar: "QMenuBar", app_name: str):
        self._mainwindow = main
        self._tabs = tabs
        self._menubar = menubar
        self._listeners: dict[str, list[Callable]] = {}
        self.app_name = app_name
        self._mod_handler = {}
        self._current_mod_name = ""
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        self._settings = QSettings(main)
        self._settings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(Path(__file__).parent.parent))
        self._db_service = DatabaseService(self.data_dir())

    # --- Widget ---
    def add_tab(self, widget, label: str):
        """Tambahkan tab baru ke jendela utama."""
        self._tabs.addTab(widget, label)


    def add_dock(self, widget: QWidget, title = "", menu_toggle = "Dockable", toggle_action_label="", area: Qt.DockWidgetArea = Qt.DockWidgetArea.AllDockWidgetAreas):
        dock = QDockWidget(self._mainwindow)
        dock.setWidget(widget)

        if title != "":
            dock.setWindowTitle(title)
        else:
            dock.setWindowTitle(widget.windowTitle())

        self._mainwindow.addDockWidget(area, dock)

        # toggleViewAction() mengembalikan QAction MILIK dock (bukan action
        # baru). Action inilah yang harus ditaruh ke menu, bukan dibuatkan
        # action baru lewat add_menu_action.
        toggle_action = dock.toggleViewAction()
        if toggle_action_label != "":
            toggle_action.setText(toggle_action_label)

        menu = self._get_or_create_menu(menu_toggle)
        menu.addAction(toggle_action)

        return dock

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
    def _get_or_create_menu(self, menu_path: str) -> QMenu | QMenuBar:
        """Cari/buat rantai submenu dari path 'File/Export/PDF' -> QMenu 'PDF'.
        Dipakai bersama oleh add_menu_action (membuat QAction baru) dan
        add_dock (menaruh QAction yang sudah ada, yaitu toggleViewAction)."""

        # 1. Pecah menu_path berdasarkan karakter '/'
        # Contoh: "File/Export/PDF" -> ['File', 'Export', 'PDF']
        menu_titles = [title.strip() for title in menu_path.split('/') if title.strip()]

        # 2. Mulai pencarian/pembuatan dari menubar utama
        current_container: QMenu | QMenuBar = self._menubar

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

        # 3. current_container di sini bisa berupa QMenuBar (kalau menu_path
        # kosong/hanya whitespace) atau QMenu di level paling dalam.
        return current_container

    def add_menu_action(self, menu_title: str, action_label: str, callback: Optional[Callable]):
        """Tambahkan item menu ke menubar dengan dukungan nested/sub-menu."""
        from PySide6.QtGui import QAction

        menu = self._get_or_create_menu(menu_title)

        act = QAction(action_label, self._menubar)
        if callback:
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
    
    def init_database(self, migrations: list[MigrationFunc], schema_version: int = 1) -> QSqlDatabase:
        """Dipanggil sekali oleh mod di setup(api). Mod hanya menyediakan daftar
        fungsi migrasi (create table, alter table, dst); path file dan penamaan
        koneksi sepenuhnya ditangani di sini, mod tidak perlu tahu."""
        if not self._current_mod_name:
            raise RuntimeError("init_database harus dipanggil dari dalam setup(api) milik mod")
        return self._db_service.init_database(self._current_mod_name, migrations, schema_version)

    def get_database_connection(self, mod_id: str | None = None) -> QSqlDatabase:
        """Ambil koneksi database milik sebuah mod. Jika mod_id tidak diisi,
        dipakai mod yang sedang aktif (hanya valid saat dipanggil dari dalam
        setup()). Aman dipanggil dari thread mana pun setelah init_database
        dijalankan — koneksi per-thread dibuat otomatis di belakang layar."""
        target = mod_id or self._current_mod_name
        if not target:
            raise RuntimeError("get_database_connection butuh mod_id, atau dipanggil dari konteks mod")
        return self._db_service.get_connection(target)

    def close_all_databases(self):
        """Dipanggil sekali oleh core saat aplikasi ditutup."""
        self._db_service.close_all()

    @staticmethod
    def data_dir():
        return Path(__file__).parent.parent / "data"

    def sendLog(self, msg):
        if self._mainwindow:
            self._mainwindow.log(msg)  # type:ignore