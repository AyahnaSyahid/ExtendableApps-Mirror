from PySide6.QtSql import QSql, QSqlDatabase, QSqlQuery, QSqlRecord
from PySide6.QtCore import Qt, Signal, Slot, QObject

from .contact import BaseContact
from .tablemanager import TableManager

_QUERIES = {}

_QUERIES['create'] = '''
CREATE TABLE IF NOT EXISTS client ( 
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL COLLATE NOCASE,
    address TEXT,
    phone_number TEXT );
'''

class Client(BaseContact):
    def __init__(self):
        super().__init__()


class ClientManager(TableManager):

    def __init__(self, con: QSqlDatabase, parent = None):
        super().__init__(con, parent)
        self.setObjectName("clientManager")

    def _real_init(self):
        '''Initalize Schema'''
        con = self.con_
        q = QSqlQuery(con)
        if not q.exec(_QUERIES['create']):
            self.error.emit('Inisialisasi skema gagal')
            return False
        # Jika suatu hari ada update schema maka update disini
        return True

    def client_from_record(self, rec: QSqlRecord):
        cl = Client()
        cl.id_ = rec.value('id') or 0
        cl.name = rec.value('name') or ""
        cl.address = rec.value('address') or ""
        cl.phone_number = rec.value('phone_number') or ""
        return cl

    def client_from_id(self, cid):
        q = QSqlQuery(self.con_)
        q.prepare('SELECT * FROM client WHERE id = :id')
        q.bindValue(':id', cid)
        if q.exec() and q.next():
            return self.client_from_record(q.record())
    
    def client_from_name(self, name):
        q = QSqlQuery(self.con_)
        q.prepare('SELECT * FROM client WHERE name = :name')
        q.bindValue(':name', name)
        if q.exec() and q.next():
            return self.client_from_record(q.record())