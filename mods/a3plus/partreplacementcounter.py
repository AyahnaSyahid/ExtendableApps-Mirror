from __future__ import annotations
from PySide6.QtWidgets import QComboBox, QDateEdit, QFormLayout, QHBoxLayout, QMessageBox, QSpinBox, QTableView, QTreeView, QVBoxLayout, QWidget, QMenu, QDialog
from PySide6.QtSql import QSqlDatabase, QSqlTableModel, QSqlQuery
from PySide6.QtCore import QDate, Qt, Slot, QPoint, QSortFilterProxyModel
from PySide6.QtGui import QAction
from app.libs.json_tree_model_qt import JsonTreeItem, JsonTreeModel, ItemEditorDialog

import logging
logger = logging.getLogger(__name__)

TABLE_NAME = "a3_part_replacement"


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
        self.dateEdit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.counterBox = QSpinBox(
            self, minimum=0, maximum=9_999_999, singleStep=1000)
        self.counterBox.setValue(lastCounter)
        self.counterBox.setAccelerated(True)

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

        _proxy = self._proxy = QSortFilterProxyModel(self)
        _proxy.setSourceModel(_model)
        rv.setModel(_proxy)

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
        dialog.exec()
