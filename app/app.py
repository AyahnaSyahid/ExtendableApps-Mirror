"""
Core Application — jendela utama. Mod tidak perlu tahu file ini.
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QLabel
from PySide6.QtCore import Qt

from app.api import PluginAPI
from app.loader import load_all_mods


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ModApp")
        self.resize(800, 520)

        # Tab widget sebagai area utama
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab default bawaan app (bukan dari mod)
        home = QLabel("Selamat datang! Mod aktif muncul sebagai tab baru.")
        home.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabs.addTab(home, "Home")

        # Buat API dan load semua mod
        api = PluginAPI(
            tabs=self.tabs,
            menubar=self.menuBar(),
            app_name="ModApp",
        )

        mods_path = Path(__file__).parent.parent / "mods"
        loaded, errors = load_all_mods(mods_path, api)

        # Tampilkan status di status bar
        msg = f"{len(loaded)} mod aktif"
        if errors:
            msg += f", {len(errors)} gagal"
        self.statusBar().showMessage(msg)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
