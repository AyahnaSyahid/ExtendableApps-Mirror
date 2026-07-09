from PySide6.QtCore import Qt, QObject
from PySide6.QtSql import QSqlQuery, QSqlRecord, QSqlDatabase

from .contact import BaseContact 
from .tablemanager import TableManager

_QUERIES = {}
_QUERIES["create"] = """
    CREATE TABLE IF NOT EXISTS printing_company (
        id INTEGER PRIMARY KEY,
        name TEXT COLLATE NOCASE,
        address TEXT COLLATE NOCASE,
        phone_number TEXT );
"""

class PrintingCompany(BaseContact):
    def __init__(self):
        super().__init__()


class PrintingCompanyManager(TableManager):

    def __init__(self, con: QSqlDatabase, parent=None):
        super().__init__(con, parent)
        self.setObjectName("printingCompanyManager")

    def _real_init(self):
        q = QSqlQuery(self.con_)
        if not q.exec(_QUERIES['create']):
            self.error.emit(f"Gagal membangun tabel untuk {__name__}")
            return False
        return True

    def printingCompany_from_record(self, rec: QSqlRecord):
        pc = PrintingCompany()
        if rec.isEmpty():
            return pc 
        pc.id_ = rec.value('id')
        pc.name = rec.value('name')
        pc.address = rec.value('address')
        pc.phone_number = rec.value('phone_number')
        return pc

    def printingCompany_from_id(self, pcid: int):
        q = QSqlQuery(self.con_)
        q.prepare('SELECT * FROM printing_company WHERE id = :id_')
        q.bindValue(':id_', pcid)
        if q.exec() and q.next():
            return self.printingCompany_from_record(q.record())
        return PrintingCompany()
    
