from PySide6.QtSql import QSql, QSqlDatabase, QSqlQuery
from PySide6.QtCore import Qt, Signal, Slot, QObject

_QUERIES = {}

_QUERIES['create'] = '''
CREATE TABLE IF NOT EXISTS client ( 
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL COLLATE NOCASE,
    address TEXT,
    phone_number TEXT );
'''

class Client:
    def __init__(self, name, address, phone):
        self.name = name
        self.id = 0
        self.address = address
        self.phone_number = phone

class ClientManager(QObject):
    con: QSqlDatabase = QSqlDatabase()
    error = Signal(str)

    def __init__(self, con: QSqlDatabase, parent: QObject | None):
        super().__init__(parent)
        self.setObjectName("clientManager")
        self._default_con = con

    def init_schema(self):
        '''Initalize Schema'''
        con: QSqlDatabase = ClientManager.con
        if not con.open():
            self.error.emit('Database gagal dibuka')
            return False
        q = QSqlQuery(con)
        if not q.exec(_QUERIES['create']):
            self.error.emit('Inisialisasi skema gagal')
            return False
        # Jika suatu hari ada update schema maka update disini
        return True

    def client_from_id(self, cid):
        q = QSqlQuery(self._default_con)
        q.prepare('SELECT * FROM client WHERE id = :id')
        q.bindValue(':id', cid)
        if q.exec() and q.next():
            cl = Client(q.value('name'), q.value('address'), q.value('phone_number'))
            cl.id = cid
            return cid
        return None

    def client_from_name(self, name):
        q = QSqlQuery(self._default_con)
        q.prepare('SELECT * FROM client WHERE name = :name')
        q.bindValue(':name', name)
        if q.exec() and q.next():
            cl = Client(q.value('name'), q.value('address'), q.value('phone_number'))
            cl.id = q.value('id')
            return cl
        return None
    
