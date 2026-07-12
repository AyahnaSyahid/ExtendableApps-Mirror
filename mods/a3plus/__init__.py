from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt
from app.api import PluginAPI
from .schema import schemas
import logging

logger = logging.getLogger(__name__)

def _migrate(con: QSqlDatabase, queries):
    if not con.transaction():
        logger.warning(f"[a3plus] Tidak dapat melakukan transaksi database")
        return False
    q = QSqlQuery(con)
    for query in queries:
        if not q.exec(query):
            logger.warning(f"[a3plus] Tidak dapat menginisialisasi scheme database")
            return False
    return con.commit()


def _migrate_v1(con: QSqlDatabase):
    return _migrate(con, schemas[0])

def _migrate_v2(con: QSqlDatabase):
    return _migrate(con, schemas[1])


from .tonercounter import TonerCounterWidget
from .partreplacementcounter import PartReplacementCounterWidget
from PySide6.QtWidgets import QWidget, QTabWidget, QVBoxLayout


def setup(api: PluginAPI):
    con = api.init_database([_migrate_v1, _migrate_v2], 2)
    container = QWidget()
    container.setObjectName("a3plus_container")
    container.setLayout(QVBoxLayout())
    container_layout = container.layout()
    tabWidget = QTabWidget(container)
    container_layout.addWidget(tabWidget)
    
    tw = TonerCounterWidget(con)
    tabWidget.addTab(tw,"Toner Counter")

    prc = PartReplacementCounterWidget(con)    
    tabWidget.addTab(prc, "Penggantian Part")

    api.add_tab(container, "A3Plus Data")