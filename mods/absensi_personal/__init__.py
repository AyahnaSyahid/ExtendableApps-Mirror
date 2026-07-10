from app.api import PluginAPI
from PySide6.QtWidgets import QWidget
from PySide6.QtSql import QSqlDatabase, QSqlQuery, QSqlQueryModel
from PySide6.QtCore import Qt, QDate, QTime, QDateTime

import logging

logger = logging.getLogger(__name__)

class AbsenData:
    user = ''
    sign_date: QDateTime = QDateTime()
    time_in: QTime = QTime()
    time_out: QTime = QTime()

def _migrate_v0(con: QSqlDatabase):
    if not con.open():
        logger.warning("[Migrate0] Database tidak dapat dibuka")
        return False
    if not con.transaction():
        logger.warning("[Migrate0] Tidak dapat melakukan transaksi database")
        return False
    
    create = '''
CREATE TABLE IF NOT EXISTS absensi (
    user TEXT NOT NULL COLLATE NOCASE,
    sign_date TEXT NOT NULL,
    time_in TEXT NOT NULL DEFAULT '08:00',
    time_out TEXT NOT NULL DEFAULT '16:00',
    CONSTRAINT unique_user_date UNIQUE (user, sign_date)
)
'''
    q = QSqlQuery(con)
    if not q.exec(create):
        logger.warning("[Migrate0] Tidak dapat membuat tabel")
        return False
    return con.commit()

def setup(api: PluginAPI):
    con = api.init_database([_migrate_v0])
    
