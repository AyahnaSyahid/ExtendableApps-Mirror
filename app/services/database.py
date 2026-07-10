"""
Database Service — satu-satunya pihak yang tahu penamaan koneksi QSqlDatabase.

Mod tidak pernah menentukan connection name atau path file sendiri. Mod hanya:
  1. Panggil `init_database(migrations=[...])` sekali di setup(api).
  2. Panggil `get_database_connection()` kapan pun butuh koneksi — termasuk
     dari thread lain. Koneksi baru per-thread dibuat otomatis di belakang
     layar (QSqlDatabase tidak boleh dipakai lintas-thread), menunjuk ke
     file fisik yang sama.

Migrasi skema hanya dijalankan sekali per mod (dilacak lewat tabel `meta`),
bukan setiap kali sebuah thread baru membuka koneksi.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable

from PySide6.QtSql import QSql, QSqlDatabase, QSqlQuery

logger = logging.getLogger(__name__)

# Sebuah migrasi menerima koneksi yang sudah terbuka dan mengembalikan True/False.
MigrationFunc = Callable[[QSqlDatabase], bool]


class ModDatabaseHandle:
    """Menyimpan registrasi database milik satu mod: path file, daftar migrasi,
    dan cache koneksi per-thread."""

    def __init__(self, mod_id: str, db_path: Path, migrations: list[MigrationFunc], schema_version: int):
        self.mod_id = mod_id
        self.db_path = db_path
        self.migrations = migrations
        self.schema_version = schema_version
        self._connections: dict[int, str] = {}  # thread_ident -> connection_name
        self._lock = threading.Lock()
        self._migrated = False

    def _connection_name_for(self, thread_ident: int) -> str:
        # Prefix "modsvc::" mencegah tabrakan dengan connection name lain di aplikasi.
        return f"modsvc::{self.mod_id}::t{thread_ident}"

    def get_connection(self) -> QSqlDatabase:
        thread_ident = threading.get_ident()

        with self._lock:
            existing_name = self._connections.get(thread_ident)
            if existing_name is not None and QSqlDatabase.contains(existing_name):
                con = QSqlDatabase.database(existing_name)
                if con.isOpen() or con.open():
                    return con
                logger.error(f"[{self.mod_id}] Koneksi thread {thread_ident} gagal dibuka ulang: {con.lastError().text()}")
                return con

            conn_name = self._connection_name_for(thread_ident)
            con = QSqlDatabase.addDatabase("QSQLITE", conn_name)
            con.setDatabaseName(str(self.db_path))

            if not con.open():
                raise RuntimeError(f"[{self.mod_id}] Gagal membuka database: {con.lastError().text()}")

            # WAL memungkinkan banyak koneksi baca berjalan bersamaan dengan satu
            # penulis, tanpa saling mengunci file. Tetap disarankan mod men-serialisasi
            # operasi tulis sendiri (mis. lewat satu worker thread/queue).
            QSqlQuery(con).exec("PRAGMA journal_mode=WAL")

            self._connections[thread_ident] = conn_name

            if not self._migrated:
                if not self._run_migrations(con):
                    raise RuntimeError(f"[{self.mod_id}] Migrasi skema gagal, lihat log untuk detail")
                self._migrated = True

            return con

    def _run_migrations(self, con: QSqlDatabase) -> bool:
        q = QSqlQuery(con)

        if "meta" not in con.tables(QSql.TableType.Tables):
            if not q.exec("CREATE TABLE meta (name TEXT PRIMARY KEY COLLATE NOCASE, value TEXT NOT NULL)"):
                logger.error(f"[{self.mod_id}] Gagal membuat tabel meta: {q.lastError().text()}")
                return False
            current_version = 0
            q.prepare("INSERT INTO meta (name, value) VALUES ('VERSION', :v)")
            q.bindValue(":v", current_version)
            q.exec()
        else:
            if not q.exec("SELECT value FROM meta WHERE name = 'VERSION'") or not q.next():
                logger.error(f"[{self.mod_id}] Tidak dapat membaca versi skema")
                return False
            current_version = int(q.value(0))

        pending = self.migrations[current_version:self.schema_version]
        for step in pending:
            if not step(con):
                logger.error(f"[{self.mod_id}] Migrasi gagal pada langkah versi {current_version + 1}")
                return False
            current_version += 1
            q.prepare("UPDATE meta SET value = :v WHERE name = 'VERSION'")
            q.bindValue(":v", current_version)
            q.exec()

        return True

    def close_all(self):
        for name in list(self._connections.values()):
            if QSqlDatabase.contains(name):
                QSqlDatabase.database(name).close()
                # QSqlDatabase.removeDatabase(name)
        self._connections.clear()


class DatabaseService:
    """Registry pusat: satu ModDatabaseHandle per mod_id."""

    def __init__(self, data_dir: Path):
        self._data_dir = Path(data_dir)
        self._handles: dict[str, ModDatabaseHandle] = {}

    def init_database(self, mod_id: str, migrations: list[MigrationFunc], schema_version: int = 1) -> QSqlDatabase:
        if mod_id in self._handles:
            logger.warning(f"[{mod_id}] init_database dipanggil lebih dari sekali, mengembalikan handle yang ada")
            return self._handles[mod_id].get_connection()

        self._data_dir.mkdir(parents=True, exist_ok=True)
        db_path = self._data_dir / f"{mod_id}.db"
        handle = ModDatabaseHandle(mod_id, db_path, migrations, schema_version)
        self._handles[mod_id] = handle
        return handle.get_connection()

    def get_connection(self, mod_id: str) -> QSqlDatabase:
        handle = self._handles.get(mod_id)
        if handle is None:
            raise RuntimeError(f"Mod '{mod_id}' belum memanggil init_database() sebelum minta koneksi")
        return handle.get_connection()

    def close_all(self):
        for handle in self._handles.values():
            handle.close_all()
