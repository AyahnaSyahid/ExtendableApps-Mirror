from app.api import PluginAPI
from PySide6.QtSql import QSqlDatabase, QSqlQuery, QSql
from .schema import client

import logging

logger = logging.getLogger(__name__)

__ENV = {"DEVEL": True}

def setup(api: PluginAPI):
    logger.debug(f"Loading {api.current_mod_id()}")
    database_name: str = api.current_mod_id() if api.current_mod_id() else "catatan_order"
    database_path = str(api.data_dir() / f"{database_name}.db")
    default_con = QSqlDatabase.addDatabase("QSQLITE", f"default:{database_name}")
    
    if __ENV['DEVEL']:
        import os
        os.remove(database_path)

    default_con.setDatabaseName(database_path)
    if not default_con.open():
        logger.debug(f"Unable to open database {database_path}")
    api.register_database(default_con)
    if api.get_database_connection(api.current_mod_id()) != default_con:
        logger.debug("Objek database yang diregister berbeda dengan yang diberikan")

    __ENV["connection_name"] = default_con.connectionName()

    init_success = _register_tables()
    
    if not init_success:
        logger.warning("Inisialisasi database Gagal !!")
        return

def _register_tables():
    """Registering database tables"""
    con = QSqlDatabase.database(__ENV["connection_name"])
    q = QSqlQuery(con)
    schema_version = 1
    if not "meta" in con.tables(QSql.TableType.Tables):
        """Uninitialized database"""
        eok = q.exec("CREATE TABLE meta (name TEXT PRIMARY KEY COLLATE NOCASE, value TEXT NOT NULL )")
        if not eok:
            logger.debug(f"GAGAL membuat table meta")
            return False
        q.prepare("INSERT INTO meta (name, value) VALUES (:name, :value)")
        q.bindValue(":name", "VERSION")
        q.bindValue(":value", 1)
        if not q.exec():
            if q.lastError().isValid():
                logger.error(q.lastError().text())
            return False
    else:
        q.exec("SELECT [value] FROM meta WHERE name = 'VERSION'")
        if not q.next():
            logger.error("Tidak dapat membaca versi schema database")
            return False
        schema_version = q.value(0)
    
    # init all database schema here
    return True
