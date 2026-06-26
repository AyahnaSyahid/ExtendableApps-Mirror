from app.api import PluginAPI
from PySide6.QtWidgets import QMessageBox

_WIN32COM_INSTALLED = False
_COREL_INSTALLED = None 

try:
    from win32com import client
    _WIN32COM_INSTALLED = True
except ImportError as ie:
    _WIN32COM_INSTALLED = False

def setup(api: PluginAPI):
    api.add_menu_action("Automation/CorelDraw", "Check Version", check_coreldraw)

def check_coreldraw():
    global _WIN32COM_INSTALLED, client, _COREL_INSTALLED
    if not _WIN32COM_INSTALLED:
        QMessageBox.warning(None, "Import Error", "Modul win32com tidak ditemukan") # type ignore
        return
    if _COREL_INSTALLED is None:
    corel = client.Dispatch("CorelDRAW.Application")
    QMessageBox.information(None, "Corel ditemukan", f"Corel Terinstall \n{corel.Version}")
