from app.api import PluginAPI
from PySide6.QtWidgets import QWidget
from PySide6.QtSql import QSqlDatabase, QSqlQuery, QSqlQueryModel
from PySide6.QtCore import Qt


def setup(api: PluginAPI):
    mod_id = api.current_mod_id()
    database_file = api.data_dir() / (mod_id + ".db")
    database = QSqlDatabase.addDatabase("QSQLITE", mod_id)
    database.setDatabaseName(str(database_file))
    if  not database.open():
        raise RuntimeError(f"Tidak dapat membuka database")
    api.register_database(database)
    widget = _create_widget()


def _create_widget():
    pass