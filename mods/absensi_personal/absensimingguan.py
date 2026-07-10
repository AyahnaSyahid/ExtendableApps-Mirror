"""
Modul absensi mingguan.

Berisi:
- ModelMingguan  : QAbstractTableModel yang menampilkan 7 hari (Senin-Minggu)
                   untuk kombinasi user/tahun/minggu (ISO 8601) tertentu.
- DelegateWaktu  : QStyledItemDelegate dengan editor QTimeEdit untuk kolom waktu.
- TabelMingguan  : QTableView yang sudah dipasangi DelegateWaktu.
- AbsensiWidget  : QWidget berisi filter (user/tahun/minggu) + TabelMingguan.

Skema tabel yang diasumsikan:
    CREATE TABLE IF NOT EXISTS absensi (
        user TEXT NOT NULL COLLATE NOCASE,
        sign_date TEXT NOT NULL,           -- format 'yyyy-MM-dd'
        time_in TEXT NOT NULL DEFAULT '08:00',
        time_out TEXT NOT NULL DEFAULT '16:00',
        CONSTRAINT unique_user_date UNIQUE (user, sign_date)
    )
"""

from __future__ import annotations

import datetime

from PySide6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QDate, QTime, QPersistentModelIndex,
    QPoint, Slot
)
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtWidgets import (
    QWidget,
    QTableView,
    QComboBox,
    QSpinBox,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QStyledItemDelegate,
    QTimeEdit,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QMenu
)

HARI_INDONESIA = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

COL_HARI, COL_TANGGAL, COL_MASUK, COL_KELUAR = range(4)
HEADERS = ["Hari", "Tanggal", "Masuk", "Keluar"]
FORMAT_TANGGAL = 'd MMM'

# --------------------------------------------------------------------------- #
# MODEL
# --------------------------------------------------------------------------- #
class ModelMingguan(QAbstractTableModel):
    """Model 7 baris (Senin-Minggu) untuk satu user pada minggu ISO tertentu."""

    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        self._db = db

        today = datetime.date.today()
        iso_year, iso_week, _ = today.isocalendar()
        self._user: str = ""
        self._year: int = iso_year
        self._week: int = iso_week
        self._rows: list[dict] = []

        self._reload()

    # ---------------- Filter API ---------------- #
    def set_user(self, user: str) -> None:
        if user != self._user:
            self._user = user
            self._reload()

    def set_year(self, year: int) -> None:
        if year != self._year:
            self._year = year
            self._reload()

    def set_week(self, week: int) -> None:
        if week != self._week:
            self._week = week
            self._reload()

    def set_filter(self, user: str, year: int, week: int) -> None:
        self._user = user
        self._year = year
        self._week = week
        self._reload()

    # ---------------- Muat ulang data ---------------- #
    def _reload(self) -> None:
        self.beginResetModel()
        self._rows = []

        if self._user and self._year and self._week:
            try:
                senin = datetime.date.fromisocalendar(self._year, self._week, 1)
            except ValueError:
                # Minggu ke-N tidak valid untuk tahun tsb (mis. minggu 53
                # pada tahun yang cuma punya 52 minggu ISO).
                senin = None

            if senin is not None:
                for i in range(7):
                    tanggal = senin + datetime.timedelta(days=i)
                    time_in, time_out, ada = self._fetch(tanggal)
                    self._rows.append(
                        {
                            "date": QDate(tanggal.year, tanggal.month, tanggal.day),
                            "time_in": time_in,
                            "time_out": time_out,
                            "ada": ada,
                        }
                    )

        self.endResetModel()

    def _fetch(self, tanggal: datetime.date) -> tuple[QTime, QTime, bool]:
        query = QSqlQuery(self._db)
        query.prepare(
            "SELECT time_in, time_out FROM absensi WHERE user = ? AND sign_date = ?"
        )
        query.addBindValue(self._user)
        query.addBindValue(tanggal.isoformat())
        query.exec()

        if query.next():
            time_in = QTime.fromString(query.value(0), "HH:mm")
            time_out = QTime.fromString(query.value(1), "HH:mm")
            if time_in.isValid() and time_out.isValid():
                return time_in, time_out, True

        # Belum ada record -> nilai default sesuai skema, tapi ditandai
        # 'belum diinput' supaya tidak ikut ditampilkan di kolom Masuk/Keluar.
        return QTime(8, 0), QTime(16, 0), False

    def _persist(self, row: int) -> None:
        data = self._rows[row]
        tanggal: QDate = data["date"]

        query = QSqlQuery(self._db)
        query.prepare(
            "INSERT OR REPLACE INTO absensi (user, sign_date, time_in, time_out) "
            "VALUES (?, ?, ?, ?)"
        )
        query.addBindValue(self._user)
        query.addBindValue(tanggal.toString("yyyy-MM-dd"))
        query.addBindValue(data["time_in"].toString("HH:mm"))
        query.addBindValue(data["time_out"].toString("HH:mm"))

        if not query.exec():
            raise RuntimeError(query.lastError().text())

    # ---------------- QAbstractTableModel overrides ---------------- #
    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(HEADERS)

    def headerData(self, section, orientation, role = int (Qt.ItemDataRole.DisplayRole)):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return HEADERS[section]
        return str(section + 1)

    def flags(self, index: QModelIndex | QPersistentModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() in (COL_MASUK, COL_KELUAR):
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    def data(self, index: QModelIndex | QPersistentModelIndex, role= int (Qt.ItemDataRole.DisplayRole)):
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.EditRole:
            # EditRole selalu kirim nilai (default 08:00/16:00 kalau belum
            # ada record) supaya editor QTimeEdit punya titik awal yang wajar.
            if col == COL_MASUK:
                return row["time_in"]
            if col == COL_KELUAR:
                return row["time_out"]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == COL_HARI:
                return HARI_INDONESIA[row["date"].dayOfWeek() - 1]
            if col == COL_TANGGAL:
                return row["date"].toString(FORMAT_TANGGAL)
            if col == COL_MASUK:
                return row["time_in"].toString("HH:mm") if row["ada"] else ""
            if col == COL_KELUAR:
                return row["time_out"].toString("HH:mm") if row["ada"] else ""

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

        return None

    def setData(self, index: QModelIndex | QPersistentModelIndex, value, role= int (Qt.ItemDataRole.EditRole)) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False

        col = index.column()
        if col not in (COL_MASUK, COL_KELUAR):
            return False
        if not isinstance(value, QTime) or not value.isValid():
            return False

        row = index.row()
        key = "time_in" if col == COL_MASUK else "time_out"
        lama = self._rows[row][key]
        ada_lama = self._rows[row]["ada"]

        self._rows[row][key] = value
        self._rows[row]["ada"] = True

        try:
            self._persist(row)
        except RuntimeError:
            # Gagal simpan -> rollback nilai & status 'ada' di memori
            self._rows[row][key] = lama
            self._rows[row]["ada"] = ada_lama
            return False

        # _persist menulis time_in & time_out sekaligus, jadi kolom
        # pasangannya (yang tadinya kosong) juga ikut jadi terisi -> refresh
        # tampilan untuk kedua kolom waktu di baris ini.
        kiri = self.index(row, COL_MASUK)
        kanan = self.index(row, COL_KELUAR)
        self.dataChanged.emit(kiri, kanan, [role])
        return True

    # ---------------- Helper ---------------- #
    def date_at(self, row: int) -> QDate:
        return self._rows[row]["date"]


# --------------------------------------------------------------------------- #
# DELEGATE
# --------------------------------------------------------------------------- #
class DelegateWaktu(QStyledItemDelegate):
    """Editor QTimeEdit untuk kolom Masuk/Keluar."""

    def createEditor(self, parent, option, index):
        editor = QTimeEdit(parent)
        editor.setDisplayFormat("HH:mm")
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        if isinstance(value, QTime):
            editor.setTime(value)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.time(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


# --------------------------------------------------------------------------- #
# VIEW
# --------------------------------------------------------------------------- #
class TabelMingguan(QTableView):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)

        self._delegate_waktu = DelegateWaktu(self)
        self.setItemDelegateForColumn(COL_MASUK, self._delegate_waktu)
        self.setItemDelegateForColumn(COL_KELUAR, self._delegate_waktu)


# --------------------------------------------------------------------------- #
# DIALOG
# --------------------------------------------------------------------------- #
class DialogTambahAbsensi(QDialog):
    """Dialog untuk menambah/menimpa satu baris data absensi.

    - cb_user   : QComboBox editable, bisa pilih user lama atau ketik nama baru.
    - date_edit : QDateEdit, default hari ini.
    - time_in / time_out : QTimeEdit, default 08:00 / 16:00 sesuai skema tabel.
    """

    def __init__(self, existing_users: list[str], parent=None, default_date: QDate | None = None):
        super().__init__(parent)
        self.setWindowTitle("Tambah Data Absensi")

        self.cb_user = QComboBox(self)
        self.cb_user.setEditable(True)
        self.cb_user.addItems(existing_users)
        self.cb_user.setCurrentText("")

        self.date_edit = QDateEdit(self)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.setDate(default_date or QDate.currentDate())

        self.time_in = QTimeEdit(self)
        self.time_in.setDisplayFormat("HH:mm")
        self.time_in.setTime(QTime(8, 0))

        self.time_out = QTimeEdit(self)
        self.time_out.setDisplayFormat("HH:mm")
        self.time_out.setTime(QTime(16, 0))

        form = QFormLayout()
        form.addRow("User:", self.cb_user)
        form.addRow("Tanggal:", self.date_edit)
        form.addRow("Masuk:", self.time_in)
        form.addRow("Keluar:", self.time_out)

        tombol = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        tombol.accepted.connect(self._validasi_lalu_terima)
        tombol.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(tombol)

    def _validasi_lalu_terima(self) -> None:
        if not self.cb_user.currentText().strip():
            QMessageBox.warning(self, "Data belum lengkap", "Nama/kode user tidak boleh kosong.")
            self.cb_user.setFocus()
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "user": self.cb_user.currentText().strip(),
            "date": self.date_edit.date(),
            "time_in": self.time_in.time(),
            "time_out": self.time_out.time(),
        }


# --------------------------------------------------------------------------- #
# WIDGET
# --------------------------------------------------------------------------- #
class AbsensiWidget(QWidget):
    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        self._db = db

        # --- Model & View ---
        self.model = ModelMingguan(db, self)
        self.tabel: QTableView = TabelMingguan(self)

        self.tabel.setModel(self.model)

        # --- Custom Context Menu ---
        self.tabel.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabel.customContextMenuRequested.connect(self.tabelContextMenu)

        # --- Filter widgets ---
        self.cb_user = QComboBox(self)

        self.spin_tahun = QSpinBox(self)
        self.spin_tahun.setRange(2000, 2100)

        self.spin_minggu = QSpinBox(self)
        self.spin_minggu.setRange(1, 53)

        today = datetime.date.today()
        iso_year, iso_week, _ = today.isocalendar()
        self.spin_tahun.setValue(iso_year)
        self.spin_minggu.setValue(iso_week)

        self._load_users()

        # --- Layout ---
        layout_filter = QHBoxLayout()
        layout_filter.addWidget(QLabel("Nama:"))
        layout_filter.addWidget(self.cb_user)
        layout_filter.addWidget(QLabel("Tahun:"))
        layout_filter.addWidget(self.spin_tahun)
        layout_filter.addWidget(QLabel("Minggu ke:"))
        layout_filter.addWidget(self.spin_minggu)
        layout_filter.addStretch()

        layout_utama = QVBoxLayout(self)
        layout_utama.addLayout(layout_filter)
        layout_utama.addWidget(self.tabel)

        # --- Signal wiring ---
        self.cb_user.currentTextChanged.connect(self._terapkan_filter)
        self.spin_tahun.valueChanged.connect(self._terapkan_filter)
        self.spin_minggu.valueChanged.connect(self._terapkan_filter)

        self._terapkan_filter()

        self.tabel.resizeColumnsToContents()

    def _load_users(self) -> None:
        query = QSqlQuery(self._db)
        query.exec("SELECT DISTINCT user FROM absensi ORDER BY DATE(sign_date) ASC")

        self.cb_user.blockSignals(True)
        self.cb_user.clear()
        while query.next():
            self.cb_user.addItem(query.value(0))
        self.cb_user.blockSignals(False)

    def _terapkan_filter(self, *_args) -> None:
        user = self.cb_user.currentText()
        tahun = self.spin_tahun.value()
        minggu = self.spin_minggu.value()
        self.model.set_filter(user, tahun, minggu)

    def refresh_users(self) -> None:
        """Panggil manual kalau daftar user di database berubah dari luar
        (mis. ada karyawan baru ditambahkan lewat bagian lain aplikasi)."""
        current = self.cb_user.currentText()
        self._load_users()
        idx = self.cb_user.findText(current)
        if idx >= 0:
            self.cb_user.setCurrentIndex(idx)
    
    @Slot(QPoint)
    def tabelContextMenu(self, pt):
        menu = QMenu(self.tabel)
        tambah = menu.addAction("Tambah data")

        aksi = menu.exec(self.tabel.viewport().mapToGlobal(pt))

        if aksi == tambah:
            self._tambah_data()

    def _tambah_data(self) -> None:
        users = [self.cb_user.itemText(i) for i in range(self.cb_user.count())]

        # Kalau user diklik dari baris yang sedang tampil, pakai tanggal baris
        # itu sebagai default supaya lebih cepat isi datanya.
        index = self.tabel.currentIndex()
        default_date = self.model.date_at(index.row()) if index.isValid() else None

        dialog = DialogTambahAbsensi(users, self, default_date=default_date)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        if not self._simpan_data_baru(data):
            return

        # Refresh combobox user (siapa tahu ada kode/user baru) & tabel
        self.refresh_users()
        self._terapkan_filter()

    def _simpan_data_baru(self, data: dict) -> bool:
        query = QSqlQuery(self._db)
        query.prepare(
            "INSERT OR REPLACE INTO absensi (user, sign_date, time_in, time_out) "
            "VALUES (?, ?, ?, ?)"
        )
        query.addBindValue(data["user"])
        query.addBindValue(data["date"].toString("yyyy-MM-dd"))
        query.addBindValue(data["time_in"].toString("HH:mm"))
        query.addBindValue(data["time_out"].toString("HH:mm"))

        if not query.exec():
            QMessageBox.warning(self, "Gagal menyimpan", query.lastError().text())
            return False
        return True