from PySide6.QtCore import QObject


class MetaManager(QObject):

    def __init__(self, /, parent: QObject | None = ..., *, objectName: str | None = ...) -> None:   # type: ignore
        super().__init__(parent)
        if objectName:
            self.setObjectName(objectName)