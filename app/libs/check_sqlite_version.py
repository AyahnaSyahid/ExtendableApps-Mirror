from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import QCoreApplication


app = QCoreApplication()

db = QSqlDatabase.addDatabase("QSQLITE")
db.setDatabaseName(":memory:")
db.open()

query = QSqlQuery(db)
query.exec("SELECT sqlite_version()")
if query.next():
    print("SQLite version:", query.value(0))