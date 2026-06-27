from app.api import PluginAPI
from PySide6.QtWidgets import QMessageBox
import logging

logger = logging.getLogger("corel_automation")

_WIN32COM_INSTALLED = False
_COREL_INSTALLED = None 

try:
    from win32com import client
    _WIN32COM_INSTALLED = True
except ImportError as ie:
    pass

def setup(api: PluginAPI):
    logger.debug("Entering setup")
    api.add_menu_action("Automation/CorelDraw", "Check Version", check_coreldraw)
    logger.debug("Finished setup")

def check_coreldraw():
    global _WIN32COM_INSTALLED, client, _COREL_INSTALLED
    if not _WIN32COM_INSTALLED:
        QMessageBox.warning(None, "Import Error", "Modul win32com tidak ditemukan") # type ignore
        return
    corel = client.Dispatch("CorelDRAW.Application")
    QMessageBox.information(None, "Corel ditemukan", f"Corel Terinstall\n{corel.Version}")
    _COREL_INSTALLED = True