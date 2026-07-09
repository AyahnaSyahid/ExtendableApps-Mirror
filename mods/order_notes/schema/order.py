from PySide6.QtCore import QDateTime

class Order:
    id_ = 0
    name = ''
    received_at: QDateTime = QDateTime()
    client = 0
    vendor = 0
    