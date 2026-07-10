"""
Core Application — jendela utama. Mod tidak perlu tahu file ini.
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QLabel, QSplitter, QPlainTextEdit
from PySide6.QtCore import Qt, Slot, QSettings, Signal, QTimer, QLocale
from PySide6.QtGui import QFont, QPalette, QColor

from app.api import PluginAPI
from app.loader import load_all_mods

class LinuxConsoleEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Set menjadi Read-Only
        self.setReadOnly(True)
        
        # 2. Atur Font menjadi Monospace (khas Terminal)
        font = QFont("Courier New", 9)  # Bisa juga menggunakan "Consolas" atau "Monospace"
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        
        # 3. Atur Palet Warna (Background Hitam, Teks Hijau Terang)
        palette = self.palette()
        
        # Warna latar belakang komponen
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0)) 
        # Warna teks biasa
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 255, 0)) 
        # Warna teks saat diblok/di-highlight (opsional, agar tetap kontras)
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 128, 0)) 
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255)) 
        
        self.setPalette(palette)
        
        # 4. Menghilangkan frame bawaan agar terlihat lebih clean (opsional)
        self.setFrameShape(QPlainTextEdit.Shape.NoFrame)

class MainWindow(QMainWindow):
    sendLog = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ModApp")
        self.resize(800, 520)

        # Tab widget sebagai area utama
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab default bawaan app (bukan dari mod)
        home = QLabel("Halo Developer saya !!")
        home.setAlignment(Qt.AlignmentFlag.AlignCenter)
        home.setMinimumHeight(100)
        
        console = LinuxConsoleEdit(self)
        console.setObjectName("console")
        self.sendLog.connect(console.appendPlainText)
        self.console = console
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(home)
        split.addWidget(console)
        
        self.tabs.addTab(split, "Home")

        # Buat API dan load semua mod
        api = PluginAPI(
            main=self,
            tabs=self.tabs,
            menubar=self.menuBar(),
            app_name="ModApp",
        )

        self.api = api
        tmr = QTimer.singleShot(0, self._initialize_all_mods)

    @Slot()
    def _initialize_all_mods(self):
        mods_path = Path(__file__).parent.parent / "mods"
        loaded, errors = load_all_mods(mods_path, self.api)
        # Tampilkan status di status bar
        msg = f"{len(loaded)} mod aktif"
        if errors:
            msg += f", {len(errors)} gagal"
        self.statusBar().showMessage(msg)


    @Slot()
    def clearConsole(self):
        self.console.clear()

    def closeEvent(self, event):
        self.api.close_all_databases()
        super().closeEvent(event)

    def log(self, msg: str):
        self.sendLog.emit(msg)

def main():
    app = QApplication(sys.argv)
    locInd = QLocale(QLocale.Language.Indonesian, QLocale.Country.Indonesia)
    QLocale.setDefault(locInd)

    win = MainWindow()
    win.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
