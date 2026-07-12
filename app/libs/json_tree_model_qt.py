"""
JSON Tree Model - Python equivalent of QJsonModel
Versi ini mewarisi QAbstractItemModel sehingga bisa langsung dipasang
ke QTreeView / QTreeWidget dengan model/view Qt yang sesungguhnya.

Membutuhkan PySide6 (bisa diganti ke PyQt5/PyQt6 tinggal ganti import).
"""

import json
from typing import Any, Optional, List

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt, QPersistentModelIndex
from PySide6.QtWidgets import (
    QDialog,
    QLineEdit,
    QComboBox,
    QFormLayout,
    QDialogButtonBox,
    QVBoxLayout,
    QLabel,
    QStackedWidget,
)


class JsonTreeItem:
    """Merepresentasikan satu node di dalam tree JSON (internal pointer)"""

    __slots__ = ("key", "value", "item_type", "parent", "children")

    def __init__(
        self,
        key: str = "",
        value: Any = None,
        item_type: str = "null",
        parent: Optional["JsonTreeItem"] = None,
    ):
        self.key = key
        self.value = value
        self.item_type = item_type  # "object", "array", "string", "number", "boolean", "null"
        self.parent = parent
        self.children: List["JsonTreeItem"] = []

    def add_child(self, child: "JsonTreeItem") -> None:
        self.children.append(child)
        child.parent = self

    def child_count(self) -> int:
        return len(self.children)

    def get_child(self, row: int) -> Optional["JsonTreeItem"]:
        if 0 <= row < len(self.children):
            return self.children[row]
        return None

    def row(self) -> int:
        """Index baris relatif terhadap parent-nya"""
        if self.parent:
            return self.parent.children.index(self)
        return 0


class JsonTreeModel(QAbstractItemModel):
    """Model Qt untuk menampilkan data JSON dalam bentuk tree (2 kolom: Key / Value)"""

    def __init__(self, exceptions: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.root_item = JsonTreeItem(key="root", item_type="object")
        self.exceptions = exceptions or []
        self.quote_visible = False
        self.headers = ["Key", "Value"]

    # ------------------------------------------------------------------
    # Loading data
    # ------------------------------------------------------------------
    def load_json_file(self, filepath: str) -> bool:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self.load_json_data(data)
        except Exception as e:
            print(f"Error loading file: {e}")
            return False

    def load_json_string(self, json_string: str) -> bool:
        try:
            data = json.loads(json_string)
            return self.load_json_data(data)
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return False

    def load_json_data(self, data: Any) -> bool:
        """Membangun ulang seluruh tree. Membungkusnya dengan beginResetModel/
        endResetModel supaya semua view yang terpasang ikut ter-refresh."""
        self.beginResetModel()
        self.root_item = self._load_recursive(data, None)
        self.root_item.key = "root"
        self.endResetModel()
        return True

    def _load_recursive(self, value: Any, parent: Optional[JsonTreeItem]) -> JsonTreeItem:
        item = JsonTreeItem(parent=parent)

        if isinstance(value, dict):
            item.item_type = "object"
            for key, val in value.items():
                if not self._is_exception(key):
                    child = self._load_recursive(val, item)
                    child.key = key
                    item.add_child(child)

        elif isinstance(value, list):
            item.item_type = "array"
            for idx, val in enumerate(value):
                child = self._load_recursive(val, item)
                child.key = str(idx)
                item.add_child(child)

        elif isinstance(value, bool):
            item.item_type = "boolean"
            item.value = value

        elif isinstance(value, (int, float)):
            item.item_type = "number"
            item.value = value

        elif isinstance(value, str):
            item.item_type = "string"
            item.value = value

        else:
            item.item_type = "null"
            item.value = None

        return item

    def _is_exception(self, key: str) -> bool:
        return any(exc.lower() in key.lower() for exc in self.exceptions)

    def add_exceptions(self, exceptions: List[str]) -> None:
        self.exceptions = exceptions

    def set_quote_visible(self, visible: bool) -> None:
        self.beginResetModel()
        self.quote_visible = visible
        self.endResetModel()

    # ------------------------------------------------------------------
    # Wajib diimplementasikan: kerangka QAbstractItemModel
    # ------------------------------------------------------------------
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_item = self._item_from_index(parent)
        child_item = parent_item.get_child(row)

        if child_item is not None:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        child_item: JsonTreeItem = index.internalPointer()
        parent_item = child_item.parent

        if parent_item is None or parent_item is self.root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        parent_item = self._item_from_index(parent)
        return parent_item.child_count()

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        item: JsonTreeItem = index.internalPointer()

        if role in (Qt.DisplayRole, Qt.EditRole):
            if index.column() == 0:
                return item.key
            elif index.column() == 1:
                return self._display_value(item)

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False

        item: JsonTreeItem = index.internalPointer()

        if index.column() == 0:
            item.key = str(value)
        elif index.column() == 1:
            item.value = self._coerce_value(item.item_type, value)
        else:
            return False

        self.dataChanged.emit(index, index, [role])
        return True

    def insertRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        """Menyisipkan `count` baris baru (item null) sebelum `row`, dibawah `parent`."""
        parent_item = self._item_from_index(parent)

        if row < 0 or row > parent_item.child_count():
            return False

        self.beginInsertRows(parent, row, row + count - 1)
        for i in range(count):
            new_item = JsonTreeItem(item_type="null", value=None)
            if parent_item.item_type == "array":
                new_item.key = str(row + i)  # sementara, akan direnumber di bawah
            else:
                new_item.key = "new_key"
            new_item.parent = parent_item
            parent_item.children.insert(row + i, new_item)
        if parent_item.item_type == "array":
            self._renumber_array_keys(parent_item)
        self.endInsertRows()
        return True

    def removeRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        """Menghapus `count` baris mulai dari `row`, dibawah `parent`."""
        parent_item = self._item_from_index(parent)

        if row < 0 or row + count > parent_item.child_count():
            return False

        self.beginRemoveRows(parent, row, row + count - 1)
        del parent_item.children[row:row + count]
        if parent_item.item_type == "array":
            self._renumber_array_keys(parent_item)
        self.endRemoveRows()
        return True

    def _renumber_array_keys(self, array_item: "JsonTreeItem") -> None:
        """Menjaga agar key anak-anak sebuah array selalu berupa index 0..n-1."""
        for idx, child in enumerate(array_item.children):
            child.key = str(idx)

    # ------------------------------------------------------------------
    # Convenience API untuk menambah / menghapus data
    # ------------------------------------------------------------------
    def add_item(
        self,
        parent_index: QModelIndex = QModelIndex(),
        key: str = "new_key",
        value: Any = None,
        item_type: str = "null",
        row: Optional[int] = None,
    ) -> QModelIndex:
        """Menambahkan satu item baru di bawah `parent_index`.

        - Jika parent bertipe "array", `key` diabaikan (akan di-renumber otomatis).
        - Jika parent bertipe "object", `key` dipakai apa adanya (pastikan unik bila perlu).
        - `item_type` boleh "string" / "number" / "boolean" / "null" / "object" / "array".
        - Mengembalikan QModelIndex dari item yang baru dibuat.
        """
        parent_item = self._item_from_index(parent_index)
        key = key.strip() if isinstance(key, str) else key

        # Validasi ketat: key wajib untuk parent object, dan harus unik.
        if parent_item.item_type == "object":
            if not key:
                raise ValueError("Key tidak boleh kosong untuk item di dalam object")
            if self.key_exists(parent_item, key):
                raise ValueError(f"Key '{key}' sudah digunakan di level ini")

        if item_type not in ("object", "array", "string", "number", "boolean", "null"):
            raise ValueError(f"item_type '{item_type}' tidak dikenal")

        # Node leaf (string/number/boolean/null) otomatis "naik pangkat" jadi
        # object saat pertama kali diberi anak, supaya to_json() tetap valid.
        # (Pemanggil/UI sebaiknya sudah meminta konfirmasi ke user sebelum ini.)
        if parent_item.item_type not in ("object", "array"):
            parent_item.item_type = "object"
            parent_item.value = None

        insert_row = parent_item.child_count() if row is None else row
        insert_row = max(0, min(insert_row, parent_item.child_count()))

        self.beginInsertRows(parent_index, insert_row, insert_row)
        new_item = JsonTreeItem(
            key=str(insert_row) if parent_item.item_type == "array" else key,
            value=value,
            item_type=item_type,
            parent=parent_item,
        )
        parent_item.children.insert(insert_row, new_item)
        if parent_item.item_type == "array":
            self._renumber_array_keys(parent_item)
        self.endInsertRows()

        return self.index(insert_row, 0, parent_index)

    def remove_item(self, index: QModelIndex) -> bool:
        """Menghapus item pada `index` beserta seluruh sub-treenya."""
        if not index.isValid():
            return False
        return self.removeRow(index.row(), self.parent(index))

    def key_exists(
        self,
        parent_item: "JsonTreeItem",
        key: str,
        exclude_item: Optional["JsonTreeItem"] = None,
    ) -> bool:
        """Cek apakah `key` sudah dipakai oleh sibling lain di bawah `parent_item`.
        Tidak relevan untuk parent bertipe array (key selalu berupa index)."""
        if parent_item.item_type != "object":
            return False
        return any(
            child.key == key for child in parent_item.children if child is not exclude_item
        )

    def update_item(
        self,
        index: QModelIndex,
        key: str,
        value: Any,
        item_type: str,
    ) -> bool:
        """Mengubah key/value/tipe dari item yang SUDAH ADA pada `index`.

        - Jika tipe berubah dari container (object/array) yang punya children menuju
          tipe leaf, seluruh children akan dihapus (UI wajib konfirmasi ke user dulu
          sebelum memanggil method ini).
        - Key hanya diterapkan jika parent bukan array dan lolos validasi unik.
        - Melempar ValueError bila validasi gagal, supaya UI bisa menampilkan pesan.
        """
        if not index.isValid():
            return False

        item: JsonTreeItem = index.internalPointer()
        parent_item = item.parent or self.root_item
        key = key.strip() if isinstance(key, str) else key

        if item_type not in ("object", "array", "string", "number", "boolean", "null"):
            raise ValueError(f"item_type '{item_type}' tidak dikenal")

        if parent_item.item_type == "object":
            if not key:
                raise ValueError("Key tidak boleh kosong untuk item di dalam object")
            if self.key_exists(parent_item, key, exclude_item=item):
                raise ValueError(f"Key '{key}' sudah digunakan di level ini")

        parent_index = self.parent(index)
        was_container = item.item_type in ("object", "array")
        becomes_leaf = item_type not in ("object", "array")

        if was_container and becomes_leaf and item.children:
            self.beginRemoveRows(index, 0, len(item.children) - 1)
            item.children.clear()
            self.endRemoveRows()

        item.item_type = item_type
        item.value = None if item_type in ("object", "array") else value

        if parent_item.item_type != "array":
            item.key = key

        top_left = self.index(index.row(), 0, parent_index)
        bottom_right = self.index(index.row(), self.columnCount() - 1, parent_index)
        self.dataChanged.emit(top_left, bottom_right)
        return True

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags

        # Semua perubahan (create/modify/delete) diarahkan lewat dialog + context
        # menu yang tervalidasi, bukan inline edit bebas, supaya key/tipe/value
        # tidak pernah masuk dalam kondisi yang melanggar aturan JSON.
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.headers):
                return self.headers[section]
        return None

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _item_from_index(self, index: QModelIndex) -> JsonTreeItem:
        if index.isValid():
            return index.internalPointer()
        return self.root_item

    def _display_value(self, item: JsonTreeItem) -> Any:
        if item.item_type in ("object", "array"):
            return ""
        if self.quote_visible and item.item_type == "string":
            return f'"{item.value}"'
        return item.value if item.value is not None else ""

    @staticmethod
    def _coerce_value(item_type: str, raw: Any) -> Any:
        """Mengonversi input teks dari editor kembali ke tipe Python yang sesuai."""
        try:
            if item_type == "number":
                text = str(raw)
                return float(text) if ("." in text or "e" in text.lower()) else int(text)
            if item_type == "boolean":
                if isinstance(raw, bool):
                    return raw
                return str(raw).strip().lower() in ("true", "1", "yes")
            if item_type == "null":
                return None
            return raw
        except (ValueError, TypeError):
            return raw

    # ------------------------------------------------------------------
    # Ekspor kembali ke JSON
    # ------------------------------------------------------------------
    def to_json(self, compact: bool = False) -> str:
        data = self._tree_to_json(self.root_item)
        if compact:
            return json.dumps(data, separators=(",", ":"))
        return json.dumps(data, indent=4)

    def _tree_to_json(self, item: JsonTreeItem) -> Any:
        if item.item_type == "object":
            return {child.key: self._tree_to_json(child) for child in item.children}
        elif item.item_type == "array":
            return [self._tree_to_json(child) for child in item.children]
        else:
            return item.value

    def get_root(self) -> JsonTreeItem:
        return self.root_item


# ----------------------------------------------------------------------
# Contoh penggunaan dengan QTreeView
# ----------------------------------------------------------------------
class ItemEditorDialog(QDialog):
    """Dialog terpadu untuk MENAMBAH item baru atau MENGEDIT item yang sudah ada.

    Semua aturan penulisan JSON divalidasi secara real-time di sini:
    - Key wajib diisi & tidak boleh duplikat dalam object yang sama (key
      diabaikan/dinonaktifkan untuk parent array karena selalu berupa index).
    - Value untuk tipe "number" wajib berupa angka valid.
    - Value untuk tipe "boolean" dipilih dari dropdown true/false (tidak mungkin salah ketik).
    - Tipe "null"/"object"/"array" tidak punya input value sama sekali.
    - Tombol OK otomatis nonaktif selama ada input yang belum valid.
    """

    ITEM_TYPES = ["string", "number", "boolean", "null", "object", "array"]

    def __init__(
        self,
        model: "JsonTreeModel",
        parent_item: "JsonTreeItem",
        existing_item: Optional["JsonTreeItem"] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.model = model
        self.parent_item = parent_item
        self.existing_item = existing_item
        self.is_array_parent = parent_item.item_type == "array"
        self.edit_mode = existing_item is not None

        self.setWindowTitle("Edit Item" if self.edit_mode else "Tambah Item Baru")
        self.setMinimumWidth(340)

        # --- Key ---
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("nama_key")
        if self.is_array_parent:
            self.key_edit.setDisabled(True)
            self.key_edit.setPlaceholderText("(index otomatis untuk array)")

        # --- Tipe ---
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.ITEM_TYPES)

        # --- Value: 3 halaman berbeda sesuai tipe, supaya input tidak mungkin invalid ---
        self.value_text = QLineEdit()
        self.value_bool = QComboBox()
        self.value_bool.addItems(["true", "false"])
        self.value_empty_label = QLabel("(tidak ada value untuk tipe ini)")
        self.value_empty_label.setStyleSheet("color: gray; font-style: italic;")

        self.value_stack = QStackedWidget()
        self.value_stack.addWidget(self.value_text)    # index 0: string/number
        self.value_stack.addWidget(self.value_bool)     # index 1: boolean
        self.value_stack.addWidget(self.value_empty_label)  # index 2: null/object/array

        # --- Pesan error ---
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #c0392b;")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)

        form = QFormLayout()
        form.addRow("Key:", self.key_edit)
        form.addRow("Tipe:", self.type_combo)
        form.addRow("Value:", self.value_stack)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

        # Sinyal validasi real-time
        self.key_edit.textChanged.connect(self._validate)
        self.value_text.textChanged.connect(self._validate)
        self.value_bool.currentTextChanged.connect(self._validate)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        if self.edit_mode:
            self._prefill(existing_item)
        else:
            self._on_type_changed(self.type_combo.currentText())

    # -- Pengisian awal saat mode edit --------------------------------
    def _prefill(self, item: "JsonTreeItem") -> None:
        self.key_edit.setText(item.key)
        self.type_combo.setCurrentText(item.item_type)
        self._on_type_changed(item.item_type)

        if item.item_type == "boolean":
            self.value_bool.setCurrentText("true" if item.value else "false")
        elif item.item_type not in ("object", "array", "null"):
            self.value_text.setText("" if item.value is None else str(item.value))

    # -- Tampilan value mengikuti tipe yang dipilih -------------------
    def _on_type_changed(self, item_type: str) -> None:
        if item_type == "boolean":
            self.value_stack.setCurrentWidget(self.value_bool)
        elif item_type in ("null", "object", "array"):
            self.value_stack.setCurrentWidget(self.value_empty_label)
        else:
            self.value_stack.setCurrentWidget(self.value_text)
            self.value_text.setPlaceholderText(
                "contoh: 42 atau 3.14" if item_type == "number" else "Masukkan teks"
            )
        self._validate()

    # -- Validasi ketat sebelum mengizinkan OK -------------------------
    def _validate(self) -> None:
        errors = []
        item_type = self.type_combo.currentText()
        key = self.key_edit.text().strip()

        if not self.is_array_parent:
            if not key:
                errors.append("Key tidak boleh kosong.")
            elif self.model.key_exists(self.parent_item, key, exclude_item=self.existing_item):
                errors.append(f"Key '{key}' sudah dipakai di level ini.")

        if item_type == "number":
            text = self.value_text.text().strip()
            if not text:
                errors.append("Value angka wajib diisi.")
            else:
                try:
                    float(text)
                except ValueError:
                    errors.append("Value harus berupa angka yang valid.")

        # Peringatan (bukan error blocking) saat mengubah container berisi
        # children menjadi leaf: OK tetap diizinkan, tapi caller yang akan
        # menampilkan konfirmasi kehilangan data sebelum benar-benar diterapkan.

        ok_button = self.buttons.button(QDialogButtonBox.Ok)
        if errors:
            self.error_label.setText("⚠ " + "  |  ".join(errors))
            self.error_label.setVisible(True)
            ok_button.setEnabled(False)
        else:
            self.error_label.setVisible(False)
            ok_button.setEnabled(True)

    def will_lose_children(self) -> bool:
        """True jika perubahan ini akan menghapus children dari item yang sudah ada."""
        if not self.edit_mode:
            return False
        item_type = self.type_combo.currentText()
        return (
            self.existing_item.item_type in ("object", "array")
            and item_type not in ("object", "array")
            and len(self.existing_item.children) > 0
        )

    def get_values(self):
        """Mengembalikan (key, item_type, value) yang sudah tervalidasi."""
        item_type = self.type_combo.currentText()
        key = self.key_edit.text().strip()

        if item_type == "boolean":
            value = self.value_bool.currentText() == "true"
        elif item_type in ("null", "object", "array"):
            value = None
        elif item_type == "number":
            value = JsonTreeModel._coerce_value("number", self.value_text.text().strip())
        else:  # string
            value = self.value_text.text()

        return key, item_type, value


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import (
        QApplication,
        QTreeView,
        QMainWindow,
        QWidget,
        QHBoxLayout,
        QPushButton,
        QMenu,
        QMessageBox,
    )
    from PySide6.QtCore import Qt as QtNS

    app = QApplication(sys.argv)

    json_data = """
    {
        "name": "John",
        "age": 30,
        "active": true,
        "hobbies": ["reading", "coding"],
        "address": {
            "city": "New York",
            "zip": "10001"
        }
    }
    """

    model = JsonTreeModel()
    model.load_json_string(json_data)

    view = QTreeView()
    view.setModel(model)
    view.expandAll()
    view.resizeColumnToContents(0)
    view.setContextMenuPolicy(QtNS.CustomContextMenu)

    def count_descendants(item: JsonTreeItem) -> int:
        total = len(item.children)
        for child in item.children:
            total += count_descendants(child)
        return total

    def show_context_menu(pos):
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

    view.customContextMenuRequested.connect(show_context_menu)

    def on_print_json():
        print(model.to_json())

    btn_print = QPushButton("Cetak JSON")
    btn_print.clicked.connect(on_print_json)

    button_row = QHBoxLayout()
    button_row.addWidget(btn_print)

    layout = QVBoxLayout()
    layout.addLayout(button_row)
    layout.addWidget(view)

    central = QWidget()
    central.setLayout(layout)

    window = QMainWindow()
    window.setCentralWidget(central)
    window.resize(550, 450)
    window.setWindowTitle("JSON Tree Model - Klik kanan untuk Tambah/Hapus")
    window.show()

    sys.exit(app.exec())
