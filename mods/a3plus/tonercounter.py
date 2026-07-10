from PySide6.QtWidgets import QWidget, QTableView, QVBoxLayout, QMenu
from PySide6.QtCore import Qt, QSortFilterProxyModel, QObject, Slot, QPoint
from PySide6.QtSql import QSql, QSqlDatabase, QSqlQuery, QSqlQueryModel, QSqlTableModel


class TonerCounterWidget(QWidget):

    def __init__(self, con: QSqlDatabase, parent: QWidget | None = None):
        super().__init__(parent)
        self._db = con
        self.counterView = QTableView(self)
        
        cv = self.counterView
        cv.verticalHeader().setMinimumSectionSize(18)
        cv.verticalHeader().setDefaultSectionSize(20)
        cv.setAlternatingRowColors(True)
        cv.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        cv.customContextMenuRequested.connect(self.counterContextMenu)


        self._table_model = QSqlTableModel(self, con)
        tm = self._table_model
        tm.setTable('toner_counter')

        self._proxy_model = QSortFilterProxyModel(self)
        pm = self._proxy_model
        pm.setSourceModel(self._table_model)
        tm.select()

        cv.setModel(self._proxy_model)
                
        pm.sort(0, Qt.SortOrder.DescendingOrder)
        pm.setHeaderData(0, Qt.Orientation.Horizontal, "RowID", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(1, Qt.Orientation.Horizontal, "Masuk", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(2, Qt.Orientation.Horizontal, "Oleh", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(3, Qt.Orientation.Horizontal, "Kondisi", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(4, Qt.Orientation.Horizontal, "Tipe", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(5, Qt.Orientation.Horizontal, "Counter", Qt.ItemDataRole.DisplayRole)
        
        cv.hideColumn(0)
        cv.setSortingEnabled(True)
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(cv)
        self.setLayout(mainLayout)
        cv.resizeColumnsToContents()

    @Slot(QPoint)
    def counterContextMenu(self, pt):
        menu = QMenu()
        aksi1 = menu.addAction("Input data") # type:ignore
        menu.exec(self.counterView.viewport().mapToGlobal(pt))