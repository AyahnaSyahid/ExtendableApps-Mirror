# ExtendableApps

Kerangka aplikasi desktop berbasis Python yang dirancang untuk **mudah dikembangkan lewat sistem plugin (mod)**. Inti aplikasi dijaga tetap kecil — semua fitur ditambahkan sebagai modul terpisah yang dimuat otomatis saat aplikasi berjalan, tanpa perlu mengubah kode inti sama sekali.

Dibangun dengan [PySide6](https://doc.qt.io/qtforpython/) (Qt for Python) sebagai UI toolkit dan SQLite (via `QtSql`) sebagai penyimpanan data per-modul.

## Fitur Utama

- **Arsitektur mod/plugin** — setiap fitur adalah folder mandiri di dalam `mods/`, dikenali lewat manifest `mod.json`, dan dimuat otomatis tanpa perlu didaftarkan manual di kode inti.
- **Isolasi kegagalan** — jika satu mod gagal dimuat, mod lain tetap berjalan normal; error dicatat ke log, bukan menghentikan aplikasi.
- **Plugin API terpusat** (`app/api.py`) — satu-satunya jalur resmi bagi mod untuk berinteraksi dengan jendela utama:
  - `add_tab()` — menambahkan tab baru
  - `add_dock()` — menambahkan panel dockable beserta toggle action di menu
  - `add_menu_action()` — menambahkan item menu, mendukung submenu bertingkat (`"File/Export/PDF"`)
  - `on_event()` / `emit_event()` — komunikasi antar-mod berbasis event, tanpa saling bergantung langsung
  - `sendLog()` — mengirim log ke konsol bawaan aplikasi
- **Database otomatis per mod** (`app/services/database.py`):
  - Satu file SQLite per mod, disimpan otomatis di folder `data/`
  - Sistem migrasi skema dengan pelacakan versi (tabel `meta`), migrasi hanya dijalankan sekali
  - Koneksi *thread-safe* — mod yang butuh akses database dari thread lain otomatis mendapat koneksi baru yang menunjuk ke file fisik yang sama
  - Mode `WAL` aktif secara default agar baca/tulis bisa berjalan bersamaan
- **Konsol log bawaan** — tampilan mirip terminal (hitam-hijau) di tab Home untuk memantau aktivitas semua mod secara real-time.
- **Locale Indonesia** sebagai default aplikasi.

## Struktur Proyek

```
ExtendableApps/
├── main.py                  # Entry point (python main.py)
├── app/
│   ├── app.py                # Jendela utama (MainWindow) & bootstrap aplikasi
│   ├── api.py                 # PluginAPI — kontrak resmi antara core dan mod
│   ├── loader.py               # Mod loader — scan & jalankan setup(api) tiap mod
│   └── services/
│       └── database.py          # DatabaseService — manajemen koneksi & migrasi SQLite per mod
└── mods/
    ├── a3plus/                 # Toner counter & pencatatan penggantian part
    ├── absensi_personal/        # Pencatat absensi harian pribadi
    ├── order_notes/              # Pencatat order klien & percetakan
    └── corelautomation/           # Integrasi automasi CorelDraw (Windows, via win32com)
```

## Instalasi

Prasyarat: Python 3.10+ dan PySide6.

```bash
git clone https://github.com/AyahnaSyahid/ExtendableApps-Mirror.git
cd ExtendableApps-Mirror
pip install PySide6
python main.py
```

> Catatan: mod `corelautomation` opsional dan hanya aktif penuh di Windows dengan CorelDraw + `pywin32` terpasang. Di platform lain, mod ini tetap dimuat tapi fitur automasinya akan menampilkan peringatan modul tidak ditemukan.

## Membuat Mod Baru

Setiap mod minimal terdiri dari dua file:

```
mods/nama_mod_anda/
├── mod.json          # Metadata: id, name, version, author, description
└── __init__.py        # Wajib punya fungsi setup(api: PluginAPI)
```

Contoh `mod.json`:

```json
{
    "id": "mod_saya",
    "name": "Mod Contoh",
    "version": "1.0.0",
    "author": "Nama Anda",
    "description": "Deskripsi singkat mod ini"
}
```

Contoh `__init__.py` minimal dengan database:

```python
from app.api import PluginAPI
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtWidgets import QLabel

def _migrate_v1(con: QSqlDatabase) -> bool:
    q = QSqlQuery(con)
    return q.exec("CREATE TABLE IF NOT EXISTS data (id INTEGER PRIMARY KEY, value TEXT)")

def setup(api: PluginAPI):
    con = api.init_database([_migrate_v1], schema_version=1)
    api.add_tab(QLabel("Halo dari mod saya!"), "Mod Saya")
```

Simpan folder tersebut di dalam `mods/`, jalankan ulang aplikasi — mod akan otomatis terdeteksi dan dimuat oleh `loader.py`.

## Lisensi

Proyek ini dirilis di bawah lisensi **[GNU General Public License v3.0](LICENSE)**.

Ini berarti:

- Bebas digunakan, dimodifikasi, dan didistribusikan ulang, termasuk untuk keperluan komersial.
- Jika kamu mendistribusikan versi modifikasi, source code-nya wajib tetap dibuka dengan lisensi yang sama (GPL-3.0).
- Notice hak cipta & lisensi asli wajib dipertahankan di setiap salinan/turunan.
- Tidak ada jaminan (warranty) apa pun atas perangkat lunak ini.

Lihat file [`LICENSE`](LICENSE) untuk teks lengkapnya.
