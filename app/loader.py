"""
Mod Loader — scan folder mods/, baca mod.json, jalankan setup(api).
"""
import importlib
import json
import sys
from pathlib import Path
from app.api import PluginAPI


def load_all_mods(mods_dir: str | Path, api: PluginAPI):
    mods_dir = Path(mods_dir)
    data_dir = mods_dir.parent / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    loaded = []
    errors = []

    for mod_folder in sorted(mods_dir.iterdir()):
        if not mod_folder.is_dir():
            continue

        manifest_path = mod_folder / "mod.json"
        if not manifest_path.exists():
            continue  # bukan mod yang valid

        # Baca metadata
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mod_id = manifest.get("id", mod_folder.name)
        mod_name = manifest.get("name", mod_id)

        try:
            # Tambah folder mod ke sys.path agar bisa import relatif
            if str(mod_folder.parent) not in sys.path:
                sys.path.insert(0, str(mod_folder.parent))

            module = importlib.import_module(mod_folder.name)

            if not hasattr(module, "setup"):
                raise AttributeError(f"Mod '{mod_id}' tidak punya fungsi setup(api)")

            api.set_current_mod(mod_id)
            module.setup(api)
            api.set_current_mod("")
            loaded.append(mod_name)
            print(f"[ModLoader] ✓ {mod_name} ({mod_id})")
            api.register_handler(mod_name, module)
            
        except Exception as e:
            import traceback
            errors.append((mod_name, str(e)))
            print(f"[ModLoader] ✗ {mod_name}: {e}")
            traceback.print_exc()
    
    return loaded, errors
