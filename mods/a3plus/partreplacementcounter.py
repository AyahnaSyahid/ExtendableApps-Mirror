from __future__ import annotations
from PySide6.QtWidgets import QComboBox, QDateEdit, QFormLayout, QHBoxLayout, QMessageBox, QPushButton, QSpinBox, QTableView, QTreeView, QVBoxLayout, QWidget, QMenu, QDialog
from PySide6.QtSql import QSqlDatabase, QSqlTableModel, QSqlQuery
from PySide6.QtCore import QDate, QModelIndex, Qt, Slot, QPoint, QSortFilterProxyModel
from PySide6.QtGui import QAction
from app.libs.json_tree_model_qt import JsonTreeItem, JsonTreeModel, ItemEditorDialog
from app.libs.json_to_text_tree import json_to_text_tree
from app.api import PluginAPI

import logging
logger = logging.getLogger(__name__)

TABLE_NAME = "a3_part_replacement"
API: PluginAPi | None = None

class AddReplacementCounterDataDialog(QDialog):

    def __init__(self, parent=None, lastCounter=0, partNames: list[str] = [], installers: list[str] = []):
        super().__init__(parent)
        self.setWindowTitle("Ganti Sparepart")
        _form = self.formWidget = QWidget(self)
        fl = QFormLayout()
        _form.setLayout(fl)
        
        self.comboPart = QComboBox(self, editable=True)
        self.comboPart.addItems(partNames)
        self.comboInstaller = QComboBox(self, editable=True)
        self.comboInstaller.addItems(installers)
        self.dateEdit = QDateEdit(QDate.currentDate(), self)
        self.dateEdit.setDisplayFormat("dd MMMM yyyy")
        self.dateEdit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dateEdit.setCalendarPopup(True)
        self.counterBox = QSpinBox(
            self, minimum=lastCounter, maximum=9_999_999, singleStep=1000)
        self.counterBox.setValue(lastCounter)
        self.counterBox.setAccelerated(True)
        self.counterBox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.counterBox.setButtonSymbols(self.counterBox.ButtonSymbols.NoButtons)

        tree = self.extraInfoTree = QTreeView(self)
        self.extraInfoModel = JsonTreeModel(parent=self)
        tree.setModel(self.extraInfoModel)
        self.extraInfoModel.load_json_string('{}')
        tree.expandAll()
        tree.resizeColumnToContents(0)
        tree.setContextMenuPolicy(Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.treeContextMenu)

        fl.addRow("Nama Part", self.comboPart)
        fl.addRow("Pemasang", self.comboInstaller)
        fl.addRow("Tanggal", self.dateEdit)
        fl.addRow("Counter", self.counterBox)

        vl = QVBoxLayout()
        vl.addWidget(_form)
        vl.addWidget(self.extraInfoTree)

        button = QPushButton("Simpan", self)
        vl.addWidget(button, alignment=Qt.AlignRight)
        button.clicked.connect(self.simpanClicked)

        self.setLayout(vl)

    @Slot(QPoint)
    def treeContextMenu(self, pos):
        view = self.extraInfoTree
        model = self.extraInfoModel
        index = view.indexAt(pos)  # QModelIndex() invalid -> klik di area kosong = root
        target_item = model._item_from_index(index)

        menu = QMenu(view)
        add_action = menu.addAction("➕ Tambah Child di sini...")
        edit_action = menu.addAction("✏️ Edit Item Ini...")
        remove_action = menu.addAction("🗑️ Hapus Item Ini")

        edit_action.setEnabled(index.isValid())
        remove_action.setEnabled(index.isValid())

        chosen = menu.exec(view.viewport().mapToGlobal(pos))
        if chosen is None:
            return

        def count_descendants(item: JsonTreeItem) -> int:
            total = len(item.children)
            for child in item.children:
                total += count_descendants(child)
            return total

        # ---------------- CREATE ----------------
        if chosen == add_action:
            # Jika node target masih leaf (string/number/dst), menambah child
            # akan mengubahnya jadi object dan MENGHILANGKAN value lamanya.
            # Wajib konfirmasi dulu supaya user tidak kehilangan data tanpa sadar.
            if target_item.item_type not in ("object", "array"):
                current_display = "null" if target_item.value is None else repr(target_item.value)
                proceed = QMessageBox.question(
                    view,
                    "Ubah menjadi Object?",
                    f"Item '{target_item.key}' saat ini bertipe {target_item.item_type} "
                    f"dengan value {current_display}.\n\n"
                    "Menambahkan child akan mengubah item ini menjadi object dan "
                    "value lamanya akan hilang. Lanjutkan?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if proceed != QMessageBox.Yes:
                    return

            dialog = ItemEditorDialog(model, parent_item=target_item, parent=view)
            if dialog.exec() == QDialog.Accepted:
                key, item_type, value = dialog.get_values()
                try:
                    model.add_item(index, key=key, value=value, item_type=item_type)
                    view.expand(index)
                except ValueError as e:
                    QMessageBox.warning(view, "Gagal Menambah Item", str(e))

        # ---------------- MODIFY (edit) ----------------
        elif chosen == edit_action:
            parent_index = model.parent(index)
            parent_item = model._item_from_index(parent_index)

            dialog = ItemEditorDialog(
                model, parent_item=parent_item, existing_item=target_item, parent=view
            )
            if dialog.exec() == QDialog.Accepted:
                if dialog.will_lose_children():
                    n = count_descendants(target_item)
                    proceed = QMessageBox.question(
                        view,
                        "Konfirmasi Perubahan Tipe",
                        f"Item '{target_item.key}' memiliki {n} child item di dalamnya. "
                        "Mengubah tipenya akan MENGHAPUS seluruh isi tersebut secara permanen.\n\n"
                        "Lanjutkan?",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if proceed != QMessageBox.Yes:
                        return

                key, item_type, value = dialog.get_values()
                try:
                    model.update_item(index, key=key, value=value, item_type=item_type)
                except ValueError as e:
                    QMessageBox.warning(view, "Gagal Mengubah Item", str(e))

        # ---------------- DELETE ----------------
        elif chosen == remove_action:
            n = count_descendants(target_item)
            message = f"Yakin ingin menghapus item '{target_item.key}'?"
            if n > 0:
                message += f"\n\n{n} child item di dalamnya juga akan ikut terhapus."

            proceed = QMessageBox.question(
                view,
                "Konfirmasi Hapus",
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,  # default focus di "No" supaya tidak terhapus tidak sengaja
            )
            if proceed == QMessageBox.Yes:
                model.remove_item(index)        

    @Slot()
    def simpanClicked(self):
        if self.comboPart.currentText() == '' or \
           self.comboInstaller.currentText() == '':
            QMessageBox.warning(self, "Periksa input", "Nama Part dan Penginstall harus diisi")
            return;
        if self.counterBox.value() <= self.counterBox.minimum():
            QMessageBox.warning(self, "Periksa Input", "Belum menentukan counter\natau Counter sama dengan sebelumnya")
            return;
        self.dialogResult = {'part_name': self.comboPart.currentText(), 
                             'installer': self.comboInstaller.currentText(),
                             'counter':   self.counterBox.value(),
                             'install_date': self.dateEdit.date().toString("yyyy-MM-dd"),
                             'ext_info':  self.extraInfoModel.to_json(True)}
        self.accept()


class ReplacementCounterDataProxy(QSortFilterProxyModel):

    def __init__(self, parent):
        super().__init__(parent)

    def data(self, index: QModelIndex = QModelIndex(), role=Qt.DisplayRole):
        if index.isValid() and role == Qt.ItemDataRole.ToolTipRole:
            lines = [txt for txt in json_to_text_tree(index.data)]
            return "\n".join(lines)
        return super().data(index, role)


class PartReplacementCounterWidget(QWidget):
    _completionData = None

    def __init__(self, con: QSqlDatabase, parent=None):
        super().__init__(parent)
        self.setObjectName('partReplacementCounterWidget')
        self.setWindowTitle("Simpan data penggantian part")
        self._db = con
        rv = self.replacementView = QTableView(self)
        rv.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        rv.customContextMenuRequested.connect(self.replacementViewContextMenu)

        _model = self._model = QSqlTableModel(self, self._db)
        _model.setTable(TABLE_NAME)
        _model.select()

        _proxy = self._proxy = ReplacementCounterDataProxy(self)
        _proxy.setSourceModel(_model)
        rv.setModel(_proxy)
        _proxy.setHeaderData(0, Qt.Horizontal, "ID", Qt.DisplayRole)
        _proxy.setHeaderData(1, Qt.Horizontal, "Part", Qt.DisplayRole)
        _proxy.setHeaderData(2, Qt.Horizontal, "Tanggal", Qt.DisplayRole)
        _proxy.setHeaderData(3, Qt.Horizontal, "Oleh", Qt.DisplayRole)
        _proxy.setHeaderData(4, Qt.Horizontal, "Counter", Qt.DisplayRole)
        _proxy.setHeaderData(5, Qt.Horizontal, "Info", Qt.DisplayRole)

        rv.hideColumn(0)
        rv.hideColumn(5)

        self.setLayout(QHBoxLayout())
        lay = self.layout()
        lay.addWidget(rv)

        self._load_completion_data()

    @Slot()
    def _load_completion_data(self):
        cdata = {'parts': [], 'installers': []}
        def logError(x): return logger.error(x, exc_info=True)

        _DATA = [[
            f"SELECT DISTINCT part_name COLLATE NOCASE FROM {TABLE_NAME}",
            f"SELECT DISTINCT installer COLLATE NOCASE FROM {TABLE_NAME}",
            f"SELECT COALESCE(MAX(counter_fullcolor_value), 0) FROM {TABLE_NAME}"],
            ['parts', 'installers', 'lastCounter']
        ]
        q = QSqlQuery(self._db)

        for qs, key in zip(*_DATA):
            if q.exec(qs):
                while q.next():
                    if key == 'lastCounter':
                        cdata[key] = q.value(0)
                    else:
                        cdata[key].append(q.value(0))
            else:
                logError(f"Tidak dapat mengeksekusi query [{key}]")

        self._completionData = cdata

    @Slot(QPoint)
    def replacementViewContextMenu(self, point: QPoint):
        contextMenu = QMenu('context')
        add_action = contextMenu.addAction("Tambah data")
        add_action.triggered.connect(self.addData)
        contextMenu.exec(self.replacementView.viewport().mapToGlobal(point))

    @Slot()
    def addData(self):
        dialog = AddReplacementCounterDataDialog(
            self,
            lastCounter=self._completionData['lastCounter'],
            partNames=self._completionData['parts'],
            installers=self._completionData['installers'])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.dialogResult
            self._save_data(data)
    
    @Slot(object)
    def _save_data(self, data: dict):
        q = QSqlQuery(self._db)
        q.prepare(f"INSERT INTO {TABLE_NAME} ( "
                  "part_name, install_date, installer, counter_fullcolor_value, description) "
                  "VALUES (:pn, :insd, :insl, :ctr, :desc)")
        q.bindValue(":pn", data["part_name"])
        q.bindValue(":insd", data["install_date"])
        q.bindValue(":insl", data["installer"])
        q.bindValue(":ctr", data["counter"])
        q.bindValue(":desc", data["ext_info"])

        if not q.exec():
            QMessageBox.warning(self, "Gagal menambahkan data", q.lastError().text())
            return
        self._model.select()
     