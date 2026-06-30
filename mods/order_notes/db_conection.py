from PySide6.QtSql import QSqlDatabase
from PySide6.QtCore import Qt, Signal, Slot, QObject
from typing import Callable
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DatabaseManager(QObject):
    databaseReady = Signal()
    databaseError = Signal(str)

    def __init__(self, /, parent: QObject | None = ..., *, objectName: str | None = ...) -> None:  # type: ignore
        super().__init__(parent)
        if objectName is not None:
            self.setObjectName(objectName)
        self._managed_tables = {}
        self._database_path = ":memory:"
        self._database_connection = {}

    def register_table(self, name, create_func: Callable):
        self._managed_tables[name] = {"name": name, "create_func": create_func}

    def setDatabasePath(self, path):
        str_path = path if type(path) == str else str(path)
        if os.path.isdir(str_path):
            logger.debug(f"tidak dapat menyetel database ke {str_path} (Sebuah direktori)")
            return
        self._database_path = str_path

    @Slot()
    def initializeDatabase(self):
        for name in self._managed_tables:
            logger.debug("Inisialisasi table " + name)
            result = self._managed_tables[name]["create_func"]()
            if result:
                logger.debug(f"table {name} terinisialisasi")
            else:
                logger.debug(f"table {name} tidak terinisialisasi")
                self.databaseError.emit(f"Gagal inisialisasi tabel {name}")
                return
        self.databaseReady.emit()
