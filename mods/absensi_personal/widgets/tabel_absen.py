from ..models.model_mingguan import TimeEditDelegate
from PySide6.QtWidgets import QTableView


class TabelAbsen(QTableView):

    def __init__(self, /, parent = ..., *, showGrid = ..., gridStyle = ..., sortingEnabled = ..., wordWrap = ..., cornerButtonEnabled = ...):
        super().__init__(parent, showGrid=showGrid, gridStyle=gridStyle, sortingEnabled=sortingEnabled, wordWrap=wordWrap, cornerButtonEnabled=cornerButtonEnabled)
        self.setObjectName("tabelMingguan")
        delegate = TimeEditDelegate(self)
        self.setItemDelegate(delegate)
