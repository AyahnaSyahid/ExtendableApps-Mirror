from PySide6.QtWidgets import (
    QCheckBox, QDateEdit, QDialog, QFrame, QPushButton, QStyleOptionViewItem, QStyledItemDelegate,
    QWidget, QTableView,
    QVBoxLayout, QMenu,
    QComboBox, QSpinBox, QFormLayout,
    QMessageBox
)

from PySide6.QtCore import QLocale, QModelIndex, QTime, QTimeZone, Qt, QSortFilterProxyModel, QObject, Slot, QPoint, QDate, QDateTime
from PySide6.QtSql import QSql, QSqlDatabase, QSqlQuery, QSqlQueryModel, QSqlTableModel

import logging
logger = logging.getLogger(__name__)

class CounterViewDelegate(QStyledItemDelegate):
    
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
    
    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex):
        super().initStyleOption(option, index)
        column = index.column()
        if column == 6:
            option.displayAlignment = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
            # option.text = f'{index.data():,}'
            option.text = QLocale().toString(index.data())
        else:
            option.displayAlignment = Qt.AlignmentFlag.AlignCenter


class DialogAddDataCounter(QDialog):

    def __init__(self, parent: QWidget | None = None, con: QSqlDatabase = QSqlDatabase()):
        super().__init__(parent)
        self._db = con
        self.setWindowTitle("Simpan catatan Counter")
        self.autoDate = QCheckBox("Tanggal Otomatis")
        self.autoDate.setChecked(True)
        self.autoDate.toggled.connect(self._autoDateToggled)

        self.dateEdit = QDateEdit(QDate.currentDate(), self)
        self.dateEdit.setEnabled(False)
        self.dateEdit.setDisplayFormat("dd MMMM yyyy")

        self.comboUser = QComboBox(self, editable=True)

        self.modelUser = QSqlQueryModel(self)
        mu = self.modelUser
        q1 = QSqlQuery(con)
        q1.exec("SELECT DISTINCT inserted_by COLLATE NOCASE FROM toner_counter ORDER BY inserted_by;")
        mu.setQuery(q1)

        self.comboUser.setModel(mu)

        q = QSqlQuery(con)
        q.exec("""
SELECT
    COALESCE(MAX(CASE WHEN counter_type = 'FULLCOLOR' THEN counter_value END), 0) AS max_full,
    COALESCE(MAX(CASE WHEN counter_type = 'BW' THEN counter_value END), 0) AS max_bw
FROM toner_counter;""")

        q.next()

        self._max = {'FULLCOLOR': q.value(0), 'BW': q.value(1)}
        print(self._max)

        self.comboColor = QComboBox(self, editable=False)
        cc = self.comboColor
        cc.addItem("Cyan", "C")
        cc.addItem("Magenta", "M")
        cc.addItem("Yellow", "Y")
        cc.addItem("Black", "K")
        cc.setCurrentIndex(-1)
        cc.currentIndexChanged.connect(self._comboColorChanged)

        self.comboCondition = QComboBox(self, editable=False)
        cx = self.comboCondition
        cx.addItem("Baru", "NEW")
        cx.addItem("Sisa", "USED")
        cx.setCurrentIndex(0)

        self.counterBox = QSpinBox(self, maximum=99_999_999)
        cb = self.counterBox
        cb.setButtonSymbols(cb.ButtonSymbols.NoButtons)
        cb.setStepType(cb.StepType.AdaptiveDecimalStepType)
        cb.setAccelerated(True)
        cb.setGroupSeparatorShown(True)
        cb.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.simpanButton = QPushButton("Simpan", self)
        self.simpanButton.clicked.connect(self._simpan)
        
        ml = QVBoxLayout()
        form = QFormLayout()
        form.addRow(self.autoDate)
        form.addRow("Tanggal Masuk", self.dateEdit)
        form.addRow(self._h_line())
        form.addRow("Pengguna", self.comboUser)
        form.addRow("Warna", self.comboColor)
        form.addRow("Kondisi", self.comboCondition)
        form.addRow("Counter", self.counterBox)

        ml.addLayout(form)
        ml.addWidget(self.simpanButton, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(ml)
        self.setMinimumWidth(240)

    def _currentCounterType(self):
        cc = self.comboColor
        ctext = cc.currentText()
        if ctext == '':
            return ''
        if ctext == 'Black':
            return 'BW'
        return 'FULLCOLOR'

    def _validate_input(self):
        ok =  self.comboUser.currentText() != '' and self.comboColor.currentText() != ''
        return ok

    def _validate_counter(self):
        min_counter = self._max.get(self._currentCounterType(), 0)
        logger.debug(f'{min_counter=} |||| {self._currentCounterType()=}')
        return self.counterBox.value() > min_counter

    @Slot()
    def _simpan(self):
        if not self._validate_input():
            QMessageBox.information(self, "Kesalahan data input", "Periksa input anda dan pastikan field Nama dan Warna telah diisi")
            return 
        if not self._validate_counter():
            QMessageBox.information(self, "Kesalahan data counter", "Periksa input counter (counter tidak lebih besar dari sebelumnya)")
            return
        q = QSqlQuery(self._db)
        q.prepare('''
    INSERT INTO toner_counter (
        inserted_at,
        inserted_by,
        color,
        condition,
        counter_type,
        counter_value ) VALUES (:ia, :ib, :c, :cd, :ct, :cv);
''')
        q.bindValue(':ia', QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss') 
                    if self.autoDate.isChecked() 
                        else QDateTime(self.dateEdit.date(), QTime.currentTime())
                            .toString('yyyy-MM-dd HH:mm:ss'))
        q.bindValue(':ib', self.comboUser.currentText())
        q.bindValue(':c', self.comboColor.currentData())
        q.bindValue(':cd', self.comboCondition.currentData())
        q.bindValue(':ct', self._currentCounterType())
        q.bindValue(':cv', self.counterBox.value())

        if not q.exec():
            QMessageBox.warning(self, "Input Gagal", q.lastError().text())
            return
        self.accept()

    @Slot(bool)
    def _autoDateToggled(self, togg):
        self.dateEdit.setDisabled(togg)

    @Slot()
    def _comboColorChanged(self):
        counterType = self._currentCounterType()
        self.counterBox.setValue(self._max.get(counterType, 0))
    
    def _h_line(self):
        frme = QFrame(self, frameShape=QFrame.Shape.HLine, frameShadow=QFrame.Shadow.Sunken)
        return frme


class TonerCounterWidget(QWidget):

    def __init__(self, con: QSqlDatabase, parent: QWidget | None = None):
        super().__init__(parent)
        self._db = con
        self.counterView = QTableView(self)

        cv = self.counterView
        cv.setItemDelegate(CounterViewDelegate(self))
        cv.verticalHeader().setMinimumSectionSize(18)
        cv.verticalHeader().setDefaultSectionSize(20)
        cv.setAlternatingRowColors(True)
        cv.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        cv.customContextMenuRequested.connect(self.counterContextMenu)
        cv.setVerticalScrollMode(cv.ScrollMode.ScrollPerPixel)
        cv.setHorizontalScrollMode(cv.ScrollMode.ScrollPerPixel)

        self._table_model = QSqlTableModel(self, con)
        tm = self._table_model
        tm.setTable('toner_counter')

        self._proxy_model = QSortFilterProxyModel(self)
        pm = self._proxy_model
        pm.setSourceModel(self._table_model)
        tm.select()

        cv.setModel(self._proxy_model)

        pm.sort(0, Qt.SortOrder.DescendingOrder)
        pm.setHeaderData(0, Qt.Orientation.Horizontal,
                         "RowID", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(1, Qt.Orientation.Horizontal,
                         "Masuk", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(2, Qt.Orientation.Horizontal,
                         "Oleh", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(3, Qt.Orientation.Horizontal,
                         "Warna", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(4, Qt.Orientation.Horizontal,
                         "Kondisi", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(5, Qt.Orientation.Horizontal,
                         "Tipe", Qt.ItemDataRole.DisplayRole)
        pm.setHeaderData(6, Qt.Orientation.Horizontal,
                         "Counter", Qt.ItemDataRole.DisplayRole)

        cv.hideColumn(0)
        cv.setSortingEnabled(True)
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(cv)
        self.setLayout(mainLayout)
        cv.resizeColumnsToContents()

    @Slot()
    def _addData(self):
        d = DialogAddDataCounter(self, self._db)
        if d.exec() == QDialog.DialogCode.Accepted:
            self._table_model.select()

    @Slot(QPoint)
    def counterContextMenu(self, pt):
        menu = QMenu()
        aksi_input = menu.addAction("Input data")  # type:ignore
        aksi_resize_column = menu.addAction("Ukuran kolom auto")

        aksi_input.triggered.connect(self._addData)
        aksi_resize_column.triggered.connect(
            self.counterView.resizeColumnsToContents)
        menu.exec(self.counterView.viewport().mapToGlobal(pt))
