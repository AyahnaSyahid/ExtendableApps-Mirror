from app.api import PluginAPI
from PySide6.QtSql import QSqlDatabase

import logging

logger = logging.getLogger(__name__)


def setup(api: PluginAPI):
    logger.debug(f"Loading {api.current_mod_id()}")
    database_name: str = api.current_mod_id() if api.current_mod_id() else "catatan_order"
    database_path = str(api.data_dir() / f"{database_name}.db")
    default_con = QSqlDatabase.addDatabase("QSQLITE", f"default:{database_name}")
    default_con.setDatabaseName(database_path)
    if not default_con.open():
        logger.debug(f"Unable to open database {database_path}")
    api.register_database(default_con)
    if api.get_database_connection(api.current_mod_id()) != default_con:
        logger.debug("Objek database yang diregister berbeda dengan yang di berikan")

