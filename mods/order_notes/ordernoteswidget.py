from PySide6.QtWidgets import QWidget, QTableView, QVBoxLayout, QHBoxLayout
from PySide6.QtSql import QSqlDatabase, QSqlQueryModel, QSqlQuery
from typing import Optional

class OrderNotesWidget(QWidget):

    def __init__(self, parent: Optional[QWidget] = None, connection: Optional[QSqlDatabase] = None):
        super().__init__(parent = parent)
        self.setupUi()
    
    def setupUi(self):
        view = QTableView(self)
        model = QSqlQueryModel(self)
        

        