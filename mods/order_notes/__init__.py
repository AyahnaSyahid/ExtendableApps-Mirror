from app.api import PluginAPI
from PySide6.QtSql import QSqlDatabase

from .schema.client import ClientManager
from .schema.printingcompany import PrintingCompanyManager

import logging

logger = logging.getLogger(__name__)


def _migration_v1(con: QSqlDatabase) -> bool:
    """Migrasi awal: buat tabel client dan printing_company."""
    ok_client = ClientManager(con).init_schema()
    ok_printing = PrintingCompanyManager(con).init_schema()
    return ok_client and ok_printing


# Tambahkan _migration_v2, _migration_v3, dst di sini kalau skema berubah nanti.
# Urutan dalam list MIGRATIONS harus sama dengan urutan versi (index 0 = versi 1).
MIGRATIONS = [_migration_v1]
SCHEMA_VERSION = len(MIGRATIONS)


def setup(api: PluginAPI):
    logger.debug(f"Loading {api.current_mod_id()}")

    # api.init_database menangani path file, penamaan koneksi, dan migrasi.
    # Mod ini tidak perlu tahu ke mana file .db disimpan atau nama koneksinya.
    con = api.init_database(migrations=MIGRATIONS, schema_version=SCHEMA_VERSION)

    if not con.isOpen():
        logger.error("Database tidak berhasil disiapkan, mod tidak dimuat penuh")
        return

    logger.debug(f"Database siap untuk {api.current_mod_id()}")
