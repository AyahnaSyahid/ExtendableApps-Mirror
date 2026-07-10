from ..models.model_mingguan import ModelMingguan
from .tabel_absen import TabelAbsen

from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import ( QWidget, QComboBox, QSpinBox, QHBoxLayout, QVBoxLayout )

class ui_AbsenWidget:

    def setupUi(self, aw: QWidget = ...):
        self.tabel = TabelAbsen(aw)
        


class AbsenWidget(QWidget):
    ui: ui_AbsenWidget = ...

    def __init__(self, /, parent):
        super().__(parent)
        self.setObjectName("absenWidget")
        self.ui.setupUi(self)

    
