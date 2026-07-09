from typing import Any

from PySide6.QtWidgets import QTableView
from PySide6.QtSql import QSqlQueryModel, QSqlQuery
from PySide6.QtCore import ( 
    QAbstractTableModel, QModelIndex, QPersistentModelIndex, QDate, QTime, Qt )


class ModelMingguan(QAbstractTableModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('modelMingguan')
        self.model_year = QDate.currentDate().year()
        self.model_weekNum = QDate.currentDate().dayOfWeek()
        self.model_user = ''
        self._internal_data = None

    def headerData(self, section: int, orientation: Qt.Orientation, /, role: int = 0) -> Any:
        horizontalSectionData = ['Tanggal', 'Masuk', 'Pulang']
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return horizontalSectionData[section]
        return super().headerData(section, orientation, role)

    def rowCount(self, /, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 7 if self._internal_data is None else len(self._internal_data)

    def columnCount(self, /, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 3

    def setUser(self, userName):
        self.model_user = userName


