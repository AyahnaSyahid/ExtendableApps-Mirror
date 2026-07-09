from PySide6.QtCore import QObject

class MetaManager(QObject):

    def __init__(self, parent = None):
        super().__init__(parent)
        self.setObjectName("metaManager")