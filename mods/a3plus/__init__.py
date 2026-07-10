from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt
from app.api import PluginAPI
from .schema import schemas
import logging

logger = logging.getLogger(__name__)

def _migrate_v1(con: QSqlDatabase):
    if not con.transaction():
        logger.warning(f"[a3plus] Tidak dapat melakukan transaksi database")
        return False
    q = QSqlQuery(con)
    s_v1 = schemas[0]
    for query in s_v1:
        if not q.exec(query):
            logger.warning(f"[a3plus] Tidak dapat menginisialisasi scheme database")
            return False
    return con.commit()

from .tonercounter import TonerCounterWidget

def setup(api: PluginAPI):
    con = api.init_database([_migrate_v1])
    tw = TonerCounterWidget(con)
    api.add_tab(tw, "Counter Toner")