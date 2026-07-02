from PySide6.QtCore import Qt, Signal, Slot, QObject
from PySide6.QtSql import QSqlDatabase
from .exceptions import DatabaseNotReadyError

class TableManager(QObject):
    error = Signal(str)

    def __init__(self, con: QSqlDatabase, parent=None):
        super().__init__(parent)
        self.con_ = con
    
    def init_schema(self):
        if not self.con_.open():
            raise DatabaseNotReadyError("Database tidak dapat dibuka")
        return self._real_init()

    def _real_init(self) -> bool:
        return False